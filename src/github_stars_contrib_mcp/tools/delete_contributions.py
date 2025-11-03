"""MCP tool to delete a contribution via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from ..application.use_cases.delete_contribution import DeleteContribution
from ..di.container import get_stars_api
from ..shared import mcp

logger = structlog.get_logger(__name__)


class DeleteContributionArgs(BaseModel):
    id: str


async def delete_contribution_impl(contribution_id: str) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = DeleteContributionArgs(id=contribution_id)
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    try:
        use_case = DeleteContribution(get_stars_api())
        data = await use_case(payload.id)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def delete_contribution(id: str) -> dict:
    """
    Delete a single contribution from GitHub Stars profile.

    Args:
        id: The ID of the contribution to delete
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await delete_contribution_impl(id)
