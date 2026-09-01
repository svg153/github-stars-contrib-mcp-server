from __future__ import annotations

from ...domain.ports.stars_api import StarsAPIPort


class UpsertContribution:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self, client_id: str, data: dict) -> dict:
        return await self._api.upsert_contribution(client_id, data)
