"""The history of calls to AI providers, and how many tokens they used.

Every call is recorded with what it was for, which connection and model answered, and the tokens
the provider counted. The text of the prompt and the answer is kept only when the user turns that
on in Settings. Old entries are removed after a number of days (90 by default).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Select, delete, func, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from kodalo.core.settings.ai.errors import AiInvalidError, AiNotFoundError
from kodalo.core.storage import Database, StorageError, database_path
from kodalo.core.storage.models import AiCall, Setting

PURPOSES = ("palette", "studio", "connection_test")
PERIODS = ("day", "week", "month", "year", "all", "custom")
DEFAULT_RETENTION_DAYS = 90
MAX_RETENTION_DAYS = 3650
MAX_PAGE = 200
MAX_OFFSET = 10_000_000
DEFAULT_PAGE = 50
MAX_TEXT = 200_000

GROUP = "ai"
STORE_TEXT_KEY = "history_store_text"
RETENTION_KEY = "history_retention_days"
_PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


@dataclass(frozen=True)
class AiHistorySettings:
    """Whether the text of calls is kept, and after how many days entries are removed.

    ``retention_days`` of 0 keeps entries until they are purged by hand."""

    store_text: bool = False
    retention_days: int = DEFAULT_RETENTION_DAYS


@dataclass(frozen=True)
class Period:
    """A time window in UTC. ``start`` is included and ``end`` is excluded; ``None`` is open."""

    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class AiCallRecord:
    """One call, without its text."""

    id: str
    created_at: str
    title: str
    purpose: str
    provider: str
    model: str
    status: str
    error: str
    input_tokens: int
    output_tokens: int
    has_text: bool


@dataclass(frozen=True)
class AiCallDetail:
    """One call with its text. The text is ``None`` when it was not kept."""

    record: AiCallRecord
    prompt_text: str | None
    reply_text: str | None


@dataclass(frozen=True)
class HistoryPage:
    """A page of calls, newest first, and how many calls match in all."""

    total: int
    items: tuple[AiCallRecord, ...]


@dataclass(frozen=True)
class UsageRow:
    """Calls and tokens for one connection and model."""

    provider: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class DayUsage:
    """Tokens used on one UTC day."""

    day: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Usage:
    """Tokens used in a period, per connection and model and per day."""

    rows: tuple[UsageRow, ...]
    days: tuple[DayUsage, ...]

    @property
    def calls(self) -> int:
        return sum(row.calls for row in self.rows)

    @property
    def input_tokens(self) -> int:
        return sum(row.input_tokens for row in self.rows)

    @property
    def output_tokens(self) -> int:
        return sum(row.output_tokens for row in self.rows)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _day_start(text: str, label: str) -> datetime:
    try:
        return datetime.combine(date.fromisoformat(text), datetime.min.time(), tzinfo=UTC)
    except ValueError as exc:
        raise AiInvalidError(f"{label} must be a date like 2026-11-04.") from exc


def resolve_period(
    name: str = "all",
    start: str | None = None,
    end: str | None = None,
    now: datetime | None = None,
) -> Period:
    """Turn a period name into a window. ``custom`` needs ``start`` and/or ``end`` as dates, and
    includes both days. ``day``, ``week``, ``month`` and ``year`` end now and reach back 1, 7, 30
    and 365 days."""
    if name not in PERIODS:
        raise AiInvalidError(f"Unknown period: {name}. Use one of: {', '.join(PERIODS)}.")
    if name == "all":
        return Period()
    if name == "custom":
        first = _day_start(start, "The start") if start else None
        last = _day_start(end, "The end") + timedelta(days=1) if end else None
        if first is not None and last is not None and first >= last:
            raise AiInvalidError("The start must not be after the end.")
        if first is None and last is None:
            raise AiInvalidError("A custom period needs a start, an end or both.")
        return Period(_stamp(first) if first else None, _stamp(last) if last else None)
    moment = now or datetime.now(UTC)
    return Period(_stamp(moment - timedelta(days=_PERIOD_DAYS[name])), None)


def _within(query: Any, period: Period) -> Any:
    if period.start is not None:
        query = query.where(AiCall.created_at >= period.start)
    if period.end is not None:
        query = query.where(AiCall.created_at < period.end)
    return query


def _record(row: AiCall) -> AiCallRecord:
    return AiCallRecord(
        id=row.id,
        created_at=row.created_at,
        title=row.title,
        purpose=row.purpose,
        provider=row.provider,
        model=row.model,
        status=row.status,
        error=row.error,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        has_text=row.prompt_text is not None or row.reply_text is not None,
    )


class AiHistory:
    """The recorded calls and the two settings that govern them, in the local database."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # -- settings --------------------------------------------------------------------------------

    @staticmethod
    def _setting(key: str) -> Select[Setting]:
        return select(Setting).where(
            Setting.scope == "global",
            Setting.owner_id == "",
            Setting.group_name == GROUP,
            Setting.key == key,
        )

    def settings(self) -> AiHistorySettings:
        """Return the saved settings, or the defaults (no text, 90 days)."""
        with self._database.session() as session:
            return self._settings(session)

    def _settings(self, session: Session) -> AiHistorySettings:
        text = session.scalars(self._setting(STORE_TEXT_KEY)).first()
        days = session.scalars(self._setting(RETENTION_KEY)).first()
        retention = DEFAULT_RETENTION_DAYS
        if days is not None and days.data_type == "integer":
            try:
                retention = int(days.value)
            except ValueError:
                retention = DEFAULT_RETENTION_DAYS
        return AiHistorySettings(
            store_text=text is not None and text.value == "true", retention_days=retention
        )

    def save_settings(
        self, store_text: bool | None = None, retention_days: int | None = None
    ) -> AiHistorySettings:
        """Change the settings. ``None`` keeps a saved value."""
        if retention_days is not None and not 0 <= retention_days <= MAX_RETENTION_DAYS:
            raise AiInvalidError(
                f"Keep history for 0 to {MAX_RETENTION_DAYS} days (0 never removes it)."
            )
        with self._database.session() as session:
            if store_text is not None:
                self._store(session, STORE_TEXT_KEY, "true" if store_text else "false", "boolean")
            if retention_days is not None:
                self._store(session, RETENTION_KEY, str(retention_days), "integer")
            session.flush()
            return self._settings(session)

    def _store(self, session: Session, key: str, value: str, data_type: str) -> None:
        row = session.scalars(self._setting(key)).first()
        if row is None:
            row = Setting(scope="global", owner_id="", group_name=GROUP, key=key, mode="own")
            session.add(row)
        row.value = value
        row.data_type = data_type

    # -- recording -------------------------------------------------------------------------------

    def record(
        self,
        *,
        title: str,
        purpose: str,
        provider: str,
        model: str,
        status: str,
        error: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        prompt: str | None = None,
        reply: str | None = None,
        at: str | None = None,
    ) -> None:
        """Add one call. The prompt and reply are kept only when the settings allow it."""
        with self._database.session() as session:
            keep = self._settings(session).store_text
            row = AiCall(
                title=title[:128],
                purpose=purpose,
                provider=provider,
                model=model[:128],
                status=status,
                error=error[:256],
                input_tokens=max(input_tokens, 0),
                output_tokens=max(output_tokens, 0),
                prompt_text=prompt[:MAX_TEXT] if keep and prompt is not None else None,
                reply_text=reply[:MAX_TEXT] if keep and reply is not None else None,
            )
            if at is not None:
                row.created_at = at
            session.add(row)

    # -- reading ---------------------------------------------------------------------------------

    def list(
        self, period: Period | None = None, limit: int = DEFAULT_PAGE, offset: int = 0
    ) -> HistoryPage:
        """Return one page of calls in the period, newest first."""
        if not 1 <= limit <= MAX_PAGE or not 0 <= offset <= MAX_OFFSET:
            raise AiInvalidError(
                f"limit must be from 1 to {MAX_PAGE} and offset from 0 to {MAX_OFFSET}."
            )
        window = period or Period()
        with self._database.session() as session:
            total = session.scalar(_within(select(func.count()).select_from(AiCall), window))
            rows = session.scalars(
                _within(select(AiCall), window)
                .order_by(AiCall.created_at.desc(), AiCall.id)
                .limit(limit)
                .offset(offset)
            )
            return HistoryPage(total or 0, tuple(_record(row) for row in rows))

    def get(self, call_id: str) -> AiCallDetail:
        """Return one call with its text. Raises ``AiNotFoundError``."""
        with self._database.session() as session:
            row = session.get(AiCall, call_id)
            if row is None:
                raise AiNotFoundError("There is no such entry in the history.")
            return AiCallDetail(_record(row), row.prompt_text, row.reply_text)

    def usage(self, period: Period | None = None) -> Usage:
        """Return the calls and tokens in the period per connection and model and per day."""
        window = period or Period()
        day = func.substr(AiCall.created_at, 1, 10)
        with self._database.session() as session:
            by_model = _within(
                select(
                    AiCall.provider,
                    AiCall.model,
                    func.count(),
                    func.sum(AiCall.input_tokens),
                    func.sum(AiCall.output_tokens),
                ),
                window,
            ).group_by(AiCall.provider, AiCall.model)
            per_day = _within(
                select(day, func.sum(AiCall.input_tokens), func.sum(AiCall.output_tokens)),
                window,
            ).group_by(day)
            return Usage(
                rows=tuple(
                    UsageRow(provider, model, calls, tokens_in or 0, tokens_out or 0)
                    for provider, model, calls, tokens_in, tokens_out in sorted(
                        session.execute(by_model).all()
                    )
                ),
                days=tuple(
                    DayUsage(label, tokens_in or 0, tokens_out or 0)
                    for label, tokens_in, tokens_out in sorted(session.execute(per_day).all())
                ),
            )

    # -- removing --------------------------------------------------------------------------------

    def purge_all(self) -> int:
        """Remove every entry. Return how many were removed."""
        with self._database.session() as session:
            return cast(CursorResult[Any], session.execute(delete(AiCall))).rowcount

    def purge_expired(self, now: datetime | None = None) -> int:
        """Remove entries older than the retention setting. Return how many were removed."""
        with self._database.session() as session:
            days = self._settings(session).retention_days
            if days == 0:
                return 0
            cutoff = _stamp((now or datetime.now(UTC)) - timedelta(days=days))
            result = session.execute(delete(AiCall).where(AiCall.created_at < cutoff))
            return cast(CursorResult[Any], result).rowcount


def purge_expired_history(data_dir: Path) -> int:
    """Remove old history from the database in ``data_dir``, if there is one. Used when the
    command line, the window or the API starts, so it never fails and never creates a database."""
    path = database_path(data_dir)
    if not path.is_file():
        return 0
    try:
        database = Database.open(path)
    except (StorageError, OSError):
        return 0
    try:
        return AiHistory(database).purge_expired()
    except Exception:  # a failed cleanup must never stop the program from starting
        return 0
    finally:
        database.close()
