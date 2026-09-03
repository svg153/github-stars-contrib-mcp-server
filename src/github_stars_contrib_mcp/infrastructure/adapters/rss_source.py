"""RSS/Atom discovery source adapter."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

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

FEED_MEDIA_TYPES = (
    "application/atom+xml",
    "application/rss+xml",
    "application/xml",
    "text/plain",
    "text/xml",
)
_RECENT_ID_LIMIT = 256


def _evidence_id(source_id: str, external_id: str, url: str) -> str:
    material = f"{source_id}\0{external_id}\0{url}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


def _entry_time(entry: FeedEntry) -> datetime | None:
    return entry.published_at or entry.updated_at


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_cursor_time(cursor: dict[str, Any] | None) -> datetime | None:
    if not cursor:
        return None
    value = cursor.get("watermark")
    if not isinstance(value, str) or not value:
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return _as_utc(datetime.fromisoformat(candidate))
    except ValueError:
        return None


def _classify_fetch_failure(result: SafeFetchResult) -> SourceAdapterError:
    if result.outcome is FetchOutcome.BLOCKED:
        return SourceAdapterError(
            AdapterErrorKind.SECURITY,
            result.error_code or "safe fetch blocked the feed URL",
        )
    if result.status_code in {401, 403}:
        return SourceAdapterError(AdapterErrorKind.AUTH, "feed request was unauthorized")
    if result.status_code == 429:
        return SourceAdapterError(
            AdapterErrorKind.RATE_LIMIT, "feed request was rate limited"
        )
    return SourceAdapterError(
        AdapterErrorKind.UNAVAILABLE,
        result.error_code or f"feed fetch failed: {result.outcome.value}",
    )


def _should_emit(
    entry: FeedEntry,
    *,
    watermark: datetime | None,
    ids_at_watermark: set[str],
    recent_ids: set[str],
) -> bool:
    if entry.stable_id in recent_ids:
        return False
    observed = _entry_time(entry)
    if observed is None or watermark is None:
        return True
    observed = _as_utc(observed)
    if observed > watermark:
        return True
    return observed == watermark and entry.stable_id not in ids_at_watermark


def build_feed_batch(
    *,
    source: SourceRecord,
    entries: tuple[FeedEntry, ...],
    cursor: dict[str, Any] | None,
    feed_url: str,
    parser_errors: tuple[str, ...] = (),
) -> SourceBatch:
    """Build one deterministic incremental checkpoint from parsed feed entries."""

    watermark = _parse_cursor_time(cursor)
    ids_at_watermark = {
        str(value) for value in (cursor or {}).get("ids_at_watermark", []) if value
    }
    recent_ids = {
        str(value) for value in (cursor or {}).get("recent_ids", []) if value
    }

    emissions: list[AdapterEmission] = []
    for entry in entries:
        if not _should_emit(
            entry,
            watermark=watermark,
            ids_at_watermark=ids_at_watermark,
            recent_ids=recent_ids,
        ):
            continue
        item = SourceItem(
            source_id=source.id,
            external_id=entry.stable_id,
            title=entry.title,
            url=entry.link,
            description=entry.summary,
            published_at=entry.published_at,
            updated_at=entry.updated_at,
            author=entry.author,
            type_hint=ContributionType.BLOGPOST,
            metadata={"feed_url": feed_url},
        )
        evidence = Evidence(
            id=_evidence_id(source.id, item.external_id, feed_url),
            source_id=source.id,
            source_item_id=item.external_id,
            url=feed_url,
            text_excerpt=entry.summary,
            data={
                "entry_url": entry.link,
                "author": entry.author,
                "parser_errors": list(parser_errors),
            },
        )
        emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

    dated_entries = [
        (_as_utc(observed), entry.stable_id)
        for entry in entries
        if (observed := _entry_time(entry)) is not None
    ]
    max_time = max((observed for observed, _ in dated_entries), default=watermark)
    next_ids_at_watermark = set(ids_at_watermark)
    if max_time is not None:
        if watermark is None or max_time > watermark:
            next_ids_at_watermark = {
                stable_id
                for observed, stable_id in dated_entries
                if observed == max_time
            }
        elif max_time == watermark:
            next_ids_at_watermark.update(
                stable_id
                for observed, stable_id in dated_entries
                if observed == watermark
            )

    next_recent = list(
        dict.fromkeys(
            [
                *(emission.item.external_id for emission in emissions),
                *recent_ids,
            ]
        )
    )[:_RECENT_ID_LIMIT]
    next_cursor: dict[str, Any] = {
        "watermark": max_time.isoformat() if max_time is not None else None,
        "ids_at_watermark": sorted(next_ids_at_watermark),
        "recent_ids": next_recent,
    }
    return SourceBatch(emissions=tuple(emissions), next_cursor=next_cursor)


class RSSSourceAdapter:
    """Discover contribution candidates from a registered RSS/Atom feed."""

    name = "rss"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.RSS

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership is OwnershipStatus.REJECTED:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="source ownership was rejected",
            )
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        result = await self._fetcher.fetch(
            SafeFetchRequest(
                url=source.url,
                allowed_media_types=FEED_MEDIA_TYPES,
            )
        )
        if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
            raise _classify_fetch_failure(result)
        try:
            parsed = parse_feed(result.text)
        except ValueError as exc:
            raise SourceAdapterError(AdapterErrorKind.PARSE, str(exc)) from exc
        yield build_feed_batch(
            source=source,
            entries=parsed.entries,
            cursor=cursor,
            feed_url=result.final_url,
            parser_errors=parsed.errors,
        )
