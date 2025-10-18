"""MCP tool to fetch public profile stars/contributions from GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog

from .. import shared
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_stars_impl(username: str) -> dict:
    """Implementation: call Stars API to get public profile stars for a user."""
    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized", "data": None}

    res = await shared.stars_client.get_stars(username)
    if res.get("ok"):
        data = res.get("data") or {}
        return {"success": True, "data": data}
    return {"success": False, "error": res.get("error"), "data": None}


@mcp.tool()
async def get_stars(username: str) -> dict:
    """
    Get the public profile stars/contributions for a GitHub user from the Stars API.

    Args:
        username: The GitHub username to fetch stars for

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_stars_impl(username)
