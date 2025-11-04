"""MCP tool to fetch logged user data including nominations from GitHub Stars GraphQL API.

Refactored to use the Clean Architecture path (DI → use case → adapter).
"""

from __future__ import annotations

import structlog

from ..application.use_cases.get_user import GetUser
from ..di.container import get_stars_api
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_user_impl() -> dict:
    """Implementation: call Stars API via use case to get current logged user data with nominations."""
    logger.info("Getting user data")
    try:
        use_case = GetUser(get_stars_api())
        data = await use_case()
        if data.get("loggedUser") is None:
            # If loggedUser is null, return success with empty data instead of error
            return {"success": True, "data": None}
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "data": None}


@mcp.tool()
async def get_user() -> dict:
    """
    Get the currently logged user's data including nominations from the Stars API.

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_user_impl()
