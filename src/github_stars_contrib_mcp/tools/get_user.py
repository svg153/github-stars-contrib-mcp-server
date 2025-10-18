"""MCP tool to fetch logged user data including nominations from GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog

from .. import shared
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_user_impl() -> dict:
    """Implementation: call Stars API to get current logged user data with nominations."""
    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized", "data": None}

    res = await shared.stars_client.get_user()
    if res.get("ok"):
        data = res.get("data") or {}
        if data.get("loggedUser") is None:
            # If loggedUser is null, return success with empty data instead of error
            return {"success": True, "data": None}
        return {"success": True, "data": data}
    return {"success": False, "error": res.get("error"), "data": None}


@mcp.tool()
async def get_user() -> dict:
    """
    Get the currently logged user's data including nominations from the Stars API.

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_user_impl()