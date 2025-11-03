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

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return normalized


# Global settings instance, exported by the package in __init__.py
settings = Settings()
