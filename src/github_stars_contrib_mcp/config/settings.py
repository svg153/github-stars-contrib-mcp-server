"""Application settings (12-factor) for Stars MCP server.

Consolidated settings implementation using pydantic-settings.
This replaces the earlier ad-hoc dataclass to support validation
and additional fields required by the server (e.g., log_level).
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    stars_api_url: str = Field(
        default="https://api-stars.github.com/",
        description="Base URL for GitHub Stars GraphQL API",
    )
    stars_api_token: str | None = Field(
        default=None, description="Personal Stars API token from stars.github.com"
    )
    log_level: str = Field(default="INFO", description="Python logging level")
    dangerously_omit_auth: bool = Field(
        default=False,
        description="ONLY for local dev/tests: allow running without a token",
    )
    validate_urls: bool = Field(
        default=False,
        description="When true, perform a lightweight HEAD check for URLs before calling the API (may slow calls).",
    )
    url_validation_timeout_s: int = Field(
        default=3,
        description="Timeout in seconds for URL validation requests",
    )
    url_validation_ttl_s: int = Field(
        default=3600,
        description="TTL in seconds to cache URL validation results",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize and validate LOG_LEVEL.

        Accept standard levels and allow the common alias TRACE by mapping it to DEBUG
        so that environments using LOG_LEVEL=TRACE don't crash.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        # Support TRACE as an alias of DEBUG
        if normalized == "TRACE":
            return "DEBUG"
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid log level: {v}. Must be one of {valid_levels} or 'TRACE'"
            )
        return normalized


# Global settings instance, exported by the package in __init__.py
settings = Settings()
