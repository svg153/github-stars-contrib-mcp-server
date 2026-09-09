"""Regression-oriented labeled evaluation for discovery decisions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from github_stars_contrib_mcp.application.discovery.confidence import assess_confidence
from github_stars_contrib_mcp.application.discovery.deduplicator import (
    Deduplicator,
    StarsSnapshot,
)
from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    DuplicateState,
    Evidence,
    Provenance,
    SourceRecord,
)
from github_stars_contrib_mcp.models import ContributionType

FIXTURE = Path(__file__).parent / "fixtures" / "discovery_cases.json"


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _candidate(payload: dict[str, Any], *, suffix: str = "") -> CandidateContribution:
    contribution_type = payload.get("type")
    return CandidateContribution(
        id=f"eval:{payload['external_id']}{suffix}",
        source_id=payload["source_id"],
        external_id=payload["external_id"],
        title=payload["title"],
        url=payload["url"],
        contribution_type=(
            ContributionType(contribution_type) if contribution_type is not None else None
        ),
        date=_dt(payload.get("date")),
        provenance=Provenance(
            adapter="eval",
            adapter_version="1",
            metadata=dict(payload.get("provenance") or {}),
        ),
    )


def _evidence(source_id: str, payloads: list[dict[str, Any]]) -> list[Evidence]:
    return [
        Evidence(
            id=item["id"],
            source_id=source_id,
            source_item_id="eval-item",
            url=item.get("url"),
            text_excerpt=item.get("text"),
        )
        for item in payloads
    ]


def _load_cases() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE.read_text())
    assert isinstance(data, list)
    return data


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["id"])
def test_labeled_discovery_decisions(case: dict[str, Any]) -> None:
    source_payload = case["source"]
    source = SourceRecord(
        id=source_payload["id"],
        source_type=source_payload["type"],
        url=source_payload["url"],
        ownership=source_payload["ownership"],
        evidence=list(source_payload.get("evidence") or []),
    )
    candidate = _candidate(case["candidate"])
    evidence = _evidence(source.id, case["evidence"])
    local = [
        _candidate(item, suffix=f":local:{index}")
        for index, item in enumerate(case.get("local") or [])
    ]
    snapshot_payload = case["stars"]
    snapshot = StarsSnapshot(
        available=bool(snapshot_payload["available"]),
        contributions=tuple(snapshot_payload.get("contributions") or ()),
        error=None if snapshot_payload["available"] else "eval:stars_unavailable",
    )

    duplicate, _ = Deduplicator(snapshot).assess(candidate, local)
    confidence = assess_confidence(
        source,
        candidate,
        evidence,
        duplicate_state=duplicate.state,
    )
    expected = case["expected"]

    assert duplicate.state is DuplicateState(expected["duplicate"])
    actual_type = (
        candidate.contribution_type.value
        if candidate.contribution_type is not None
        else None
    )
    assert actual_type == expected["type"]
    assert expected["ownership_min"] <= confidence.ownership <= expected["ownership_max"]
    assert (
        expected["contribution_min"]
        <= confidence.contribution
        <= expected["contribution_max"]
    )
    assert len(evidence) >= expected["required_evidence"]


def test_eval_corpus_covers_precision_and_safety_cases() -> None:
    cases = _load_cases()
    ids = {case["id"] for case in cases}

    assert len(ids) == len(cases)
    assert {
        "rss_new_blog",
        "github_release",
        "youtube_owned_video",
        "sessionize_verified_talk",
        "social_url_missing_metadata",
        "exact_duplicate_tracking_url",
        "likely_duplicate_mirror",
        "unrelated_noise_incomplete",
        "prompt_injection_is_evidence_only",
    } <= ids
    assert {case["expected"]["duplicate"] for case in cases} >= {
        "clear",
        "exact",
        "likely",
    }


def test_prompt_injection_text_never_becomes_identity_or_confidence_reason() -> None:
    case = next(
        item
        for item in _load_cases()
        if item["id"] == "prompt_injection_is_evidence_only"
    )
    source_payload = case["source"]
    source = SourceRecord(
        id=source_payload["id"],
        source_type=source_payload["type"],
        url=source_payload["url"],
        ownership=source_payload["ownership"],
        evidence=source_payload["evidence"],
    )
    candidate = _candidate(case["candidate"])
    evidence = _evidence(source.id, case["evidence"])
    duplicate, fingerprints = Deduplicator(StarsSnapshot(True, ())).assess(
        candidate, []
    )
    confidence = assess_confidence(
        source,
        candidate,
        evidence,
        duplicate_state=duplicate.state,
    )

    malicious = case["evidence"][0]["text"]
    assert malicious not in fingerprints.source
    assert malicious not in fingerprints.url
    assert malicious not in (fingerprints.content or "")
    assert malicious not in " ".join(confidence.ownership_reasons)
    assert malicious not in " ".join(confidence.contribution_reasons)
    assert candidate.contribution_type is ContributionType.BLOGPOST
