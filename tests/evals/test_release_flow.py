"""Offline source-to-review-to-publish-dry-run release gate."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from github_stars_contrib_mcp.application.discovery.orchestrator import (
    DiscoveryOrchestrator,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateState,
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    CapabilityStatus,
    SourceBatch,
    SourceCapability,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)
from github_stars_contrib_mcp.models import ContributionType
from github_stars_contrib_mcp.tools import discovery_candidates, publish_candidates


class FakeStarsAPI:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, dict[str, Any]]] = []

    async def list_contributions(self, page: int = 1) -> dict[str, Any]:
        return {"data": [], "pagination": {"page": page, "totalPages": 1}}

    async def upsert_contribution(
        self,
        client_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        self.upserts.append((client_id, data))
        return {"id": client_id}


class FixtureAdapter:
    name = "release-fixture"
    version = "1"

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.WEBSITE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        del cursor
        item = SourceItem(
            source_id=source.id,
            external_id="release-talk",
            title="Release fixture talk",
            url="https://example.com/talks/release-fixture",
            description="Synthetic public-safe release fixture",
            published_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
            type_hint=ContributionType.SPEAKING,
        )
        evidence = Evidence(
            id="evidence:release-fixture",
            source_id=source.id,
            source_item_id=item.external_id,
            url=item.url,
            data={"fixture": True},
        )
        yield SourceBatch(
            emissions=(AdapterEmission(item=item, evidence=(evidence,)),),
            next_cursor={"after": item.external_id},
        )


async def test_offline_source_candidate_review_publish_dry_run(
    monkeypatch,
    tmp_path,
) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )
    repository.upsert_source(source)
    stars = FakeStarsAPI()
    orchestrator = DiscoveryOrchestrator(
        repository,
        (FixtureAdapter(),),
        stars_api=stars,
    )

    run = await orchestrator.run(source_ids={source.id})
    assert run.summary["sources_succeeded"] == 1
    candidates = repository.list_candidates()
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.state is CandidateState.REVIEW_READY
    assert repository.get_cursor(source.id) == {"after": "release-talk"}

    runtime = SimpleNamespace(
        repository=repository,
        orchestrator=orchestrator,
        stars_api=stars,
    )
    monkeypatch.setattr(
        discovery_candidates,
        "initialize_discovery_runtime",
        lambda: runtime,
    )
    monkeypatch.setattr(
        publish_candidates,
        "initialize_discovery_runtime",
        lambda: runtime,
    )

    review = discovery_candidates.review_candidate_impl(
        candidate.id,
        "approve",
        reason="Release fixture reviewed by human",
    )
    assert review["success"] is True
    assert repository.get_candidate(candidate.id).state is CandidateState.APPROVED

    publish = await publish_candidates.publish_approved_candidates_impl([candidate.id])
    assert publish["success"] is True
    assert publish["dry_run"] is True
    assert publish["data"][0]["status"] == "dry_run"
    assert stars.upserts == []
    assert repository.get_candidate(candidate.id).state is CandidateState.APPROVED
