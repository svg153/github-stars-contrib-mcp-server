"""MCP tool to delete a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from ..application.use_cases.delete_link import DeleteLink
from ..di.container import get_stars_api
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

    try:
        use_case = DeleteLink(get_stars_api())
        data = await use_case(payload.id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
