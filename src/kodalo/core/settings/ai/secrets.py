"""Keep API keys in the system keychain, never in the database or in a file."""

from typing import Protocol

from kodalo.core.settings.ai.errors import AiSecretError

SERVICE = "Kodalo"


class SecretStore(Protocol):
    """Where keys are kept. The default is the system keychain; tests pass an in-memory one."""

    def get(self, ref: str) -> str | None: ...

    def set(self, ref: str, value: str) -> None: ...

    def delete(self, ref: str) -> None: ...


class KeychainSecrets:
    """The system keychain (Windows Credential Manager, macOS Keychain, Secret Service)."""

    def get(self, ref: str) -> str | None:
        import keyring
        from keyring.errors import KeyringError

        try:
            return keyring.get_password(SERVICE, ref)
        except KeyringError as exc:
            raise AiSecretError(_MESSAGE) from exc

    def set(self, ref: str, value: str) -> None:
        import keyring
        from keyring.errors import KeyringError

        try:
            keyring.set_password(SERVICE, ref, value)
        except KeyringError as exc:
            raise AiSecretError(_MESSAGE) from exc

    def delete(self, ref: str) -> None:
        import keyring
        from keyring.errors import KeyringError, PasswordDeleteError

        try:
            keyring.delete_password(SERVICE, ref)
        except PasswordDeleteError:
            pass  # nothing was stored
        except KeyringError as exc:
            raise AiSecretError(_MESSAGE) from exc


_MESSAGE = "Kodalo could not use the system keychain to store the API key."
