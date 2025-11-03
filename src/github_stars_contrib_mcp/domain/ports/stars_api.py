"""Port for interacting with GitHub Stars API.

Defines the abstract contract the application layer depends on.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StarsAPIPort(Protocol):
    async def get_user_data(self) -> dict[str, Any]:
        """Return the raw JSON-like dict for the logged user data.

        On error, should raise an exception specific to the adapter or return
        a structured error at the adapter boundary (adapters may wrap).
        Application layer will normalize/handle exceptions.
        """
        ...

    async def get_user(self) -> dict[str, Any]:
        """Return the logged user data including nominations."""
        ...

    async def get_stars(self, username: str) -> dict[str, Any]:
        """Return the public profile stars for the given username."""
        ...

    # Contributions
    async def create_contribution(self, *, type: str, date: str, title: str, url: str, description: str | None) -> dict[str, Any]:
        """Create a single contribution and return the raw GraphQL data dict."""
        ...

    async def create_contributions(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """Create multiple contributions; returns data dict, typically containing ids."""
        ...

    async def update_contribution(self, contribution_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a single contribution and return data dict."""
        ...

    async def delete_contribution(self, contribution_id: str) -> dict[str, Any]:
        """Delete a single contribution and return data dict."""
        ...

    # Links
    async def create_link(self, link: str, platform: str) -> dict[str, Any]:
        ...

    async def update_link(self, link_id: str, link: str | None, platform: str | None) -> dict[str, Any]:
        ...

    async def delete_link(self, link_id: str) -> dict[str, Any]:
        ...

    # Profile
    async def update_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        ...
