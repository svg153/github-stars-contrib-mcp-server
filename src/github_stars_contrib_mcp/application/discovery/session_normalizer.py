"""Provider-neutral session normalization and verified speaker matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from github_stars_contrib_mcp.domain.discovery import SourceItem, SourceRecord
from github_stars_contrib_mcp.models import ContributionType


@dataclass(frozen=True, slots=True)
class SpeakerMatch:
    """Explain how a session matched an explicitly verified speaker identity."""

    method: str
    value: str


@dataclass(frozen=True, slots=True)
class SessionDescriptor:
    """Provider-neutral public speaking session representation."""

    provider: str
    event_name: str
    external_id: str
    title: str
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    speaker_ids: tuple[str, ...] = ()
    speaker_names: tuple[str, ...] = ()
    speaker_urls: tuple[str, ...] = ()
    session_url: str | None = None
    recording_url: str | None = None
    slides_url: str | None = None
    format_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def parse_datetime(value: Any) -> datetime | None:
    """Parse common provider timestamps into timezone-aware UTC datetimes."""

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


def normalize_session_format(value: Any) -> str | None:
    """Normalize provider-specific session format labels without inventing Stars types."""

    if not isinstance(value, str) or not value.strip():
        return None
    normalized = " ".join(value.strip().split()).casefold()
    if "workshop" in normalized or "hands-on" in normalized:
        return "workshop"
    if "keynote" in normalized:
        return "keynote"
    if any(token in normalized for token in ("talk", "presentation", "session")):
        return "talk"
    return normalized[:80]


def _metadata_values(metadata: dict[str, Any], *keys: str) -> tuple[str, ...]:
    values: list[str] = []
    for key in keys:
        raw = metadata.get(key)
        if isinstance(raw, str) and raw.strip():
            values.append(raw.strip())
        elif isinstance(raw, (list, tuple, set)):
            values.extend(str(item).strip() for item in raw if str(item).strip())
    return tuple(dict.fromkeys(values))


def _normalize_identity_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower().rstrip(".")
    if not scheme or not host:
        return value.strip().rstrip("/")
    try:
        port = parsed.port
    except ValueError:
        port = None
    default_port = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    netloc = host if port is None or default_port else f"{host}:{port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def has_verified_speaker_identity(source: SourceRecord) -> bool:
    """Return whether source metadata contains an explicit speaker identity anchor."""

    metadata = source.metadata
    return bool(
        _metadata_values(metadata, "verified_speaker_ids", "speaker_ids", "speaker_id")
        or _metadata_values(
            metadata,
            "verified_speaker_names",
            "speaker_names",
            "speaker_name",
        )
        or _metadata_values(
            metadata,
            "verified_speaker_urls",
            "speaker_urls",
            "speaker_url",
        )
    )


def verified_speaker_match(
    source: SourceRecord,
    *,
    speaker_ids: tuple[str, ...] = (),
    speaker_names: tuple[str, ...] = (),
    speaker_urls: tuple[str, ...] = (),
) -> SpeakerMatch | None:
    """Match only exact configured IDs, URLs, or names; never fuzzy names."""

    metadata = source.metadata
    configured_ids = set(
        _metadata_values(metadata, "verified_speaker_ids", "speaker_ids", "speaker_id")
    )
    for value in speaker_ids:
        normalized = value.strip()
        if normalized and normalized in configured_ids:
            return SpeakerMatch(method="speaker_id", value=normalized)

    configured_urls = {
        _normalize_identity_url(value)
        for value in _metadata_values(
            metadata,
            "verified_speaker_urls",
            "speaker_urls",
            "speaker_url",
        )
    }
    for value in speaker_urls:
        normalized = _normalize_identity_url(value)
        if normalized and normalized in configured_urls:
            return SpeakerMatch(method="speaker_url", value=normalized)

    configured_names = {
        " ".join(value.split()).casefold()
        for value in _metadata_values(
            metadata,
            "verified_speaker_names",
            "speaker_names",
            "speaker_name",
        )
    }
    for value in speaker_names:
        normalized = " ".join(value.split()).casefold()
        if normalized and normalized in configured_names:
            return SpeakerMatch(method="speaker_name", value=normalized)
    return None


def build_session_item(
    source: SourceRecord,
    descriptor: SessionDescriptor,
    *,
    speaker_match: SpeakerMatch | None,
) -> SourceItem:
    """Create a provider-neutral source item while preserving session evidence metadata."""

    title = " ".join(descriptor.title.split()).strip()
    if not title:
        raise ValueError("session title must not be empty")
    item_url = descriptor.session_url or descriptor.recording_url or source.url
    metadata = {
        "provider": descriptor.provider,
        "event_name": descriptor.event_name,
        "session_end": descriptor.ends_at.isoformat() if descriptor.ends_at else None,
        "speaker_ids": list(descriptor.speaker_ids),
        "speaker_names": list(descriptor.speaker_names),
        "speaker_urls": list(descriptor.speaker_urls),
        "speaker_match_method": speaker_match.method if speaker_match else None,
        "speaker_match_value": speaker_match.value if speaker_match else None,
        "session_format": normalize_session_format(descriptor.format_hint),
        "recording_url": descriptor.recording_url,
        "slides_url": descriptor.slides_url,
        **descriptor.metadata,
    }
    return SourceItem(
        source_id=source.id,
        external_id=descriptor.external_id,
        title=title,
        url=item_url,
        description=descriptor.description,
        published_at=descriptor.starts_at,
        updated_at=descriptor.starts_at,
        author=", ".join(descriptor.speaker_names) or None,
        type_hint=ContributionType.SPEAKING if speaker_match else None,
        metadata=metadata,
    )
