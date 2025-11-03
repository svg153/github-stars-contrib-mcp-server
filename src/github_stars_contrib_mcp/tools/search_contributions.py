"""MCP tool to search/filter contributions from public profile data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..shared import mcp

logger = structlog.get_logger(__name__)


class SearchArgs(BaseModel):
    username: str | None = Field(default=None, description="GitHub username to query")
    type: str | None = Field(
        default=None, description="Contribution type to match exactly"
    )
    title_contains: str | None = Field(
        default=None, description="Substring to match in the title (case-insensitive)"
    )
    date_from: str | None = Field(
        default=None, description="Lower date bound (inclusive), ISO date or YYYY-MM-DD"
    )
    date_to: str | None = Field(
        default=None, description="Upper date bound (inclusive), ISO date or YYYY-MM-DD"
    )


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # Accept full ISO or YYYY-MM-DD
        if len(s) == 10:
            # Treat date-only as midnight UTC to ensure tz-aware comparisons
            return datetime.fromisoformat(s).replace(tzinfo=UTC)
        # Normalize trailing Z to +00:00 to get tz-aware datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        raise ValueError("Invalid date format. Use ISO 8601 or YYYY-MM-DD") from None


def _extract_contributions(data: dict[str, Any]) -> list[dict[str, Any]]:
    profile = (data or {}).get("publicProfile") or {}
    items = profile.get("contributions")
    return items or []


async def search_contributions_impl(args: dict[str, Any]) -> dict:
    try:
        payload = SearchArgs(**(args or {}))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    # Fetch source data
    try:
        use_case = GetStars(get_stars_api())
        # For now require username explicitly (public data)
        if not payload.username:
            return {"success": False, "error": "username is required"}
        raw = await use_case(payload.username)
    except Exception as e:
        return {"success": False, "error": str(e)}

    try:
        t_from = _parse_date(payload.date_from)
        t_to = _parse_date(payload.date_to)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    items = _extract_contributions(raw or {})
    if not items:
        return {"success": True, "data": []}

    def match(item: dict[str, Any]) -> bool:
        # type match
        if payload.type and (str(item.get("type")) != payload.type):
            return False

        # title substring (case-insensitive)
        if payload.title_contains:
            title = str(item.get("title") or "")
            if payload.title_contains.lower() not in title.lower():
                return False

        # date range
        if t_from or t_to:
            try:
                d = _parse_date(str(item.get("date")))
            except Exception:
                return False
            if d is None:
                return False
            if t_from and d < t_from:
                return False
            if t_to and d > t_to:
                return False

        return True

    matched = [it for it in items if match(it)]
    logger.info(
        "search_contributions.result",
        input_count=len(items),
        matched_count=len(matched),
    )
    return {"success": True, "data": matched}


@mcp.tool()
async def search_contributions(args: dict[str, Any]) -> dict:
    """
    Search contributions from a user's public Stars profile using local filters.

    Args:
        args: { username?: str, type?: str, title_contains?: str, date_from?: str, date_to?: str }
    Returns:
        { "success": boolean, "data": list, "error"?: string }
    """
    return await search_contributions_impl(args)
