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

    def __getattr__(self, name: str):
        """Proxy attribute access to keys inside `data`.

        This allows convenient access like `result.ids` when
        the payload is returned under `data = {"ids": [...]}`.
        """
        if name in {"ok", "data", "error"}:
            return super().__getattribute__(name)
        if self.data and isinstance(self.data, dict) and name in self.data:
            return self.data[name]
        raise AttributeError(name)
