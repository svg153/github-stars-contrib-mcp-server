"""Tool facade using DI + use case to get logged user data.

This does not replace existing tools yet; it demonstrates the new wiring.
"""
from __future__ import annotations

from typing import Any

from ...application.use_cases.get_user_data import GetUserData
from ...di.container import get_stars_api


async def run() -> dict[str, Any]:
    use_case = GetUserData(get_stars_api())
    return await use_case()
