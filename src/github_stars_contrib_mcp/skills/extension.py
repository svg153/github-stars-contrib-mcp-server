"""Official MCP Skills extension adapter for the canonical Stars skill catalog.

The wire contract follows ``io.modelcontextprotocol/skills`` while the actual skill
bytes, validation, and manifests remain owned by :mod:`.catalog`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import mcp.types as types
from mcp import MCPError
from mcp.server.context import ServerRequestContext
from mcp.server.extension import Extension, MethodBinding, ResourceBinding
from mcp.server.mcpserver.resources import FunctionResource
from pydantic import BaseModel, Field

from .catalog import SkillCatalog, SkillCatalogError
from .models import SkillEntry, SkillResource

SKILLS_EXTENSION_ID = "io.modelcontextprotocol/skills"
SKILLS_PROTOCOL_VERSIONS = frozenset({"2026-07-28"})
DEFAULT_SKILLS_TTL_MS = 300_000
DEFAULT_SKILLS_PAGE_SIZE = 50


class SkillResourceManifest(BaseModel):
    """One resource descriptor in an MCP Skills static manifest."""

    uri: str
    digest: str
    size: int = Field(ge=0)


class SkillWireEntry(BaseModel):
    """Complete skill metadata returned by ``skills/list`` and ``skills/get``."""

    uri: str
    frontmatter: dict[str, Any]
    resources: list[SkillResourceManifest]


class SkillsListParams(types.PaginatedRequestParams):
    """Parameters for ``skills/list``."""


class SkillsGetParams(types.RequestParams):
    """Parameters for ``skills/get``."""

    uri: str


class SkillsListResult(types.Result):
    """Complete cacheable page returned by ``skills/list``."""

    result_type: Literal["complete"] = "complete"
    skills: list[SkillWireEntry]
    next_cursor: str | None = None
    ttl_ms: int = Field(default=DEFAULT_SKILLS_TTL_MS, ge=0)
    cache_scope: Literal["public", "private"] = "public"


class SkillsGetResult(types.Result):
    """Complete cacheable result returned by ``skills/get``."""

    result_type: Literal["complete"] = "complete"
    skill: SkillWireEntry
    ttl_ms: int = Field(default=DEFAULT_SKILLS_TTL_MS, ge=0)
    cache_scope: Literal["public", "private"] = "public"


class SkillsExtension(Extension):
    """Serve canonical Agent Skills using the official MCP Skills extension."""

    identifier = SKILLS_EXTENSION_ID

    def __init__(
        self,
        catalog: SkillCatalog | None = None,
        *,
        page_size: int = DEFAULT_SKILLS_PAGE_SIZE,
        ttl_ms: int = DEFAULT_SKILLS_TTL_MS,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        if ttl_ms < 0:
            raise ValueError("ttl_ms must be >= 0")
        self.catalog = catalog or SkillCatalog()
        self.page_size = page_size
        self.ttl_ms = ttl_ms

    def settings(self) -> dict[str, Any]:
        """Advertise Skills support without optional directory reading."""
        return {}

    def methods(self) -> Sequence[MethodBinding]:
        """Register the two request methods required by the Skills extension."""
        return (
            MethodBinding(
                "skills/list",
                SkillsListParams,
                self._list_skills,
                protocol_versions=SKILLS_PROTOCOL_VERSIONS,
            ),
            MethodBinding(
                "skills/get",
                SkillsGetParams,
                self._get_skill,
                protocol_versions=SKILLS_PROTOCOL_VERSIONS,
            ),
        )

    def resources(self) -> Sequence[ResourceBinding]:
        """Contribute every manifest file as a lazy standard MCP resource."""
        bindings: list[ResourceBinding] = []
        for skill in self.catalog.list():
            for resource in skill.resources:
                bindings.append(
                    ResourceBinding(
                        resource=FunctionResource.from_function(
                            self._resource_reader(resource),
                            uri=resource.uri,
                            name=resource.relative_path,
                            description=f"Agent Skill resource for {skill.name}",
                            mime_type=resource.mime_type,
                        )
                    )
                )
        return tuple(bindings)

    async def _list_skills(
        self,
        _ctx: ServerRequestContext[Any, Any],
        params: SkillsListParams,
    ) -> SkillsListResult:
        entries = self.catalog.list()
        start = self._decode_cursor(params.cursor, len(entries))
        end = min(start + self.page_size, len(entries))
        next_cursor = str(end) if end < len(entries) else None
        return SkillsListResult(
            skills=[self._wire_entry(entry) for entry in entries[start:end]],
            next_cursor=next_cursor,
            ttl_ms=self.ttl_ms,
            cache_scope="public",
        )

    async def _get_skill(
        self,
        _ctx: ServerRequestContext[Any, Any],
        params: SkillsGetParams,
    ) -> SkillsGetResult:
        try:
            entry = self.catalog.get(params.uri)
        except SkillCatalogError as exc:
            raise MCPError(
                code=types.INVALID_PARAMS,
                message=f"Unknown skill URI: {params.uri}",
            ) from exc
        return SkillsGetResult(
            skill=self._wire_entry(entry),
            ttl_ms=self.ttl_ms,
            cache_scope="public",
        )

    def _wire_entry(self, entry: SkillEntry) -> SkillWireEntry:
        return SkillWireEntry(
            uri=entry.uri,
            frontmatter=dict(entry.frontmatter),
            resources=[
                SkillResourceManifest(
                    uri=resource.uri,
                    digest=resource.digest,
                    size=resource.size,
                )
                for resource in entry.resources
            ],
        )

    def _resource_reader(self, resource: SkillResource):
        def read() -> str | bytes:
            data = self.catalog.read(resource.uri)
            if _is_text_resource(resource.mime_type):
                try:
                    return data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise RuntimeError(
                        f"text skill resource is not valid UTF-8: {resource.uri}"
                    ) from exc
            return data

        return read

    @staticmethod
    def _decode_cursor(cursor: str | None, total: int) -> int:
        if cursor is None:
            return 0
        if not cursor.isascii() or not cursor.isdigit():
            raise MCPError(
                code=types.INVALID_PARAMS,
                message=f"Unknown skills cursor: {cursor!r}",
            )
        start = int(cursor)
        if start < 0 or start >= total:
            raise MCPError(
                code=types.INVALID_PARAMS,
                message=f"Unknown skills cursor: {cursor!r}",
            )
        return start


def _is_text_resource(mime_type: str) -> bool:
    essence = mime_type.split(";", 1)[0].strip().lower()
    return (
        essence.startswith("text/")
        or essence in {"application/json", "application/xml"}
        or essence.endswith(("+json", "+xml"))
    )
