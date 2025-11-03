from __future__ import annotations

from typing import Any

from ...domain.ports.stars_api import StarsAPIPort


class GetUser:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self) -> dict[str, Any]:
        return await self._api.get_user()
