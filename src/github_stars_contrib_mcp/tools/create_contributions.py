"""MCP tool to create contributions via GitHub Stars GraphQL API."""

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


class CreateContributionsArgs(BaseModel):
    data: list[ContributionInput]


async def create_contributions_impl(data: list[dict]) -> dict:
    """Implementation: validates input and calls Stars API client."""
    try:
        payload = CreateContributionsArgs(data=[ContributionInput(**item) for item in data])
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if not shared.stars_client:
        return {"success": False, "error": "Stars client not initialized"}

    items = [
        {
            "title": i.title,
            "url": str(i.url),
            "description": i.description,
            "type": i.type,
            "date": i.date.isoformat(),
        }
        for i in payload.data
    ]

    result = await shared.stars_client.create_contributions(items)
    if result.ok:
        return {"success": True, "ids": result.ids}
    return {"success": False, "error": result.error}


@mcp.tool()
async def create_contributions(data: list[dict]) -> dict:
    """
    Create one or more contributions in GitHub Stars profile.

    Args:
        data: List of contribution items with keys: title, url, description?, type, date (ISO)
    Returns:
        { "ids": [...], "success": true }
    """
    return await create_contributions_impl(data)
