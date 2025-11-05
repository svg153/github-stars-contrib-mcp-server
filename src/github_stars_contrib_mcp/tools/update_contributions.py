"""MCP tool to update a contribution via GitHub Stars GraphQL API."""

from __future__ import annotations

from datetime import datetime

import structlog
from pydantic import BaseModel, HttpUrl, ValidationError

from ..application.use_cases.update_contribution import UpdateContribution
from ..di.container import get_stars_api
from ..models import ContributionType
from ..observability import MetricsCollector, get_tracer
from ..shared import mcp

logger = structlog.get_logger(__name__)


class UpdateContributionInput(BaseModel):
    title: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    type: ContributionType | None = None
    date: datetime | None = None


class UpdateContributionArgs(BaseModel):
    id: str
    data: UpdateContributionInput


async def update_contribution_impl(contribution_id: str, data: dict) -> dict:
    """Implementation: validates input and calls Stars API client."""
    tracer = get_tracer()

    with tracer.span("update_contribution", {"contribution_id": contribution_id}):
        logger.info("Updating contribution", contribution_id=contribution_id, data=data)
        try:
            payload = UpdateContributionArgs(
                id=contribution_id, data=UpdateContributionInput(**data)
            )
        except ValidationError as e:
            MetricsCollector.record_error("VALIDATION_ERROR", "/contributions")
            return {"success": False, "error": e.errors()}

        # Convert to dict, handling datetime
        update_data = payload.data.model_dump()
        if update_data.get("date"):
            update_data["date"] = update_data["date"].isoformat()
        if update_data.get("url"):
            update_data["url"] = str(update_data["url"])
        try:
            use_case = UpdateContribution(get_stars_api())
            result = await use_case(payload.id, update_data)

            # Record metrics
            if update_data.get("type"):
                MetricsCollector.record_contribution_updated(update_data["type"])

            return {"success": True, "data": result}
        except Exception as e:
            logger.error(
                "update_contribution.failed",
                contribution_id=contribution_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            MetricsCollector.record_error("API_ERROR", "/contributions")
            return {"success": False, "error": str(e)}


@mcp.tool()
async def update_contribution(contribution_id: str, data: dict) -> dict:
    """
    Update a single contribution in GitHub Stars profile.

    Args:
        contribution_id: The ID of the contribution to update
        data: Dictionary with optional fields to update: title, url, description, type, date (ISO string)
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await update_contribution_impl(contribution_id, data)
