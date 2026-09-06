"""Pretalx public API contribution discovery adapter."""

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


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _fetch_error(result: SafeFetchResult, provider: str) -> SourceAdapterError:
    if result.outcome is FetchOutcome.BLOCKED:
        return SourceAdapterError(
            AdapterErrorKind.SECURITY,
            result.error_code or f"safe fetch blocked {provider} source",
        )
    if result.status_code in {401, 403}:
        return SourceAdapterError(AdapterErrorKind.AUTH, f"{provider} source was unauthorized")
    if result.status_code == 429:
        return SourceAdapterError(AdapterErrorKind.RATE_LIMIT, f"{provider} source was rate limited")
    return SourceAdapterError(
        AdapterErrorKind.UNAVAILABLE,
        result.error_code or f"{provider} fetch failed: {result.outcome.value}",
    )


def _results(payload: Any, *, label: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("results", "submissions", "slots"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise SourceAdapterError(AdapterErrorKind.PARSE, f"invalid Pretalx {label} payload")


def _speaker_values(submission: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    ids: list[str] = []
    names: list[str] = []
    urls: list[str] = []
    raw = submission.get("speakers")
    if not isinstance(raw, list):
        return (), (), ()
    for speaker in raw:
        if isinstance(speaker, (str, int)):
            ids.append(str(speaker))
            continue
        if not isinstance(speaker, dict):
            continue
        for key in ("code", "id"):
            if speaker.get(key) is not None:
                ids.append(str(speaker[key]))
                break
        name = _string(speaker.get("name"))
        if name:
            names.append(name)
        for key in ("url", "profile_url"):
            value = speaker.get(key)
            if isinstance(value, str) and value.strip():
                urls.append(value.strip())
    return (
        tuple(dict.fromkeys(ids)),
        tuple(dict.fromkeys(names)),
        tuple(dict.fromkeys(urls)),
    )


def _submission_id(submission: dict[str, Any]) -> str | None:
    for key in ("code", "id"):
        value = submission.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _slot_submission_id(slot: dict[str, Any]) -> str | None:
    raw = slot.get("submission")
    if isinstance(raw, dict):
        return _submission_id(raw)
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    for key in ("submission_code", "submissionCode"):
        value = slot.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _slot_map(slots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for slot in slots:
        submission_id = _slot_submission_id(slot)
        if submission_id:
            result[submission_id] = slot
    return result


def _session_url(source: SourceRecord, submission: dict[str, Any], submission_id: str) -> str | None:
    value = submission.get("url")
    if isinstance(value, str) and value.strip():
        return value.strip()
    event_url = source.metadata.get("public_event_url")
    if isinstance(event_url, str) and event_url.strip():
        return f"{event_url.rstrip('/')}/talk/{submission_id}/"
    return None


def _format_hint(submission: dict[str, Any]) -> str | None:
    value = submission.get("submission_type") or submission.get("type")
    if isinstance(value, dict):
        return _string(value.get("name")) or _string(value.get("title"))
    return _string(value)


def _fingerprint(submission: dict[str, Any], slot: dict[str, Any] | None, descriptor: SessionDescriptor) -> str:
    material = {
        "submission": submission,
        "slot": slot,
        "normalized": {
            "title": descriptor.title,
            "starts_at": descriptor.starts_at.isoformat() if descriptor.starts_at else None,
            "ends_at": descriptor.ends_at.isoformat() if descriptor.ends_at else None,
            "url": descriptor.session_url,
            "format": descriptor.format_hint,
        },
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _evidence_id(source_id: str, submission_id: str, fingerprint: str) -> str:
    payload = f"{source_id}\0{submission_id}\0{fingerprint}".encode()
    return f"evidence:{hashlib.sha256(payload).hexdigest()}"


class PretalxSourceAdapter:
    """Read explicitly registered Pretalx public submission/schedule APIs."""

    name = "pretalx"
    version = "1"

    def __init__(self, fetcher: ContentFetcher) -> None:
        self._fetcher = fetcher

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type is SourceType.PRETALX

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        if source.ownership not in {OwnershipStatus.EXPLICIT, OwnershipStatus.VERIFIED}:
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="Pretalx discovery requires an explicit or verified source",
            )
        if not has_verified_speaker_identity(source):
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="Pretalx discovery requires a verified speaker ID, URL, or exact name",
            )
        schedule_url = source.metadata.get("schedule_url")
        if not isinstance(schedule_url, str) or not schedule_url.strip():
            return SourceCapability(
                status=CapabilityStatus.LIMITED,
                reason="no explicit Pretalx schedule_url; session dates may be unavailable",
            )
        return SourceCapability(status=CapabilityStatus.AVAILABLE)

    async def _fetch_json(self, url: str, *, label: str) -> Any:
        result = await self._fetcher.fetch(
            SafeFetchRequest(url=url, allowed_media_types=_JSON_MEDIA_TYPES)
        )
        if result.outcome is not FetchOutcome.SUCCESS or result.text is None:
            raise _fetch_error(result, "Pretalx")
        try:
            return json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise SourceAdapterError(
                AdapterErrorKind.PARSE,
                f"invalid Pretalx {label} JSON",
            ) from exc

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        submissions_payload = await self._fetch_json(source.url, label="submissions")
        submissions = _results(submissions_payload, label="submissions")
        schedule_url = source.metadata.get("schedule_url")
        slots: list[dict[str, Any]] = []
        if isinstance(schedule_url, str) and schedule_url.strip():
            schedule_payload = await self._fetch_json(schedule_url.strip(), label="schedule")
            slots = _results(schedule_payload, label="schedule")
        slots_by_submission = _slot_map(slots)

        prior = (cursor or {}).get("fingerprints", {})
        if not isinstance(prior, dict):
            prior = {}
        next_fingerprints = {str(key): str(value) for key, value in prior.items()}
        event_name = _string(source.metadata.get("event_name")) or "Pretalx event"
        emissions: list[AdapterEmission] = []

        for submission in submissions:
            submission_id = _submission_id(submission)
            title = _string(submission.get("title"))
            if submission_id is None or title is None:
                continue
            speaker_ids, speaker_names, speaker_urls = _speaker_values(submission)
            match = verified_speaker_match(
                source,
                speaker_ids=speaker_ids,
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
            )
            if match is None:
                continue
            slot = slots_by_submission.get(submission_id)
            starts_at = parse_datetime((slot or {}).get("start"))
            ends_at = parse_datetime((slot or {}).get("end"))
            description = (
                _string(submission.get("abstract"))
                or _string(submission.get("description"))
                or _string(submission.get("notes"))
            )
            if description:
                description = sanitize_untrusted_content(
                    description,
                    media_type="text/plain",
                    source_url=source.url,
                    max_chars=4_000,
                ).excerpt
            descriptor = SessionDescriptor(
                provider="pretalx",
                event_name=event_name,
                external_id=f"pretalx:submission:{submission_id}",
                title=title,
                description=description,
                starts_at=starts_at,
                ends_at=ends_at,
                speaker_ids=speaker_ids,
                speaker_names=speaker_names,
                speaker_urls=speaker_urls,
                session_url=_session_url(source, submission, submission_id),
                recording_url=_string(submission.get("recording_url")),
                slides_url=_string(submission.get("slides_url")),
                format_hint=_format_hint(submission),
                metadata={
                    "room": (slot or {}).get("room"),
                    "track": submission.get("track"),
                    "state": submission.get("state"),
                },
            )
            fingerprint = _fingerprint(submission, slot, descriptor)
            next_fingerprints[submission_id] = fingerprint
            if str(prior.get(submission_id, "")) == fingerprint:
                continue
            item = build_session_item(source, descriptor, speaker_match=match)
            excerpt = sanitize_untrusted_content(
                description or title,
                media_type="text/plain",
                source_url=source.url,
                max_chars=2_000,
            )
            evidence = Evidence(
                id=_evidence_id(source.id, submission_id, fingerprint),
                source_id=source.id,
                source_item_id=item.external_id,
                url=source.url,
                text_excerpt=excerpt.excerpt,
                data={
                    "security_label": UNTRUSTED_LABEL,
                    "event_name": event_name,
                    "submission_id": submission_id,
                    "speaker_ids": list(speaker_ids),
                    "speaker_names": list(speaker_names),
                    "speaker_match_method": match.method,
                    "session_format": normalize_session_format(descriptor.format_hint),
                    "slot": slot,
                    "session_url": descriptor.session_url,
                },
            )
            emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

        next_fingerprints = dict(list(next_fingerprints.items())[-_CURSOR_LIMIT:])
        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={"fingerprints": next_fingerprints},
        )
