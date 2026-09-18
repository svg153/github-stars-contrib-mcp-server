"""Privacy-safe historical audit coverage accounting tests."""

from datetime import UTC, datetime

from github_stars_contrib_mcp.application.audit.coverage import AuditCoverageAnalyzer
from github_stars_contrib_mcp.domain.audit import (
    AuditObservation,
    AuditRequest,
    AuditScanReport,
    AuditSourceScan,
    AuditSourceStatus,
)
from github_stars_contrib_mcp.domain.audit_coverage import (
    AuditBlindSpotCode,
    AuditCoverageState,
    AuditSourceCoverageState,
)
from github_stars_contrib_mcp.domain.discovery import (
    Evidence,
    SourceItem,
    SourceType,
)
from github_stars_contrib_mcp.models import ContributionType


def _request(**overrides) -> AuditRequest:
    values = {
        "start": datetime(2026, 1, 1, tzinfo=UTC),
        "end": datetime(2026, 2, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return AuditRequest(**values)


def _scan(
    source_id: str,
    source_type: SourceType,
    status: AuditSourceStatus,
    *,
    undated_items: int = 0,
    truncated: bool = False,
) -> AuditSourceScan:
    return AuditSourceScan(
        source_id=source_id,
        source_type=source_type,
        adapter=f"{source_type.value}-adapter",
        capability=status.value,
        status=status,
        batches_scanned=1,
        items_seen=max(1, undated_items),
        items_in_window=0,
        undated_items=undated_items,
        truncated=truncated,
    )


def test_coverage_is_conservative_across_blind_spots() -> None:
    report = AuditScanReport(
        request=_request(
            source_types=(
                SourceType.GITHUB,
                SourceType.YOUTUBE,
                SourceType.RSS,
                SourceType.WEBSITE,
                SourceType.PRETALX,
                SourceType.LINKEDIN,
            )
        ),
        sources=(
            _scan("github:one", SourceType.GITHUB, AuditSourceStatus.SEARCHED),
            _scan("youtube:one", SourceType.YOUTUBE, AuditSourceStatus.LIMITED),
            _scan("rss:one", SourceType.RSS, AuditSourceStatus.UNAVAILABLE),
            _scan("website:one", SourceType.WEBSITE, AuditSourceStatus.FAILED),
            _scan(
                "pretalx:one",
                SourceType.PRETALX,
                AuditSourceStatus.TRUNCATED,
                truncated=True,
            ),
        ),
    )

    coverage = AuditCoverageAnalyzer().analyze(report)

    assert coverage.summary.status is AuditCoverageState.PARTIAL
    assert coverage.summary.configured_sources_total == 5
    assert coverage.summary.complete_sources == 1
    assert coverage.summary.partial_sources == 2
    assert coverage.summary.unavailable_sources == 1
    assert coverage.summary.failed_sources == 1
    assert coverage.summary.configured_source_coverage_ratio == 0.2
    assert coverage.summary.requested_source_types_total == 6
    assert coverage.summary.configured_requested_source_types == 5
    assert coverage.summary.requested_type_configuration_ratio == 5 / 6
    assert coverage.summary.unconfigured_requested_source_types == 1
    assert (
        coverage.summary.blind_spots_by_code[
            AuditBlindSpotCode.UNCONFIGURED_SOURCE_TYPE.value
        ]
        == 1
    )


def test_undated_items_reduce_temporal_coverage() -> None:
    report = AuditScanReport(
        request=_request(),
        sources=(
            _scan(
                "website:one",
                SourceType.WEBSITE,
                AuditSourceStatus.SEARCHED,
                undated_items=2,
            ),
        ),
    )

    coverage = AuditCoverageAnalyzer().analyze(report)

    assert coverage.sources[0].coverage_state is AuditSourceCoverageState.PARTIAL
    assert coverage.summary.complete_sources == 0
    assert coverage.summary.configured_source_coverage_ratio == 0.0
    assert coverage.summary.status is AuditCoverageState.INCOMPLETE
    assert coverage.blind_spots[0].code is AuditBlindSpotCode.UNDATED_ITEMS
    assert coverage.blind_spots[0].affected_items == 2


def test_explicit_but_unscanned_source_is_reported_without_raw_id() -> None:
    secret_source_id = "website:https://private.example/me?token=SECRET-TOKEN"
    report = AuditScanReport(
        request=_request(source_ids=(secret_source_id,)),
    )

    coverage = AuditCoverageAnalyzer().analyze(report)
    serialized = coverage.model_dump_json()

    assert coverage.summary.status is AuditCoverageState.INCOMPLETE
    assert coverage.summary.requested_sources_not_scanned == 1
    assert coverage.blind_spots[0].code is (
        AuditBlindSpotCode.REQUESTED_SOURCE_NOT_SCANNED
    )
    assert coverage.blind_spots[0].source_key.startswith("src_")
    assert secret_source_id not in serialized
    assert "private.example" not in serialized
    assert "SECRET-TOKEN" not in serialized


def test_coverage_output_does_not_copy_observation_or_error_content() -> None:
    source_id = "website:https://secret.example/private"
    item = SourceItem(
        source_id=source_id,
        external_id="TOP-SECRET-ID",
        title="TOP-SECRET-TITLE",
        url="https://secret.example/contribution",
        description="TOP-SECRET-DESCRIPTION",
        published_at=datetime(2026, 1, 10, tzinfo=UTC),
        type_hint=ContributionType.BLOGPOST,
    )
    evidence = Evidence(
        id="evidence-secret",
        source_id=source_id,
        source_item_id=item.external_id,
        url=item.url,
        text_excerpt="TOP-SECRET-EVIDENCE",
    )
    report = AuditScanReport(
        request=_request(),
        sources=(
            AuditSourceScan(
                source_id=source_id,
                source_type=SourceType.WEBSITE,
                adapter="website",
                capability="unavailable",
                status=AuditSourceStatus.UNAVAILABLE,
                reason="TOP-SECRET-PROVIDER-ERROR",
            ),
        ),
        observations=(
            AuditObservation(
                source_id=source_id,
                adapter="website",
                batch_index=1,
                item=item,
                evidence=(evidence,),
            ),
        ),
    )

    coverage = AuditCoverageAnalyzer().analyze(report)
    serialized = coverage.model_dump_json()

    for secret in (
        "secret.example",
        "TOP-SECRET-ID",
        "TOP-SECRET-TITLE",
        "TOP-SECRET-DESCRIPTION",
        "TOP-SECRET-EVIDENCE",
        "TOP-SECRET-PROVIDER-ERROR",
    ):
        assert secret not in serialized
