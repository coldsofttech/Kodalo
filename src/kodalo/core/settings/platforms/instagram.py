"""The Instagram connection: an access token and account ID the user pastes, checked with Meta.

The token is a secret, so it lives in the system keychain only. The settings table keeps what is
safe to show: the account's name and ID, its type, the last four characters of the token and when
it was connected. Kodalo never asks for an Instagram password.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from kodalo.core.settings.ai.errors import AiSecretError
from kodalo.core.settings.ai.secrets import KeychainSecrets, SecretStore
from kodalo.core.settings.platforms.errors import (
    PlatformConnectionError,
    PlatformInvalidError,
    PlatformSecretError,
)
from kodalo.core.storage import Database
from kodalo.core.storage.models import Setting

GRAPH_BASE = "https://graph.facebook.com/v21.0"
MAX_ACCOUNT_ID_LENGTH = 40
MAX_CAPTION = 2200
MAX_ALT_TEXT = 1000
MAX_CAROUSEL = 10
SECRET_REF = "platform/instagram/token"  # noqa: S105 - the keychain entry name, not a secret
MAX_TOKEN_LENGTH = 1024
_GROUP = "platform_instagram"
_TIMEOUT = 15
_PUBLISH_TIMEOUT = 60
_READY_TIMEOUT = 120
_MAX_BYTES = 1_000_000
_KEYS = ("username", "account_id", "account_type", "token_hint", "connected_at")


@dataclass(frozen=True)
class InstagramAccount:
    """The Instagram account Kodalo is connected to. Never carries the token."""

    username: str
    account_id: str
    account_type: str
    token_hint: str
    connected_at: str


@dataclass(frozen=True)
class PublishedPost:
    """A post that is now on Instagram."""

    media_id: str
    permalink: str


Fetcher = Callable[[str, str], dict[str, Any]]
GraphCall = Callable[[str, str, dict[str, str], str], dict[str, Any]]


class InstagramConnection:
    """Connects, checks and disconnects the Instagram account."""

    def __init__(
        self,
        database: Database,
        secrets: SecretStore | None = None,
        fetcher: Fetcher | None = None,
        graph: GraphCall | None = None,
    ) -> None:
        self._database = database
        self._secrets = secrets if secrets is not None else KeychainSecrets()
        self._fetch = fetcher if fetcher is not None else _fetch_profile
        self._graph = graph if graph is not None else _graph_call

    def get(self) -> InstagramAccount | None:
        """The connected account, or ``None`` when Instagram is not connected."""
        with self._database.session() as session:
            values = {key: self._value(session, key) for key in _KEYS}
        if not values["username"]:
            return None
        return InstagramAccount(**values)

    def connect(self, token: str, account_id: str) -> InstagramAccount:
        """Check ``token`` for the Instagram account ``account_id`` with Meta, then keep the token
        in the keychain and the account details in the settings. Raises ``PlatformInvalidError``
        for an empty or malformed token or account ID, ``PlatformConnectionError`` when Meta
        refuses them or cannot be reached and ``PlatformSecretError`` when the keychain is
        unavailable. Nothing is kept on failure."""
        token = token.strip()
        account_id = account_id.strip()
        if not token or len(token) > MAX_TOKEN_LENGTH or any(c.isspace() for c in token):
            raise PlatformInvalidError("Paste the access token as one piece of text.")
        if not account_id.isdigit() or len(account_id) > MAX_ACCOUNT_ID_LENGTH:
            raise PlatformInvalidError("The Instagram account ID is a number.")
        profile = _profile(self._fetch(token, account_id), account_id)
        self._keep_secret(token)
        account = InstagramAccount(
            username=profile["username"],
            account_id=profile["account_id"],
            account_type=profile["account_type"],
            token_hint=token[-4:],
            connected_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        self._save(account)
        return account

    def check(self) -> InstagramAccount:
        """Ask Instagram again whether the saved token still works and refresh the account's
        details. Raises ``PlatformConnectionError`` when it is not connected or the token has
        expired or been revoked."""
        current = self.get()
        token = self._read_secret() if current is not None else None
        if current is None or token is None:
            raise PlatformConnectionError("Instagram is not connected.")
        profile = _profile(self._fetch(token, current.account_id), current.account_id)
        account = InstagramAccount(
            username=profile["username"],
            account_id=profile["account_id"],
            account_type=profile["account_type"],
            token_hint=current.token_hint,
            connected_at=current.connected_at,
        )
        self._save(account)
        return account

    def publish(
        self,
        image_urls: Sequence[str],
        caption: str,
        alt_texts: Sequence[str] = (),
        *,
        wait: Callable[[float], None] = time.sleep,
    ) -> PublishedPost:
        """Post the pictures at ``image_urls`` (public JPEG addresses) with ``caption``: one is a
        single image post, two to ten a carousel. ``alt_texts`` go with the pictures in order.
        Raises ``PlatformInvalidError`` for a post Instagram would refuse,
        ``PlatformConnectionError`` when it is not connected or Instagram refuses or cannot be
        reached, and ``PlatformSecretError`` when the keychain is unavailable."""
        if not 1 <= len(image_urls) <= MAX_CAROUSEL:
            raise PlatformInvalidError(f"A post has 1 to {MAX_CAROUSEL} pictures.")
        if len(caption) > MAX_CAPTION:
            raise PlatformInvalidError(f"The caption is longer than {MAX_CAPTION} characters.")
        if caption.count("#") > 30:
            raise PlatformInvalidError("Instagram allows up to 30 hashtags on a post.")
        account = self.get()
        token = self._read_secret() if account is not None else None
        if account is None or token is None:
            raise PlatformConnectionError("Instagram is not connected.")
        alts = [a[:MAX_ALT_TEXT] for a in alt_texts] + [""] * len(image_urls)
        base = f"/{account.account_id}"

        def create(params: dict[str, str]) -> str:
            return _text(self._graph("POST", f"{base}/media", params, token), "id")

        def ready(container: str) -> None:
            deadline = time.monotonic() + _READY_TIMEOUT
            while True:
                found = self._graph("GET", f"/{container}", {"fields": "status_code"}, token)
                status = found.get("status_code")
                if status == "FINISHED":
                    return
                if status in ("ERROR", "EXPIRED") or time.monotonic() > deadline:
                    raise PlatformConnectionError("Instagram could not process the pictures.")
                wait(2)

        if len(image_urls) == 1:
            container = create({"image_url": image_urls[0], "caption": caption, **_alt(alts[0])})
        else:
            children = [
                create({"image_url": url, "is_carousel_item": "true", **_alt(alt)})
                for url, alt in zip(image_urls, alts, strict=False)
            ]
            for child in children:
                ready(child)
            container = create(
                {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
            )
        ready(container)
        published = _text(
            self._graph("POST", f"{base}/media_publish", {"creation_id": container}, token), "id"
        )
        link = self._graph("GET", f"/{published}", {"fields": "permalink"}, token)
        permalink = link.get("permalink")
        return PublishedPost(published, permalink if isinstance(permalink, str) else "")

    def disconnect(self) -> None:
        """Remove the token from the keychain and forget the account. Nothing happens when
        Instagram is not connected."""
        try:
            self._secrets.delete(SECRET_REF)
        except AiSecretError as error:
            raise PlatformSecretError(_KEYCHAIN_MESSAGE) from error
        with self._database.session() as session:
            session.execute(
                delete(Setting).where(
                    Setting.scope == "global",
                    Setting.owner_id == "",
                    Setting.group_name == _GROUP,
                    Setting.key.in_(_KEYS),
                )
            )

    def _keep_secret(self, token: str) -> None:
        try:
            self._secrets.set(SECRET_REF, token)
        except AiSecretError as error:
            raise PlatformSecretError(_KEYCHAIN_MESSAGE) from error

    def _read_secret(self) -> str | None:
        try:
            return self._secrets.get(SECRET_REF)
        except AiSecretError as error:
            raise PlatformSecretError(_KEYCHAIN_MESSAGE) from error

    def _save(self, account: InstagramAccount) -> None:
        with self._database.session() as session:
            for key in _KEYS:
                row = self._row(session, key)
                if row is None:
                    row = Setting(
                        scope="global", owner_id="", group_name=_GROUP, key=key, mode="own"
                    )
                    session.add(row)
                row.value = getattr(account, key)
                row.data_type = "string"

    def _value(self, session: Session, key: str) -> str:
        row = self._row(session, key)
        return row.value if row is not None else ""

    @staticmethod
    def _row(session: Session, key: str) -> Setting | None:
        return session.scalars(
            select(Setting).where(
                Setting.scope == "global",
                Setting.owner_id == "",
                Setting.group_name == _GROUP,
                Setting.key == key,
            )
        ).first()


_KEYCHAIN_MESSAGE = "Kodalo could not use the system keychain to store the Instagram token."
_UNREADABLE = "Instagram sent an answer Kodalo could not read."


def _profile(data: dict[str, Any], account_id: str) -> dict[str, str]:
    """The account details out of Meta's answer, as text. The account type is not part of the
    answer, so it stays empty."""
    username = data.get("username")
    if not isinstance(username, str) or not username:
        raise PlatformConnectionError(_UNREADABLE)
    found = data.get("id")
    return {
        "username": username[:100],
        "account_id": str(found)[:MAX_ACCOUNT_ID_LENGTH] if found else account_id,
        "account_type": "",
    }


def _fetch_profile(token: str, account_id: str) -> dict[str, Any]:
    """Ask Meta for the Instagram account the token can reach. Messages never contain the token."""
    query = urllib.parse.urlencode({"fields": "id,username", "access_token": token})
    request = urllib.request.Request(  # noqa: S310
        f"{GRAPH_BASE}/{account_id}?{query}", headers={"Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
            data = json.loads(response.read(_MAX_BYTES))
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 401, 403):
            raise PlatformConnectionError(
                "Instagram rejected the token. It may be wrong, expired or revoked."
            ) from exc
        raise PlatformConnectionError(f"Instagram returned an error (HTTP {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PlatformConnectionError("Could not reach Instagram.") from exc
    except ValueError as exc:
        raise PlatformConnectionError(_UNREADABLE) from exc
    if not isinstance(data, dict):
        raise PlatformConnectionError(_UNREADABLE)
    return data


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str | int) or value == "":
        raise PlatformConnectionError(_UNREADABLE)
    return str(value)


def _alt(text: str) -> dict[str, str]:
    return {"alt_text": text} if text else {}


def _graph_call(method: str, path: str, params: dict[str, str], token: str) -> dict[str, Any]:
    """One call to the Instagram API. The token travels in the request, never in a message."""
    body = {**params, "access_token": token}
    if method == "GET":
        request = urllib.request.Request(  # noqa: S310
            f"{GRAPH_BASE}{path}?{urllib.parse.urlencode(body)}",
            headers={"Accept": "application/json"},
        )
    else:
        request = urllib.request.Request(  # noqa: S310
            f"{GRAPH_BASE}{path}",
            data=urllib.parse.urlencode(body).encode("utf-8"),
            headers={"Accept": "application/json"},
            method=method,
        )
    try:
        with urllib.request.urlopen(request, timeout=_PUBLISH_TIMEOUT) as response:  # noqa: S310
            data = json.loads(response.read(_MAX_BYTES))
    except urllib.error.HTTPError as exc:
        raise PlatformConnectionError(_refusal(exc, token)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PlatformConnectionError("Could not reach Instagram.") from exc
    except ValueError as exc:
        raise PlatformConnectionError(_UNREADABLE) from exc
    if not isinstance(data, dict):
        raise PlatformConnectionError(_UNREADABLE)
    return data


def _refusal(error: urllib.error.HTTPError, token: str) -> str:
    """What Instagram said when it refused a call, without the token."""
    try:
        said = json.loads(error.read(_MAX_BYTES)).get("error", {}).get("message", "")
    except (ValueError, AttributeError, OSError):
        said = ""
    said = str(said).replace(token, "***")[:200]
    if said:
        return f"Instagram refused the post: {said}"
    return f"Instagram returned an error (HTTP {error.code})."
