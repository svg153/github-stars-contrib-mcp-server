"""Contribution statistics with an optional MCP Apps visualization."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

import structlog
from mcp.types import EmbeddedResource, TextResourceContents
from pydantic import BaseModel, Field, ValidationError

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..shared import mcp
from ..utils.plotly_charts import PlotlyChartGenerator

logger = structlog.get_logger(__name__)
MCP_APP_HTML_MIME_TYPE = "text/html;profile=mcp-app"


class StatsArgs(BaseModel):
    username: str
    group_by: str | None = Field(default=None)
    include_ui: bool = False


async def get_contributions_stats_impl(
    args: dict[str, Any],
) -> dict | list[EmbeddedResource]:
    try:
        payload = StatsArgs(**(args or {}))
    except ValidationError as exc:
        return {"success": False, "error": exc.errors()}

    if payload.group_by not in {None, "type", "month", "year"}:
        return {"success": False, "error": "group_by must be type, month, or year"}

    try:
        raw = await GetStars(get_stars_api())(payload.username)
    except Exception as exc:
        logger.warning("stats.fetch_failed", error=str(exc))
        return {"success": False, "error": str(exc)}

    items = ((raw or {}).get("publicProfile") or {}).get("contributions") or []
    stats = _compute_stats(items, payload.group_by)
    if payload.include_ui:
        return _create_ui(payload.username, stats)
    return {"success": True, "data": stats}


def _compute_stats(items: list[dict[str, Any]], group_by: str | None) -> dict[str, Any]:
    by_type = Counter(str(item.get("type") or "UNKNOWN") for item in items)
    dates = [_parse_date(item.get("date")) for item in items]
    valid_dates = [date for date in dates if date is not None]
    date_range = None
    if valid_dates:
        date_range = {
            "earliest": min(valid_dates).isoformat(),
            "latest": max(valid_dates).isoformat(),
        }

    grouped: dict[str, Any] = {}
    if group_by == "type":
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            buckets[str(item.get("type") or "UNKNOWN")].append(item)
        grouped = dict(buckets)
    elif group_by in {"month", "year"}:
        counts: Counter[str] = Counter()
        for item in items:
            date = _parse_date(item.get("date"))
            if date is not None:
                key = date.strftime("%Y-%m" if group_by == "month" else "%Y")
                counts[key] += 1
        grouped = {key: {"count": count} for key, count in sorted(counts.items())}

    return {
        "total_count": len(items),
        "by_type": dict(by_type),
        "date_range": date_range,
        "grouped": grouped,
    }


def _parse_date(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _create_ui(username: str, stats: dict[str, Any]) -> list[EmbeddedResource]:
    if not stats["total_count"]:
        html = f"<html><body><h1>No contributions for @{username}</h1></body></html>"
    else:
        labels = list(stats["by_type"].keys())
        values = list(stats["by_type"].values())
        html = PlotlyChartGenerator.pie_chart(
            labels=labels,
            values=values,
            title=f"Contributions for @{username}",
        )

    resource = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=f"ui://contributions-stats/{username}",
            mime_type=MCP_APP_HTML_MIME_TYPE,
            text=html,
        ),
    )
    return [resource]


@mcp.tool()
async def get_contributions_stats(
    args: dict[str, Any],
) -> dict | list[EmbeddedResource]:
    """Return contribution statistics, optionally as an MCP Apps resource."""
    return await get_contributions_stats_impl(args)
