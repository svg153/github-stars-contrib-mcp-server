"""Port for interacting with GitHub Stars APIs."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StarsAPIPort(Protocol):
    async def get_user_data(self) -> dict[str, Any]: ...
    async def get_user(self) -> dict[str, Any]: ...
    async def get_stars(self, username: str) -> dict[str, Any]: ...

    async def list_contributions(self, page: int = 1) -> dict[str, Any]:
        """Return one authenticated REST contributions page."""
        ...

    async def create_contribution(
        self, *, type: str, date: str, title: str, url: str, description: str | None
    ) -> dict[str, Any]:
        """Create a single contribution via REST POST."""
        ...

    async def create_contributions(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Create multiple contributions via REST POST."""
        ...

    async def upsert_contribution(
        self, client_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Idempotently create/replace a full contribution by stable client ID."""
        ...

    async def create_link(self, link: str, platform: str) -> dict[str, Any]: ...

    async def update_link(
        self, link_id: str, link: str | None, platform: str | None
    ) -> dict[str, Any]: ...

    async def delete_link(self, link_id: str) -> dict[str, Any]: ...
    async def update_profile(self, data: dict[str, Any]) -> dict[str, Any]: ...
