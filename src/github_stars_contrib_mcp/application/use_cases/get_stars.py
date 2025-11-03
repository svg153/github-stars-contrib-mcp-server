from __future__ import annotations

from typing import Any

from ...domain.ports.stars_api import StarsAPIPort


class GetStars:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self, username: str) -> dict[str, Any]:
        if not username or not username.strip():
            raise ValueError("username is required")
        return await self._api.get_stars(username.strip())
