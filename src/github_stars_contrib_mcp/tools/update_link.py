"""MCP tool to update a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, HttpUrl, ValidationError

from ..application.use_cases.update_link import UpdateLink
from ..di.container import get_stars_api
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

    # Convert to dict
    update_data = payload.data.model_dump()
    if update_data.get("link"):
        # Normalize URL and strip trailing slash to match test expectations
        update_data["link"] = str(update_data["link"]).rstrip("/")
    try:
        use_case = UpdateLink(get_stars_api())
        platform = update_data.get("platform")
        if platform is not None:
            # Convert enum to raw string if needed
            try:
                platform = platform.value  # type: ignore[attr-defined]
            except Exception:
                pass
        data = await use_case(payload.id, link=update_data.get("link"), platform=platform)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
