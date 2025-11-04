"""GraphQL adapter implementing StarsAPIPort using the existing StarsClient."""

from __future__ import annotations

from typing import Any

from ...domain.ports.stars_api import StarsAPIPort
from ...utils.stars_client import StarsClient


class StarsAPIAdapter(StarsAPIPort):
    def __init__(self, client: StarsClient) -> None:
        self._client = client

    async def get_user_data(self) -> dict[str, Any]:
        res = await self._client.get_user_data()
        if not res.ok:
            # Bubble up as exception to simplify use case; could define custom errors
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def get_user(self) -> dict[str, Any]:
        res = await self._client.get_user()
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def get_stars(self, username: str) -> dict[str, Any]:
        res = await self._client.get_stars(username)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    # Contributions
    async def create_contribution(
        self, *, type: str, date: str, title: str, url: str, description: str | None
    ) -> dict[str, Any]:
        res = await self._client.create_contribution(
            type=type, date=date, title=title, url=url, description=description or ""
        )
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def create_contributions(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        res = await self._client.create_contributions(items)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def update_contribution(
        self, contribution_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        res = await self._client.update_contribution(contribution_id, data)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def delete_contribution(self, contribution_id: str) -> dict[str, Any]:
        res = await self._client.delete_contribution(contribution_id)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    # Links
    async def create_link(self, link: str, platform: str) -> dict[str, Any]:
        res = await self._client.create_link(link, platform)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def update_link(
        self, link_id: str, link: str | None, platform: str | None
    ) -> dict[str, Any]:
        res = await self._client.update_link(link_id, link or "", platform or "")
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def delete_link(self, link_id: str) -> dict[str, Any]:
        res = await self._client.delete_link(link_id)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    # Profile
    async def update_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        res = await self._client.update_profile(data)
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}
