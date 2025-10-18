"""MCP tool to delete a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from .. import shared
from ..shared import mcp

logger = structlog.get_logger(__name__)


class DeleteLinkArgs(BaseModel):
    id: str


async def delete_link_impl(link_id: str) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = DeleteLinkArgs(id=link_id)
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    result = await shared.stars_client.delete_link(payload.id)
    if result.get("ok"):
        return {"success": True, "data": result.get("data")}
    return {"success": False, "error": result.get("error")}


@mcp.tool()
async def delete_link(id: str) -> dict:
    """
    Delete a link from GitHub Stars profile.

    Args:
        id: The ID of the link to delete
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await delete_link_impl(id)
