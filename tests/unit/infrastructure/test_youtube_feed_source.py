from __future__ import annotations

import pytest

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
from github_stars_contrib_mcp.domain.ports.source_adapter import CapabilityStatus
from github_stars_contrib_mcp.infrastructure.adapters.youtube_feed_source import (
    YouTubeFeedSourceAdapter,
)
from github_stars_contrib_mcp.models import ContributionType

CHANNEL_ID = "UC" + "d" * 22
ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <title>Example channel</title>
  <entry>
    <id>yt:video:abc123</id>
    <yt:videoId>abc123</yt:videoId>
    <title>Recent video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
    <author><name>Example</name></author>
    <published>2026-09-01T10:00:00+00:00</published>
    <updated>2026-09-01T10:05:00+00:00</updated>
    <summary>Recent upload</summary>
  </entry>
</feed>
"""


class FakeFetcher:
    def __init__(self) -> None:
        self.requests: list[SafeFetchRequest] = []

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        self.requests.append(request)
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/atom+xml",
            text=ATOM,
            byte_count=len(ATOM.encode()),
        )


def _source(url: str | None = None) -> SourceRecord:
    return SourceRecord(
        id="source:youtube",
        source_type=SourceType.YOUTUBE,
        url=url or f"https://www.youtube.com/channel/{CHANNEL_ID}",
        ownership=OwnershipStatus.EXPLICIT,
    )


@pytest.mark.asyncio
async def test_feed_fallback_is_limited_safe_fetch_and_incremental() -> None:
    fetcher = FakeFetcher()
    adapter = YouTubeFeedSourceAdapter(fetcher)
    assert adapter.capabilities(_source()).status is CapabilityStatus.LIMITED

    first = [batch async for batch in adapter.iter_items(_source(), None)]
    assert len(first[0].emissions) == 1
    emission = first[0].emissions[0]
    assert emission.item.external_id == "youtube:video:abc123"
    assert emission.item.type_hint is ContributionType.VIDEO_PODCAST
    assert emission.item.metadata["limited_history"] is True
    assert "feeds/videos.xml" in fetcher.requests[0].url
    assert fetcher.requests[0].url.endswith(f"channel_id={CHANNEL_ID}")

    second = [
        batch
        async for batch in adapter.iter_items(_source(), first[0].next_cursor)
    ]
    assert second[0].emissions == ()


def test_feed_fallback_rejects_handle_without_canonical_id() -> None:
    adapter = YouTubeFeedSourceAdapter(FakeFetcher())
    source = _source("https://www.youtube.com/@example")
    capability = adapter.capabilities(source)
    assert capability.status is CapabilityStatus.UNAVAILABLE
    assert "canonical channel ID" in (capability.reason or "")
