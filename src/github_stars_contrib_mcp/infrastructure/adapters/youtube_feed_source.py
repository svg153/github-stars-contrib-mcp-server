"""Credential-free limited YouTube channel Atom feed adapter."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qs, urlsplit

from github_stars_contrib_mcp.application.discovery.youtube_identity import source_channel_id
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    OwnershipStatus,
    SourceItem,
    SourceRecord,
    SourceType,
)
from github_stars_contrib_mcp.domain.ports.content_fetcher import (
    ContentFetcher,
    FetchOutcome,
    SafeFetchRequest,
    SafeFetchResult,
)
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapterError,
    SourceBatch,
    SourceCapability,
)
from github_stars_contrib_mcp.models import ContributionType

from .feed_parser import FeedEntry, parse_feed

_YOUTUBE_FEED_MEDIA_TYPES = (
    "application/atom+xml",
    "application/xml",
    "text/xml",
    "text/plain",
)
_RECENT_ID_LIMIT = 128


def _video_id(entry: FeedEntry) -> str:
    query = parse_qs(urlsplit(entry.link).query)
    values = query.get("v")
    if values and values[0]:
        return values[0]
    if entry.stable_id.startswith("yt:video:"):
        return entry.stable_id.removeprefix("yt:video:")
    return entry.stable_id


def _evidence_id(source_id: str, video_id: str, feed_url: str) -> str:
    material = f"{source_id}\0{video_id}\0{feed_url}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


def _fetch_error(result: SafeFetchResult) -> SourceAdapterError:
    if result.outcome is FetchOutcome.BLOCKED:
        return SourceAdapterError(
            AdapterErrorKind.SECURITY,
            result.error_code or "safe fetch blocked YouTube channel feed",
        )
    if result.status_code in {401, 403}:
        return SourceAdapterError(
            AdapterErrorKind.AUTH, "YouTube channel feed request was unauthorized"
        )
    if result.status_code == 429:
        return SourceAdapterError(
            AdapterErrorKind.RATE_LIMIT, "YouTube channel feed was rate limited"
        )
    return SourceAdapterError(
        AdapterErrorKind.UNAVAILABLE,
        result.error_code or f"YouTube channel feed failed: {result.outcome.value}",
    )


class YouTubeFeedSourceAdapter:
    """Recent-upload fallback using only the public channel Atom feed."""

    name = "youtube-feed"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.YOUTUBE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership is OwnershipStatus.REJECTED:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="source ownership was rejected",
            )
        if source_channel_id(source.url, source.metadata) is None:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason=(
                    "credential-free YouTube fallback requires a canonical channel ID"
                ),
            )
        return SourceCapability(
            status=CapabilityStatus.LIMITED,
            reason=(
                "public YouTube Atom feed exposes only recent uploads and reduced metadata"
            ),
        )

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        channel_id = source_channel_id(source.url, source.metadata)
        if channel_id is None:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                "credential-free YouTube fallback requires a canonical channel ID",
            )
        feed_url = (
            "https://www.youtube.com/feeds/videos.xml" f"?channel_id={channel_id}"
        )
        result = await self._fetcher.fetch(
            SafeFetchRequest(
                url=feed_url,
                allowed_media_types=_YOUTUBE_FEED_MEDIA_TYPES,
            )
        )
        if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
            raise _fetch_error(result)
        try:
            parsed = parse_feed(result.text)
        except ValueError as exc:
            raise SourceAdapterError(AdapterErrorKind.PARSE, str(exc)) from exc

        prior_recent = [
            str(item)
            for item in (cursor or {}).get("recent_ids", [])
            if isinstance(item, str)
        ]
        recent_set = set(prior_recent)
        seen_video_ids: list[str] = []
        emissions: list[AdapterEmission] = []
        for entry in parsed.entries:
            video_id = _video_id(entry)
            seen_video_ids.append(video_id)
            if video_id in recent_set:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            external_id = f"youtube:video:{video_id}"
            item = SourceItem(
                source_id=source.id,
                external_id=external_id,
                title=entry.title,
                url=url,
                description=entry.summary,
                published_at=entry.published_at,
                updated_at=entry.updated_at,
                author=entry.author,
                type_hint=ContributionType.VIDEO_PODCAST,
                metadata={
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "discovery_mode": "atom_feed",
                    "limited_history": True,
                },
            )
            evidence = Evidence(
                id=_evidence_id(source.id, video_id, result.final_url),
                source_id=source.id,
                source_item_id=external_id,
                url=result.final_url,
                text_excerpt=entry.summary,
                data={
                    "entry_url": entry.link,
                    "channel_id": channel_id,
                    "video_id": video_id,
                    "parser_errors": list(parsed.errors),
                    "discovery_mode": "atom_feed",
                    "limited_history": True,
                },
            )
            emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

        next_recent = list(dict.fromkeys([*seen_video_ids, *prior_recent]))[
            :_RECENT_ID_LIMIT
        ]
        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={
                "channel_id": channel_id,
                "recent_ids": next_recent,
                "limited_history": True,
            },
        )
