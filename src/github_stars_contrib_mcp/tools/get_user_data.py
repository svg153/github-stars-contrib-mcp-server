"""MCP tool to fetch logged user data from GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog

from .. import shared
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_user_data_impl() -> dict:
    """Implementation: call Stars API to get current logged user data."""
    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized", "data": None}

    res = await shared.stars_client.get_user_data()
    if res.get("ok"):
        data = res.get("data") or {}
        if data.get("loggedUser") is None:
            return {
                "success": False,
                "error": "Not authenticated or invalid token: loggedUser is null",
                "data": None,
            }
        return {"success": True, "data": data}
    return {"success": False, "error": res.get("error"), "data": None}


@mcp.tool()
async def get_user_data() -> dict:
    """
    Get the currently logged user's data (profile, nominee, contributions) from the Stars API.

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_user_data_impl()
