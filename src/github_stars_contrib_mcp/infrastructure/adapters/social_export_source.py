"""Local-only neutral JSON/CSV import for restricted social evidence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from github_stars_contrib_mcp.application.discovery.social_capabilities import (
    SocialAccessMode,
    assess_social_capability,
    is_supported_social_post_url,
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
from github_stars_contrib_mcp.domain.discovery import Evidence, SourceItem, SourceRecord, SourceType
from github_stars_contrib_mcp.domain.ports.source_adapter import (
    AdapterEmission,
    AdapterErrorKind,
    CapabilityStatus,
    SourceAdapterError,
    SourceBatch,
    SourceCapability,
)
from github_stars_contrib_mcp.models import ContributionType

_MAX_IMPORT_BYTES = 10 * 1024 * 1024


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


def _provider(value: Any) -> SourceType | None:
    raw = (_string(value) or "").lower()
    if raw in {"x", "twitter"}:
        return SourceType.X
    if raw == "linkedin":
        return SourceType.LINKEDIN
    return None


def _load_records(path: Path, expected_provider: SourceType) -> list[dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SourceAdapterError(AdapterErrorKind.UNAVAILABLE, f"cannot read import file: {exc}") from exc
    if len(raw) > _MAX_IMPORT_BYTES:
        raise SourceAdapterError(AdapterErrorKind.SECURITY, "social import exceeds 10 MiB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceAdapterError(AdapterErrorKind.PARSE, "social import must be UTF-8") from exc

    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SourceAdapterError(AdapterErrorKind.PARSE, "invalid social import JSON") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise SourceAdapterError(AdapterErrorKind.PARSE, "JSON social import requires schema_version 1")
        if _provider(payload.get("provider")) is not expected_provider:
            raise SourceAdapterError(AdapterErrorKind.PARSE, "social import provider does not match source")
        records = payload.get("posts")
        if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
            raise SourceAdapterError(AdapterErrorKind.PARSE, "JSON social import posts must be objects")
        return list(records)
    if suffix == ".csv":
        rows = list(csv.DictReader(io.StringIO(text)))
        for row in rows:
            if str(row.get("schema_version", "")).strip() != "1":
                raise SourceAdapterError(AdapterErrorKind.PARSE, "CSV social import requires schema_version 1")
            if _provider(row.get("provider")) is not expected_provider:
                raise SourceAdapterError(AdapterErrorKind.PARSE, "social import provider does not match source")
        return [dict(row) for row in rows]
    raise SourceAdapterError(AdapterErrorKind.PARSE, "social import must use .json or .csv")


def _fingerprint(record: dict[str, Any], canonical_url: str) -> str:
    payload = json.dumps(
        {"url": canonical_url, "record": record},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _evidence_id(source_id: str, external_id: str, fingerprint: str) -> str:
    material = f"{source_id}\0{external_id}\0{fingerprint}".encode()
    return f"evidence:{hashlib.sha256(material).hexdigest()}"


class SocialExportSourceAdapter:
    """Import user-provided local evidence without uploading provider exports."""

    name = "social-export"
    version = "1"

    def supports(self, source: SourceRecord) -> bool:
        return source.source_type in {SourceType.X, SourceType.LINKEDIN} and (
            social_access_mode(source) is SocialAccessMode.EXPORT_IMPORT
        )

    def capabilities(self, source: SourceRecord) -> SourceCapability:
        capability = assess_social_capability(source).as_source_capability()
        if capability.status is not CapabilityStatus.AVAILABLE:
            return capability
        path = Path(str(source.metadata.get("import_path", ""))).expanduser()
        if not path.is_file():
            return SourceCapability(
                status=CapabilityStatus.UNAVAILABLE,
                reason="configured social import file does not exist or is not a file",
                user_action="provide an existing local .json or .csv import_path",
            )
        return capability

    async def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]:
        capability = self.capabilities(source)
        if capability.status is CapabilityStatus.UNAVAILABLE:
            raise SourceAdapterError(
                AdapterErrorKind.UNAVAILABLE,
                capability.reason or "social export import is unavailable",
            )
        path = Path(str(source.metadata["import_path"])).expanduser()
        records = _load_records(path, source.source_type)
        prior = (cursor or {}).get("fingerprints", {})
        if not isinstance(prior, dict):
            prior = {}
        next_fingerprints = {str(key): str(value) for key, value in prior.items()}
        emissions: list[AdapterEmission] = []

        for record in records:
            raw_url = _string(record.get("url"))
            if raw_url is None or not is_supported_social_post_url(source.source_type, raw_url):
                raise SourceAdapterError(AdapterErrorKind.PARSE, "social import contains a non-post or invalid URL")
            canonical = canonicalize_source_url(raw_url)
            supplied_id = _string(record.get("id"))
            external_id = (
                f"{source.source_type.value}:{supplied_id}"
                if supplied_id
                else social_post_external_id(source.source_type, canonical.canonical_url)
            )
            fingerprint = _fingerprint(record, canonical.canonical_url)
            next_fingerprints[external_id] = fingerprint
            if str(prior.get(external_id, "")) == fingerprint:
                continue

            raw_text = _string(record.get("text")) or _string(record.get("description"))
            safe_text = None
            if raw_text:
                safe_text = sanitize_untrusted_content(
                    raw_text,
                    media_type="text/plain",
                    source_url=canonical.canonical_url,
                    max_chars=4_000,
                ).excerpt
            title = _string(record.get("title"))
            if title is None and raw_text:
                title = raw_text[:120].strip()
            title = title or canonical.canonical_url
            item = SourceItem(
                source_id=source.id,
                external_id=external_id,
                title=title,
                url=canonical.canonical_url,
                description=safe_text,
                published_at=_datetime(record.get("published_at")),
                author=_string(record.get("author")),
                type_hint=_contribution_type(record.get("contribution_type")),
                metadata={
                    "provider": source.source_type.value,
                    "ingestion_mode": SocialAccessMode.EXPORT_IMPORT.value,
                    "metadata_source": "local_user_export",
                    "imported_evidence": True,
                    "network_fetch": False,
                    "uploaded": False,
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
                    "ingestion_mode": SocialAccessMode.EXPORT_IMPORT.value,
                    "metadata_source": "local_user_export",
                    "imported_evidence": True,
                    "import_file": path.name,
                    "network_fetch": False,
                    "uploaded": False,
                },
            )
            emissions.append(AdapterEmission(item=item, evidence=(evidence,)))

        yield SourceBatch(
            emissions=tuple(emissions),
            next_cursor={"fingerprints": next_fingerprints},
        )
