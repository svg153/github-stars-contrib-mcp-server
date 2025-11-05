"""MCP tool to delete a contribution via GitHub Stars GraphQL API."""

from __future__ import annotations

import structlog
from pydantic import BaseModel, ValidationError

from ..application.use_cases.delete_contribution import DeleteContribution
from ..di.container import get_stars_api
from ..observability import MetricsCollector, get_tracer
from ..shared import mcp

logger = structlog.get_logger(__name__)


class DeleteContributionArgs(BaseModel):
    id: str


async def delete_contribution_impl(contribution_id: str) -> dict:
    """Implementation: validates input and calls Stars API client."""
    tracer = get_tracer()

    with tracer.span("delete_contribution", {"contribution_id": contribution_id}):
        logger.info("Deleting contribution", contribution_id=contribution_id)
        try:
            payload = DeleteContributionArgs(id=contribution_id)
        except ValidationError as e:
            MetricsCollector.record_error("VALIDATION_ERROR", "/contributions")
            return {"success": False, "error": e.errors()}

        try:
            use_case = DeleteContribution(get_stars_api())
            result = await use_case(payload.id)

            # Record metrics
            MetricsCollector.record_contribution_deleted()

            return {"success": True, "data": result}
        except Exception as e:
            logger.error(
                "delete_contribution.failed",
                contribution_id=contribution_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            MetricsCollector.record_error("API_ERROR", "/contributions")
            return {"success": False, "error": str(e)}


@mcp.tool()
async def delete_contribution(id: str) -> dict:
    """
    Delete a single contribution from GitHub Stars profile.

    Args:
        id: The ID of the contribution to delete
    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await delete_contribution_impl(id)
