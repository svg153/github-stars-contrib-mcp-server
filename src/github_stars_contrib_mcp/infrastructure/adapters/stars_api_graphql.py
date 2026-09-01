"""Hybrid GitHub Stars API adapter.

Contributions use the September 2026 REST API. Profile, link and public-profile
operations continue to use the GraphQL calls in StarsClient until GitHub
publishes equivalent supported REST endpoints for those surfaces. The module
name is retained to avoid an unrelated import-path break.
"""

from __future__ import annotations

from typing import Any

from ...domain.ports.stars_api import StarsAPIPort
from ...utils.stars_client import StarsClient


class StarsAPIAdapter(StarsAPIPort):
    def __init__(self, client: StarsClient) -> None:
        self._client = client

    @staticmethod
    def _unwrap(res: Any) -> dict[str, Any]:
        if not res.ok:
            raise RuntimeError(res.error or "Unknown Stars API error")
        return res.data or {}

    async def get_user_data(self) -> dict[str, Any]:
        return self._unwrap(await self._client.get_user_data())

    async def get_user(self) -> dict[str, Any]:
        return self._unwrap(await self._client.get_user())

    async def get_stars(self, username: str) -> dict[str, Any]:
        return self._unwrap(await self._client.get_stars(username))

    async def list_contributions(self, page: int = 1) -> dict[str, Any]:
        return self._unwrap(await self._client.list_contributions(page))

    async def create_contribution(
        self, *, type: str, date: str, title: str, url: str, description: str | None
    ) -> dict[str, Any]:
        return self._unwrap(
            await self._client.create_contribution(
                type=type,
                date=date,
                title=title,
                url=url,
                description=description or "",
            )
        )

    async def create_contributions(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        return self._unwrap(await self._client.create_contributions(items))

    async def upsert_contribution(
        self, client_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        return self._unwrap(await self._client.upsert_contribution(client_id, data))

    async def create_link(self, link: str, platform: str) -> dict[str, Any]:
        return self._unwrap(await self._client.create_link(link, platform))

    async def update_link(
        self, link_id: str, link: str | None, platform: str | None
    ) -> dict[str, Any]:
        return self._unwrap(
            await self._client.update_link(link_id, link or "", platform or "")
        )

    async def delete_link(self, link_id: str) -> dict[str, Any]:
        return self._unwrap(await self._client.delete_link(link_id))

    async def update_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._unwrap(await self._client.update_profile(data))
