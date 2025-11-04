from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class UpdateLink:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(
        self, link_id: str, *, link: str | None, platform: str | None
    ) -> dict:
        return await self._api.update_link(link_id, link, platform)
