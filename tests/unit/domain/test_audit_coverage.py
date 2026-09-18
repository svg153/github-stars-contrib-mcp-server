"""Audit coverage model tests."""

from github_stars_contrib_mcp.domain.audit_coverage import (
    AuditCoverageState,
    AuditCoverageSummary,
)


def test_empty_coverage_summary_can_represent_insufficient_data() -> None:
    summary = AuditCoverageSummary(
        status=AuditCoverageState.INSUFFICIENT_DATA,
        configured_sources_total=0,
        complete_sources=0,
        partial_sources=0,
        unavailable_sources=0,
        failed_sources=0,
        requested_source_types_total=0,
        configured_requested_source_types=0,
        unconfigured_requested_source_types=0,
        requested_sources_not_scanned=0,
        blind_spots_total=0,
    )

    assert summary.configured_source_coverage_ratio is None
    assert summary.requested_type_configuration_ratio is None
    assert "fully covered configured sources" in summary.definition
