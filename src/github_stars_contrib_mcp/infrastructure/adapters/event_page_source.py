"""Bounded generic event-page contribution discovery adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

from github_stars_contrib_mcp.application.discovery.session_normalizer import (
    SessionDescriptor,
    build_session_item,
    has_verified_speaker_identity,
    parse_datetime,
    verified_speaker_match,
)
from github_stars_contrib_mcp.application.discovery.untrusted_content import (
    UNTRUSTED_LABEL,
    sanitize_untrusted_content,
)
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    OwnershipStatus,
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

_JSON_LD_LIMIT = 100_000
_EVENT_TYPES = {
    "BusinessEvent",
    "EducationEvent",
    "Event",
    "PublicationEvent",
    "SocialEvent",
}


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower().rstrip(".")
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80 if scheme == "http" else None
    return scheme, host, port


def _same_origin(base_url: str, candidate_url: str) -> bool:
    try:
        return _origin(base_url) == _origin(candidate_url)
    except ValueError:
        return False


def _event_types(payload: dict[str, Any]) -> set[str]:
    raw = payload.get("@type")
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(value) for value in raw}
    return set()


def _collect_event_nodes(payload: Any, output: list[dict[str, Any]]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_event_nodes(item, output)
        return
    if not isinstance(payload, dict):
        return
    graph = payload.get("@graph")
    if isinstance(graph, list):
        _collect_event_nodes(graph, output)
    if _event_types(payload) & _EVENT_TYPES:
        output.append(payload)
    for key in ("subEvent", "subEvents", "event"):
        nested = payload.get(key)
        if isinstance(nested, (dict, list)):
            _collect_event_nodes(nested, output)


class _EventPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.og: dict[str, str] = {}
        self.events: list[dict[str, Any]] = []
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        lowered = tag.lower()
        if lowered == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = (values.get("content") or "").strip()
            if key.startswith("og:") and content:
                self.og[key] = content
        elif (
            lowered == "script"
            and (values.get("type") or "").lower() == "application/ld+json"
        ):
            self._in_json_ld = True
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._json_ld_parts.append(data)

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
        _collect_event_nodes(payload, self.events)


def _identity_values(value: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    names: list[str] = []
    urls: list[str] = []
    records = value if isinstance(value, list) else [value]
    for record in records:
        if isinstance(record, str):
            names.append(record)
            continue
        if not isinstance(record, dict):
            continue
        name = _string(record.get("name"))
        if name:
            names.append(name)
        for key in ("url", "sameAs"):
            raw = record.get(key)
            if isinstance(raw, str) and raw.strip():
                urls.append(raw.strip())
            elif isinstance(raw, list):
                urls.extend(str(item).strip() for item in raw if str(item).strip())
    return tuple(dict.fromkeys(names)), tuple(dict.fromkeys(urls))


def _event_url(source_url: str, final_url: str, event: dict[str, Any]) -> str:
    raw = event.get("url")
    if isinstance(raw, str) and raw.strip():
        candidate = urljoin(final_url, raw.strip())
        if _same_origin(source_url, candidate):
            return candidate
    return final_url


def _event_fingerprint(event: dict[str, Any], item_url: str) -> str:
    payload = json.dumps(
        {"event": event, "item_url": item_url},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _evidence_id(source_id: str, external_id: str, fingerprint: str) -> str:
    payload = f"{source_id}\0{external_id}\0{fingerprint}".encode()
    return f"evidence:{hashlib.sha256(payload).hexdigest()}"


class EventPageSourceAdapter:
    """Extract one explicitly registered event/session page without crawling."""

    name = "event-page"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.EVENT_PAGE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership not in {OwnershipStatus.EXPLICIT, OwnershipStatus.VERIFIED}:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="event-page discovery requires an explicit or verified source",
            )
        if not has_verified_speaker_identity(source):
            return SourceCapability(
                status=CapabilityStatus.LIMITED,
                reason="no verified speaker identity; extracted event remains review-only",
            )
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        result = await self._fetcher.fetch(
            SafeFetchRequest(url=source.url, allowed_media_types=("text/html",))
        )
        if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
            kind = (
                AdapterErrorKind.SECURITY
                if result.outcome is FetchOutcome.BLOCKED
                else AdapterErrorKind.UNAVAILABLE
            )
            raise SourceAdapterError(
                kind,
                result.error_code or f"event page fetch failed: {result.outcome.value}",
            )

        parser = _EventPageParser()
        parser.feed(result.text)
        parser.close()
        visible = sanitize_untrusted_content(
            result.text,
            media_type="text/html",
            source_url=result.final_url,
            max_chars=4_000,
        )
        prior = (cursor or {}).get("fingerprints", {})
        if not isinstance(prior, dict):
            prior = {}
        next_fingerprints = {str(key): str(value) for key, value in prior.items()}
        emissions: list[AdapterEmission] = []

        event_nodes = parser.events
        if not event_nodes and parser.og.get("og:title"):
            event_nodes = [
                {
                    "@type": "Event",
                    "name": parser.og.get("og:title"),
                    "description": parser.og.get("og:description"),
                    "url": parser.og.get("og:url") or result.final_url,
                }
            ]

        for index, event in enumerate(event_nodes):
            title = _string(event.get("name")) or _string(event.get("headline"))
            if title is None:
                continue
            session_url = _event_url(source.url, result.final_url, event)
            raw_id = event.get("@id") or event.get("identifier") or session_url
            external_id = (
                f"event-page:{hashlib.sha256(str(raw_id).encode()).hexdigest()[:24]}"
            )
            speaker_names, speaker_urls = _identity_values(
                event.get("speaker") or event.get("performer")
            )
            match = verified_speaker_match(
                source,
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
            )
            description = _string(event.get("description")) or parser.og.get(
                "og:description"
            )
            if description:
                description = sanitize_untrusted_content(
                    description,
                    media_type="text/plain",
                    source_url=result.final_url,
                    max_chars=4_000,
                ).excerpt
            event_name = _string(source.metadata.get("event_name"))
            super_event = event.get("superEvent")
            if event_name is None and isinstance(super_event, dict):
                event_name = _string(super_event.get("name"))
            event_name = event_name or _string(event.get("eventName")) or title
            descriptor = SessionDescriptor(
                provider="event_page",
                event_name=event_name,
                external_id=external_id,
                title=title,
                description=description,
                starts_at=parse_datetime(event.get("startDate")),
                ends_at=parse_datetime(event.get("endDate")),
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
                session_url=session_url,
                recording_url=_string(event.get("recordedIn"))
                or _string(event.get("video")),
                slides_url=_string(event.get("workFeatured")),
                format_hint=_string(event.get("eventStatus")),
                metadata={
                    "event_page_index": index,
                    "speaker_identity_evidenced": match is not None,
                    "session_title_evidenced": True,
                    "confidence_hint": "medium" if match else "low",
                },
            )
            fingerprint = _event_fingerprint(event, session_url)
            next_fingerprints[external_id] = fingerprint
            if str(prior.get(external_id, "")) == fingerprint:
                continue
            item = build_session_item(source, descriptor, speaker_match=match)
            evidence = Evidence(
                id=_evidence_id(source.id, external_id, fingerprint),
                source_id=source.id,
                source_item_id=external_id,
                url=result.final_url,
                text_excerpt=visible.excerpt,
                data={
                    "security_label": UNTRUSTED_LABEL,
                    "json_ld_event": event,
                    "open_graph": parser.og,
                    "speaker_names": list(speaker_names),
                    "speaker_urls": list(speaker_urls),
                    "speaker_match_method": match.method if match else None,
                    "no_recursive_fetch": True,
                },
            )
            emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={"fingerprints": next_fingerprints},
        )
