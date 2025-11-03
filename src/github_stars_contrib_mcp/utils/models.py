"""Data models for the GitHub Stars MCP server."""

from dataclasses import dataclass
from typing import Any


@dataclass
class APIResult:
    """Result of an API operation."""
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None

    def __getitem__(self, key: str):
        """Allow dict-like access for backward compatibility."""
        return getattr(self, key)

    def get(self, key: str, default=None):
        """Dict-like get method."""
        return getattr(self, key, default)