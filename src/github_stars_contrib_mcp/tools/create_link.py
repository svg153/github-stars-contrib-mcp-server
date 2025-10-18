"""MCP tool to create a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from .. import shared
from ..models import PlatformType
from ..shared import mcp

logger = structlog.get_logger(__name__)


class CreateLinkArgs(BaseModel):
    link: HttpUrl
    platform: PlatformType = Field(description="Platform type, one of: GITHUB, LINKEDIN, TWITTER, WEBSITE, OTHER")


async def create_link_impl(link: str, platform: str) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = CreateLinkArgs(link=link, platform=platform)
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    result = await shared.stars_client.create_link(str(payload.link), payload.platform)
    if result.get("ok"):
        return {"success": True, "data": result.get("data")}
    return {"success": False, "error": result.get("error")}


@mcp.tool()
async def create_link(link: str, platform: str) -> dict:
    """
    Create a link in GitHub Stars profile.

    Args:
        link: The URL of the link
        platform: Platform type (GITHUB, LINKEDIN, TWITTER, WEBSITE, OTHER)
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await create_link_impl(link, platform)
