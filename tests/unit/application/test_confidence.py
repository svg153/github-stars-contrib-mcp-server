from datetime import UTC, datetime

from github_stars_contrib_mcp.application.discovery.confidence import assess_confidence
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    DuplicateState,
    OwnershipStatus,
    Provenance,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.models import ContributionType


def test_confidence_is_separate_explainable_and_ambiguity_sensitive() -> None:
    source = SourceRecord(
        id="youtube:me",
        source_type=SourceType.YOUTUBE,
        url="https://youtube.com/@me",
        ownership=OwnershipStatus.VERIFIED,
        evidence=["profile-link"],
    )
    candidate = CandidateContribution(
        id="c",
        source_id=source.id,
        external_id="video-1",
        title="A talk",
        url="https://youtube.com/watch?v=1",
        contribution_type=ContributionType.VIDEO_PODCAST,
        date=datetime(2026, 9, 1, tzinfo=UTC),
        provenance=Provenance(adapter="youtube", adapter_version="1"),
    )
    clear = assess_confidence(source, candidate, duplicate_state=DuplicateState.CLEAR)
    likely = assess_confidence(source, candidate, duplicate_state=DuplicateState.LIKELY)

    assert clear.ownership == 1.0
    assert clear.contribution > likely.contribution
    assert "source_ownership:verified" in clear.ownership_reasons
    assert "ambiguity_penalty:likely_duplicate" in likely.contribution_reasons
    assert clear.ownership_band == "high"
