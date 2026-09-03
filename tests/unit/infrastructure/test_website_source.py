"""Trusted website adapter tests."""

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
from github_stars_contrib_mcp.infrastructure.adapters.website_source import (
    WebsiteSourceAdapter,
)


class FakeFetcher:
    def __init__(self, responses: dict[str, tuple[str, str]]) -> None:
        self.responses = responses
        self.requests: list[SafeFetchRequest] = []

    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        self.requests.append(request)
        media_type, text = self.responses[request.url]
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type=media_type,
            text=text,
            byte_count=len(text.encode()),
        )


PAGE = """\
<html><head>
<link rel="alternate" type="application/rss+xml" href="/feed.xml">
<link rel="alternate" type="application/rss+xml" href="https://evil.example/feed.xml">
<meta property="og:type" content="article">
<meta property="og:title" content="Structured article">
<meta property="og:url" content="https://example.com/article">
<meta property="og:description" content="Article description">
<meta property="article:published_time" content="2026-09-01T10:00:00Z">
</head><body></body></html>
"""
FEED = """\
<rss version="2.0"><channel><item>
<guid>feed-one</guid><title>Feed one</title>
<link>https://example.com/feed-one</link>
<pubDate>Tue, 01 Sep 2026 11:00:00 GMT</pubDate>
</item></channel></rss>
"""


async def test_website_adapter_discovers_structured_article_and_trusted_feed_only() -> (
    None
):
    fetcher = FakeFetcher(
        {
            "https://example.com": ("text/html", PAGE),
            "https://example.com/feed.xml": ("application/rss+xml", FEED),
        }
    )
    adapter = WebsiteSourceAdapter(fetcher)
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.VERIFIED,
    )

    batches = [batch async for batch in adapter.iter_items(source, None)]
    batch = batches[0]
    assert len(batch.emissions) == 2
    assert batch.emissions[0].item.title == "Structured article"
    assert batch.emissions[1].item.title == "Feed one"
    assert [request.url for request in fetcher.requests] == [
        "https://example.com",
        "https://example.com/feed.xml",
    ]
    assert batch.emissions[0].evidence[0].data["blocked_cross_origin_feed_links"] == [
        "https://evil.example/feed.xml"
    ]


def test_website_adapter_requires_explicit_or_verified_ownership() -> None:
    adapter = WebsiteSourceAdapter(FakeFetcher({}))
    source = SourceRecord(
        id="website:https://example.com",
        source_type=SourceType.WEBSITE,
        url="https://example.com",
        ownership=OwnershipStatus.INFERRED,
    )

    capability = adapter.capabilities(source)
    assert capability.status is CapabilityStatus.UNAVAILABLE
