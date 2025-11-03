from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class CreateLink:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self, link: str, platform: str) -> dict:
        return await self._api.create_link(link, platform)
