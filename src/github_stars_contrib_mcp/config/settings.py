"""Application settings (12-factor) for Stars MCP server."""

from __future__ import annotations

from typing import Literal

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
    stars_auth_mode: Literal["both", "bearer", "cookie"] = Field(
        default="both",
        description="Credential transport: bearer header, cookie, or both",
    )
    stars_user_agent: str = Field(
        default="github-stars-contrib-mcp-server/0.3.1",
        description="User-Agent sent to GitHub Stars endpoints",
    )
    log_level: str = Field(default="INFO", description="Python logging level")
    dangerously_omit_auth: bool = Field(
        default=False,
        description="ONLY for local dev/tests: allow running without a token",
    )
    validate_urls: bool = Field(
        default=False,
        description=(
            "When true, perform a lightweight HEAD check for URLs before calling "
            "the API (may slow calls)."
        ),
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

    @field_validator("stars_user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        normalized = v.strip()
        if not normalized:
            raise ValueError("STARS_USER_AGENT must not be empty")
        return normalized


settings = Settings()
