"""Regression tests for privacy-safe product metric aggregation."""

from datetime import UTC, datetime, timedelta

from github_stars_contrib_mcp.application.use_cases.get_product_metrics import (
    GetProductMetrics,
)
from github_stars_contrib_mcp.domain.product_metrics import (
    CandidateMetricFact,
    ProductMetricsSnapshot,
    ReviewMetricFact,
    RunMetricFact,
    RunSourceMetricFact,
)


class StaticQuery:
    def __init__(self, snapshot: ProductMetricsSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> ProductMetricsSnapshot:
        return self._snapshot


def _candidate(
    *,
    state: str,
    duplicate: str,
    adapter: str = "github",
    source_type: str = "github",
    contribution_type: str = "blogpost",
    updated_minutes_ago: int = 5,
) -> CandidateMetricFact:
    created = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    as_of = datetime(2026, 9, 16, 20, 0, tzinfo=UTC)
    return CandidateMetricFact(
        source_type=source_type,
        adapter=adapter,
        contribution_type=contribution_type,
        state=state,
        duplicate_state=duplicate,
        created_at=created,
        updated_at=as_of - timedelta(minutes=updated_minutes_ago),
    )


def _review(
    decision: str,
    *,
    edited: bool = False,
    adapter: str = "github",
    source_type: str = "github",
    contribution_type: str = "blogpost",
    decided_minutes_after_creation: int = 30,
) -> ReviewMetricFact:
    created = datetime(2026, 9, 16, 18, 0, tzinfo=UTC)
    return ReviewMetricFact(
        decision=decision,
        edited=edited,
        source_type=source_type,
        adapter=adapter,
        contribution_type=contribution_type,
        candidate_created_at=created,
        decided_at=created + timedelta(minutes=decided_minutes_after_creation),
    )


def test_product_metrics_are_deterministic_and_explicit() -> None:
    as_of = datetime(2026, 9, 16, 20, 0, tzinfo=UTC)
    approve = _review("approve", edited=True)
    reject = _review("reject")
    defer = _review("defer", adapter="rss", source_type="rss")
    snapshot = ProductMetricsSnapshot(
        candidates=(
            _candidate(state="review_ready", duplicate="clear"),
            _candidate(state="published", duplicate="clear"),
            _candidate(state="rejected", duplicate="clear"),
            _candidate(state="blocked_duplicate", duplicate="exact"),
        ),
        review_actions=(approve, reject, defer),
        latest_reviews=(approve, reject, defer),
        first_reviews=(approve, reject, defer),
        run_sources=(
            RunSourceMetricFact(
                source_type="github",
                adapter="github",
                capability="available",
                status="completed",
                error_kind="none",
                candidate_count=3,
            ),
            RunSourceMetricFact(
                source_type="rss",
                adapter="rss",
                capability="limited",
                status="failed",
                error_kind="rate_limit",
                candidate_count=1,
            ),
        ),
        runs=(
            RunMetricFact(
                status="completed",
                dry_run=False,
                candidates_seen=3,
                source_count=1,
                started_at=as_of - timedelta(hours=1),
                finished_at=as_of - timedelta(minutes=55),
            ),
            RunMetricFact(
                status="partial",
                dry_run=True,
                candidates_seen=1,
                source_count=1,
                started_at=as_of - timedelta(minutes=30),
                finished_at=as_of - timedelta(minutes=25),
            ),
        ),
    )

    report = GetProductMetrics(StaticQuery(snapshot)).generate(as_of=as_of)

    assert report["eligibility"]["eligible_count"] == 2
    assert report["eligibility"]["noise_count"] == 2
    assert report["eligibility"]["eligible_rate"]["value"] == 0.5
    assert report["duplicates"]["exact_rate"]["value"] == 0.25
    assert report["reviews"]["edit_rate"]["value"] == 1 / 3
    assert report["reviews"]["acceptance_by_adapter"]["github"]["value"] == 0.5
    assert report["source_executions"]["failure_rate"]["value"] == 0.5
    assert report["source_executions"]["rate_limit_rate"]["value"] == 0.5
    assert report["candidates"]["per_run"]["value"] == 2.0
    assert (
        report["unavailable"]["missing_contribution_audit_yield"]["status"]
        == "unavailable"
    )


def test_empty_snapshot_never_fabricates_quality_conclusions() -> None:
    report = GetProductMetrics(StaticQuery(ProductMetricsSnapshot())).generate(
        as_of=datetime(2026, 9, 16, 20, 0, tzinfo=UTC)
    )

    assert report["candidates"]["total"] == 0
    assert report["eligibility"]["eligible_rate"]["value"] is None
    assert report["eligibility"]["eligible_rate"]["status"] == "insufficient_data"
    assert report["duplicates"]["exact_rate"]["value"] is None
    assert report["reviews"]["queue"]["age"]["status"] == "insufficient_data"
    assert report["reviews"]["time_to_first_decision"]["status"] == (
        "insufficient_data"
    )
