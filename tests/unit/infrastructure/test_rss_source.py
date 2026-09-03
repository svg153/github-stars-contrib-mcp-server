"""RSS adapter incremental discovery tests."""

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
from github_stars_contrib_mcp.infrastructure.adapters.rss_source import RSSSourceAdapter


class FakeFetcher:
    def __init__(self, text: str) -> None:
        self.text = text
        self.requests: list[SafeFetchRequest] = []

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        self.requests.append(request)
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/rss+xml",
            text=self.text,
            byte_count=len(self.text.encode()),
        )


RSS = """\
<rss version="2.0"><channel>
<item><guid>a</guid><title>A</title><link>https://example.com/a</link>
<pubDate>Tue, 01 Sep 2026 10:00:00 GMT</pubDate></item>
<item><guid>b</guid><title>B</title><link>https://example.com/b</link>
<pubDate>Tue, 01 Sep 2026 10:00:00 GMT</pubDate></item>
</channel></rss>
"""


async def _batches(
    adapter: RSSSourceAdapter,
    source: SourceRecord,
    cursor: dict | None,
) -> list:
    return [batch async for batch in adapter.iter_items(source, cursor)]


async def test_rss_adapter_uses_safe_fetch_and_same_timestamp_cursor() -> None:
    fetcher = FakeFetcher(RSS)
    adapter = RSSSourceAdapter(fetcher)
    source = SourceRecord(
        id="rss:https://example.com/feed.xml",
        source_type=SourceType.RSS,
        url="https://example.com/feed.xml",
        ownership=OwnershipStatus.EXPLICIT,
    )

    first = (await _batches(adapter, source, None))[0]
    assert [emission.item.external_id for emission in first.emissions] == ["a", "b"]
    assert first.next_cursor is not None
    assert first.next_cursor["ids_at_watermark"] == ["a", "b"]
    assert fetcher.requests[0].url == source.url

    second = (await _batches(adapter, source, first.next_cursor))[0]
    assert second.emissions == ()
    assert len(fetcher.requests) == 2
