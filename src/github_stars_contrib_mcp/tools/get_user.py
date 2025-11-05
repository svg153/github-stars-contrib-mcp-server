"""MCP tool to fetch logged user data including nominations from GitHub Stars GraphQL API.

Refactored to use the Clean Architecture path (DI → use case → adapter).
"""

from __future__ import annotations

import structlog

from ..application.use_cases.get_user import GetUser
from ..di.container import get_stars_api
from ..observability import MetricsCollector, get_tracer
from ..shared import mcp

logger = structlog.get_logger(__name__)


async def get_user_impl() -> dict:
    """Implementation: call Stars API via use case to get current logged user data with nominations."""
    tracer = get_tracer()

    with tracer.span("get_user") as span:
        logger.info("Getting user data")
        try:
            use_case = GetUser(get_stars_api())
            data = await use_case()

            tracer.add_event(
                span,
                "user_fetched",
                {"has_data": data is not None and data.get("loggedUser") is not None},
            )

            if data.get("loggedUser") is None:
                # If loggedUser is null, return success with empty data instead of error
                return {"success": True, "data": None}
            return {"success": True, "data": data}
        except Exception as e:
            logger.error(
                "get_user.failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            MetricsCollector.record_error("API_ERROR", "/user")
            tracer.add_event(
                span,
                "error",
                {"error": str(e), "type": type(e).__name__},
            )
            return {"success": False, "error": str(e), "data": None}


@mcp.tool()
async def get_user() -> dict:
    """
    Get the currently logged user's data including nominations from the Stars API.

    Returns:
        { "success": boolean, "data": object | null, "error": string | null }
    """
    return await get_user_impl()
