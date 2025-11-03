from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class DeleteLink:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self, link_id: str) -> dict:
        return await self._api.delete_link(link_id)
