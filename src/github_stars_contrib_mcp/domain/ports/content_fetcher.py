"""Provider-neutral contract for bounded, security-classified remote content fetches."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_ALLOWED_MEDIA_TYPES: tuple[str, ...] = (
    "text/plain",
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
    "application/rss+xml",
    "application/atom+xml",
)

_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "key",
    "password",
    "secret",
    "sig",
    "signature",
    "token",
    "x-amz-signature",
}
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY|AUTHORIZATION)[A-Z0-9_]*)"
    r"\s*([:=])\s*([^\s,;\"'<>]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_PROVIDER_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_-]{16,})\b"
)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def has_sensitive_query(url: str) -> bool:
    """Return whether a URL contains a credential-like query key."""

    try:
        query = urlsplit(url).query
    except ValueError:
        return False
    return any(key.lower() in _SENSITIVE_QUERY_KEYS for key, _ in parse_qsl(query))


def redact_url(url: str) -> str:
    """Redact values for credential-like query parameters without logging them."""

    try:
        parsed = urlsplit(url)
    except ValueError:
        return "<invalid-url>"
    query = urlencode(
        [
            (key, "[REDACTED]" if key.lower() in _SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
    )
    hostname = parsed.hostname or ""
    if not hostname:
        return "<invalid-url>"
    host = (
        f"[{hostname}]"
        if ":" in hostname and not hostname.startswith("[")
        else hostname
    )
    try:
        port = parsed.port
    except ValueError:
        return "<invalid-url>"
    netloc = f"{host}:{port}" if port is not None else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


def redact_secret_text(text: str) -> str:
    """Remove common credential/token forms from material that may be persisted."""

    value = _SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text
    )
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    return _PROVIDER_TOKEN_RE.sub("[REDACTED]", value)


class FetchOutcome(StrEnum):
    SUCCESS = "success"
    BLOCKED = "blocked"
    TOO_LARGE = "too_large"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    HTTP_ERROR = "http_error"
    NETWORK_ERROR = "network_error"


class FetchSecurityClassification(StrEnum):
    UNTRUSTED_PUBLIC = "untrusted_public"
    BLOCKED_UNSAFE_TARGET = "blocked_unsafe_target"
    NOT_FETCHED = "not_fetched"


class SafeFetchRequest(BaseModel):
    """Caller-controlled limits for one safe remote fetch."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=4096)
    max_bytes: int = Field(default=1_000_000, ge=1, le=10_000_000)
    max_redirects: int = Field(default=3, ge=0, le=10)
    connect_timeout_s: float = Field(default=3.0, gt=0, le=30)
    read_timeout_s: float = Field(default=10.0, gt=0, le=60)
    allowed_media_types: tuple[str, ...] = DEFAULT_ALLOWED_MEDIA_TYPES
    robots_policy: Literal["respect"] = "respect"
    cache_policy: Literal["default", "bypass"] = "default"

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("url must not be empty")
        return normalized

    @field_validator("allowed_media_types")
    @classmethod
    def normalize_media_types(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            sorted({value.strip().lower() for value in values if value.strip()})
        )
        if not normalized:
            raise ValueError("allowed_media_types must not be empty")
        return normalized


class SafeFetchResult(BaseModel):
    """Bounded fetch result safe to pass to later discovery layers."""

    model_config = ConfigDict(extra="forbid")

    final_url: str
    outcome: FetchOutcome
    security: FetchSecurityClassification
    status_code: int | None = None
    media_type: str | None = None
    text: str | None = None
    byte_count: int = Field(default=0, ge=0)
    redirect_count: int = Field(default=0, ge=0)
    truncated: bool = False
    error_code: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)


@runtime_checkable
class ContentFetcher(Protocol):
    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        """Fetch one remote resource under deterministic safety constraints."""
        ...
