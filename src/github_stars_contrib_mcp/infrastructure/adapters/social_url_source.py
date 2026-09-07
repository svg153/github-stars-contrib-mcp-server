"""Explicit X/LinkedIn post URL ingestion without scraping or session cookies."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from github_stars_contrib_mcp.application.discovery.social_capabilities import (
    SocialAccessMode,
    assess_social_capability,
    social_access_mode,
    social_post_external_id,
)
from github_stars_contrib_mcp.application.discovery.source_identity import (
    canonicalize_source_url,
)
from github_stars_contrib_mcp.application.discovery.untrusted_content import (
    UNTRUSTED_LABEL,
    sanitize_untrusted_content,
)
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    SourceItem,
    SourceRecord,
    SourceType,
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


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _datetime(value: Any) -> datetime | None:
    raw = _string(value)
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _contribution_type(value: Any) -> ContributionType | None:
    raw = _string(value)
    if raw is None:
        return None
    try:
        return ContributionType(raw.upper())
    except ValueError:
        return None


def _fingerprint(source: SourceRecord, canonical_url: str) -> str:
    payload = json.dumps(
        {
            "url": canonical_url,
            "title": source.metadata.get("title"),
            "text": source.metadata.get("text") or source.metadata.get("description"),
            "published_at": source.metadata.get("published_at"),
            "author": source.metadata.get("author"),
            "contribution_type": source.metadata.get("contribution_type"),
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _evidence_id(source_id: str, external_id: str, fingerprint: str) -> str:
    material = f"{source_id}\0{external_id}\0{fingerprint}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


class SocialURLSourceAdapter:
    """Ingest one explicitly registered post URL as reviewable evidence."""

    name = "social-url"
    version = "1"

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type in {SourceType.X, SourceType.LINKEDIN} and (
            social_access_mode(source) is SocialAccessMode.EXPLICIT_URL
        )

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        return assess_social_capability(source).as_source_capability()

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        capability = self.capabilities(source)
        if capability.status is CapabilityStatus.UNAVAILABLE:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                capability.reason or "explicit social URL is unavailable",
            )

        canonical = canonicalize_source_url(source.url)
        external_id = social_post_external_id(
            source.source_type, canonical.canonical_url
        )
        fingerprint = _fingerprint(source, canonical.canonical_url)
        if (cursor or {}).get("fingerprint") == fingerprint:
            yield SourceBatch(next_cursor={"fingerprint": fingerprint})
            return

        raw_text = _string(source.metadata.get("text")) or _string(
            source.metadata.get("description")
        )
        safe_text = None
        if raw_text:
            safe_text = sanitize_untrusted_content(
                raw_text,
                media_type="text/plain",
                source_url=canonical.canonical_url,
                max_chars=4_000,
            ).excerpt
        title = _string(source.metadata.get("title"))
        if title is None and raw_text:
            title = raw_text[:120].strip()
        title = title or canonical.canonical_url

        item = SourceItem(
            source_id=source.id,
            external_id=external_id,
            title=title,
            url=canonical.canonical_url,
            description=safe_text,
            published_at=_datetime(source.metadata.get("published_at")),
            author=_string(source.metadata.get("author")),
            type_hint=_contribution_type(source.metadata.get("contribution_type")),
            metadata={
                "provider": source.source_type.value,
                "ingestion_mode": SocialAccessMode.EXPLICIT_URL.value,
                "metadata_source": "user_registered",
                "network_fetch": False,
                "authenticated_session": False,
                "review_required": True,
            },
        )
        evidence = Evidence(
            id=_evidence_id(source.id, external_id, fingerprint),
            source_id=source.id,
            source_item_id=external_id,
            url=canonical.canonical_url,
            text_excerpt=safe_text,
            data={
                "security_label": UNTRUSTED_LABEL,
                "provider": source.source_type.value,
                "ingestion_mode": SocialAccessMode.EXPLICIT_URL.value,
                "metadata_source": "user_registered",
                "network_fetch": False,
                "authenticated_session": False,
                "review_required": True,
            },
        )
        yield SourceBatch(
            emissions=(AdapterEmission(item=item, evidence=(evidence,)),),
            next_cursor={"fingerprint": fingerprint},
        )
