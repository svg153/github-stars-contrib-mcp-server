"""Tests for the read-only product metrics MCP tool implementation."""

from types import SimpleNamespace

from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.tools import product_metrics


def test_product_metrics_tool_returns_empty_safe_report(tmp_path, monkeypatch) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    monkeypatch.setattr(
        product_metrics,
        "initialize_discovery_runtime",
        lambda: SimpleNamespace(repository=repository),
    )

    result = product_metrics.get_product_metrics_impl("2026-09-16T20:00:00Z")

    assert result["success"] is True
    assert result["data"]["candidates"]["total"] == 0
    assert result["data"]["privacy"]["scope"] == (
        "local aggregate product-quality metrics"
    )


def test_product_metrics_tool_rejects_naive_as_of(tmp_path, monkeypatch) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    monkeypatch.setattr(
        product_metrics,
        "initialize_discovery_runtime",
        lambda: SimpleNamespace(repository=repository),
    )

    result = product_metrics.get_product_metrics_impl("2026-09-16T20:00:00")

    assert result["success"] is False
    assert "timezone" in result["error"]
