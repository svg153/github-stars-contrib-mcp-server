"""Discovery composition remains offline and independent from MCP registration."""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from github_stars_contrib_mcp.config import Settings
from github_stars_contrib_mcp.di.discovery import build_discovery_runtime
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
    SafeFetchResult,
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


class FakeFetcher:
    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            text="offline",
        )


class FakeAdapter:
    name = "fake"
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
        item = SourceItem(
            source_id=source.id,
            external_id="one",
            title="One",
            url=f"{source.url}/one",
        )
        evidence = Evidence(
            id="evidence-one",
            source_id=source.id,
            source_item_id=item.external_id,
            url=item.url,
        )
        yield SourceBatch(
            emissions=(AdapterEmission(item=item, evidence=(evidence,)),),
            next_cursor={"after": "one"},
        )


@pytest.mark.asyncio
async def test_runtime_runs_fake_adapter_end_to_end(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    fetcher = FakeFetcher()
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)

    runtime = build_discovery_runtime(
        repository=repository,
        fetcher=fetcher,
        adapters=(FakeAdapter(),),
    )
    run = await runtime.orchestrator.run()

    assert runtime.repository is repository
    assert runtime.fetcher is fetcher
    assert run.summary["sources_succeeded"] == 1
    assert len(repository.list_candidates()) == 1
    assert repository.get_cursor(source.id) == {"after": "one"}


def test_default_runtime_registers_github_without_reusing_stars_token(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    runtime = build_discovery_runtime(
        settings=Settings(stars_api_token="stars-only"),
        repository=repository,
        fetcher=FakeFetcher(),
    )
    github = next(adapter for adapter in runtime.adapters if adapter.name == "github")
    source = SourceRecord(
        id="github:https://github.com/alice",
        source_type=SourceType.GITHUB,
        url="https://github.com/alice",
        ownership=OwnershipStatus.EXPLICIT,
    )

    assert github.capabilities(source).status is CapabilityStatus.LIMITED


def test_default_runtime_uses_dedicated_github_discovery_token(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    runtime = build_discovery_runtime(
        settings=Settings(github_discovery_token="github-token"),
        repository=repository,
        fetcher=FakeFetcher(),
    )
    github = next(adapter for adapter in runtime.adapters if adapter.name == "github")
    source = SourceRecord(
        id="github:https://github.com/alice",
        source_type=SourceType.GITHUB,
        url="https://github.com/alice",
        ownership=OwnershipStatus.EXPLICIT,
    )

    assert github.capabilities(source).status is CapabilityStatus.AVAILABLE


def test_default_runtime_social_adapters_are_mutually_exclusive(tmp_path) -> None:
    runtime = build_discovery_runtime(
        repository=SQLiteDiscoveryRepository(tmp_path / "discovery.db"),
        fetcher=FakeFetcher(),
    )
    social = [adapter for adapter in runtime.adapters if adapter.name.startswith("social-")]
    explicit = SourceRecord(
        id="x:https://x.com/alice/status/123",
        source_type=SourceType.X,
        url="https://x.com/alice/status/123",
        ownership=OwnershipStatus.EXPLICIT,
    )
    imported = SourceRecord(
        id="x:https://x.com/alice",
        source_type=SourceType.X,
        url="https://x.com/alice",
        ownership=OwnershipStatus.EXPLICIT,
        metadata={"social_mode": "export_import", "import_path": "/tmp/posts.json"},
    )

    assert [adapter.name for adapter in social if adapter.supports(explicit)] == [
        "social-url"
    ]
    assert [adapter.name for adapter in social if adapter.supports(imported)] == [
        "social-export"
    ]
