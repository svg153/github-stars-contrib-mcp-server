"""Provider-neutral discovery source adapter contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from github_stars_contrib_mcp.domain.discovery import Evidence, SourceItem, SourceRecord


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


class AdapterErrorKind(StrEnum):
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    PARSE = "parse"
    SECURITY = "security"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class SourceCapability(BaseModel):
    """Availability of one adapter for one configured source."""

    model_config = ConfigDict(extra="forbid")

    status: CapabilityStatus
    reason: str | None = None
    requires_credentials: bool = False
    permissions: tuple[str, ...] = ()


class AdapterEmission(BaseModel):
    """One provider-neutral item plus supporting evidence."""

    model_config = ConfigDict(extra="forbid")

    item: SourceItem
    evidence: tuple[Evidence, ...] = Field(min_length=1)


class SourceBatch(BaseModel):
    """One atomic adapter checkpoint worth of source items."""

    model_config = ConfigDict(extra="forbid")

    emissions: tuple[AdapterEmission, ...] = ()
    next_cursor: dict[str, Any] | None = None


class SourceAdapterError(RuntimeError):
    """Classified provider failure isolated by the orchestrator."""

    def __init__(self, kind: AdapterErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@runtime_checkable
class SourceAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def supports(self, source: SourceRecord) -> bool: ...

    def capabilities(self, source: SourceRecord) -> SourceCapability: ...

    def iter_items(
        self,
        source: SourceRecord,
        cursor: dict[str, Any] | None,
    ) -> AsyncIterator[SourceBatch]: ...
