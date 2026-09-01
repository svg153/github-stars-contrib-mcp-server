"""MCP tool to export contributions in multiple formats (JSON, CSV, Markdown)."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError

from ..application.use_cases.get_stars import GetStars
from ..di.container import get_stars_api
from ..shared import mcp

logger = structlog.get_logger(__name__)


class ExportArgs(BaseModel):
    username: str = Field(description="GitHub username to export")
    format: str = Field(
        default="json",
        description="Export format: 'json', 'csv', or 'markdown'",
    )
    sort_by: str | None = Field(
        default=None,
        description="Sort by field: 'date', 'title', 'type', or None for original order",
    )


async def export_contributions_impl(args: dict[str, Any]) -> dict:
    """Export contributions in the requested format."""
    try:
        payload = ExportArgs(**(args or {}))
    except ValidationError as e:
        return {"success": False, "error": e.errors()}

    # Validate format
    if payload.format not in ("json", "csv", "markdown"):
        return {
            "success": False,
            "error": "Invalid format. Use: json, csv, or markdown",
        }

    try:
        use_case = GetStars(get_stars_api())
        raw = await use_case(payload.username)
    except Exception as e:
        logger.warning("export.fetch_failed", error=str(e))
        return {"success": False, "error": str(e)}

    profile = (raw or {}).get("publicProfile") or {}
    items = profile.get("contributions") or []

    if not items:
        items = []

    # Sort if requested
    items = _sort_items(items, payload.sort_by)

    # Format output
    try:
        if payload.format == "json":
            output = _export_json(items)
        elif payload.format == "csv":
            output = _export_csv(items)
        elif payload.format == "markdown":
            output = _export_markdown(items, payload.username)
        else:
            return {"success": False, "error": "Unknown format"}
    except Exception as e:
        logger.error("export.formatting_failed", format=payload.format, error=str(e))
        return {"success": False, "error": f"Export failed: {e!s}"}

    logger.info(
        "export_contributions.result",
        username=payload.username,
        format=payload.format,
        count=len(items),
    )

    return {
        "success": True,
        "data": {
            "format": payload.format,
            "username": payload.username,
            "count": len(items),
            "content": output,
        },
    }


def _sort_items(
    items: list[dict[str, Any]], sort_by: str | None
) -> list[dict[str, Any]]:
    """Sort contributions by specified field."""
    if not sort_by or sort_by == "none":
        return items

    def _get_sort_key(item: dict[str, Any]) -> Any:
        if sort_by == "date":
            try:
                return datetime.fromisoformat(
                    str(item.get("date") or "").replace("Z", "+00:00")
                )
            except Exception:
                return datetime.min
        elif sort_by == "title":
            return str(item.get("title") or "").lower()
        elif sort_by == "type":
            return str(item.get("type") or "")
        return item

    try:
        return sorted(items, key=_get_sort_key, reverse=(sort_by == "date"))
    except Exception:
        logger.warning("sort_failed", sort_by=sort_by)
        return items


def _export_json(items: list[dict[str, Any]]) -> str:
    """Export as JSON."""
    return json.dumps(items, indent=2, default=str)


def _export_csv(items: list[dict[str, Any]]) -> str:
    """Export as CSV."""
    if not items:
        return "title,type,date,url,description\n"

    # Extract all keys from all items to ensure we capture everything
    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    # Standard column order with fallback to any additional columns
    standard_cols = ["title", "type", "date", "url", "description"]
    fieldnames = [col for col in standard_cols if col in all_keys]
    # Add any remaining columns
    fieldnames.extend(sorted(all_keys - set(fieldnames)))

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in items:
        # Convert item to include only fieldnames, with defaults for missing values
        row = {k: item.get(k, "") for k in fieldnames}
        writer.writerow(row)

    return output.getvalue()


def _export_markdown(items: list[dict[str, Any]], username: str) -> str:
    """Export as Markdown."""
    lines = [
        f"# Contributions for @{username}",
        "",
        f"**Total contributions:** {len(items)}",
        "",
        "| Title | Type | Date | URL |",
        "|-------|------|------|-----|",
    ]

    for item in items:
        title = str(item.get("title") or "N/A").replace("|", "\\|")
        contrib_type = str(item.get("type") or "N/A")
        date = str(item.get("date") or "N/A")[:10]  # Just date part
        url = item.get("url") or "#"

        # Make title a link if URL exists
        if url and url != "#":
            title_md = f"[{title}]({url})"
        else:
            title_md = title

        lines.append(f"| {title_md} | {contrib_type} | {date} | {url} |")

    lines.append("")
    lines.append("---")
    lines.append(f"_Generated: {datetime.now(UTC).isoformat()}_")

    return "\n".join(lines)


@mcp.tool()
async def export_contributions(args: dict[str, Any]) -> dict:
    """
    Export contributions in multiple formats (JSON, CSV, Markdown).

    Args:
        args: {
            "username": str (required),
            "format": "json" | "csv" | "markdown" (optional, default: "json"),
            "sort_by": "date" | "title" | "type" | None (optional)
        }

    Returns:
        {
            "success": boolean,
            "data": {
                "format": str,
                "username": str,
                "count": int,
                "content": str (the exported data)
            },
            "error"?: string
        }
    """
    return await export_contributions_impl(args)
