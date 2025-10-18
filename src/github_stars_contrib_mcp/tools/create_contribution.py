"""MCP tool to create a single contribution via GitHub Stars GraphQL API."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from .. import shared
from ..models import ContributionType
from ..shared import mcp

logger = structlog.get_logger(__name__)


class ContributionInput(BaseModel):
    title: str
    url: HttpUrl
    description: str | None = None
    type: ContributionType = Field(description="Contribution type, one of: SPEAKING, BLOGPOST, ARTICLE_PUBLICATION, EVENT_ORGANIZATION, HACKATHON, OPEN_SOURCE_PROJECT, VIDEO_PODCAST, FORUM, OTHER")
    date: datetime


async def create_contribution_impl(data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = ContributionInput(**data)
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    result = await shared.stars_client.create_contribution(
        type=payload.type,
        date=payload.date.isoformat(),
        title=payload.title,
        url=str(payload.url),
        description=payload.description or ""
    )
    if result["ok"]:
        return {"success": True, "contribution": result["data"]["createContribution"]}
    return {"success": False, "error": result["error"]}


@mcp.tool()
async def create_contribution(data: dict) -> dict:
    """
    Create a single contribution in GitHub Stars profile.

    Args:
        data: Contribution item with keys: title, url, description?, type, date (ISO)
    Returns:
        { "contribution": {...}, "success": true }
    """
    return await create_contribution_impl(data)