from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class UpdateContribution:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self, contribution_id: str, data: dict) -> dict:
        return await self._api.update_contribution(contribution_id, data)
