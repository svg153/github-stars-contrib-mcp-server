"""Sessionize public JSON contribution discovery adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from typing import Any

from github_stars_contrib_mcp.application.discovery.session_normalizer import (
    SessionDescriptor,
    build_session_item,
    has_verified_speaker_identity,
    normalize_session_format,
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

_JSON_MEDIA_TYPES = ("application/json", "text/plain")
_CURSOR_LIMIT = 256


def _fetch_error(result: SafeFetchResult) -> SourceAdapterError:
    if result.outcome is FetchOutcome.BLOCKED:
        return SourceAdapterError(
            AdapterErrorKind.SECURITY,
            result.error_code or "safe fetch blocked Sessionize source",
        )
    if result.status_code in {401, 403}:
        return SourceAdapterError(AdapterErrorKind.AUTH, "Sessionize source was unauthorized")
    if result.status_code == 429:
        return SourceAdapterError(AdapterErrorKind.RATE_LIMIT, "Sessionize source was rate limited")
    return SourceAdapterError(
        AdapterErrorKind.UNAVAILABLE,
        result.error_code or f"Sessionize fetch failed: {result.outcome.value}",
    )


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _speaker_urls(speaker: dict[str, Any]) -> tuple[str, ...]:
    urls: list[str] = []
    for key in ("profileUrl", "url"):
        value = speaker.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
    links = speaker.get("links")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            value = link.get("url")
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())
    return tuple(dict.fromkeys(urls))


def _format_from_categories(
    session: dict[str, Any], categories: list[dict[str, Any]]
) -> str | None:
    item_ids = {
        str(value)
        for value in session.get("categoryItems", [])
        if isinstance(value, (str, int))
    }
    if not item_ids:
        return _string(session.get("format"))
    for category in categories:
        if not isinstance(category, dict):
            continue
        title = _string(category.get("title")) or ""
        items = category.get("items")
        if "format" not in title.casefold() or not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or str(item.get("id")) not in item_ids:
                continue
            return _string(item.get("name"))
    return _string(session.get("format"))


def _session_url(source: SourceRecord, session: dict[str, Any], session_id: str) -> str | None:
    for key in ("url", "sessionUrl"):
        value = session.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    template = source.metadata.get("session_url_template")
    if isinstance(template, str) and "{id}" in template:
        return template.replace("{id}", session_id)
    event_url = source.metadata.get("public_event_url")
    return event_url.strip() if isinstance(event_url, str) and event_url.strip() else None


def _fingerprint(session: dict[str, Any], descriptor: SessionDescriptor) -> str:
    material = {
        "session": session,
        "normalized": {
            "title": descriptor.title,
            "starts_at": descriptor.starts_at.isoformat() if descriptor.starts_at else None,
            "ends_at": descriptor.ends_at.isoformat() if descriptor.ends_at else None,
            "url": descriptor.session_url,
            "recording_url": descriptor.recording_url,
            "format": descriptor.format_hint,
        },
    }
    payload = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def _evidence_id(source_id: str, session_id: str, fingerprint: str) -> str:
    payload = f"{source_id}\0{session_id}\0{fingerprint}".encode()
    return f"evidence:{hashlib.sha256(payload).hexdigest()}"


class SessionizeSourceAdapter:
    """Read explicitly registered Sessionize public API JSON sources."""

    name = "sessionize"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.SESSIONIZE

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership not in {OwnershipStatus.EXPLICIT, OwnershipStatus.VERIFIED}:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="Sessionize discovery requires an explicit or verified source",
            )
        if not has_verified_speaker_identity(source):
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="Sessionize discovery requires a verified speaker ID, URL, or exact name",
            )
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        result = await self._fetcher.fetch(
            SafeFetchRequest(url=source.url, allowed_media_types=_JSON_MEDIA_TYPES)
        )
        if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
            raise _fetch_error(result)
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise SourceAdapterError(AdapterErrorKind.PARSE, "invalid Sessionize JSON") from exc
        if not isinstance(payload, dict):
            raise SourceAdapterError(AdapterErrorKind.PARSE, "Sessionize payload must be an object")

        sessions = payload.get("sessions")
        speakers = payload.get("speakers")
        categories = payload.get("categories")
        if not isinstance(sessions, list) or not isinstance(speakers, list):
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                "Sessionize payload must contain sessions and speakers arrays",
            )
        category_records = [item for item in categories or [] if isinstance(item, dict)]
        speaker_map = {
            str(speaker.get("id")): speaker
            for speaker in speakers
            if isinstance(speaker, dict) and speaker.get("id") is not None
        }
        prior = (cursor or {}).get("fingerprints", {})
        if not isinstance(prior, dict):
            prior = {}
        next_fingerprints = {str(key): str(value) for key, value in prior.items()}
        emissions: list[AdapterEmission] = []
        event_name = (
            _string(source.metadata.get("event_name"))
            or _string(payload.get("eventName"))
            or "Sessionize event"
        )

        for raw_session in sessions:
            if not isinstance(raw_session, dict) or raw_session.get("id") is None:
                continue
            if raw_session.get("isServiceSession") is True:
                continue
            session_id = str(raw_session["id"])
            raw_speaker_ids = raw_session.get("speakers")
            speaker_ids = tuple(
                str(value)
                for value in raw_speaker_ids or []
                if isinstance(value, (str, int))
            )
            speaker_records = [speaker_map[value] for value in speaker_ids if value in speaker_map]
            speaker_names = tuple(
                name
                for speaker in speaker_records
                if (name := _string(speaker.get("fullName"))) is not None
            )
            speaker_urls = tuple(
                dict.fromkeys(
                    url for speaker in speaker_records for url in _speaker_urls(speaker)
                )
            )
            match = verified_speaker_match(
                source,
                speaker_ids=speaker_ids,
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
            )
            if match is None:
                continue
            title = _string(raw_session.get("title"))
            if title is None:
                continue
            description = _string(raw_session.get("description"))
            if description:
                description = sanitize_untrusted_content(
                    description,
                    media_type="text/plain",
                    source_url=result.final_url,
                    max_chars=4_000,
                ).excerpt
            recording_url = _string(raw_session.get("recordingUrl"))
            live_url = _string(raw_session.get("liveUrl"))
            descriptor = SessionDescriptor(
                provider="sessionize",
                event_name=event_name,
                external_id=f"sessionize:session:{session_id}",
                title=title,
                description=description,
                starts_at=parse_datetime(raw_session.get("startsAt")),
                ends_at=parse_datetime(raw_session.get("endsAt")),
                speaker_ids=speaker_ids,
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
                session_url=_session_url(source, raw_session, session_id),
                recording_url=recording_url or live_url,
                slides_url=_string(raw_session.get("slidesUrl")),
                format_hint=_format_from_categories(raw_session, category_records),
                metadata={
                    "room_id": raw_session.get("roomId"),
                    "status": raw_session.get("status"),
                    "live_url": live_url,
                },
            )
            fingerprint = _fingerprint(raw_session, descriptor)
            next_fingerprints[session_id] = fingerprint
            if str(prior.get(session_id, "")) == fingerprint:
                continue
            item = build_session_item(source, descriptor, speaker_match=match)
            evidence_excerpt = sanitize_untrusted_content(
                description or title,
                media_type="text/plain",
                source_url=result.final_url,
                max_chars=2_000,
            )
            evidence = Evidence(
                id=_evidence_id(source.id, session_id, fingerprint),
                source_id=source.id,
                source_item_id=item.external_id,
                url=result.final_url,
                text_excerpt=evidence_excerpt.excerpt,
                data={
                    "security_label": UNTRUSTED_LABEL,
                    "event_name": event_name,
                    "session_id": session_id,
                    "speaker_ids": list(speaker_ids),
                    "speaker_names": list(speaker_names),
                    "speaker_match_method": match.method,
                    "session_format": normalize_session_format(descriptor.format_hint),
                    "recording_url": descriptor.recording_url,
                    "session_url": descriptor.session_url,
                },
            )
            emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

        next_fingerprints = dict(list(next_fingerprints.items())[-_CURSOR_LIMIT:])
        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={"fingerprints": next_fingerprints},
        )
