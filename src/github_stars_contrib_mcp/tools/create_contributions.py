"""MCP tool to create contributions through the GitHub Stars REST API."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from ..application.use_cases.create_contributions import CreateContributions
from ..config.settings import settings
from ..di.container import get_stars_api
from ..models import ContributionType
from ..shared import mcp
from ..utils.normalization import normalize_description
from ..utils.url_check import check_url_head

logger = structlog.get_logger(__name__)


class ContributionInput(BaseModel):
    title: str
    url: HttpUrl
    description: str | None = None
    type: ContributionType = Field(
        description="Contribution type, one of: SPEAKING, BLOGPOST, ARTICLE_PUBLICATION, EVENT_ORGANIZATION, HACKATHON, OPEN_SOURCE_PROJECT, VIDEO_PODCAST, FORUM, OTHER"
    )
    date: datetime


class CreateContributionsArgs(BaseModel):
    data: list[ContributionInput]


async def create_contributions_impl(data: list[dict]) -> dict:
    """Validate input and create one REST batch."""
    try:
        payload = CreateContributionsArgs(
            data=[ContributionInput(**item) for item in data]
        )
    except ValidationError as exc:
        return {"success": False, "error": exc.errors()}

    items = []
    for item in payload.data:
        if settings.validate_urls:
            ok, reason = await check_url_head(
                str(item.url), timeout_s=settings.url_validation_timeout_s
            )
            if not ok:
                logger.warning(
                    "create_contributions.url_invalid",
                    url=str(item.url),
                    reason=reason,
                )
                return {
                    "success": False,
                    "error": f"Invalid URL ({reason}) for: {item.url}",
                }
        items.append(
            {
                "title": item.title,
                "url": str(item.url),
                "description": normalize_description(item.description),
                "type": item.type.value,
                "date": item.date.isoformat(),
            }
        )

    try:
        result = await CreateContributions(get_stars_api())(items)
        return {"success": True, "ids": (result or {}).get("ids", [])}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def create_contributions(data: list[dict]) -> dict:
    """Create one or more contributions in one REST POST request."""
    return await create_contributions_impl(data)
