"""MCP tool to fetch public profile stars/contributions from GitHub Stars GraphQL API.

Refactored to use the Clean Architecture path (DI → use case → adapter).
"""

from __future__ import annotations

import structlog

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..observability import MetricsCollector, get_tracer
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_stars_impl(username: str) -> dict:
    """Implementation: call Stars API via use case to get public profile stars for a user."""
    tracer = get_tracer()

    with tracer.span("get_stars", {"username": username}) as span:
        logger.info("Getting stars for user", username=username)
        try:
            use_case = GetStars(get_stars_api())
            data = await use_case(username)

            tracer.add_event(
                span,
                "stars_fetched",
                {
                    "username": username,
                    "has_data": data is not None,
                },
            )

            return {"success": True, "data": data}
        except Exception as e:
            logger.error(
                "get_stars.failed",
                username=username,
                error=str(e),
                error_type=type(e).__name__,
            )
            MetricsCollector.record_error("API_ERROR", f"/stars/{username}")
            tracer.add_event(
                span,
                "error",
                {"error": str(e), "type": type(e).__name__},
            )
            return {"success": False, "error": str(e), "data": None}


@mcp.tool()
async def get_stars(username: str) -> dict:
    """
    Get the public profile stars/contributions for a GitHub user from the Stars API.

    Args:
        username: The GitHub username to fetch stars for

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_stars_impl(username)
