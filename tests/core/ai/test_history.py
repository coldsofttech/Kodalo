"""The AI history: what is recorded, the text switch, filters, usage and purging."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from kodalo.core.ai import (
    AiConnectionError,
    AiConnections,
    AiHistory,
    AiInvalidError,
    AiNotFoundError,
    GenerateRequest,
    Generation,
    Probe,
    purge_expired_history,
    resolve_period,
)
from kodalo.core.storage import Database, database_path

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


class _Secrets:
    def get(self, ref: str) -> str | None:
        return "sk-test-1234567890abcdef"

    def set(self, ref: str, value: str) -> None:
        return None

    def delete(self, ref: str) -> None:
        return None


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path))
    yield db
    db.close()


def _stamp(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat(timespec="seconds")


def _add(history: AiHistory, days_ago: float, model: str = "m1", tokens: int = 10) -> None:
    history.record(
        title="t",
        purpose="palette",
        provider="claude_api",
        model=model,
        status="ok",
        input_tokens=tokens,
        output_tokens=tokens * 2,
        at=_stamp(days_ago),
    )


def test_defaults_and_settings_validation(database: Database) -> None:
    history = AiHistory(database)
    assert (history.settings().store_text, history.settings().retention_days) == (False, 90)
    saved = history.save_settings(store_text=True, retention_days=30)
    assert (saved.store_text, saved.retention_days) == (True, 30)
    assert history.save_settings(retention_days=0).retention_days == 0
    assert history.settings().store_text is True
    with pytest.raises(AiInvalidError):
        history.save_settings(retention_days=-1)


def test_text_is_kept_only_when_allowed(database: Database) -> None:
    history = AiHistory(database)
    history.record(
        title="a",
        purpose="studio",
        provider="claude_api",
        model="m",
        status="ok",
        prompt="p",
        reply="r",
    )
    first = history.list().items[0]
    assert first.has_text is False
    assert history.get(first.id).prompt_text is None
    history.save_settings(store_text=True)
    history.record(
        title="b",
        purpose="studio",
        provider="claude_api",
        model="m",
        status="ok",
        prompt="p",
        reply="r",
    )
    kept = next(i for i in history.list().items if i.title == "b")
    detail = history.get(kept.id)
    assert (detail.prompt_text, detail.reply_text) == ("p", "r")
    with pytest.raises(AiNotFoundError):
        history.get("missing")


def test_periods() -> None:
    assert resolve_period("all").start is None
    week = resolve_period("week", now=NOW)
    assert week.start == _stamp(7)
    assert week.end is None
    custom = resolve_period("custom", "2026-11-01", "2026-11-03")
    assert custom.start == "2026-11-01T00:00:00+00:00"
    assert custom.end == "2026-11-04T00:00:00+00:00"
    for bad in (("bogus", None, None), ("custom", None, None), ("custom", "x", None)):
        with pytest.raises(AiInvalidError):
            resolve_period(*bad)
    with pytest.raises(AiInvalidError):
        resolve_period("custom", "2026-11-03", "2026-11-01")


def test_list_filters_and_pages_newest_first(database: Database) -> None:
    history = AiHistory(database)
    for days in (0.5, 3, 40):
        _add(history, days)
    assert history.list().total == 3
    assert history.list(resolve_period("day", now=NOW)).total == 1
    month = history.list(resolve_period("month", now=NOW))
    assert month.total == 2
    assert [i.created_at for i in month.items] == [_stamp(0.5), _stamp(3)]
    assert len(history.list(limit=1, offset=1).items) == 1
    with pytest.raises(AiInvalidError):
        history.list(limit=0)


def test_usage_sums_per_connection_model_and_day(database: Database) -> None:
    history = AiHistory(database)
    _add(history, 0.5, "m1", 10)
    _add(history, 0.4, "m1", 5)
    _add(history, 0.3, "m2", 1)
    usage = history.usage()
    assert [(r.model, r.calls, r.input_tokens, r.output_tokens) for r in usage.rows] == [
        ("m1", 2, 15, 30),
        ("m2", 1, 1, 2),
    ]
    assert (usage.calls, usage.input_tokens, usage.output_tokens) == (3, 16, 32)
    assert len(usage.days) == 1
    assert usage.days[0].input_tokens == 16
    assert AiHistory(database).usage(resolve_period("day", now=NOW + timedelta(days=30))).rows == ()


def test_purge_expired_and_all(database: Database) -> None:
    history = AiHistory(database)
    _add(history, 100)
    _add(history, 10)
    assert history.purge_expired(NOW) == 1
    assert history.list().total == 1
    history.save_settings(retention_days=0)
    _add(history, 1000)
    assert history.purge_expired(NOW) == 0
    assert history.purge_all() == 2
    assert history.list().total == 0


def test_purge_on_start_skips_a_missing_database(tmp_path: Path) -> None:
    assert purge_expired_history(tmp_path / "nothing") == 0
    assert not database_path(tmp_path / "nothing").exists()


def test_purge_on_start_removes_old_entries(tmp_path: Path) -> None:
    with_db = Database.open(database_path(tmp_path))
    _add(AiHistory(with_db), 200)
    with_db.close()
    assert purge_expired_history(tmp_path) == 1


def test_generate_and_connection_test_are_recorded(database: Database) -> None:
    def generator(request: GenerateRequest) -> Generation:
        if request.prompt == "boom":
            raise AiConnectionError("It failed.")
        return Generation("answer", 7, 3)

    def prober(provider: str, base_url: str, api_key: str) -> Probe:
        return Probe(["m1"], "Connected.")

    ai = AiConnections(database, _Secrets(), prober, generator)
    ai.save("claude_api", api_key="sk-test-1234567890abcdef")
    ai.refresh_models("claude_api")
    ai.set_default("claude_api")
    ai.set_default_model("claude_api", "m1")
    ai.history.save_settings(store_text=True)
    ai.generate("sys", "hello", 100, purpose="palette", title="Suggest a palette")
    with pytest.raises(AiConnectionError):
        ai.generate("sys", "boom", 100, purpose="studio", title="Parsers")
    ai.test("claude_api")
    items = ai.history.list().items
    by_title = {i.title: i for i in items}
    ok = by_title["Suggest a palette"]
    assert (ok.status, ok.input_tokens, ok.output_tokens, ok.model) == ("ok", 7, 3, "m1")
    assert ai.history.get(ok.id).prompt_text == "sys\n\nhello"
    assert ai.history.get(ok.id).reply_text == "answer"
    failed = by_title["Parsers"]
    assert (failed.status, failed.error, failed.input_tokens) == ("failed", "It failed.", 0)
    check = by_title["Test the Claude API connection"]
    assert (check.purpose, check.status) == ("connection_test", "ok")
