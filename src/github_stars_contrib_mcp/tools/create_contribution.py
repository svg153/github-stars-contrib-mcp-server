"""MCP tool to create a single contribution via GitHub Stars GraphQL API."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from ..application.use_cases.create_contribution import CreateContribution
from ..di.container import get_stars_api
from ..models import ContributionType
from ..shared import mcp
from ..utils.normalization import normalize_description

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

    try:
        use_case = CreateContribution(get_stars_api())
        data = await use_case(
            type=str(payload.type),
            date=payload.date.isoformat(),
            title=payload.title,
            url=str(payload.url),
            description=normalize_description(payload.description),
        )
        return {"success": True, "contribution": data.get("createContribution")}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
