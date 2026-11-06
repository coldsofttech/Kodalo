"""AI connections and their models, kept in the local database.

API keys go to the system keychain; the database keeps only a reference and the last characters
of the key, so the key can be recognised without being shown.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.ai.clients import GenerateRequest, Generation, Generator, Prober, generate, probe
from kodalo.core.settings.ai.defaults import defaults_for
from kodalo.core.settings.ai.errors import (
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
)
from kodalo.core.settings.ai.history import AiHistory
from kodalo.core.settings.ai.providers import PROVIDER_IDS, PROVIDERS, Kind, Provider, get_provider
from kodalo.core.settings.ai.secrets import KeychainSecrets, SecretStore
from kodalo.core.storage import Database
from kodalo.core.storage.models import AiConnectionRow, AiModelRow, utc_now

MAX_URL = 512
MAX_MODEL_NAME = 128
MAX_TOKENS_LIMIT = 1_000_000
MAX_TEMPERATURE = 2.0
MAX_TIMEOUT = 600
_HINT_LENGTH = 4


@dataclass(frozen=True)
class AiModel:
    """A model and its generation defaults. ``None`` means the provider's own default."""

    name: str
    source: str
    is_default: bool
    max_tokens: int | None
    temperature: float | None
    timeout_s: int | None


@dataclass(frozen=True)
class AiConnection:
    """How one provider is reached. ``key_hint`` is the end of the saved key, never the key."""

    provider: str
    label: str
    kind: Kind
    saved: bool
    enabled: bool
    is_default: bool
    base_url: str
    default_base_url: str
    has_key: bool
    key_hint: str
    status: str
    status_detail: str
    checked_at: str | None
    models: tuple[AiModel, ...]

    @property
    def default_model(self) -> str | None:
        """The name of the model marked as the default, if any."""
        return next((model.name for model in self.models if model.is_default), None)


@dataclass(frozen=True)
class ConnectionCheck:
    """The outcome of trying one connection."""

    provider: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class AiTarget:
    """The default connection and model, with the generation settings saved for that model."""

    provider: str
    label: str
    model: str
    max_tokens: int | None
    temperature: float | None
    timeout_s: int | None


class AiConnections:
    """The AI connections: one per provider, each with its models."""

    def __init__(
        self,
        database: Database,
        secrets: SecretStore | None = None,
        prober: Prober | None = None,
        generator: Generator | None = None,
    ) -> None:
        self._database = database
        self._secrets: SecretStore = secrets if secrets is not None else KeychainSecrets()
        self._prober: Prober = prober if prober is not None else probe
        self._generator: Generator = generator if generator is not None else generate
        self.history = AiHistory(database)

    # -- using the default -----------------------------------------------------------------------

    def default_target(self) -> AiTarget:
        """Return the default connection and its default model. Raises ``AiInvalidError`` when
        either is not set."""
        for connection in self.list_all():
            if connection.is_default and connection.enabled:
                name = connection.default_model
                model = next((m for m in connection.models if m.name == name), None)
                if model is not None:
                    return AiTarget(
                        connection.provider,
                        connection.label,
                        model.name,
                        model.max_tokens,
                        model.temperature,
                        model.timeout_s,
                    )
                raise AiInvalidError(f"Choose a default model for {connection.label} in Settings.")
        raise AiInvalidError("Choose a default AI connection in Settings first.")

    def generate(
        self, system: str, prompt: str, max_tokens: int, *, purpose: str, title: str
    ) -> Generation:
        """Send ``prompt`` to the default model. The model's saved settings apply, and its
        maximum tokens, when set, caps ``max_tokens``. The call is added to the history under
        ``title`` and ``purpose`` (one of ``PURPOSES``). Raises ``AiConnectionError``."""
        target = self.default_target()
        info = _provider(target.provider)
        request = GenerateRequest(
            provider=target.provider,
            base_url="" if info.kind == "local_cli" else self._base_url(info),
            api_key=self._key_for(info),
            model=target.model,
            system=system,
            prompt=prompt,
            max_tokens=min(max_tokens, target.max_tokens or max_tokens),
            temperature=target.temperature,
            timeout_s=target.timeout_s,
        )
        sent = f"{system}\n\n{prompt}"
        try:
            reply = self._generator(request)
        except AiConnectionError as exc:
            self._log(target, purpose, title, "failed", str(exc), prompt=sent)
            raise
        self._log(
            target,
            purpose,
            title,
            "ok",
            "",
            reply.input_tokens,
            reply.output_tokens,
            sent,
            reply.text,
        )
        return reply

    def _log(
        self,
        target: AiTarget,
        purpose: str,
        title: str,
        status: str,
        error: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        prompt: str | None = None,
        reply: str | None = None,
    ) -> None:
        """Add a call to the history. A failure to write it never stops the call itself."""
        try:
            self.history.record(
                title=title,
                purpose=purpose,
                provider=target.provider,
                model=target.model,
                status=status,
                error=error,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                prompt=prompt,
                reply=reply,
            )
        except Exception:
            return

    # -- connections ---------------------------------------------------------------------------

    def list_all(self) -> list[AiConnection]:
        """Return every supported provider, in a fixed order, saved or not."""
        with self._database.session() as session:
            rows = {row.provider: row for row in session.scalars(select(AiConnectionRow))}
            return [_connection(provider, rows.get(provider.id)) for provider in PROVIDERS]

    def get(self, provider: str) -> AiConnection:
        """Return the connection to ``provider``; it is unsaved when never configured."""
        info = _provider(provider)
        with self._database.session() as session:
            return _connection(info, _find(session, provider))

    def save(
        self,
        provider: str,
        *,
        enabled: bool | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> AiConnection:
        """Save the connection to ``provider``. ``None`` keeps a saved value; an empty
        ``base_url`` goes back to the provider's address. A new connection starts enabled."""
        info = _provider(provider)
        key = _valid_key(info, api_key)
        url = _valid_url(info, base_url)
        with self._database.session() as session:
            row = _find(session, provider)
            if row is None:
                row = AiConnectionRow(provider=provider, enabled=True, is_default=False)
                session.add(row)
            changed = False
            if key is not None:
                ref = f"ai/{provider}"
                self._secrets.set(ref, key)
                row.secret_ref = ref
                row.key_hint = _hint(key)
                changed = True
            if url is not None and url != row.base_url:
                row.base_url = url
                changed = True
            if changed:
                row.last_status, row.last_detail, row.last_checked_at = "", "", None
            if enabled is not None:
                row.enabled = enabled
                if not enabled:
                    row.is_default = False
            session.flush()
            return _connection(info, row)

    def remove(self, provider: str) -> bool:
        """Forget the connection to ``provider``: its models, settings and key. Return whether
        there was anything to forget."""
        _provider(provider)
        with self._database.session() as session:
            row = _find(session, provider)
            ref = row.secret_ref if row is not None else None
            if row is not None:
                session.delete(row)
        if ref is not None:
            self._secrets.delete(ref)
        return row is not None

    def set_default(self, provider: str) -> AiConnection:
        """Make ``provider`` the default connection. It must be saved and enabled."""
        info = _provider(provider)
        with self._database.session() as session:
            row = _find(session, provider)
            if row is None or not row.enabled:
                raise AiInvalidError(f"Save and enable {info.label} before making it the default.")
            for other in session.scalars(select(AiConnectionRow).where(AiConnectionRow.is_default)):
                other.is_default = False
            session.flush()
            row.is_default = True
            session.flush()
            return _connection(info, row)

    def test(self, provider: str) -> ConnectionCheck:
        """Try the connection to ``provider`` and remember the outcome."""
        info = _provider(provider)
        api_key = self._key_for(info)
        model = self.get(provider).default_model or ""
        target = AiTarget(provider, info.label, model, None, None, None)
        title = f"Test the {info.label} connection"
        try:
            result = self._prober(provider, self._base_url(info), api_key)
        except AiConnectionError as exc:
            self._record(provider, "failed", str(exc))
            self._log(target, "connection_test", title, "failed", str(exc))
            return ConnectionCheck(provider, False, str(exc))
        self._record(provider, "ok", result.detail)
        self._log(target, "connection_test", title, "ok", "")
        return ConnectionCheck(provider, True, result.detail)

    # -- models --------------------------------------------------------------------------------

    def models(self, provider: str) -> list[AiModel]:
        """Return the saved models of ``provider``, by name."""
        return list(self.get(provider).models)

    def refresh_models(self, provider: str) -> list[AiModel]:
        """Ask ``provider`` for its models and save them. Models typed in by hand are kept, and so
        are the settings of models that are still offered. Raises ``AiConnectionError``."""
        info = _provider(provider)
        api_key = self._key_for(info)
        self._require_saved(provider)
        try:
            result = self._prober(provider, self._base_url(info), api_key)
        except AiConnectionError as exc:
            self._record(provider, "failed", str(exc))
            raise
        offered = set(result.models)
        with self._database.session() as session:
            row = _require(session, info)
            existing = {model.name: model for model in row.models}
            for name in sorted(offered - existing.keys()):
                standard = defaults_for(name)
                row.models.append(
                    AiModelRow(
                        name=name,
                        source="fetched",
                        is_default=False,
                        max_tokens=standard.max_tokens,
                        temperature=standard.temperature,
                        timeout_s=standard.timeout_s,
                    )
                )
            for name, model in existing.items():
                if model.source == "fetched" and name not in offered:
                    row.models.remove(model)
            row.last_status, row.last_detail = "ok", result.detail[:256]
            row.last_checked_at = utc_now()
            session.flush()
            return list(_connection(info, row).models)

    def save_model(
        self,
        provider: str,
        name: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_s: int | None = None,
    ) -> AiModel:
        """Add the model ``name`` to ``provider`` or update it. A new model starts with the
        standard settings for its family wherever one is left as ``None``. An existing model gets
        the three settings as given, so ``None`` clears one back to the provider's default."""
        info = _provider(provider)
        name = _valid_model(name)
        _check_range("Max tokens", max_tokens, 1, MAX_TOKENS_LIMIT)
        _check_range("Temperature", temperature, 0.0, MAX_TEMPERATURE)
        _check_range("Timeout", timeout_s, 1, MAX_TIMEOUT)
        with self._database.session() as session:
            row = _require(session, info)
            model = next((m for m in row.models if m.name == name), None)
            if model is None:
                standard = defaults_for(name)
                model = AiModelRow(name=name, source="manual", is_default=False)
                row.models.append(model)
                max_tokens = standard.max_tokens if max_tokens is None else max_tokens
                temperature = standard.temperature if temperature is None else temperature
                timeout_s = standard.timeout_s if timeout_s is None else timeout_s
            model.max_tokens = max_tokens
            model.temperature = temperature
            model.timeout_s = timeout_s
            session.flush()
            return _model(model)

    def set_default_model(self, provider: str, name: str) -> AiModel:
        """Make ``name`` the model ``provider`` uses by default."""
        info = _provider(provider)
        with self._database.session() as session:
            row = _require(session, info)
            target = _find_model(row, name)
            for model in row.models:
                model.is_default = False
            session.flush()
            target.is_default = True
            session.flush()
            return _model(target)

    def remove_model(self, provider: str, name: str) -> None:
        """Forget the model ``name`` of ``provider``."""
        info = _provider(provider)
        with self._database.session() as session:
            row = _require(session, info)
            row.models.remove(_find_model(row, name))

    # -- helpers -------------------------------------------------------------------------------

    def _require_saved(self, provider: str) -> None:
        info = _provider(provider)
        with self._database.session() as session:
            _require(session, info)

    def _base_url(self, info: Provider) -> str:
        with self._database.session() as session:
            row = _find(session, info.id)
            return (row.base_url if row is not None else "") or info.default_base_url

    def _key_for(self, info: Provider) -> str:
        """Return the saved key of ``info``, or an empty string for a provider that needs none."""
        if info.kind == "local_cli":
            return ""
        with self._database.session() as session:
            row = _find(session, info.id)
            ref = row.secret_ref if row is not None else None
        key = self._secrets.get(ref) if ref is not None else None
        if not key:
            raise AiInvalidError(f"Save an API key for {info.label} first.")
        return key

    def _record(self, provider: str, status: str, detail: str) -> None:
        with self._database.session() as session:
            row = _find(session, provider)
            if row is not None:
                row.last_status, row.last_detail = status, detail[:256]
                row.last_checked_at = utc_now()


def _provider(provider: str) -> Provider:
    info = get_provider(provider)
    if info is None:
        raise AiInvalidError(
            f"Unknown provider: {provider}. Use one of: {', '.join(PROVIDER_IDS)}."
        )
    return info


def _find(session: Session, provider: str) -> AiConnectionRow | None:
    return session.scalars(
        select(AiConnectionRow).where(AiConnectionRow.provider == provider)
    ).first()


def _require(session: Session, info: Provider) -> AiConnectionRow:
    row = _find(session, info.id)
    if row is None:
        raise AiInvalidError(f"Save the {info.label} connection first.")
    return row


def _find_model(row: AiConnectionRow, name: str) -> AiModelRow:
    model = next((m for m in row.models if m.name == name.strip()), None)
    if model is None:
        raise AiNotFoundError(f"There is no model called {name.strip()} on this connection.")
    return model


def _valid_key(info: Provider, api_key: str | None) -> str | None:
    if api_key is None:
        return None
    if info.kind == "local_cli":
        raise AiInvalidError(f"{info.label} uses your own sign-in and needs no API key.")
    api_key = api_key.strip()
    if not api_key:
        raise AiInvalidError("The API key cannot be empty.")
    return api_key


def _valid_url(info: Provider, base_url: str | None) -> str | None:
    if base_url is None:
        return None
    if info.kind == "local_cli":
        raise AiInvalidError(f"{info.label} runs on this computer and has no address to set.")
    base_url = base_url.strip().rstrip("/")
    if not base_url:
        return ""
    if len(base_url) > MAX_URL:
        raise AiInvalidError(f"The address must be at most {MAX_URL} characters.")
    if not base_url.startswith(("https://", "http://")):
        raise AiInvalidError("The address must start with https:// or http://.")
    return base_url


def _valid_model(name: str) -> str:
    name = name.strip()
    if not name or len(name) > MAX_MODEL_NAME:
        raise AiInvalidError(f"The model name must be from 1 to {MAX_MODEL_NAME} characters.")
    return name


def _check_range(label: str, value: float | None, low: float, high: float) -> None:
    if value is not None and not low <= value <= high:
        raise AiInvalidError(f"{label} must be from {low:g} to {high:g}.")


def _hint(key: str) -> str:
    return key[-_HINT_LENGTH:] if len(key) >= 3 * _HINT_LENGTH else ""


def _model(row: AiModelRow) -> AiModel:
    return AiModel(
        name=row.name,
        source=row.source,
        is_default=row.is_default,
        max_tokens=row.max_tokens,
        temperature=row.temperature,
        timeout_s=row.timeout_s,
    )


def _connection(info: Provider, row: AiConnectionRow | None) -> AiConnection:
    if row is None:
        return AiConnection(
            provider=info.id,
            label=info.label,
            kind=info.kind,
            saved=False,
            enabled=False,
            is_default=False,
            base_url="",
            default_base_url=info.default_base_url,
            has_key=False,
            key_hint="",
            status="",
            status_detail="",
            checked_at=None,
            models=(),
        )
    return AiConnection(
        provider=info.id,
        label=info.label,
        kind=info.kind,
        saved=True,
        enabled=row.enabled,
        is_default=row.is_default,
        base_url=row.base_url,
        default_base_url=info.default_base_url,
        has_key=row.secret_ref is not None,
        key_hint=row.key_hint,
        status=row.last_status,
        status_detail=row.last_detail,
        checked_at=row.last_checked_at,
        models=tuple(_model(model) for model in sorted(row.models, key=lambda m: m.name)),
    )
