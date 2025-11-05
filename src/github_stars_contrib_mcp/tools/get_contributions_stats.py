"""MCP tool to get contribution statistics and analytics with MCP-UI visualization."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

import structlog
from mcp_ui_server import create_ui_resource
from mcp_ui_server.core import UIResource
from pydantic import BaseModel, Field, ValidationError

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..shared import mcp
from ..utils.plotly_charts import PlotlyChartGenerator

logger = structlog.get_logger(__name__)


class StatsArgs(BaseModel):
    username: str = Field(description="GitHub username to analyze")
    group_by: str | None = Field(
        default=None,
        description="Group statistics by field: 'type', 'month', 'year', or None for total",
    )
    include_ui: bool = Field(
        default=False,
        description="Include interactive MCP-UI visualization with Plotly charts",
    )


async def get_contributions_stats_impl(args: dict[str, Any]) -> dict | list[UIResource]:
    """Get contribution statistics for a user with optional MCP-UI visualization."""
    try:
        payload = StatsArgs(**(args or {}))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    try:
        use_case = GetStars(get_stars_api())
        raw = await use_case(payload.username)
    except Exception as e:
        logger.warning("stats.fetch_failed", error=str(e))
        return {"success": False, "error": str(e)}

    profile = (raw or {}).get("publicProfile") or {}
    items = profile.get("contributions") or []

    if not items:
        result = {
            "success": True,
            "data": {
                "total_count": 0,
                "by_type": {},
                "date_range": None,
                "grouped": {},
            },
        }
        if payload.include_ui:
            return _create_empty_ui_resource(payload.username)
        return result

    stats = _compute_stats(items, payload.group_by)

    logger.info(
        "get_contributions_stats.result",
        username=payload.username,
        total_count=stats["total_count"],
        group_by=payload.group_by,
        include_ui=payload.include_ui,
    )

    if payload.include_ui:
        return _create_stats_ui_resource(stats, payload.username, payload.group_by)
    else:
        return {"success": True, "data": stats}


def _compute_stats(items: list[dict[str, Any]], group_by: str | None) -> dict:
    """Compute statistics from contribution list."""
    stats = {
        "total_count": len(items),
        "by_type": defaultdict(int),
        "date_range": None,
        "grouped": {},
    }

    dates = []

    for item in items:
        contrib_type = str(item.get("type") or "UNKNOWN")
        stats["by_type"][contrib_type] += 1

        try:
            d = datetime.fromisoformat(
                str(item.get("date") or "").replace("Z", "+00:00")
            )
            dates.append(d)
        except Exception:
            # Silently skip items with invalid date fields to ensure robustness
            pass

    stats["by_type"] = dict(stats["by_type"])

    if dates:
        stats["date_range"] = {
            "earliest": min(dates).isoformat(),
            "latest": max(dates).isoformat(),
        }

    if group_by == "type":
        stats["grouped"] = _group_by_type(items)
    elif group_by == "month":
        stats["grouped"] = _group_by_month(items)
    elif group_by == "year":
        stats["grouped"] = _group_by_year(items)

    return stats


def _group_by_type(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Group contributions by type."""
    grouped = defaultdict(list)
    for item in items:
        contrib_type = str(item.get("type") or "UNKNOWN")
        grouped[contrib_type].append({
            "title": item.get("title"),
            "date": item.get("date"),
            "url": item.get("url"),
        })
    return {k: v for k, v in grouped.items()}


def _group_by_month(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Group contributions by month (YYYY-MM)."""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "types": defaultdict(int)}
    )

    for item in items:
        try:
            d = datetime.fromisoformat(
                str(item.get("date") or "").replace("Z", "+00:00")
            )
            month_key = d.strftime("%Y-%m")
            month_data = grouped[month_key]
            month_data["count"] = month_data.get("count", 0) + 1
            contrib_type = str(item.get("type") or "UNKNOWN")
            types_dict = month_data.get("types", defaultdict(int))
            types_dict[contrib_type] = types_dict.get(contrib_type, 0) + 1
            month_data["types"] = types_dict
        except Exception:
            # Silently skip items with invalid or missing date fields to ensure robustness
            pass

    return {
        k: {"count": v["count"], "types": dict(v["types"])} for k, v in grouped.items()
    }


def _group_by_year(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Group contributions by year."""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "types": defaultdict(int)}
    )

    for item in items:
        try:
            d = datetime.fromisoformat(
                str(item.get("date") or "").replace("Z", "+00:00")
            )
            year_key = d.strftime("%Y")
            year_data = grouped[year_key]
            year_data["count"] = year_data.get("count", 0) + 1
            contrib_type = str(item.get("type") or "UNKNOWN")
            types_dict = year_data.get("types", defaultdict(int))
            types_dict[contrib_type] = types_dict.get(contrib_type, 0) + 1
            year_data["types"] = types_dict
        except Exception:
            # Silently skip items with invalid date fields to ensure robustness
            pass

    return {
        k: {"count": v["count"], "types": dict(v["types"])} for k, v in grouped.items()
    }


def _create_stats_ui_resource(
    stats: dict, username: str, group_by: str | None
) -> list[UIResource]:
    """Create MCP-UI resource with interactive charts."""
    try:
        generator = PlotlyChartGenerator()

        # Create main chart based on group_by
        by_type = stats.get("by_type", {})
        labels = list(by_type.keys())
        values = list(by_type.values())

        if group_by == "type":
            chart_html = generator.pie_chart(
                labels=labels,
                values=values,
                title="Contributions by Type",
            )
            chart_title = "Distribution by Type"
        elif group_by == "month":
            grouped = stats.get("grouped", {})
            months = sorted(grouped.keys())
            month_values = [grouped[m]["count"] for m in months]
            chart_html = generator.bar_chart(
                labels=months,
                values=month_values,
                title="Contributions per Month",
                x_label="Month",
                y_label="Count",
            )
            chart_title = "Monthly Activity"
        elif group_by == "year":
            grouped = stats.get("grouped", {})
            years = sorted(grouped.keys())
            year_values = [grouped[y]["count"] for y in years]
            chart_html = generator.bar_chart(
                labels=years,
                values=year_values,
                title="Contributions per Year",
                x_label="Year",
                y_label="Count",
            )
            chart_title = "Yearly Activity"
        else:
            # Default: pie chart of types
            chart_html = generator.pie_chart(
                labels=labels,
                values=values,
                title="Contribution Distribution",
            )
            chart_title = "Distribution"

        # Create dashboard HTML with stats and chart
        dashboard_html = _create_dashboard_html(
            username, stats, chart_html, chart_title
        )

        ui_resource = create_ui_resource({
            "uri": f"ui://contributions-stats/{username}",
            "content": {
                "type": "rawHtml",
                "htmlString": dashboard_html,
            },
            "encoding": "text",
        })

        logger.info(
            "ui_resource.created", username=username, uri=ui_resource.resource.uri
        )
        return [ui_resource]

    except Exception as e:
        logger.error("ui_resource_creation_failed", error=str(e))
        raise


def _create_empty_ui_resource(username: str) -> list[UIResource]:
    """Create UI resource for user with no contributions."""
    html = (
        """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>No Contributions</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }
        .container { max-width: 600px; margin: 100px auto; text-align: center; background: white; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
        h1 { color: #1a202c; font-size: 24px; margin-bottom: 10px; }
        p { color: #718096; font-size: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>No Contributions Found</h1>
        <p>User <strong>"""
        + username
        + """</strong> has no recorded contributions yet.</p>
    </div>
</body>
</html>"""
    )

    ui_resource = create_ui_resource({
        "uri": f"ui://contributions-stats/{username}/empty",
        "content": {
            "type": "rawHtml",
            "htmlString": html,
        },
        "encoding": "text",
    })
    return [ui_resource]


def _create_dashboard_html(
    username: str, stats: dict, chart_html: str, chart_title: str
) -> str:
    """Create complete dashboard HTML."""
    by_type = stats.get("by_type", {})
    total_count = stats.get("total_count", 0)
    date_range = stats.get("date_range")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contributions Stats - {username}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #f5f7fa; padding: 20px; }}
        .dashboard {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ margin-bottom: 30px; }}
        .header h1 {{ color: #1a202c; font-size: 28px; font-weight: 600; }}
        .header p {{ color: #718096; font-size: 14px; margin-top: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 30px; }}
        .metric-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); border-left: 4px solid #4a90e2; }}
        .metric-label {{ font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
        .metric-value {{ font-size: 32px; font-weight: 700; color: #1a202c; }}
        .metric-detail {{ font-size: 12px; color: #a0aec0; margin-top: 8px; }}
        .chart-section {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }}
        .chart-section h2 {{ color: #1a202c; font-size: 18px; font-weight: 600; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
        .breakdown {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 20px; }}
        .breakdown-item {{ background: #f7fafc; border-radius: 4px; padding: 12px; }}
        .breakdown-type {{ font-size: 12px; color: #718096; }}
        .breakdown-count {{ font-size: 18px; font-weight: 700; color: #4a90e2; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 Contributions for @{username}</h1>
            <p>Interactive statistics and visualization</p>
        </div>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Total Contributions</div>
                <div class="metric-value">{total_count}</div>
                <div class="metric-detail">All-time contributions</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Contribution Types</div>
                <div class="metric-value">{len(by_type)}</div>
                <div class="metric-detail">Different types</div>
            </div>"""

    if date_range:
        html += f"""
            <div class="metric-card">
                <div class="metric-label">Date Range</div>
                <div class="metric-value">📅</div>
                <div class="metric-detail">{date_range.get("earliest", "N/A")[:10]} to {date_range.get("latest", "N/A")[:10]}</div>
            </div>"""

    html += (
        """
        </div>

        <div class="chart-section">
            <h2>"""
        + chart_title
        + """</h2>
"""
    )

    # Embed the chart
    html += chart_html

    html += """
            <div class="breakdown">"""

    # Add breakdown by type
    for contrib_type, count in sorted(
        by_type.items(), key=lambda x: x[1], reverse=True
    ):
        html += f"""
                <div class="breakdown-item">
                    <div class="breakdown-type">{contrib_type}</div>
                    <div class="breakdown-count">{count}</div>
                </div>"""

    html += """
            </div>
        </div>
    </div>
</body>
</html>"""

    return html


@mcp.tool()
async def get_contributions_stats(args: dict[str, Any]) -> dict | list[UIResource]:
    """
    Get statistics and analytics for a user's contributions with optional MCP-UI visualization.

    Args:
        args: {
            "username": str (required),
            "group_by": "type" | "month" | "year" | None (optional, default: None for total stats),
            "include_ui": bool (optional, default: False, returns MCP-UI UIResource with interactive charts)
        }

    Returns:
        If include_ui=False:
            {
                "success": boolean,
                "data": {
                    "total_count": int,
                    "by_type": {type: count, ...},
                    "date_range": {"earliest": ISO, "latest": ISO} | null,
                    "grouped": {...}
                },
                "error"?: string
            }

        If include_ui=True:
            list[UIResource] - MCP-UI resource with interactive Plotly charts and dashboard
    """
    return await get_contributions_stats_impl(args)
