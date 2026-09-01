"""Unit tests for SQLite discovery persistence."""

import sqlite3
from datetime import UTC, datetime

import pytest

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    Evidence,
    OwnershipStatus,
    Provenance,
    ReviewDecision,
    ReviewDecisionType,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.persistence.discovery_sqlite import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.models import ContributionType


def _source(*, source_id: str = "site:example", enabled: bool = True) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        source_type=SourceType.WEBSITE,
        url=f"https://{source_id.replace(':', '-')}.example.com",
        ownership=OwnershipStatus.EXPLICIT,
        enabled=enabled,
        evidence=["profile-link"],
        metadata={"b": 2, "a": 1},
    )


def _candidate(
    *, candidate_id: str = "candidate:1", external_id: str = "post:1"
) -> CandidateContribution:
    return CandidateContribution(
        id=candidate_id,
        source_id="site:example",
        external_id=external_id,
        title="Example post",
        url=f"https://example.com/{external_id}",
        contribution_type=ContributionType.BLOGPOST,
        date=datetime(2026, 1, 1, tzinfo=UTC),
        provenance=Provenance(adapter="fixture", adapter_version="1"),
    )


def test_source_cursor_and_reopen_round_trip(tmp_path) -> None:
    path = tmp_path / "discovery.db"
    repository = SQLiteDiscoveryRepository(path)
    source = _source()

    repository.upsert_source(source)
    repository.save_cursor(source.id, {"page": 2, "ids": ["b", "a"]})

    reopened = SQLiteDiscoveryRepository(path)
    assert reopened.get_source(source.id) == source
    assert reopened.get_cursor(source.id) == {"ids": ["b", "a"], "page": 2}


def test_enabled_source_and_candidate_state_filters(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    repository.upsert_source(_source())
    repository.upsert_source(_source(source_id="site:disabled", enabled=False))
    approved = _candidate(candidate_id="candidate:approved", external_id="approved")
    approved.state = CandidateState.APPROVED
    discovered = _candidate(candidate_id="candidate:new", external_id="new")
    repository.save_candidate(approved)
    repository.save_candidate(discovered)

    assert [item.id for item in repository.list_sources(enabled_only=True)] == [
        "site:example"
    ]
    assert [
        item.id for item in repository.list_candidates(states={CandidateState.APPROVED})
    ] == ["candidate:approved"]


def test_candidate_evidence_run_review_and_publication_persist(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    repository.upsert_source(_source())
    candidate = _candidate()
    evidence = Evidence(
        id="evidence:1",
        source_id="site:example",
        source_item_id="post:1",
        url="https://example.com/post:1",
        data={"published": True},
    )

    repository.save_candidate(candidate, [evidence])
    repository.record_review(
        ReviewDecision(
            candidate_id=candidate.id,
            decision=ReviewDecisionType.APPROVE,
            reason="Verified fixture",
        )
    )
    repository.record_publication(candidate.id, "client:1", {"success": True})
    run = DiscoveryRun(id="run:1", source_ids=["site:example"])
    repository.save_run(run)

    assert repository.get_candidate(candidate.id) == candidate
    assert repository.list_evidence(candidate.id) == [evidence]
    assert repository.get_run(run.id) == run


def test_candidate_and_evidence_write_is_atomic(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    repository.upsert_source(_source())
    evidence = Evidence(id="evidence:shared", source_id="site:example")
    repository.save_candidate(_candidate(), [evidence])
    second = _candidate(candidate_id="candidate:2", external_id="post:2")

    with pytest.raises(ValueError, match="immutable across candidates"):
        repository.save_candidate(second, [evidence])

    assert repository.get_candidate(second.id) is None


def test_explicit_transaction_rolls_back_multiple_repository_operations(
    tmp_path,
) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    repository.upsert_source(_source())

    with pytest.raises(RuntimeError, match="abort fixture"):
        with repository.transaction():
            repository.save_candidate(_candidate())
            repository.save_cursor("site:example", {"page": 9})
            raise RuntimeError("abort fixture")

    assert repository.get_candidate("candidate:1") is None
    assert repository.get_cursor("site:example") is None


def test_nested_transactions_are_rejected(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")

    with repository.transaction():
        with pytest.raises(RuntimeError, match="Nested discovery transactions"):
            with repository.transaction():
                pass


def test_unsupported_schema_version_is_rejected(tmp_path) -> None:
    path = tmp_path / "discovery.db"
    repository = SQLiteDiscoveryRepository(path)
    del repository
    connection = sqlite3.connect(path)
    connection.execute("UPDATE schema_version SET version = 99")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError, match="Unsupported discovery schema version: 99"):
        SQLiteDiscoveryRepository(path)
