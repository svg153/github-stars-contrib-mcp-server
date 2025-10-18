"""MCP tool to update a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, HttpUrl, ValidationError

from .. import shared
from ..models import PlatformType
from ..shared import mcp

logger = structlog.get_logger(__name__)


class UpdateLinkInput(BaseModel):
    link: HttpUrl | None = None
    platform: PlatformType | None = None


class UpdateLinkArgs(BaseModel):
    id: str
    data: UpdateLinkInput


async def update_link_impl(link_id: str, data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = UpdateLinkArgs(id=link_id, data=UpdateLinkInput(**data))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    # Convert to dict
    update_data = payload.data.model_dump()
    if update_data.get("link"):
        update_data["link"] = str(update_data["link"])

    result = await shared.stars_client.update_link(payload.id, update_data.get("link"), update_data.get("platform"))
    if result.get("ok"):
        return {"success": True, "data": result.get("data")}
    return {"success": False, "error": result.get("error")}


@mcp.tool()
async def update_link(link_id: str, data: dict) -> dict:
    """
    Update a link in GitHub Stars profile.

    Args:
        link_id: The ID of the link to update
        data: Dictionary with optional fields to update: link (URL), platform (GITHUB, LINKEDIN, TWITTER, WEBSITE, OTHER)
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await update_link_impl(link_id, data)
