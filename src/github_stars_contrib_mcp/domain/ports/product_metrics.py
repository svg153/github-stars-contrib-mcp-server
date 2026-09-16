"""Read-model port for privacy-safe product metrics."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from github_stars_contrib_mcp.domain.product_metrics import ProductMetricsSnapshot


@runtime_checkable
class ProductMetricsQuery(Protocol):
    def snapshot(self) -> ProductMetricsSnapshot:
        """Return a privacy-safe local snapshot for deterministic aggregation."""
        ...
