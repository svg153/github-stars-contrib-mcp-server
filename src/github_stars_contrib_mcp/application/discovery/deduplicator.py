"""Duplicate assessment against Stars and the local discovery queue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from github_stars_contrib_mcp.application.discovery.fingerprint import (
    CandidateFingerprints,
    canonicalize_url,
    fingerprint_candidate,
    normalize_text,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    DuplicateState,
)
from github_stars_contrib_mcp.domain.ports.stars_api import StarsAPIPort


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    state: DuplicateState
    method: str
    reason: str
    target: str | None = None


@dataclass(frozen=True, slots=True)
class StarsSnapshot:
    available: bool
    contributions: tuple[dict[str, Any], ...]
    error: str | None = None


async def load_stars_snapshot(stars_api: StarsAPIPort | None) -> StarsSnapshot:
    """Read every Stars page exactly once for a discovery run."""

    if stars_api is None:
        return StarsSnapshot(False, (), "stars_api_not_configured")

    rows: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    try:
        while page <= total_pages:
            body = await stars_api.list_contributions(page)
            data = body.get("data", [])
            if not isinstance(data, list):
                raise ValueError("Stars contributions response data is not a list")
            rows.extend(item for item in data if isinstance(item, dict))
            pagination = body.get("pagination", {})
            if not isinstance(pagination, dict):
                pagination = {}
            total_pages = max(page, int(pagination.get("totalPages", page)))
            if total_pages > 1000:
                raise ValueError("Stars pagination exceeds safety limit")
            page += 1
    except Exception as exc:
        return StarsSnapshot(False, (), f"{type(exc).__name__}: {exc}")
    return StarsSnapshot(True, tuple(rows), None)


def _stars_target(item: dict[str, Any]) -> str:
    for key in ("id", "clientId", "client_id"):
        value = item.get(key)
        if value:
            return f"stars:{value}"
    return f"stars:url:{item.get('url', 'unknown')}"


def _parse_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(f"{value}T00:00:00")
        except ValueError:
            return None


def _likely_fields(
    candidate: CandidateContribution,
    *,
    title: Any,
    date: Any,
    contribution_type: Any,
) -> bool:
    if not isinstance(title, str) or normalize_text(title) != normalize_text(
        candidate.title
    ):
        return False
    candidate_type = (
        candidate.contribution_type.value
        if candidate.contribution_type is not None
        else None
    )
    if (
        candidate_type is None
        or str(contribution_type or "").upper() != candidate_type.upper()
    ):
        return False
    candidate_date = candidate.date
    other_date = _parse_date(date)
    if candidate_date is None or other_date is None:
        return False
    return abs((candidate_date.date() - other_date.date()).days) <= 1


class Deduplicator:
    def __init__(self, snapshot: StarsSnapshot) -> None:
        self._snapshot = snapshot

    @property
    def stars_available(self) -> bool:
        return self._snapshot.available

    @property
    def stars_error(self) -> str | None:
        return self._snapshot.error

    def assess(
        self,
        candidate: CandidateContribution,
        local_candidates: list[CandidateContribution],
    ) -> tuple[DuplicateMatch, CandidateFingerprints]:
        fingerprints = fingerprint_candidate(candidate)
        if not self._snapshot.available:
            return (
                DuplicateMatch(
                    DuplicateState.UNKNOWN,
                    "stars_unavailable",
                    "Stars contributions could not be loaded; duplicate status is unknown",
                ),
                fingerprints,
            )

        for existing in self._snapshot.contributions:
            existing_url = existing.get("url")
            if (
                isinstance(existing_url, str)
                and canonicalize_url(existing_url) == fingerprints.canonical_url
            ):
                return (
                    DuplicateMatch(
                        DuplicateState.EXACT,
                        "canonical_url",
                        "Canonical URL already exists in GitHub Stars",
                        _stars_target(existing),
                    ),
                    fingerprints,
                )

        for existing in local_candidates:
            if existing.id == candidate.id:
                continue
            existing_fp = fingerprint_candidate(existing)
            if existing_fp.source == fingerprints.source:
                return (
                    DuplicateMatch(
                        DuplicateState.EXACT,
                        "provider_identity",
                        "Provider source/external ID already exists in the local queue",
                        existing.id,
                    ),
                    fingerprints,
                )
            if existing_fp.url == fingerprints.url:
                return (
                    DuplicateMatch(
                        DuplicateState.EXACT,
                        "canonical_url",
                        "Canonical URL already exists in the local queue",
                        existing.id,
                    ),
                    fingerprints,
                )

        for existing in self._snapshot.contributions:
            if _likely_fields(
                candidate,
                title=existing.get("title"),
                date=existing.get("date"),
                contribution_type=existing.get("type"),
            ):
                return (
                    DuplicateMatch(
                        DuplicateState.LIKELY,
                        "normalized_title_date_type",
                        "Normalized title/type and publication date closely match GitHub Stars",
                        _stars_target(existing),
                    ),
                    fingerprints,
                )

        for existing in local_candidates:
            if existing.id == candidate.id:
                continue
            if _likely_fields(
                candidate,
                title=existing.title,
                date=existing.date,
                contribution_type=existing.contribution_type.value
                if existing.contribution_type is not None
                else None,
            ):
                return (
                    DuplicateMatch(
                        DuplicateState.LIKELY,
                        "normalized_title_date_type",
                        "Normalized title/type and publication date closely match the local queue",
                        existing.id,
                    ),
                    fingerprints,
                )

        return (
            DuplicateMatch(
                DuplicateState.CLEAR,
                "no_match",
                "No exact or likely duplicate was found",
            ),
            fingerprints,
        )
