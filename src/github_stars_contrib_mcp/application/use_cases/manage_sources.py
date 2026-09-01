"""Explicit source registry management use cases."""

from __future__ import annotations

from typing import Any

from github_stars_contrib_mcp.application.discovery.source_identity import (
    canonicalize_source_url,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    utc_now,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import SourceRepository


class ManageSources:
    """Apply user-authorized source registry transitions."""

    def __init__(self, repository: SourceRepository) -> None:
        self._repository = repository

    def list(self, *, enabled_only: bool = False) -> list[SourceRecord]:
        return self._repository.list_sources(enabled_only=enabled_only)

    def add(
        self,
        url: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> SourceRecord:
        canonical = canonicalize_source_url(url)
        existing = self._repository.get_source(canonical.source_id)
        if existing is None:
            source = SourceRecord(
                id=canonical.source_id,
                source_type=canonical.source_type,
                url=canonical.canonical_url,
                ownership=OwnershipStatus.EXPLICIT,
                evidence=[f"user-added:{canonical.canonical_url}"],
                metadata=metadata or {},
            )
        else:
            source = existing.model_copy(deep=True)
            if source.ownership is OwnershipStatus.REJECTED:
                history = list(source.metadata.get("rejection_history", []))
                rejection = source.metadata.get("rejection")
                if rejection:
                    history.append(rejection)
                source.metadata.pop("rejection", None)
                if history:
                    source.metadata["rejection_history"] = history
            if source.ownership is not OwnershipStatus.VERIFIED:
                source.ownership = OwnershipStatus.EXPLICIT
            source.url = canonical.canonical_url
            source.source_type = canonical.source_type
            source.enabled = True
            source.evidence = sorted(
                set(source.evidence).union({f"user-added:{canonical.canonical_url}"})
            )
            source.metadata = {**source.metadata, **(metadata or {})}
            source.updated_at = utc_now()
        return self._repository.upsert_source(source)

    def verify(self, source_id: str) -> SourceRecord:
        source = self._require(source_id).model_copy(deep=True)
        if source.ownership is OwnershipStatus.REJECTED:
            raise ValueError(
                "rejected source must be explicitly re-added before verification"
            )
        source.ownership = OwnershipStatus.VERIFIED
        source.enabled = True
        source.updated_at = utc_now()
        return self._repository.upsert_source(source)

    def reject(self, source_id: str, *, reason: str) -> SourceRecord:
        if not reason.strip():
            raise ValueError("rejection reason must not be empty")
        source = self._require(source_id).model_copy(deep=True)
        source.ownership = OwnershipStatus.REJECTED
        source.enabled = False
        source.metadata = {
            **source.metadata,
            "rejection": {"reason": reason.strip(), "at": utc_now().isoformat()},
        }
        source.updated_at = utc_now()
        return self._repository.upsert_source(source)

    def disable(self, source_id: str) -> SourceRecord:
        source = self._require(source_id).model_copy(deep=True)
        source.enabled = False
        source.updated_at = utc_now()
        return self._repository.upsert_source(source)

    def enable(self, source_id: str) -> SourceRecord:
        source = self._require(source_id).model_copy(deep=True)
        if source.ownership is OwnershipStatus.REJECTED:
            raise ValueError(
                "rejected source must be explicitly re-added before enabling"
            )
        source.enabled = True
        source.updated_at = utc_now()
        return self._repository.upsert_source(source)

    def _require(self, source_id: str) -> SourceRecord:
        source = self._repository.get_source(source_id)
        if source is None:
            raise KeyError(f"Unknown source: {source_id}")
        return source
