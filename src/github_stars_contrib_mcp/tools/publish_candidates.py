"""MCP tool for guarded publication of previously approved candidates."""

from __future__ import annotations

from github_stars_contrib_mcp.application.use_cases.publish_candidates import (
    PublishCandidates,
)
from github_stars_contrib_mcp.shared import initialize_discovery_runtime, mcp


async def publish_approved_candidates_impl(
    candidate_ids: list[str],
    *,
    dry_run: bool = True,
) -> dict:
    try:
        runtime = initialize_discovery_runtime()
        results = await PublishCandidates(
            runtime.repository,
            runtime.stars_api,
        )(candidate_ids, dry_run=dry_run)
        return {
            "success": True,
            "dry_run": dry_run,
            "data": [result.model_dump(mode="json") for result in results],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "dry_run": dry_run}


@mcp.tool()
async def publish_approved_candidates(
    candidate_ids: list[str],
    dry_run: bool = True,
) -> dict:
    """Publish only already-approved candidates after a fresh duplicate/policy check.

    `dry_run` defaults to true. This tool never approves candidates.
    """
    return await publish_approved_candidates_impl(candidate_ids, dry_run=dry_run)
