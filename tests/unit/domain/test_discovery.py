"""Unit tests for provider-neutral discovery domain rules."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryTransitionError,
    OwnershipStatus,
    Provenance,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.models import ContributionType


def _candidate() -> CandidateContribution:
    return CandidateContribution(
        id="candidate:1",
        source_id="site:example",
        external_id="post:1",
        title="Example post",
        url="https://example.com/post",
        contribution_type=ContributionType.BLOGPOST,
        date=datetime(2026, 1, 1, tzinfo=UTC),
        provenance=Provenance(adapter="fixture", adapter_version="1"),
    )


def test_models_serialize_with_schema_version() -> None:
    source = SourceRecord(
        id="site:example",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.EXPLICIT,
    )

    payload = source.model_dump(mode="json")

    assert payload["schema_version"] == 1
    assert payload["source_type"] == "website"
    assert payload["ownership"] == "explicit"
    assert SourceRecord.model_validate(payload) == source


def test_candidate_lifecycle_allows_review_approval_and_publish() -> None:
    candidate = _candidate()

    candidate.transition_to(CandidateState.REVIEW_READY)
    candidate.transition_to(CandidateState.APPROVED)
    candidate.transition_to(CandidateState.PUBLISHED)

    assert candidate.state is CandidateState.PUBLISHED


def test_candidate_lifecycle_rejects_invalid_terminal_transition() -> None:
    candidate = _candidate()
    candidate.transition_to(CandidateState.REVIEW_READY)
    candidate.transition_to(CandidateState.REJECTED)

    with pytest.raises(DiscoveryTransitionError, match="rejected -> review_ready"):
        candidate.transition_to(CandidateState.REVIEW_READY)


def test_candidate_same_state_transition_is_idempotent() -> None:
    candidate = _candidate()
    before = candidate.updated_at

    candidate.transition_to(CandidateState.DISCOVERED)

    assert candidate.updated_at == before


def test_confidence_is_bounded() -> None:
    payload = _candidate().model_dump()
    payload["ownership_confidence"] = 1.1

    with pytest.raises(ValidationError):
        CandidateContribution.model_validate(payload)
