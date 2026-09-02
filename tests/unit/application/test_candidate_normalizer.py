"""Candidate normalization is deterministic and never invents missing data."""

from datetime import UTC, datetime

from github_stars_contrib_mcp.application.discovery.normalizer import (
    NORMALIZER_VERSION,
    normalize_candidate,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateState,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.models import ContributionType


def _source(ownership: OwnershipStatus = OwnershipStatus.VERIFIED) -> SourceRecord:
    return SourceRecord(
        id="rss:https://example.com/feed",
        source_type=SourceType.RSS,
        url="https://example.com/feed",
        ownership=ownership,
    )


def test_structured_item_normalizes_stably() -> None:
    source = _source()
    item = SourceItem(
        source_id=source.id,
        external_id="guid-1",
        title="A deterministic post",
        url="https://example.com/posts/1",
        description="Summary",
        published_at=datetime(2026, 8, 31, 10, 0, tzinfo=UTC),
        type_hint=ContributionType.BLOGPOST,
    )

    first = normalize_candidate(source, item, adapter_name="rss", adapter_version="1")
    second = normalize_candidate(source, item, adapter_name="rss", adapter_version="1")

    assert first.id == second.id
    assert first.contribution_type is ContributionType.BLOGPOST
    assert first.date == item.published_at
    assert first.state is CandidateState.DISCOVERED
    assert first.ownership_confidence == 1.0
    assert first.contribution_confidence == 0.95
    assert first.provenance.normalizer_version == NORMALIZER_VERSION
    assert first.provenance.metadata["review_required"] is False


def test_ambiguous_item_remains_review_required_without_fabrication() -> None:
    source = _source(OwnershipStatus.INFERRED)
    item = SourceItem(
        source_id=source.id,
        external_id="unknown-1",
        title="Something happened",
        url="https://example.com/unknown",
        updated_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )

    candidate = normalize_candidate(
        source,
        item,
        adapter_name="web",
        adapter_version="2",
    )

    assert candidate.contribution_type is None
    assert candidate.date is None
    assert candidate.ownership_confidence == 0.5
    assert candidate.provenance.metadata["review_required"] is True
    assert candidate.provenance.metadata["review_reasons"] == [
        "missing_contribution_type",
        "missing_publication_date",
    ]
