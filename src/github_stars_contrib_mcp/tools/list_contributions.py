"""MCP tool to list authenticated GitHub Stars contributions via REST."""

from __future__ import annotations

from ..di.container import get_stars_api
from ..shared import mcp


async def list_contributions_impl(page: int = 1) -> dict:
    """Implementation used by the MCP wrapper and local/integration tests."""
    if page < 1:
        return {"success": False, "error": "page must be >= 1"}
    try:
        result = await get_stars_api().list_contributions(page)
        return {"success": True, "data": result}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def list_contributions(page: int = 1) -> dict:
    """List the authenticated Star's contributions from the current REST API."""
    return await list_contributions_impl(page)
