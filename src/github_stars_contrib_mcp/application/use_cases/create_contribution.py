from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class CreateContribution:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(
        self, *, type: str, date: str, title: str, url: str, description: str | None
    ) -> dict:
        return await self._api.create_contribution(
            type=type, date=date, title=title, url=url, description=description
        )
