"""Restricted social sources flow through orchestrator/SQLite without scraping."""

import pytest

from github_stars_contrib_mcp.application.discovery.orchestrator import (
    DiscoveryOrchestrator,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.infrastructure.adapters.social_url_source import (
    SocialURLSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)


@pytest.mark.asyncio
async def test_explicit_social_url_is_reviewable_and_replay_safe(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="x:https://x.com/alice/status/123",
        source_type=SourceType.X,
        url="https://x.com/alice/status/123",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)
    orchestrator = DiscoveryOrchestrator(repository, (SocialURLSourceAdapter(),))

    first = await orchestrator.run()
    candidates = repository.list_candidates()
    assert first.summary["sources_succeeded"] == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.contribution_type is None
    assert candidate.date is None
    assert candidate.provenance.metadata["review_required"] is True
    assert candidate.provenance.metadata["review_reasons"] == [
        "missing_contribution_type",
        "missing_publication_date",
    ]

    second = await orchestrator.run()
    assert second.summary["candidates_persisted"] == 0
    assert len(repository.list_candidates()) == 1
