"""Rediscovery must not undo review/lifecycle decisions."""

from collections.abc import AsyncIterator
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


class StableAdapter:
    name = "stable"
    version = "1"

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.RSS

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        item = SourceItem(
            source_id=source.id,
            external_id="stable-item",
            title="Machine title",
            url="https://example.com/stable-item",
        )
        evidence = Evidence(
            id="stable-evidence",
            source_id=source.id,
            source_item_id=item.external_id,
            url=item.url,
        )
        yield SourceBatch(
            emissions=(AdapterEmission(item=item, evidence=(evidence,)),),
            next_cursor={"seen": True},
        )


async def test_rediscovery_preserves_rejected_candidate_and_human_edits(
    tmp_path,
) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="rss:https://example.com/feed.xml",
        source_type=SourceType.RSS,
        url="https://example.com/feed.xml",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)
    orchestrator = DiscoveryOrchestrator(repository, (StableAdapter(),))

    await orchestrator.run()
    candidate = repository.list_candidates()[0]
    candidate.title = "Human title"
    candidate.transition_to(CandidateState.REVIEW_READY)
    candidate.transition_to(CandidateState.REJECTED)
    repository.save_candidate(candidate)

    await orchestrator.run()
    rediscovered = repository.get_candidate(candidate.id)

    assert rediscovered is not None
    assert rediscovered.state is CandidateState.REJECTED
    assert rediscovered.title == "Human title"
