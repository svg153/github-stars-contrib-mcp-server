"""MCP tool to create a link via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from ..application.use_cases.create_link import CreateLink
from ..di.container import get_stars_api
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

    try:
        use_case = CreateLink(get_stars_api())
        # Ensure platform is passed as raw string value (e.g., "OTHER")
        data = await use_case(str(payload.link), payload.platform.value)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
