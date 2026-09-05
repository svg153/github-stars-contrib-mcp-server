from __future__ import annotations

import httpx
import pytest

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
from github_stars_contrib_mcp.infrastructure.adapters.youtube_feed_source import (
    YouTubeFeedSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.adapters.youtube_source import (
    YouTubeSourceAdapter,
)
from github_stars_contrib_mcp.infrastructure.persistence import (
    SQLiteDiscoveryRepository,
)

CHANNEL_ID = "UC" + "e" * 22
ATOM = """<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>yt:video:fallback1</id>
    <title>Fallback video</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=fallback1"/>
    <published>2026-09-01T10:00:00+00:00</published>
  </entry>
</feed>"""


class FeedFetcher:
    async def fetch(self, request: SafeFetchRequest) -> SafeFetchResult:
        return SafeFetchResult(
            final_url=request.url,
            outcome=FetchOutcome.SUCCESS,
            security=FetchSecurityClassification.UNTRUSTED_PUBLIC,
            status_code=200,
            media_type="application/atom+xml",
            text=ATOM,
            byte_count=len(ATOM.encode()),
        )


def _source(source_id: str) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        source_type=SourceType.YOUTUBE,
        url=f"https://www.youtube.com/channel/{CHANNEL_ID}",
        ownership=OwnershipStatus.VERIFIED,
    )


@pytest.mark.asyncio
async def test_data_api_path_persists_canonical_video_evidence(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [{
                        "id": CHANNEL_ID,
                        "snippet": {"title": "Example"},
                        "contentDetails": {
                            "relatedPlaylists": {"uploads": "UUuploads"}
                        },
                    }]
                },
            )
        if request.url.path.endswith("/playlistItems"):
            return httpx.Response(
                200,
                json={"items": [{"contentDetails": {"videoId": "api1"}}]},
            )
        if request.url.path.endswith("/videos"):
            return httpx.Response(
                200,
                json={"items": [{
                    "id": "api1",
                    "snippet": {
                        "title": "API video",
                        "publishedAt": "2026-09-02T10:00:00Z",
                    },
                    "status": {"privacyStatus": "public"},
                }]},
            )
        raise AssertionError(request.url)

    repository = SQLiteDiscoveryRepository(tmp_path / "api.db")
    repository.upsert_source(_source("source:youtube:api"))
    adapter = YouTubeSourceAdapter(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    runtime = build_discovery_runtime(
        repository=repository,
        adapters=(adapter,),
    )
    run = await runtime.orchestrator.run()

    assert run.status.value == "completed"
    candidates = repository.list_candidates()
    assert len(candidates) == 1
    assert candidates[0].url == "https://www.youtube.com/watch?v=api1"
    evidence = repository.list_evidence(candidates[0].id)
    assert evidence[0].data["discovery_mode"] == "data_api"
    assert evidence[0].data["channel_id"] == CHANNEL_ID


@pytest.mark.asyncio
async def test_feed_path_persists_limited_history_evidence(tmp_path) -> None:
    repository = SQLiteDiscoveryRepository(tmp_path / "feed.db")
    repository.upsert_source(_source("source:youtube:feed"))
    adapter = YouTubeFeedSourceAdapter(FeedFetcher())
    runtime = build_discovery_runtime(
        repository=repository,
        fetcher=FeedFetcher(),
        adapters=(adapter,),
    )
    run = await runtime.orchestrator.run()

    assert run.status.value == "completed"
    candidates = repository.list_candidates()
    assert len(candidates) == 1
    evidence = repository.list_evidence(candidates[0].id)
    assert evidence[0].data["discovery_mode"] == "atom_feed"
    assert evidence[0].data["limited_history"] is True
