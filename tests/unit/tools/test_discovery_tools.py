"""Thin MCP discovery/review/publish handler tests."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    DiscoveryRunStatus,
    DuplicateState,
    OwnershipStatus,
    Provenance,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.models import ContributionType
from github_stars_contrib_mcp.tools import (
    discovery_candidates,
    discovery_sources,
    publish_candidates,
)


class FakeStarsAPI:
    def __init__(self) -> None:
        self.upserts = []

    async def list_contributions(self, page: int = 1) -> dict:
        return {"data": [], "pagination": {"totalPages": 1}}

    async def upsert_contribution(self, client_id: str, data: dict) -> dict:
        self.upserts.append((client_id, data))
        return {"id": client_id}


class FakeOrchestrator:
    def __init__(self) -> None:
        self.calls = []

    async def run(self, *, source_ids=None, dry_run=False) -> DiscoveryRun:
        self.calls.append((source_ids, dry_run))
        return DiscoveryRun(
            id="discovery:test",
            status=DiscoveryRunStatus.COMPLETED,
            source_ids=sorted(source_ids or []),
            summary={"dry_run": dry_run},
        )


def _seed(repository: SQLiteDiscoveryRepository) -> CandidateContribution:
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    repository.upsert_source(source)
    candidate = CandidateContribution(
        id="candidate:tool",
        source_id=source.id,
        external_id="tool",
        title="Tool candidate",
        url="https://example.com/tool",
        contribution_type=ContributionType.SPEAKING,
        date=datetime(2026, 9, 1, tzinfo=UTC),
        state=CandidateState.REVIEW_READY,
        duplicate_state=DuplicateState.CLEAR,
        provenance=Provenance(adapter="test", adapter_version="1"),
    )
    repository.save_candidate(candidate)
    return candidate


async def test_source_handlers_use_registry_and_orchestrator(
    monkeypatch,
    tmp_path,
) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    orchestrator = FakeOrchestrator()
    runtime = SimpleNamespace(
        repository=repository,
        orchestrator=orchestrator,
        stars_api=FakeStarsAPI(),
    )
    monkeypatch.setattr(
        discovery_sources,
        "initialize_discovery_runtime",
        lambda: runtime,
    )

    added = discovery_sources.add_source_impl("https://example.com")
    listed = discovery_sources.list_sources_impl()
    synced = await discovery_sources.sync_source_impl(
        added["data"]["id"],
        dry_run=True,
    )

    assert added["success"] is True
    assert listed["data"][0]["id"] == added["data"]["id"]
    assert synced["success"] is True
    assert orchestrator.calls == [({added["data"]["id"]}, True)]


def test_review_handler_cannot_publish_and_persists_approval(
    monkeypatch,
    tmp_path,
) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    candidate = _seed(repository)
    runtime = SimpleNamespace(repository=repository)
    monkeypatch.setattr(
        discovery_candidates,
        "initialize_discovery_runtime",
        lambda: runtime,
    )

    result = discovery_candidates.review_candidate_impl(
        candidate.id,
        "approve",
        reason="Reviewed",
    )

    assert result["success"] is True
    assert result["data"]["candidate"]["state"] == "approved"
    assert repository.get_candidate(candidate.id).state is CandidateState.APPROVED


async def test_publish_handler_defaults_to_dry_run(monkeypatch, tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    candidate = _seed(repository)
    approved = candidate.model_copy(deep=True)
    approved.transition_to(CandidateState.APPROVED)
    repository.save_candidate(approved)
    stars = FakeStarsAPI()
    runtime = SimpleNamespace(repository=repository, stars_api=stars)
    monkeypatch.setattr(
        publish_candidates,
        "initialize_discovery_runtime",
        lambda: runtime,
    )

    result = await publish_candidates.publish_approved_candidates_impl([candidate.id])

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["data"][0]["status"] == "dry_run"
    assert stars.upserts == []
