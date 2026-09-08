"""Candidate review workflow tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from github_stars_contrib_mcp.application.use_cases.review_candidates import (
    ReviewCandidates,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DuplicateState,
    Evidence,
    OwnershipStatus,
    Provenance,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.models import ContributionType


def _seed(
    tmp_path,
    *,
    duplicate_state=DuplicateState.CLEAR,
    state=CandidateState.REVIEW_READY,
):
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    repository.upsert_source(source)
    candidate = CandidateContribution(
        id="candidate:one",
        source_id=source.id,
        external_id="one",
        title="Original title",
        url="https://example.com/talk",
        description="Original description",
        contribution_type=ContributionType.SPEAKING,
        date=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        state=state,
        duplicate_state=duplicate_state,
        ownership_confidence=1.0,
        contribution_confidence=0.9,
        provenance=Provenance(adapter="test", adapter_version="1"),
    )
    evidence = Evidence(
        id="evidence:one",
        source_id=source.id,
        source_item_id="one",
        url=candidate.url,
        text_excerpt="evidence",
    )
    repository.save_candidate(candidate, (evidence,))
    return repository, candidate


def test_approve_with_edit_persists_candidate_and_audit(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)
    service = ReviewCandidates(repository)

    detail = service.review(
        candidate.id,
        "approve",
        reason="Confirmed talk",
        edits={"title": "Edited title"},
    )

    persisted = repository.get_candidate(candidate.id)
    assert persisted is not None
    assert persisted.state is CandidateState.APPROVED
    assert persisted.title == "Edited title"
    assert detail["candidate"]["state"] == "approved"
    assert detail["source"]["id"] == candidate.source_id
    assert detail["evidence"][0]["id"] == "evidence:one"

    with sqlite3.connect(repository.db_path) as connection:
        row = connection.execute(
            "SELECT decision, reason, edited_fields_json FROM reviews "
            "WHERE candidate_id = ?",
            (candidate.id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "approve"
    assert row[1] == "Confirmed talk"
    assert '"title":"Edited title"' in row[2]


def test_exact_duplicate_cannot_be_approved(tmp_path) -> None:
    repository, candidate = _seed(
        tmp_path,
        duplicate_state=DuplicateState.EXACT,
        state=CandidateState.BLOCKED_DUPLICATE,
    )

    with pytest.raises(ValueError, match="exact duplicate"):
        ReviewCandidates(repository).review(candidate.id, "approve")

    assert (
        repository.get_candidate(candidate.id).state
        is CandidateState.BLOCKED_DUPLICATE
    )


def test_discovered_candidate_can_be_edited_then_approved(tmp_path) -> None:
    repository, candidate = _seed(
        tmp_path,
        state=CandidateState.DISCOVERED,
    )
    candidate.contribution_type = None
    candidate.date = None
    repository.save_candidate(candidate)

    detail = ReviewCandidates(repository).review(
        candidate.id,
        "approve",
        edits={
            "contribution_type": "SPEAKING",
            "date": "2026-09-02T10:00:00Z",
        },
    )

    assert detail["candidate"]["state"] == "approved"
    assert detail["candidate"]["contribution_type"] == "SPEAKING"


def test_approved_candidate_can_be_deferred_for_re_review(tmp_path) -> None:
    repository, candidate = _seed(tmp_path, state=CandidateState.APPROVED)

    detail = ReviewCandidates(repository).review(
        candidate.id,
        "defer",
        reason="Need event confirmation",
    )

    assert detail["candidate"]["state"] == "deferred"


def test_invalid_edit_fields_are_rejected(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)

    with pytest.raises(ValueError, match="unsupported candidate edit fields"):
        ReviewCandidates(repository).review(
            candidate.id,
            "approve",
            edits={"state": "published"},
        )
