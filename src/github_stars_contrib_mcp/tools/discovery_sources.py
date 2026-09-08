"""MCP tools for trusted discovery source management and execution."""

from __future__ import annotations

from typing import Any

from github_stars_contrib_mcp.application.use_cases.bootstrap_sources import (
    BootstrapSources,
)
from github_stars_contrib_mcp.application.use_cases.manage_sources import ManageSources
from github_stars_contrib_mcp.domain.discovery import SourceType
from github_stars_contrib_mcp.shared import initialize_discovery_runtime, mcp


async def bootstrap_sources_impl() -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        result = await BootstrapSources(runtime.stars_api, runtime.repository)()
        return {"success": True, "data": result.model_dump(mode="json")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def list_sources_impl(enabled_only: bool = False) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        sources = ManageSources(runtime.repository).list(enabled_only=enabled_only)
        return {
            "success": True,
            "data": [source.model_dump(mode="json") for source in sources],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def add_source_impl(
    url: str,
    *,
    metadata: dict[str, Any] | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        resolved_type = SourceType(source_type) if source_type else None
        source = ManageSources(runtime.repository).add(
            url,
            metadata=metadata,
            source_type=resolved_type,
        )
        return {"success": True, "data": source.model_dump(mode="json")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def sync_source_impl(source_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        if runtime.repository.get_source(source_id) is None:
            raise KeyError(f"Unknown source: {source_id}")
        run = await runtime.orchestrator.run(
            source_ids={source_id},
            dry_run=dry_run,
        )
        return {"success": True, "data": run.model_dump(mode="json")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def discover_contributions_impl(
    source_ids: list[str] | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    try:
        runtime = initialize_discovery_runtime()
        run = await runtime.orchestrator.run(
            source_ids=set(source_ids) if source_ids is not None else None,
            dry_run=dry_run,
        )
        return {"success": True, "data": run.model_dump(mode="json")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def bootstrap_sources() -> dict:
    """Bootstrap trusted source records from the authenticated Stars profile."""
    return await bootstrap_sources_impl()


@mcp.tool()
async def list_sources(enabled_only: bool = False) -> dict:
    """List configured discovery sources and their ownership/capability metadata."""
    return list_sources_impl(enabled_only)


@mcp.tool()
async def add_source(
    url: str,
    metadata: dict | None = None,
    source_type: str | None = None,
) -> dict:
    """Explicitly add a trusted source; `event_page` is the only type override."""
    return add_source_impl(url, metadata=metadata, source_type=source_type)


@mcp.tool()
async def sync_source(source_id: str, dry_run: bool = False) -> dict:
    """Run discovery for exactly one configured source."""
    return await sync_source_impl(source_id, dry_run=dry_run)


@mcp.tool()
async def discover_contributions(
    source_ids: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Run provider-neutral discovery for enabled sources."""
    return await discover_contributions_impl(source_ids, dry_run=dry_run)
