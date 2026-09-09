"""Privacy and cardinality guards for discovery observability."""

from __future__ import annotations

from typing import Any

from github_stars_contrib_mcp.observability.discovery import DiscoveryTelemetry
from github_stars_contrib_mcp.observability.metrics import get_metrics


class FakeLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def info(self, event: str, **kwargs: Any) -> None:
        self.events.append((event, kwargs))


def test_discovery_logs_use_allowlisted_privacy_safe_fields() -> None:
    logger = FakeLogger()
    telemetry = DiscoveryTelemetry(logger)
    run_id = "discovery:privacy-test"

    telemetry.record_source(
        run_id=run_id,
        source_type="youtube",
        capability="limited",
        status="failed",
        item_count=3,
        candidate_count=2,
        duration_s=0.125,
        error_class="rate_limit",
    )
    telemetry.record_candidate_batch(
        run_id=run_id,
        source_type="youtube",
        capability="limited",
        duplicate_class="likely",
        item_count=2,
        candidate_count=2,
    )
    telemetry.record_run(
        run_id=run_id,
        status="partial",
        source_count=1,
        candidate_count=2,
        duration_s=0.25,
        error_class="source_failure",
    )

    allowed = {
        "run_id",
        "source_type",
        "capability",
        "source_count",
        "item_count",
        "candidate_count",
        "duplicate_class",
        "duration_ms",
        "error_class",
        "status",
    }
    assert [event for event, _ in logger.events] == [
        "discovery_source",
        "discovery_candidates",
        "discovery_run",
    ]
    assert all(set(fields) <= allowed for _, fields in logger.events)

    serialized = repr(logger.events).lower()
    for forbidden in (
        "source_url",
        "candidate_url",
        "title",
        "description",
        "page_body",
        "prompt",
        "token",
        "authorization",
        "bearer ",
    ):
        assert forbidden not in serialized


def test_prometheus_dimensions_are_bounded_and_exclude_run_ids() -> None:
    logger = FakeLogger()
    telemetry = DiscoveryTelemetry(logger)
    run_id = "discovery:must-not-be-a-prom-label"

    telemetry.record_candidate_batch(
        run_id=run_id,
        source_type="rss",
        capability="available",
        duplicate_class="exact",
        item_count=1,
        candidate_count=1,
    )
    telemetry.record_source(
        run_id=run_id,
        source_type="rss",
        capability="available",
        status="completed",
        item_count=1,
        candidate_count=1,
        duration_s=0.01,
    )
    telemetry.record_run(
        run_id=run_id,
        status="completed",
        source_count=1,
        candidate_count=1,
        duration_s=0.02,
    )

    metrics = get_metrics().decode()
    assert "mcp_discovery_runs_total" in metrics
    assert "mcp_discovery_sources_total" in metrics
    assert "mcp_discovery_candidates_total" in metrics
    assert 'source_type="rss"' in metrics
    assert 'duplicate_class="exact"' in metrics
    assert run_id not in metrics
