"""Discovery orchestration tests use only fake provider adapters."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest

from github_stars_contrib_mcp.application.discovery.orchestrator import (
    DiscoveryOrchestrator,
)
from github_stars_contrib_mcp.domain.discovery import (
    DiscoveryRunStatus,
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapterError,
    SourceBatch,
    SourceCapability,
)
from github_stars_contrib_mcp.infrastructure.persistence import SQLiteDiscoveryRepository
from github_stars_contrib_mcp.models import ContributionType


def _source(source_id: str) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        source_type=SourceType.WEBSITE,
        url=f"https://{source_id}.example.com",
        ownership=OwnershipStatus.VERIFIED,
    )


def _emission(
    source: SourceRecord,
    suffix: str,
    *,
    evidence_id: str | None = None,
) -> AdapterEmission:
    item = SourceItem(
        source_id=source.id,
        external_id=f"item-{suffix}",
        title=f"Item {suffix}",
        url=f"{source.url}/posts/{suffix}",
        published_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        type_hint=ContributionType.BLOGPOST,
    )
    evidence = Evidence(
        id=evidence_id or f"evidence-{source.id}-{suffix}",
        source_id=source.id,
        source_item_id=item.external_id,
        url=item.url,
    )
    return AdapterEmission(item=item, evidence=(evidence,))


class FakeAdapter:
    name = "fake"
    version = "1"

    def __init__(
        self,
        source_id: str,
        batches: tuple[SourceBatch, ...] = (),
        *,
        failure: SourceAdapterError | None = None,
    ) -> None:
        self.source_id = source_id
        self.batches = batches
        self.failure = failure

    def supports(self, source: SourceRecord) -> bool:
        return source.id == self.source_id

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        if self.failure is not None:
            raise self.failure
        for batch in self.batches:
            yield batch


@pytest.mark.asyncio
async def test_run_persists_batches_and_cursor_idempotently(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = _source("source-a")
    repository.upsert_source(source)
    adapter = FakeAdapter(
        source.id,
        (
            SourceBatch(
                emissions=(_emission(source, "1"),),
                next_cursor={"page": 1},
            ),
            SourceBatch(
                emissions=(_emission(source, "2"),),
                next_cursor={"page": 2},
            ),
        ),
    )
    orchestrator = DiscoveryOrchestrator(repository, (adapter,))

    first = await orchestrator.run()
    second = await orchestrator.run()

    assert first.status is DiscoveryRunStatus.COMPLETED
    assert second.status is DiscoveryRunStatus.COMPLETED
    assert len(repository.list_candidates()) == 2
    assert repository.get_cursor(source.id) == {"page": 2}
    assert first.summary["candidates_seen"] == 2


@pytest.mark.asyncio
async def test_source_failures_are_isolated_and_classified(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    good = _source("good")
    bad = _source("bad")
    repository.upsert_source(good)
    repository.upsert_source(bad)
    adapters = (
        FakeAdapter(
            good.id,
            (SourceBatch(emissions=(_emission(good, "1"),)),),
        ),
        FakeAdapter(
            bad.id,
            failure=SourceAdapterError(AdapterErrorKind.AUTH, "token missing"),
        ),
    )

    run = await DiscoveryOrchestrator(repository, adapters).run()

    assert run.status is DiscoveryRunStatus.PARTIAL
    assert run.summary["sources_succeeded"] == 1
    assert run.summary["sources_failed"] == 1
    assert run.errors[0]["kind"] == "auth"
    assert len(repository.list_candidates()) == 1


@pytest.mark.asyncio
async def test_batch_failure_rolls_back_candidates_and_cursor(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = _source("atomic")
    repository.upsert_source(source)
    adapter = FakeAdapter(
        source.id,
        (
            SourceBatch(
                emissions=(
                    _emission(source, "1", evidence_id="same-evidence"),
                    _emission(source, "2", evidence_id="same-evidence"),
                ),
                next_cursor={"page": 1},
            ),
        ),
    )

    run = await DiscoveryOrchestrator(repository, (adapter,)).run()

    assert run.status is DiscoveryRunStatus.FAILED
    assert repository.list_candidates() == []
    assert repository.get_cursor(source.id) is None


@pytest.mark.asyncio
async def test_dry_run_persists_diagnostics_only(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = _source("dry")
    repository.upsert_source(source)
    adapter = FakeAdapter(
        source.id,
        (
            SourceBatch(
                emissions=(_emission(source, "1"),),
                next_cursor={"page": 1},
            ),
        ),
    )

    run = await DiscoveryOrchestrator(repository, (adapter,)).run(dry_run=True)

    assert run.status is DiscoveryRunStatus.COMPLETED
    assert repository.get_run(run.id) is not None
    assert repository.list_candidates() == []
    assert repository.get_cursor(source.id) is None
