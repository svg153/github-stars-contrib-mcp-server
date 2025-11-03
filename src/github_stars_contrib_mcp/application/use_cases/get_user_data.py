"""Use case: Get logged user data from Stars API.

Depends on StarsAPIPort (domain/ports).
"""

from __future__ import annotations

from typing import Any

from ...domain.ports.stars_api import StarsAPIPort


class GetUserData:
    def __init__(self, stars_api: StarsAPIPort) -> None:
        self._api = stars_api

    async def __call__(self) -> dict[str, Any]:
        # Thin orchestrator; errors bubble up to caller/presentation layer
        return await self._api.get_user_data()
