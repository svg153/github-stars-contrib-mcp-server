"""Bootstrap trusted discovery sources from existing GitHub Stars data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from github_stars_contrib_mcp.application.discovery.source_identity import (
    canonical_origin,
    canonicalize_source_url,
)
from github_stars_contrib_mcp.domain.discovery import (
    OwnershipStatus,
    SourceRecord,
    SourceType,
    utc_now,
)
from github_stars_contrib_mcp.domain.ports.discovery_repository import SourceRepository
from github_stars_contrib_mcp.domain.ports.stars_api import StarsAPIPort


class BootstrapSourcesResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    sources: list[SourceRecord] = Field(default_factory=list)


def _merge_metadata(
    current: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    merged = {**current, **incoming}
    if "bootstrap" in current or "bootstrap" in incoming:
        merged["bootstrap"] = {
            **current.get("bootstrap", {}),
            **incoming.get("bootstrap", {}),
        }
    return merged


class BootstrapSources:
    """Derive source records only from data Stars already returns."""

    def __init__(self, stars_api: StarsAPIPort, sources: SourceRepository) -> None:
        self._stars_api = stars_api
        self._sources = sources

    @staticmethod
    def _nominee(payload: dict[str, Any]) -> dict[str, Any]:
        current = (
            payload.get("data") if isinstance(payload.get("data"), dict) else payload
        )
        logged_user = current.get("loggedUser") if isinstance(current, dict) else None
        if not isinstance(logged_user, dict):
            return {}
        nominee = logged_user.get("nominee")
        return nominee if isinstance(nominee, dict) else {}

    @staticmethod
    def _merge_source(
        existing: SourceRecord | None,
        *,
        canonical_url: str,
        source_id: str,
        source_type: SourceType,
        ownership: OwnershipStatus,
        evidence: list[str],
        metadata: dict[str, Any],
    ) -> SourceRecord:
        if existing is None:
            return SourceRecord(
                id=source_id,
                source_type=source_type,
                url=canonical_url,
                ownership=ownership,
                evidence=sorted(set(evidence)),
                metadata=metadata,
            )

        source = existing.model_copy(deep=True)
        if source.ownership in {OwnershipStatus.REJECTED, OwnershipStatus.VERIFIED}:
            target_ownership = source.ownership
        elif ownership is OwnershipStatus.EXPLICIT:
            target_ownership = OwnershipStatus.EXPLICIT
        else:
            target_ownership = source.ownership

        target_evidence = sorted(set(source.evidence).union(evidence))
        target_metadata = _merge_metadata(source.metadata, metadata)
        changed = (
            source.url != canonical_url
            or source.source_type != source_type
            or source.ownership != target_ownership
            or source.evidence != target_evidence
            or source.metadata != target_metadata
        )
        if changed:
            source.url = canonical_url
            source.source_type = source_type
            source.ownership = target_ownership
            source.evidence = target_evidence
            source.metadata = target_metadata
            source.updated_at = utc_now()
        return source

    def _persist(
        self,
        result: BootstrapSourcesResult,
        existing: SourceRecord | None,
        source: SourceRecord,
    ) -> None:
        if existing is None:
            result.created += 1
            self._sources.upsert_source(source)
        elif existing.model_dump(mode="json") != source.model_dump(mode="json"):
            result.updated += 1
            self._sources.upsert_source(source)
        else:
            result.skipped += 1

    async def __call__(self) -> BootstrapSourcesResult:
        payload = await self._stars_api.get_user_data()
        nominee = self._nominee(payload)
        result = BootstrapSourcesResult()
        touched: dict[str, SourceRecord] = {}

        for link in nominee.get("links") or []:
            if not isinstance(link, dict) or not link.get("link"):
                result.skipped += 1
                continue
            try:
                canonical = canonicalize_source_url(str(link["link"]))
            except ValueError:
                result.skipped += 1
                continue

            existing = self._sources.get_source(canonical.source_id)
            existing_bootstrap = (
                existing.metadata.get("bootstrap", {}) if existing else {}
            )
            link_id = str(link.get("id") or "")
            platform = str(link.get("platform") or "")
            source = self._merge_source(
                existing,
                canonical_url=canonical.canonical_url,
                source_id=canonical.source_id,
                source_type=canonical.source_type,
                ownership=OwnershipStatus.EXPLICIT,
                evidence=[f"stars-profile-link:{link_id or canonical.canonical_url}"],
                metadata={
                    "bootstrap": {
                        "profile_link_ids": sorted(
                            set(existing_bootstrap.get("profile_link_ids", [])).union(
                                {link_id}
                            )
                            - {""}
                        ),
                        "platforms": sorted(
                            set(existing_bootstrap.get("platforms", [])).union(
                                {platform}
                            )
                            - {""}
                        ),
                    }
                },
            )
            self._persist(result, existing, source)
            touched[source.id] = source

        domain_items: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for contribution in nominee.get("contributions") or []:
            if not isinstance(contribution, dict) or not contribution.get("url"):
                continue
            try:
                origin = canonical_origin(str(contribution["url"]))
            except ValueError:
                continue
            if origin.source_type is not SourceType.WEBSITE:
                continue
            domain_items[origin.source_id].append(contribution)

        for source_id, contributions in sorted(domain_items.items()):
            if len(contributions) < 2:
                continue
            origin = canonical_origin(str(contributions[0]["url"]))
            existing = self._sources.get_source(source_id)
            contribution_ids = sorted(
                str(item.get("id") or item.get("url")) for item in contributions
            )
            source = self._merge_source(
                existing,
                canonical_url=origin.canonical_url,
                source_id=origin.source_id,
                source_type=origin.source_type,
                ownership=OwnershipStatus.INFERRED,
                evidence=[
                    f"stars-contribution:{item_id}" for item_id in contribution_ids
                ],
                metadata={
                    "bootstrap": {
                        "contribution_count": len(contributions),
                        "contribution_ids": contribution_ids,
                    }
                },
            )
            self._persist(result, existing, source)
            touched[source.id] = source

        result.sources = [touched[key] for key in sorted(touched)]
        return result
