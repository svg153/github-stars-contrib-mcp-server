"""Read-only historical audit scanner tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from github_stars_contrib_mcp.application.audit.historical_scan import (
    HistoricalAuditScanner,
)
from github_stars_contrib_mcp.domain.audit import AuditRequest, AuditSourceStatus
from github_stars_contrib_mcp.domain.discovery import (
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
from github_stars_contrib_mcp.models import ContributionType


class SpySourceRepository:
    def __init__(self, sources: list[SourceRecord]) -> None:
        self.sources = sources
        self.get_cursor_calls = 0
        self.save_cursor_calls = 0

    def get_source(self, source_id: str) -> SourceRecord | None:
        return next((source for source in self.sources if source.id == source_id), None)

    def list_sources(self, *, enabled_only: bool = False) -> list[SourceRecord]:
        if not enabled_only:
            return list(self.sources)
        return [source for source in self.sources if source.enabled]

    def upsert_source(self, source: SourceRecord) -> SourceRecord:
        raise AssertionError("audit must not mutate sources")

    def get_cursor(self, source_id: str) -> dict[str, Any] | None:
        self.get_cursor_calls += 1
        raise AssertionError("audit must not read incremental cursors")

    def save_cursor(self, source_id: str, cursor: dict[str, Any] | None) -> None:
        self.save_cursor_calls += 1
        raise AssertionError("audit must not write incremental cursors")


class FakeAdapter:
    name = "fake"
    version = "1"

    def __init__(
        self,
        source_type: SourceType,
        batches: list[SourceBatch],
        *,
        capability: CapabilityStatus = CapabilityStatus.AVAILABLE,
    ) -> None:
        self.source_type = source_type
        self.batches = batches
        self.capability = capability
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is self.source_type

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        del source
        return SourceCapability(
            status=self.capability,
            reason=(
                "fixture limitation"
                if self.capability is CapabilityStatus.LIMITED
                else None
            ),
        )

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        self.calls.append((source.id, cursor))
        for batch in self.batches:
            yield batch


def _source(source_id: str, source_type: SourceType) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        source_type=source_type,
        url=f"https://example.com/{source_id}",
        ownership=OwnershipStatus.EXPLICIT,
    )


def _emission(
    source_id: str,
    external_id: str,
    *,
    published_at: datetime | None,
    type_hint: ContributionType,
) -> AdapterEmission:
    item = SourceItem(
        source_id=source_id,
        external_id=external_id,
        title=external_id,
        url=f"https://example.com/items/{external_id}",
        published_at=published_at,
        type_hint=type_hint,
    )
    evidence = Evidence(
        id=f"evidence:{external_id}",
        source_id=source_id,
        source_item_id=external_id,
        url=item.url,
    )
    return AdapterEmission(item=item, evidence=(evidence,))


async def test_scan_filters_sources_dates_types_and_never_touches_cursors() -> None:
    github = _source("github:alice", SourceType.GITHUB)
    youtube = _source("youtube:alice", SourceType.YOUTUBE)
    repository = SpySourceRepository([github, youtube])
    github_adapter = FakeAdapter(
        SourceType.GITHUB,
        [
            SourceBatch(
                emissions=(
                    _emission(
                        github.id,
                        "inside",
                        published_at=datetime(2026, 1, 15, tzinfo=UTC),
                        type_hint=ContributionType.OPEN_SOURCE_PROJECT,
                    ),
                    _emission(
                        github.id,
                        "wrong-type",
                        published_at=datetime(2026, 1, 20, tzinfo=UTC),
                        type_hint=ContributionType.BLOGPOST,
                    ),
                    _emission(
                        github.id,
                        "outside",
                        published_at=datetime(2025, 12, 31, tzinfo=UTC),
                        type_hint=ContributionType.OPEN_SOURCE_PROJECT,
                    ),
                    _emission(
                        github.id,
                        "undated",
                        published_at=None,
                        type_hint=ContributionType.OPEN_SOURCE_PROJECT,
                    ),
                ),
                next_cursor={"page": 2},
            )
        ],
    )
    youtube_adapter = FakeAdapter(SourceType.YOUTUBE, [])
    scanner = HistoricalAuditScanner(
        repository,
        (github_adapter, youtube_adapter),
    )
    request = AuditRequest(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
        source_ids=(github.id,),
        source_types=(SourceType.GITHUB,),
        contribution_types=(ContributionType.OPEN_SOURCE_PROJECT,),
    )

    report = await scanner.scan(request)

    assert [item.item.external_id for item in report.observations] == ["inside"]
    assert report.sources[0].items_seen == 4
    assert report.sources[0].items_in_window == 1
    assert report.sources[0].undated_items == 1
    assert github_adapter.calls == [(github.id, None)]
    assert youtube_adapter.calls == []
    assert repository.get_cursor_calls == 0
    assert repository.save_cursor_calls == 0


async def test_scan_surfaces_limited_and_unavailable_capabilities() -> None:
    limited = _source("youtube:limited", SourceType.YOUTUBE)
    unavailable = _source("github:missing", SourceType.GITHUB)
    repository = SpySourceRepository([limited, unavailable])
    scanner = HistoricalAuditScanner(
        repository,
        (
            FakeAdapter(
                SourceType.YOUTUBE,
                [],
                capability=CapabilityStatus.LIMITED,
            ),
        ),
    )
    request = AuditRequest(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
    )

    report = await scanner.scan(request)
    by_id = {source.source_id: source for source in report.sources}

    assert by_id[limited.id].status is AuditSourceStatus.LIMITED
    assert by_id[unavailable.id].status is AuditSourceStatus.UNAVAILABLE
    assert "no adapter registered" in (by_id[unavailable.id].reason or "")


async def test_scan_marks_hard_item_limit_as_truncated() -> None:
    source = _source("github:bounded", SourceType.GITHUB)
    repository = SpySourceRepository([source])
    adapter = FakeAdapter(
        SourceType.GITHUB,
        [
            SourceBatch(
                emissions=tuple(
                    _emission(
                        source.id,
                        f"item-{index}",
                        published_at=datetime(2026, 1, 10, tzinfo=UTC),
                        type_hint=ContributionType.OPEN_SOURCE_PROJECT,
                    )
                    for index in range(5)
                ),
                next_cursor={"page": 2},
            )
        ],
    )
    scanner = HistoricalAuditScanner(repository, (adapter,))
    request = AuditRequest(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 2, 1, tzinfo=UTC),
        max_items_per_source=2,
    )

    report = await scanner.scan(request)

    assert report.sources[0].status is AuditSourceStatus.TRUNCATED
    assert report.sources[0].truncated is True
    assert report.sources[0].items_seen == 2
    assert len(report.observations) == 2
