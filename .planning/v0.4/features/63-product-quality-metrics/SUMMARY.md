# #63 — Privacy-safe product quality metrics — Summary

## Implemented
- Added a separate product-metrics domain/read-model boundary over the existing SQLite discovery store.
- Added deterministic aggregation for candidate volume, eligibility/noise, exact/likely duplicates, review disposition/edit rates, latest decisive acceptance by adapter/type, review queue age, time-to-first-decision, source failure/rate-limit/capability rates, and run totals.
- Added `get_product_metrics`, a read-only MCP tool with an optional timezone-aware `as_of` input for reproducible reports.
- Added explicit `insufficient_data` handling for zero denominators and empty duration samples.
- Added explicit `unavailable` entries for metrics that require future persisted evidence: #64 audit yield, #66 reconciliation findings, curated FP/FN labels and a safe dry-run→publish correlation.
- Added metric-definition and privacy documentation in `docs/product-metrics.md`.

## Privacy design
The SQLite reporting projection returns only safe categorical dimensions and timestamps. Candidate/source IDs are used only internally where needed for grouping or source-type lookup and are not present in output facts. Titles, descriptions, URLs, evidence, tokens, review reasons and edited values are not exposed.

A regression fixture deliberately persists secret-looking titles, descriptions, URLs, IDs and edited field values and asserts that none appear in the rendered reporting snapshot.

## Product boundary
The feature does not modify review/publish behavior. Product-quality metrics are evidence for operators and future real-world validation, not approval authority and not publication-volume KPIs. Operational Prometheus telemetry remains a separate surface.

## Validation
- Initial CI exposed only Ruff formatting differences; no functional workaround was applied.
- Ruff formatting was applied exactly.
- Final implementation/test head before this documentation closeout: `47c6fe79275a8196cafcc6dad1f7f687d79494f1`.
- GitHub Actions tests run #124: success.

## Follow-up
The next P0 is #64. Its first slices can now reuse this report and later fill the currently unavailable missing-audit-yield metric once audit findings and coverage are persisted.
