"""Trusted personal website discovery adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

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

from .feed_parser import parse_feed
from .rss_source import FEED_MEDIA_TYPES, build_feed_batch

_JSON_LD_LIMIT = 100_000
_SEEN_ARTICLE_LIMIT = 256


def _evidence_id(source_id: str, external_id: str, url: str) -> str:
    material = f"{source_id}\0{external_id}\0{url}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80 if scheme == "http" else None
    return scheme, host, port


def _trusted_origins(source: SourceRecord) -> set[tuple[str, str, int | None]]:
    trusted = {_origin(source.url)}
    raw = source.metadata.get("trusted_origins", [])
    if isinstance(raw, list):
        for value in raw:
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                trusted.add(_origin(value))
    return trusted


def _is_trusted_url(source: SourceRecord, url: str) -> bool:
    try:
        return _origin(url) in _trusted_origins(source)
    except ValueError:
        return False


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class _WebsiteMetadataParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.feed_links: list[str] = []
        self.og: dict[str, str] = {}
        self.json_ld: list[dict[str, Any]] = []
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        lowered = tag.lower()
        if lowered == "link":
            rel = {
                token.lower()
                for token in (values.get("rel") or "").replace(",", " ").split()
            }
            media = (values.get("type") or "").lower()
            href = values.get("href")
            if (
                "alternate" in rel
                and href
                and media
                in {
                    "application/rss+xml",
                    "application/atom+xml",
                    "application/xml",
                    "text/xml",
                }
            ):
                self.feed_links.append(urljoin(self.base_url, href))
        elif lowered == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = (values.get("content") or "").strip()
            if key.startswith("og:") and content:
                self.og[key] = content
        elif lowered == "script":
            script_type = (values.get("type") or "").lower()
            if script_type == "application/ld+json":
                self._in_json_ld = True
                self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._in_json_ld:
            return
        raw = "".join(self._json_ld_parts).strip()
        self._in_json_ld = False
        self._json_ld_parts = []
        if not raw or len(raw) > _JSON_LD_LIMIT:
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        self._collect_json_ld(payload)

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_parts.append(data)

    def _collect_json_ld(self, payload: Any) -> None:
        if isinstance(payload, list):
            for item in payload:
                self._collect_json_ld(item)
            return
        if not isinstance(payload, dict):
            return
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                self._collect_json_ld(item)
        raw_type = payload.get("@type")
        types = {raw_type} if isinstance(raw_type, str) else set(raw_type or [])
        if types & {"Article", "BlogPosting", "NewsArticle"}:
            self.json_ld.append(payload)


def _article_from_metadata(
    *,
    source: SourceRecord,
    final_url: str,
    parser: _WebsiteMetadataParser,
    seen_articles: set[str],
    blocked_feeds: list[str],
) -> AdapterEmission | None:
    structured = parser.json_ld[0] if parser.json_ld else {}
    title = structured.get("headline") or parser.og.get("og:title")
    article_url = structured.get("url") or parser.og.get("og:url") or final_url
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(article_url, str):
        return None
    article_url = urljoin(final_url, article_url)
    if not _is_trusted_url(source, article_url):
        return None
    if article_url in seen_articles:
        return None

    description = structured.get("description") or parser.og.get("og:description")
    if not isinstance(description, str):
        description = None
    author: str | None = None
    raw_author = structured.get("author")
    if isinstance(raw_author, dict):
        raw_name = raw_author.get("name")
        author = raw_name if isinstance(raw_name, str) else None
    elif isinstance(raw_author, str):
        author = raw_author

    published = _parse_iso_datetime(
        structured.get("datePublished") or parser.og.get("article:published_time")
    )
    updated = _parse_iso_datetime(
        structured.get("dateModified") or parser.og.get("article:modified_time")
    )
    raw_type = structured.get("@type")
    type_hint = (
        ContributionType.BLOGPOST
        if raw_type == "BlogPosting"
        else ContributionType.ARTICLE_PUBLICATION
    )
    external_id = f"article:{article_url}"
    item = SourceItem(
        source_id=source.id,
        external_id=external_id,
        title=title.strip(),
        url=article_url,
        description=description.strip() if description else None,
        published_at=published,
        updated_at=updated,
        author=author,
        type_hint=type_hint,
        metadata={"website_root": final_url},
    )
    evidence = Evidence(
        id=_evidence_id(source.id, external_id, final_url),
        source_id=source.id,
        source_item_id=external_id,
        url=final_url,
        text_excerpt=item.description,
        data={
            "open_graph": parser.og,
            "json_ld": structured,
            "blocked_cross_origin_feed_links": blocked_feeds,
        },
    )
    return AdapterEmission(item=item, evidence=(evidence,))


class WebsiteSourceAdapter:
    """Discover structured articles and same-origin feeds from trusted websites."""

    name = "website"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.WEBSITE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership not in {OwnershipStatus.EXPLICIT, OwnershipStatus.VERIFIED}:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="website discovery requires explicit or verified ownership",
            )
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        root_result = await self._fetcher.fetch(
            SafeFetchRequest(url=source.url, allowed_media_types=("text/html",))
        )
        if root_result.outcome is not FetchOutcome.SUCCESS or root_result.text is None:
            kind = (
                AdapterErrorKind.SECURITY
                if root_result.outcome is FetchOutcome.BLOCKED
                else AdapterErrorKind.UNAVAILABLE
            )
            raise SourceAdapterError(
                kind,
                root_result.error_code
                or f"website fetch failed: {root_result.outcome.value}",
            )

        parser = _WebsiteMetadataParser(root_result.final_url)
        parser.feed(root_result.text)
        parser.close()

        feed_links = list(dict.fromkeys(parser.feed_links))
        trusted_feeds = [url for url in feed_links if _is_trusted_url(source, url)]
        blocked_feeds = [url for url in feed_links if url not in trusted_feeds]

        seen_articles = {
            str(value) for value in (cursor or {}).get("seen_articles", []) if value
        }
        emissions: list[AdapterEmission] = []
        article = _article_from_metadata(
            source=source,
            final_url=root_result.final_url,
            parser=parser,
            seen_articles=seen_articles,
            blocked_feeds=blocked_feeds,
        )
        if article is not None:
            emissions.append(article)
            seen_articles.add(article.item.url)

        feed_cursors = (cursor or {}).get("feeds", {})
        if not isinstance(feed_cursors, dict):
            feed_cursors = {}
        next_feed_cursors: dict[str, Any] = dict(feed_cursors)

        for feed_url in trusted_feeds:
            result = await self._fetcher.fetch(
                SafeFetchRequest(url=feed_url, allowed_media_types=FEED_MEDIA_TYPES)
            )
            if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
                continue
            try:
                parsed = parse_feed(result.text)
            except ValueError:
                continue
            prior_cursor = feed_cursors.get(feed_url)
            if not isinstance(prior_cursor, dict):
                prior_cursor = None
            feed_batch = build_feed_batch(
                source=source,
                entries=parsed.entries,
                cursor=prior_cursor,
                feed_url=result.final_url,
                parser_errors=parsed.errors,
            )
            for emission in feed_batch.emissions:
                item = emission.item.model_copy(
                    update={
                        "external_id": (
                            f"feed:{hashlib.sha256(feed_url.encode()).hexdigest()[:16]}:"
                            f"{emission.item.external_id}"
                        )
                    }
                )
                evidence = tuple(
                    evidence.model_copy(
                        update={
                            "id": _evidence_id(
                                source.id,
                                item.external_id,
                                evidence.url or feed_url,
                            ),
                            "source_item_id": item.external_id,
                        }
                    )
                    for evidence in emission.evidence
                )
                emissions.append(AdapterEmission(item=item, evidence=evidence))
            next_feed_cursors[feed_url] = feed_batch.next_cursor

        next_cursor = {
            "seen_articles": sorted(seen_articles)[-_SEEN_ARTICLE_LIMIT:],
            "feeds": next_feed_cursors,
        }
        yield SourceBatch(emissions=tuple(emissions), next_cursor=next_cursor)
