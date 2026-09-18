"""Pure coverage accounting for read-only historical audit scans."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

from github_stars_contrib_mcp.domain.audit import (
    AuditScanReport,
    AuditSourceScan,
    AuditSourceStatus,
)
from github_stars_contrib_mcp.domain.audit_coverage import (
    AuditBlindSpot,
    AuditBlindSpotCode,
    AuditCoverageReport,
    AuditCoverageState,
    AuditCoverageSummary,
    AuditSourceCoverage,
    AuditSourceCoverageState,
    AuditSourceTypeCoverage,
)


def _source_key(source_id: str) -> str:
    digest = hashlib.sha256(source_id.encode()).hexdigest()[:16]
    return f"src_{digest}"


def _source_coverage(
    scan: AuditSourceScan,
) -> tuple[AuditSourceCoverageState, tuple[AuditBlindSpotCode, ...]]:
    blind_spots: list[AuditBlindSpotCode] = []

    if scan.status is AuditSourceStatus.UNAVAILABLE:
        return (
            AuditSourceCoverageState.UNAVAILABLE,
            (AuditBlindSpotCode.SOURCE_UNAVAILABLE,),
        )
    if scan.status is AuditSourceStatus.FAILED:
        return (
            AuditSourceCoverageState.FAILED,
            (AuditBlindSpotCode.SOURCE_FAILED,),
        )
    if scan.status is AuditSourceStatus.TRUNCATED or scan.truncated:
        blind_spots.append(AuditBlindSpotCode.SCAN_TRUNCATED)
    if scan.status is AuditSourceStatus.LIMITED:
        blind_spots.append(AuditBlindSpotCode.PROVIDER_LIMITED)
    if scan.undated_items:
        blind_spots.append(AuditBlindSpotCode.UNDATED_ITEMS)

    if blind_spots:
        return AuditSourceCoverageState.PARTIAL, tuple(sorted(set(blind_spots)))
    return AuditSourceCoverageState.COMPLETE, ()


def _aggregate_status(
    *,
    configured_total: int,
    complete: int,
    blind_spots_total: int,
    explicit_scope: bool,
) -> AuditCoverageState:
    if configured_total == 0:
        return (
            AuditCoverageState.INCOMPLETE
            if explicit_scope
            else AuditCoverageState.INSUFFICIENT_DATA
        )
    if complete == configured_total and blind_spots_total == 0:
        return AuditCoverageState.COMPLETE
    if complete > 0:
        return AuditCoverageState.PARTIAL
    return AuditCoverageState.INCOMPLETE


class AuditCoverageAnalyzer:
    """Derive conservative coverage without repositories, adapters or Stars access."""

    def analyze(self, report: AuditScanReport) -> AuditCoverageReport:
        source_coverages: list[AuditSourceCoverage] = []
        blind_spots: list[AuditBlindSpot] = []

        for scan in report.sources:
            coverage_state, codes = _source_coverage(scan)
            key = _source_key(scan.source_id)
            source_coverages.append(
                AuditSourceCoverage(
                    source_key=key,
                    source_type=scan.source_type,
                    adapter=scan.adapter,
                    scan_status=scan.status,
                    coverage_state=coverage_state,
                    batches_scanned=scan.batches_scanned,
                    items_seen=scan.items_seen,
                    items_in_window=scan.items_in_window,
                    undated_items=scan.undated_items,
                    blind_spots=codes,
                )
            )
            for code in codes:
                blind_spots.append(
                    AuditBlindSpot(
                        code=code,
                        source_key=key,
                        source_type=scan.source_type,
                        affected_items=(
                            scan.undated_items
                            if code is AuditBlindSpotCode.UNDATED_ITEMS
                            else None
                        ),
                    )
                )

        scanned_ids = {scan.source_id for scan in report.sources}
        missing_requested_ids = sorted(
            set(report.request.source_ids).difference(scanned_ids)
        )
        for source_id in missing_requested_ids:
            blind_spots.append(
                AuditBlindSpot(
                    code=AuditBlindSpotCode.REQUESTED_SOURCE_NOT_SCANNED,
                    source_key=_source_key(source_id),
                )
            )

        scanned_types = {scan.source_type for scan in report.sources}
        requested_types = set(report.request.source_types)
        unconfigured_types = sorted(
            requested_types.difference(scanned_types),
            key=lambda value: value.value,
        )
        for source_type in unconfigured_types:
            blind_spots.append(
                AuditBlindSpot(
                    code=AuditBlindSpotCode.UNCONFIGURED_SOURCE_TYPE,
                    source_type=source_type,
                )
            )

        counts = Counter(source.coverage_state for source in source_coverages)
        configured_total = len(source_coverages)
        complete = counts[AuditSourceCoverageState.COMPLETE]
        configured_ratio = complete / configured_total if configured_total else None

        configured_requested_types = len(requested_types.intersection(scanned_types))
        requested_type_ratio = (
            configured_requested_types / len(requested_types)
            if requested_types
            else None
        )

        blind_spot_counts = Counter(spot.code.value for spot in blind_spots)
        by_type_raw: dict[str, Counter[AuditSourceCoverageState]] = defaultdict(Counter)
        for source in source_coverages:
            by_type_raw[source.source_type.value][source.coverage_state] += 1

        by_source_type: dict[str, AuditSourceTypeCoverage] = {}
        for source_type, type_counts in sorted(by_type_raw.items()):
            by_source_type[source_type] = AuditSourceTypeCoverage(
                total=sum(type_counts.values()),
                complete=type_counts[AuditSourceCoverageState.COMPLETE],
                partial=type_counts[AuditSourceCoverageState.PARTIAL],
                unavailable=type_counts[AuditSourceCoverageState.UNAVAILABLE],
                failed=type_counts[AuditSourceCoverageState.FAILED],
            )

        explicit_scope = bool(report.request.source_ids or report.request.source_types)
        summary = AuditCoverageSummary(
            status=_aggregate_status(
                configured_total=configured_total,
                complete=complete,
                blind_spots_total=len(blind_spots),
                explicit_scope=explicit_scope,
            ),
            configured_sources_total=configured_total,
            complete_sources=complete,
            partial_sources=counts[AuditSourceCoverageState.PARTIAL],
            unavailable_sources=counts[AuditSourceCoverageState.UNAVAILABLE],
            failed_sources=counts[AuditSourceCoverageState.FAILED],
            configured_source_coverage_ratio=configured_ratio,
            requested_source_types_total=len(requested_types),
            configured_requested_source_types=configured_requested_types,
            requested_type_configuration_ratio=requested_type_ratio,
            unconfigured_requested_source_types=len(unconfigured_types),
            requested_sources_not_scanned=len(missing_requested_ids),
            blind_spots_total=len(blind_spots),
            blind_spots_by_code=dict(sorted(blind_spot_counts.items())),
            by_source_type=by_source_type,
        )
        return AuditCoverageReport(
            window_start=report.request.start,
            window_end=report.request.end,
            source_filter_applied=bool(report.request.source_ids),
            source_filter_count=len(report.request.source_ids),
            requested_source_types=report.request.source_types,
            requested_contribution_types=report.request.contribution_types,
            sources=tuple(source_coverages),
            blind_spots=tuple(blind_spots),
            summary=summary,
        )
