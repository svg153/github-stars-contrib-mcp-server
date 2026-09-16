"""Read-only MCP surface for local privacy-safe product metrics."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from github_stars_contrib_mcp.application.use_cases.get_product_metrics import (
    GetProductMetrics,
)
from github_stars_contrib_mcp.infrastructure.persistence.product_metrics_sqlite import (
    SQLiteProductMetricsQuery,
)
from github_stars_contrib_mcp.shared import initialize_discovery_runtime, mcp


def _parse_as_of(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    return parsed.astimezone(UTC)


def get_product_metrics_impl(as_of: str | None = None) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        query = SQLiteProductMetricsQuery(runtime.repository.db_path)
        data = GetProductMetrics(query).generate(as_of=_parse_as_of(as_of))
        return {"success": True, "data": data}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_product_metrics(as_of: str | None = None) -> dict:
    """Return privacy-safe local discovery/review quality metrics.

    ``as_of`` is optional ISO-8601 and exists mainly for reproducible reporting.
    """
    return get_product_metrics_impl(as_of)
