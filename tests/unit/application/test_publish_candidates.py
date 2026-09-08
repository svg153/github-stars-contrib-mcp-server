"""Guarded publication workflow tests."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from github_stars_contrib_mcp.application.use_cases.publish_candidates import (
    PublishCandidates,
    stable_client_id,
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


class FakeStarsAPI:
    def __init__(self, contributions=None, *, fail_list: bool = False) -> None:
        self.contributions = list(contributions or [])
        self.fail_list = fail_list
        self.list_calls = 0
        self.upserts: list[tuple[str, dict]] = []

    async def list_contributions(self, page: int = 1) -> dict:
        self.list_calls += 1
        if self.fail_list:
            raise RuntimeError("Stars unavailable")
        return {
            "data": self.contributions,
            "pagination": {"totalPages": 1},
        }

    async def upsert_contribution(self, client_id: str, data: dict) -> dict:
        self.upserts.append((client_id, data))
        return {"id": client_id, "data": data}


def _seed(tmp_path):
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    repository.upsert_source(source)
    candidate = CandidateContribution(
        id="candidate:publish-one",
        source_id=source.id,
        external_id="talk-one",
        title="Publish me",
        url="https://example.com/talk",
        description="A conference talk",
        contribution_type=ContributionType.SPEAKING,
        date=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        state=CandidateState.APPROVED,
        duplicate_state=DuplicateState.CLEAR,
        ownership_confidence=1.0,
        contribution_confidence=0.95,
        provenance=Provenance(adapter="test", adapter_version="1"),
    )
    evidence = Evidence(
        id="evidence:publish-one",
        source_id=source.id,
        source_item_id=candidate.external_id,
        url=candidate.url,
        text_excerpt="schedule evidence",
    )
    repository.save_candidate(candidate, (evidence,))
    return repository, candidate


async def test_dry_run_returns_exact_payload_without_write_or_mutation(
    tmp_path,
) -> None:
    repository, candidate = _seed(tmp_path)
    stars = FakeStarsAPI()

    result = (
        await PublishCandidates(repository, stars)(
            [candidate.id],
            dry_run=True,
        )
    )[0]

    assert result.status == "dry_run"
    assert result.client_id == stable_client_id(candidate.id)
    assert result.payload == {
        "title": "Publish me",
        "url": "https://example.com/talk",
        "description": "A conference talk",
        "type": "SPEAKING",
        "date": "2026-09-01T10:00:00+00:00",
    }
    assert stars.upserts == []
    assert repository.get_candidate(candidate.id).state is CandidateState.APPROVED


async def test_real_publish_is_idempotent_and_persists_provenance(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)
    stars = FakeStarsAPI()
    service = PublishCandidates(repository, stars)

    first = (await service([candidate.id], dry_run=False))[0]
    second = (await service([candidate.id], dry_run=False))[0]

    assert first.status == "published"
    assert second.status == "already_published"
    assert len(stars.upserts) == 1
    assert stars.upserts[0][0] == stable_client_id(candidate.id)
    assert repository.get_candidate(candidate.id).state is CandidateState.PUBLISHED

    with sqlite3.connect(repository.db_path) as connection:
        row = connection.execute(
            "SELECT client_id, result_json FROM publications WHERE candidate_id = ?",
            (candidate.id,),
        ).fetchone()
    assert row is not None
    assert row[0] == stable_client_id(candidate.id)
    record = json.loads(row[1])
    assert record["candidate"]["state"] == "published"
    assert record["evidence_ids"] == ["evidence:publish-one"]
    assert record["provenance"]["adapter"] == "test"
    assert record["duplicate_check"]["state"] == "clear"


async def test_fresh_exact_duplicate_blocks_without_stars_write(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)
    stars = FakeStarsAPI(
        [
            {
                "id": "existing",
                "title": candidate.title,
                "url": candidate.url,
                "type": "SPEAKING",
                "date": candidate.date.isoformat(),
            }
        ]
    )

    result = (
        await PublishCandidates(repository, stars)(
            [candidate.id],
            dry_run=False,
        )
    )[0]

    assert result.status == "blocked"
    assert result.duplicate_state is DuplicateState.EXACT
    assert stars.upserts == []
    persisted = repository.get_candidate(candidate.id)
    assert persisted.state is CandidateState.BLOCKED_DUPLICATE
    assert persisted.duplicate_state is DuplicateState.EXACT


async def test_fresh_likely_conflict_returns_candidate_to_review(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)
    stars = FakeStarsAPI(
        [
            {
                "id": "similar",
                "title": candidate.title,
                "url": "https://other.example/talk",
                "type": "SPEAKING",
                "date": candidate.date.isoformat(),
            }
        ]
    )

    result = (
        await PublishCandidates(repository, stars)(
            [candidate.id],
            dry_run=False,
        )
    )[0]

    assert result.status == "blocked"
    assert result.duplicate_state is DuplicateState.LIKELY
    assert stars.upserts == []
    assert repository.get_candidate(candidate.id).state is CandidateState.REVIEW_READY


async def test_unavailable_fresh_snapshot_never_publishes(tmp_path) -> None:
    repository, candidate = _seed(tmp_path)
    stars = FakeStarsAPI(fail_list=True)

    result = (
        await PublishCandidates(repository, stars)(
            [candidate.id],
            dry_run=False,
        )
    )[0]

    assert result.status == "blocked"
    assert result.duplicate_state is DuplicateState.UNKNOWN
    assert stars.upserts == []
    assert repository.get_candidate(candidate.id).state is CandidateState.APPROVED
