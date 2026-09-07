from datetime import UTC, datetime

import pytest

from github_stars_contrib_mcp.application.discovery.orchestrator import (
    DiscoveryOrchestrator,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateState,
    DuplicateState,
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


class FakeStars:
    def __init__(self, *, available=True):
        self.available = available
        self.calls = 0

    async def list_contributions(self, page=1):
        self.calls += 1
        if not self.available:
            raise RuntimeError("Stars unavailable")
        return {
            "data": [
                {
                    "id": "existing",
                    "title": "Existing",
                    "url": "https://example.com/existing",
                    "date": "2026-09-01",
                    "type": "SPEAKING",
                }
            ],
            "pagination": {"totalPages": 1},
        }


class Adapter:
    name = "contract"
    version = "1"

    def supports(self, source):
        return source.id == "source:test"

    def capabilities(self, source):
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(self, source, cursor=None):
        items = [
            SourceItem(
                source_id=source.id,
                external_id="1",
                title="Existing",
                url="https://example.com/existing?utm_source=x",
                published_at=datetime(2026, 9, 1, tzinfo=UTC),
                type_hint=ContributionType.SPEAKING,
            ),
            SourceItem(
                source_id=source.id,
                external_id="2",
                title="New",
                url="https://example.com/new",
                published_at=datetime(2026, 9, 2, tzinfo=UTC),
                type_hint=ContributionType.SPEAKING,
            ),
            SourceItem(
                source_id=source.id,
                external_id="3",
                title="Same run duplicate",
                url="https://example.com/new",
                published_at=datetime(2026, 9, 2, tzinfo=UTC),
                type_hint=ContributionType.SPEAKING,
            ),
        ]
        yield SourceBatch(
            emissions=tuple(
                AdapterEmission(
                    item=item,
                    evidence=(
                        Evidence(
                            id=f"e:{item.external_id}",
                            source_id=source.id,
                            source_item_id=item.external_id,
                            url=item.url,
                        ),
                    ),
                )
                for item in items
            )
        )


def source():
    return SourceRecord(
        id="source:test",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )


@pytest.mark.asyncio
async def test_exact_and_same_run_duplicates_never_become_reviewable(tmp_path) -> None:
    repo = SQLiteDiscoveryRepository(tmp_path / "d.sqlite")
    repo.upsert_source(source())
    stars = FakeStars()
    run = await DiscoveryOrchestrator(repo, [Adapter()], stars).run()
    candidates = {item.external_id: item for item in repo.list_candidates()}

    assert run.summary["stars_dedupe"]["available"] is True
    assert stars.calls == 1
    assert candidates["1"].state is CandidateState.BLOCKED_DUPLICATE
    assert candidates["1"].duplicate_state is DuplicateState.EXACT
    assert candidates["2"].state is CandidateState.REVIEW_READY
    assert candidates["2"].duplicate_state is DuplicateState.CLEAR
    assert candidates["3"].state is CandidateState.BLOCKED_DUPLICATE
    assert (
        candidates["3"].provenance.metadata["duplicate"]["target"] == candidates["2"].id
    )


@pytest.mark.asyncio
async def test_stars_failure_keeps_candidate_discovered_and_unknown(tmp_path) -> None:
    repo = SQLiteDiscoveryRepository(tmp_path / "d.sqlite")
    repo.upsert_source(source())
    run = await DiscoveryOrchestrator(
        repo, [Adapter()], FakeStars(available=False)
    ).run()
    candidates = repo.list_candidates()

    assert run.summary["stars_dedupe"]["available"] is False
    assert all(item.state is CandidateState.DISCOVERED for item in candidates)
    assert all(item.duplicate_state is DuplicateState.UNKNOWN for item in candidates)
