"""Secure credential resolution for GitHub Stars authentication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

STARS_KEYRING_SERVICE = "github-stars-contrib-mcp-server"
STARS_KEYRING_USERNAME = "stars-api-token"


class CredentialStoreUnavailable(RuntimeError):
    """Raised when no supported secure credential backend is available."""


class CredentialStoreError(RuntimeError):
    """Raised when a secure credential backend operation fails."""


class CredentialStore(Protocol):
    """Minimal token-store contract used by server bootstrap and CLI."""

    def get_stars_token(self) -> str | None: ...

    def set_stars_token(self, token: str) -> None: ...

    def delete_stars_token(self) -> bool: ...

    def status(self) -> "CredentialStatus": ...


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    """Public-safe status for the configured secure credential backend."""

    available: bool
    configured: bool
    backend: str


def _backend_name(backend: KeyringBackend) -> str:
    cls = backend.__class__
    return f"{cls.__module__}.{cls.__qualname__}"


def _assert_secure_backend(backend: KeyringBackend) -> None:
    """Reject known unavailable or intentionally insecure keyring backends."""

    module = backend.__class__.__module__
    priority = getattr(backend, "priority", 0)

    if module.startswith("keyring.backends.fail") or priority < 1:
        raise CredentialStoreUnavailable(
            "No supported secure OS credential backend is available"
        )
    if module.startswith("keyrings.alt"):
        raise CredentialStoreUnavailable(
            "Insecure alternate keyring backends are not supported"
        )


class KeyringCredentialStore:
    """Store the Stars token in the operating system credential service."""

    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend = backend or keyring.get_keyring()

    def _validated_backend(self) -> KeyringBackend:
        _assert_secure_backend(self._backend)
        return self._backend

    def get_stars_token(self) -> str | None:
        backend = self._validated_backend()
        try:
            return backend.get_password(STARS_KEYRING_SERVICE, STARS_KEYRING_USERNAME)
        except KeyringError as exc:
            raise CredentialStoreError(
                "Unable to read the Stars credential from the secure OS credential store"
            ) from exc

    def set_stars_token(self, token: str) -> None:
        if not token.strip():
            raise ValueError("Stars API token must not be empty")
        backend = self._validated_backend()
        try:
            backend.set_password(
                STARS_KEYRING_SERVICE,
                STARS_KEYRING_USERNAME,
                token,
            )
        except KeyringError as exc:
            raise CredentialStoreError(
                "Unable to store the Stars credential in the secure OS credential store"
            ) from exc

    def delete_stars_token(self) -> bool:
        backend = self._validated_backend()
        try:
            existing = backend.get_password(
                STARS_KEYRING_SERVICE,
                STARS_KEYRING_USERNAME,
            )
            if existing is None:
                return False
            backend.delete_password(
                STARS_KEYRING_SERVICE,
                STARS_KEYRING_USERNAME,
            )
            return True
        except PasswordDeleteError as exc:
            raise CredentialStoreError(
                "Unable to delete the Stars credential from the secure OS credential store"
            ) from exc
        except KeyringError as exc:
            raise CredentialStoreError(
                "Unable to access the secure OS credential store"
            ) from exc

    def status(self) -> CredentialStatus:
        backend_name = _backend_name(self._backend)
        try:
            configured = self.get_stars_token() is not None
        except CredentialStoreUnavailable:
            return CredentialStatus(
                available=False,
                configured=False,
                backend=backend_name,
            )
        return CredentialStatus(
            available=True,
            configured=configured,
            backend=backend_name,
        )


def resolve_stars_api_token(
    explicit_token: str | None,
    *,
    store: CredentialStore | None = None,
) -> str | None:
    """Resolve a Stars token without weakening current explicit-env precedence."""

    if explicit_token:
        return explicit_token

    credential_store = store or KeyringCredentialStore()
    try:
        return credential_store.get_stars_token()
    except CredentialStoreUnavailable:
        return None
