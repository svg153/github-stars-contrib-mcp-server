"""Offline contract from source registry through RSS discovery persistence."""

from github_stars_contrib_mcp.di.discovery import build_discovery_runtime
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    FetchOutcome,
    FetchSecurityClassification,
    SafeFetchRequest,
    SafeFetchResult,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)


class FakeFetcher:
    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        text = """\
<rss version="2.0"><channel><item>
<guid>contract-one</guid><title>Contract post</title>
<link>https://example.com/contract-one</link>
<pubDate>Tue, 01 Sep 2026 10:00:00 GMT</pubDate>
<description>Contract evidence</description>
</item></channel></rss>
"""
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/rss+xml",
            text=text,
            byte_count=len(text.encode()),
        )


async def test_rss_source_to_candidate_persistence_contract(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "discovery.db")
    source = SourceRecord(
        id="rss:https://example.com/feed.xml",
        source_type=SourceType.RSS,
        url="https://example.com/feed.xml",
        ownership=OwnershipStatus.EXPLICIT,
    )
    repository.upsert_source(source)
    runtime = build_discovery_runtime(repository=repository, fetcher=FakeFetcher())

    run = await runtime.orchestrator.run()
    candidates = repository.list_candidates()

    assert run.summary["sources_succeeded"] == 1
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.title == "Contract post"
    assert candidate.provenance.adapter == "rss"
    evidence = repository.list_evidence(candidate.id)
    assert evidence[0].text_excerpt == "Contract evidence"
    assert repository.get_cursor(source.id) is not None
