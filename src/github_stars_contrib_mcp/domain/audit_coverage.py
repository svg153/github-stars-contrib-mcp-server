"""Privacy-safe historical audit coverage models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from github_stars_contrib_mcp.domain.audit import AuditSourceStatus
from github_stars_contrib_mcp.domain.discovery import SourceType
from github_stars_contrib_mcp.models import ContributionType


class AuditCoverageState(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    INSUFFICIENT_DATA = "insufficient_data"


class AuditSourceCoverageState(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class AuditBlindSpotCode(StrEnum):
    PROVIDER_LIMITED = "provider_limited"
    SOURCE_UNAVAILABLE = "source_unavailable"
    SOURCE_FAILED = "source_failed"
    SCAN_TRUNCATED = "scan_truncated"
    UNDATED_ITEMS = "undated_items"
    UNCONFIGURED_SOURCE_TYPE = "unconfigured_source_type"
    REQUESTED_SOURCE_NOT_SCANNED = "requested_source_not_scanned"


class AuditBlindSpot(BaseModel):
    """One privacy-safe reason the requested historical window is incomplete."""

    model_config = ConfigDict(extra="forbid")

    code: AuditBlindSpotCode
    source_key: str | None = None
    source_type: SourceType | None = None
    affected_items: int | None = Field(default=None, ge=0)


class AuditSourceCoverage(BaseModel):
    """Privacy-safe per-source coverage facts."""

    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1)
    source_type: SourceType
    adapter: str | None = None
    scan_status: AuditSourceStatus
    coverage_state: AuditSourceCoverageState
    batches_scanned: int = Field(ge=0)
    items_seen: int = Field(ge=0)
    items_in_window: int = Field(ge=0)
    undated_items: int = Field(ge=0)
    blind_spots: tuple[AuditBlindSpotCode, ...] = ()


class AuditSourceTypeCoverage(BaseModel):
    """Aggregate configured-source counts for one source type."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    complete: int = Field(ge=0)
    partial: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    failed: int = Field(ge=0)


class AuditCoverageSummary(BaseModel):
    """Conservative aggregate audit coverage."""

    model_config = ConfigDict(extra="forbid")

    status: AuditCoverageState
    configured_sources_total: int = Field(ge=0)
    complete_sources: int = Field(ge=0)
    partial_sources: int = Field(ge=0)
    unavailable_sources: int = Field(ge=0)
    failed_sources: int = Field(ge=0)
    configured_source_coverage_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    requested_source_types_total: int = Field(ge=0)
    configured_requested_source_types: int = Field(ge=0)
    requested_type_configuration_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    unconfigured_requested_source_types: int = Field(ge=0)
    requested_sources_not_scanned: int = Field(ge=0)
    blind_spots_total: int = Field(ge=0)
    blind_spots_by_code: dict[str, int] = Field(default_factory=dict)
    by_source_type: dict[str, AuditSourceTypeCoverage] = Field(default_factory=dict)
    definition: str = (
        "configured_source_coverage_ratio = fully covered configured sources / "
        "all configured sources in the audit scan; limited, truncated, unavailable, "
        "failed or undated sources never count as complete"
    )


class AuditCoverageReport(BaseModel):
    """Privacy-safe coverage view derived from a read-only audit scan."""

    model_config = ConfigDict(extra="forbid")

    window_start: datetime
    window_end: datetime
    source_filter_applied: bool
    source_filter_count: int = Field(ge=0)
    requested_source_types: tuple[SourceType, ...] = ()
    requested_contribution_types: tuple[ContributionType, ...] = ()
    sources: tuple[AuditSourceCoverage, ...] = ()
    blind_spots: tuple[AuditBlindSpot, ...] = ()
    summary: AuditCoverageSummary
