"""Application settings (12-factor) for Stars MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def _default_discovery_db_path() -> str:
    """Return a platform-appropriate local data path without creating it."""

    home = Path.home()
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or home / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or home / ".local" / "share")
    return str(base / "github-stars-contrib-mcp-server" / "discovery.db")


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
    discovery_db_path: str = Field(
        default_factory=_default_discovery_db_path,
        description=(
            "Local SQLite database used for discovery sources, candidates, and runs"
        ),
    )
    github_discovery_token: str | None = Field(
        default=None,
        description=(
            "Optional dedicated GitHub REST token for discovery; never reuses "
            "STARS_API_TOKEN implicitly"
        ),
    )
    youtube_api_key: str | None = Field(
        default=None,
        description=(
            "Optional YouTube Data API v3 key for full channel discovery; when absent "
            "only the limited public Atom feed is available for canonical channel IDs"
        ),
    )
    discovery_fetch_connect_timeout_s: float = Field(default=3.0, gt=0, le=30)
    discovery_fetch_read_timeout_s: float = Field(default=10.0, gt=0, le=60)
    discovery_fetch_max_bytes: int = Field(default=1_000_000, ge=1_024, le=10_000_000)
    discovery_fetch_max_redirects: int = Field(default=3, ge=0, le=10)
    discovery_untrusted_excerpt_max_chars: int = Field(default=6_000, ge=256, le=50_000)
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
