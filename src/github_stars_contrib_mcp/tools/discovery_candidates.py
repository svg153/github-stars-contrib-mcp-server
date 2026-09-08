"""MCP tools for candidate inspection and explicit human review."""

from __future__ import annotations

from typing import Any

from github_stars_contrib_mcp.application.use_cases.review_candidates import (
    ReviewCandidates,
)
from github_stars_contrib_mcp.domain.discovery import CandidateState, ReviewDecisionType
from github_stars_contrib_mcp.shared import initialize_discovery_runtime, mcp


def list_candidates_impl(states: list[str] | None = None) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        resolved = {CandidateState(value) for value in states} if states else None
        data = ReviewCandidates(runtime.repository).list(states=resolved)
        return {"success": True, "data": data}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_candidate_impl(candidate_id: str) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        data = ReviewCandidates(runtime.repository).get(candidate_id)
        return {"success": True, "data": data}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def review_candidate_impl(
    candidate_id: str,
    decision: str,
    *,
    reason: str | None = None,
    edits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        data = ReviewCandidates(runtime.repository).review(
            candidate_id,
            ReviewDecisionType(decision),
            reason=reason,
            edits=edits,
        )
        return {"success": True, "data": data}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def list_candidates(states: list[str] | None = None) -> dict:
    """List discovered candidates with source, evidence, confidence and dedupe state."""
    return list_candidates_impl(states)


@mcp.tool()
async def get_candidate(candidate_id: str) -> dict:
    """Get one candidate with its source and persisted evidence."""
    return get_candidate_impl(candidate_id)


@mcp.tool()
async def review_candidate(
    candidate_id: str,
    decision: str,
    reason: str | None = None,
    edits: dict | None = None,
) -> dict:
    """Approve, reject or defer a candidate; optional edits are audited."""
    return review_candidate_impl(
        candidate_id,
        decision,
        reason=reason,
        edits=edits,
    )
