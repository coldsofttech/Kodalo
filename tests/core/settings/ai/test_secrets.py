from collections.abc import Callable

import keyring
import pytest
from keyring.errors import KeyringError, PasswordDeleteError

from kodalo.core.settings.ai import AiSecretError, KeychainSecrets
from kodalo.core.settings.ai.secrets import SERVICE


class _Vault:
    """A stand-in for the system keychain."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, name: str) -> str | None:
        return self.items.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.items[(service, name)] = value

    def delete_password(self, service: str, name: str) -> None:
        if (service, name) not in self.items:
            raise PasswordDeleteError("not found")
        del self.items[(service, name)]


@pytest.fixture
def vault(monkeypatch: pytest.MonkeyPatch) -> _Vault:
    vault = _Vault()
    for name in ("get_password", "set_password", "delete_password"):
        monkeypatch.setattr(keyring, name, getattr(vault, name))
    return vault


def test_a_key_is_stored_read_and_deleted(vault: _Vault) -> None:
    secrets = KeychainSecrets()
    assert secrets.get("ref") is None
    secrets.set("ref", "sk-secret")
    assert secrets.get("ref") == "sk-secret"
    assert vault.items == {(SERVICE, "ref"): "sk-secret"}
    secrets.delete("ref")
    assert secrets.get("ref") is None


def test_deleting_a_key_that_was_never_stored_is_fine(vault: _Vault) -> None:
    KeychainSecrets().delete("never-stored")


def _read(secrets: KeychainSecrets) -> None:
    secrets.get("ref")


def _write(secrets: KeychainSecrets) -> None:
    secrets.set("ref", "sk-secret")


def _remove(secrets: KeychainSecrets) -> None:
    secrets.delete("ref")


@pytest.mark.parametrize("action", [_read, _write, _remove])
def test_a_keychain_failure_becomes_a_clear_error(
    monkeypatch: pytest.MonkeyPatch, action: Callable[[KeychainSecrets], None]
) -> None:
    def broken(*_: object) -> None:
        raise KeyringError("the vault is locked: sk-secret")

    for name in ("get_password", "set_password", "delete_password"):
        monkeypatch.setattr(keyring, name, broken)
    with pytest.raises(AiSecretError, match="system keychain") as caught:
        action(KeychainSecrets())
    assert "sk-secret" not in str(caught.value)
