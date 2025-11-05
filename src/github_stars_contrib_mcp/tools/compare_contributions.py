"""MCP tool to compare contributions between two users."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..shared import mcp

logger = structlog.get_logger(__name__)


class CompareArgs(BaseModel):
    username1: str = Field(description="First GitHub username")
    username2: str = Field(description="Second GitHub username")
    metric: str | None = Field(
        default=None,
        description="Metric to compare: 'total', 'by_type', 'by_year', or None for detailed comparison",
    )


async def compare_contributions_impl(args: dict[str, Any]) -> dict:
    """Compare contributions between two users."""
    try:
        payload = CompareArgs(**(args or {}))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    if payload.username1 == payload.username2:
        return {"success": False, "error": "Cannot compare user with themselves"}

    use_case = GetStars(get_stars_api())

    # Fetch data for both users
    try:
        raw1 = await use_case(payload.username1)
        raw2 = await use_case(payload.username2)
    except Exception as e:
        logger.warning("compare.fetch_failed", error=str(e))
        return {"success": False, "error": str(e)}

    items1 = (raw1 or {}).get("publicProfile", {}).get("contributions") or []
    items2 = (raw2 or {}).get("publicProfile", {}).get("contributions") or []

    if not items1 or not items2:
        return {
            "success": True,
            "data": {
                "user1_count": len(items1),
                "user2_count": len(items2),
                "comparison": None,
            },
        }

    comparison = _compute_comparison(items1, items2, payload.metric)

    logger.info(
        "compare_contributions.result",
        user1=payload.username1,
        user2=payload.username2,
        metric=payload.metric,
        user1_count=len(items1),
        user2_count=len(items2),
    )

    return {
        "success": True,
        "data": {
            "user1": payload.username1,
            "user2": payload.username2,
            "user1_count": len(items1),
            "user2_count": len(items2),
            "comparison": comparison,
        },
    }


def _compute_comparison(
    items1: list[dict[str, Any]],
    items2: list[dict[str, Any]],
    metric: str | None,
) -> dict[str, Any]:
    """Compute comparison between two contribution lists."""

    if metric == "total":
        return {
            "metric": "total",
            "difference": len(items1) - len(items2),
            "ratio": len(items1) / len(items2) if len(items2) > 0 else float("inf"),
        }

    elif metric == "by_type":
        types1 = Counter(str(item.get("type") or "UNKNOWN") for item in items1)
        types2 = Counter(str(item.get("type") or "UNKNOWN") for item in items2)

        all_types = set(types1.keys()) | set(types2.keys())
        by_type = {}
        for t in sorted(all_types):
            count1 = types1.get(t, 0)
            count2 = types2.get(t, 0)
            by_type[t] = {
                "user1": count1,
                "user2": count2,
                "difference": count1 - count2,
            }

        return {"metric": "by_type", "by_type": by_type}

    elif metric == "by_year":
        years1 = _group_by_year(items1)
        years2 = _group_by_year(items2)

        all_years = set(years1.keys()) | set(years2.keys())
        by_year = {}
        for year in sorted(all_years, reverse=True):
            count1 = years1.get(year, 0)
            count2 = years2.get(year, 0)
            by_year[year] = {
                "user1": count1,
                "user2": count2,
                "difference": count1 - count2,
            }

        return {"metric": "by_year", "by_year": by_year}

    else:
        # Detailed comparison
        return {
            "metric": "detailed",
            "summary": {
                "total_difference": len(items1) - len(items2),
                "user1_total": len(items1),
                "user2_total": len(items2),
            },
            "by_type": _compare_by_type(items1, items2),
            "date_range": _compare_date_ranges(items1, items2),
        }


def _group_by_year(items: list[dict[str, Any]]) -> dict[str, int]:
    """Count contributions by year."""
    years = {}
    for item in items:
        try:
            d = datetime.fromisoformat(
                str(item.get("date") or "").replace("Z", "+00:00")
            )
            year = d.strftime("%Y")
            years[year] = years.get(year, 0) + 1
        except Exception:
            # Skip items with invalid or missing date formats
            pass
    return years


def _compare_by_type(
    items1: list[dict[str, Any]], items2: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare contributions by type."""
    types1 = Counter(str(item.get("type") or "UNKNOWN") for item in items1)
    types2 = Counter(str(item.get("type") or "UNKNOWN") for item in items2)

    all_types = set(types1.keys()) | set(types2.keys())
    result = {}
    for t in sorted(all_types):
        result[t] = {
            "user1": types1.get(t, 0),
            "user2": types2.get(t, 0),
        }

    return result


def _compare_date_ranges(
    items1: list[dict[str, Any]], items2: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compare date ranges of contributions."""

    def _extract_dates(
        items: list[dict[str, Any]],
    ) -> tuple[datetime | None, datetime | None]:
        dates = []
        for item in items:
            try:
                d = datetime.fromisoformat(
                    str(item.get("date") or "").replace("Z", "+00:00")
                )
                dates.append(d)
            except Exception:
                # Skip items with invalid date formats
                pass
        if not dates:
            return None, None
        return min(dates), max(dates)

    min1, max1 = _extract_dates(items1)
    min2, max2 = _extract_dates(items2)

    return {
        "user1": {
            "earliest": min1.isoformat() if min1 else None,
            "latest": max1.isoformat() if max1 else None,
        },
        "user2": {
            "earliest": min2.isoformat() if min2 else None,
            "latest": max2.isoformat() if max2 else None,
        },
    }


@mcp.tool()
async def compare_contributions(args: dict[str, Any]) -> dict:
    """
    Compare contributions between two users.

    Args:
        args: {
            "username1": str (required),
            "username2": str (required),
            "metric": "total" | "by_type" | "by_year" | None (optional, default: detailed)
        }

    Returns:
        {
            "success": boolean,
            "data": {
                "user1": str,
                "user2": str,
                "user1_count": int,
                "user2_count": int,
                "comparison": {
                    "metric": str,
                    ... (metric-specific fields)
                }
            },
            "error"?: string
        }
    """
    return await compare_contributions_impl(args)
