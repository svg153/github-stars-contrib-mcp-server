"""Application settings (12-factor) for Stars MCP server."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    stars_api_url: str = Field(
        default="https://api-stars.github.com/",
        description="Legacy GitHub Stars GraphQL API used for profile/link operations",
    )
    stars_contributions_api_url: str = Field(
        default="https://stars.github.com/api/contributions",
        description="Current GitHub Stars REST Contributions API",
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
    url_validation_timeout_s: int = Field(default=3)
    url_validation_ttl_s: int = Field(default=3600)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized == "TRACE":
            return "DEBUG"
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid log level: {v}. Must be one of {valid_levels} or 'TRACE'"
            )
        return normalized


settings = Settings()
