"""Read-only historical audit domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from github_stars_contrib_mcp.domain.discovery import Evidence, SourceItem, SourceType
from github_stars_contrib_mcp.models import ContributionType


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AuditSourceStatus(StrEnum):
    SEARCHED = "searched"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    TRUNCATED = "truncated"


class AuditRequest(BaseModel):
    """Bounded, explicitly read-only historical audit request."""

    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime
    source_ids: tuple[str, ...] = ()
    source_types: tuple[SourceType, ...] = ()
    contribution_types: tuple[ContributionType, ...] = ()
    max_batches_per_source: int = Field(default=50, ge=1, le=1000)
    max_items_per_source: int = Field(default=2000, ge=1, le=20_000)
    read_only: Literal[True] = True

    @field_validator("start", "end")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @field_validator("source_ids")
    @classmethod
    def normalize_source_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({value.strip() for value in values if value.strip()}))

    @field_validator("source_types")
    @classmethod
    def normalize_source_types(
        cls,
        values: tuple[SourceType, ...],
    ) -> tuple[SourceType, ...]:
        return tuple(sorted(set(values), key=lambda value: value.value))

    @field_validator("contribution_types")
    @classmethod
    def normalize_contribution_types(
        cls,
        values: tuple[ContributionType, ...],
    ) -> tuple[ContributionType, ...]:
        return tuple(sorted(set(values), key=lambda value: value.value))

    @model_validator(mode="after")
    def validate_window(self) -> AuditRequest:
        if self.start >= self.end:
            raise ValueError("audit start must be before end")
        return self


class AuditObservation(BaseModel):
    """One historical source item retained by audit filters."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    batch_index: int = Field(ge=1)
    item: SourceItem
    evidence: tuple[Evidence, ...] = Field(min_length=1)


class AuditSourceScan(BaseModel):
    """Per-source execution facts for a read-only historical scan."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_type: SourceType
    adapter: str | None = None
    capability: str | None = None
    status: AuditSourceStatus
    reason: str | None = None
    error_kind: str | None = None
    batches_scanned: int = Field(default=0, ge=0)
    items_seen: int = Field(default=0, ge=0)
    items_in_window: int = Field(default=0, ge=0)
    undated_items: int = Field(default=0, ge=0)
    truncated: bool = False


class AuditScanReport(BaseModel):
    """Read-only audit scan result before Stars comparison/classification."""

    model_config = ConfigDict(extra="forbid")

    request: AuditRequest
    sources: tuple[AuditSourceScan, ...] = ()
    observations: tuple[AuditObservation, ...] = ()

    @property
    def total_items_seen(self) -> int:
        return sum(source.items_seen for source in self.sources)

    @property
    def total_items_in_window(self) -> int:
        return sum(source.items_in_window for source in self.sources)
