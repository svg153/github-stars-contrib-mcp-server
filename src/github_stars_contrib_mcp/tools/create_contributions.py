"""MCP tool to create contributions via GitHub Stars GraphQL API."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from ..application.use_cases.create_contributions import CreateContributions
from ..di.container import get_stars_api
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
    try:
        use_case = CreateContributions(get_stars_api())
        data = await use_case(items)
        return {"success": True, "ids": (data or {}).get("ids", [])}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
