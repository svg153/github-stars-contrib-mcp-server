from __future__ import annotations

import httpx
import pytest

from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    CapabilityStatus,
    SourceAdapterError,
)
from github_stars_contrib_mcp.infrastructure.adapters.youtube_source import (
    YouTubeSourceAdapter,
)
from github_stars_contrib_mcp.models import ContributionType


def _source(url: str = "https://www.youtube.com/@github") -> SourceRecord:
    return SourceRecord(
        id="source:youtube",
        source_type=SourceType.YOUTUBE,
        url=url,
        ownership=OwnershipStatus.EXPLICIT,
    )


@pytest.mark.asyncio
async def test_data_api_resolves_handle_pages_uploads_and_batches_metadata() -> None:
    channel_id = "UC" + "a" * 22
    calls: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        calls.append((request.url.path, params))
        if request.url.path.endswith("/channels"):
            assert params["forHandle"] == "@github"
            assert params["key"] == "secret"
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": channel_id,
                            "snippet": {"title": "GitHub"},
                            "contentDetails": {
                                "relatedPlaylists": {"uploads": "UUuploads"}
                            },
                        }
                    ]
                },
            )
        if request.url.path.endswith("/playlistItems"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {"contentDetails": {"videoId": "video-1"}},
                        {"contentDetails": {"videoId": "video-2"}},
                    ]
                },
            )
        if request.url.path.endswith("/videos"):
            assert params["id"] == "video-1,video-2"
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "video-1",
                            "snippet": {
                                "title": "One",
                                "description": "First",
                                "publishedAt": "2026-09-01T10:00:00Z",
                            },
                            "status": {"privacyStatus": "public"},
                        },
                        {
                            "id": "video-2",
                            "snippet": {
                                "title": "Two",
                                "description": "Second",
                                "publishedAt": "2026-09-02T10:00:00Z",
                            },
                            "status": {"privacyStatus": "public"},
                        },
                    ]
                },
            )
        raise AssertionError(request.url)

    adapter = YouTubeSourceAdapter(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    batches = [batch async for batch in adapter.iter_items(_source(), None)]

    assert adapter.capabilities(_source()).status is CapabilityStatus.AVAILABLE
    assert len(batches) == 1
    assert [e.item.external_id for e in batches[0].emissions] == [
        "youtube:video:video-1",
        "youtube:video:video-2",
    ]
    assert all(
        emission.item.type_hint is ContributionType.VIDEO_PODCAST
        for emission in batches[0].emissions
    )
    assert batches[0].next_cursor["channel_id"] == channel_id
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_recent_cursor_prevents_duplicate_video_metadata_fetch() -> None:
    channel_id = "UC" + "a" * 22

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/channels"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": channel_id,
                            "contentDetails": {
                                "relatedPlaylists": {"uploads": "UUuploads"}
                            },
                        }
                    ]
                },
            )
        if request.url.path.endswith("/playlistItems"):
            return httpx.Response(
                200,
                json={"items": [{"contentDetails": {"videoId": "known"}}]},
            )
        if request.url.path.endswith("/videos"):
            raise AssertionError("known videos must not be re-fetched")
        raise AssertionError(request.url)

    adapter = YouTubeSourceAdapter(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    batches = [
        batch
        async for batch in adapter.iter_items(
            _source(),
            {"recent_ids": ["known"]},
        )
    ]
    assert batches[0].emissions == ()


@pytest.mark.asyncio
async def test_quota_and_invalid_key_are_classified() -> None:
    def quota_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "errors": [{"reason": "quotaExceeded"}],
                    "message": "quota",
                }
            },
        )

    quota = YouTubeSourceAdapter(
        api_key="secret",
        transport=httpx.MockTransport(quota_handler),
    )
    with pytest.raises(SourceAdapterError) as quota_error:
        _ = [batch async for batch in quota.iter_items(_source(), None)]
    assert quota_error.value.kind.value == "rate_limit"

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"errors": [{"reason": "keyInvalid"}]}},
        )

    auth = YouTubeSourceAdapter(
        api_key="bad",
        transport=httpx.MockTransport(auth_handler),
    )
    with pytest.raises(SourceAdapterError) as auth_error:
        _ = [batch async for batch in auth.iter_items(_source(), None)]
    assert auth_error.value.kind.value == "auth"
    assert auth.capabilities(_source()).status is CapabilityStatus.UNAVAILABLE


def test_custom_url_requires_api_confirmed_channel_metadata() -> None:
    adapter = YouTubeSourceAdapter(api_key="secret")
    source = _source("https://www.youtube.com/c/Example")
    assert adapter.capabilities(source).status is CapabilityStatus.UNAVAILABLE
