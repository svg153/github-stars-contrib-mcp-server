"""SQLite product metric read-model privacy tests."""

from datetime import UTC, datetime

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    DiscoveryRunStatus,
    DuplicateState,
    OwnershipStatus,
    Provenance,
    ReviewDecision,
    ReviewDecisionType,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.infrastructure.persistence.product_metrics_sqlite import (
    SQLiteProductMetricsQuery,
)
from github_stars_contrib_mcp.models import ContributionType


def test_metrics_read_model_does_not_expose_sensitive_content(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="website:https://private.example/secret-path",
        source_type=SourceType.WEBSITE,
        url="https://private.example/secret-path",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)
    candidate = CandidateContribution(
        id="candidate:SECRET-CANDIDATE-ID",
        source_id=source.id,
        external_id="SECRET-EXTERNAL-ID",
        title="TOP SECRET TITLE",
        url="https://private.example/secret-contribution",
        description="TOP SECRET DESCRIPTION",
        contribution_type=ContributionType.BLOGPOST,
        date=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
        state=CandidateState.REVIEW_READY,
        duplicate_state=DuplicateState.CLEAR,
        provenance=Provenance(adapter="website", adapter_version="1"),
    )
    repository.save_candidate(candidate)
    repository.record_review(
        ReviewDecision(
            candidate_id=candidate.id,
            decision=ReviewDecisionType.APPROVE,
            edited_fields={"description": "STILL SECRET"},
        )
    )
    repository.save_run(
        DiscoveryRun(
            id="discovery:SECRET-RUN-ID",
            status=DiscoveryRunStatus.COMPLETED,
            source_ids=[source.id],
            summary={
                "dry_run": False,
                "sources_total": 1,
                "candidates_seen": 1,
                "sources": {
                    source.id: {
                        "status": "completed",
                        "adapter": "website",
                        "capability": "available",
                        "candidates": 1,
                    }
                },
            },
            finished_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        )
    )

    snapshot = SQLiteProductMetricsQuery(repository.db_path).snapshot()
    rendered = repr(snapshot)

    assert len(snapshot.candidates) == 1
    assert len(snapshot.review_actions) == 1
    assert len(snapshot.runs) == 1
    for secret in (
        "TOP SECRET TITLE",
        "TOP SECRET DESCRIPTION",
        "STILL SECRET",
        "private.example",
        "SECRET-CANDIDATE-ID",
        "SECRET-EXTERNAL-ID",
        "SECRET-RUN-ID",
    ):
        assert secret not in rendered
