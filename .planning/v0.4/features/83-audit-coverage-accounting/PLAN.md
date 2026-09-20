# #83 — Source coverage accounting and historical blind spots — Plan

## Goal

Derive an honest, privacy-safe coverage report from the read-only `AuditScanReport` delivered by #82. The analyzer must never rescan sources, compare against Stars or mutate discovery state.

## Locked decisions

- `SEARCHED` counts as complete only when the scan is not truncated and has no undated items.
- `LIMITED` and `TRUNCATED` are partial coverage, never complete.
- `UNAVAILABLE` and `FAILED` are explicit blind spots.
- Undated items reduce temporal coverage because they cannot be placed safely inside/outside the requested window.
- Requested source types with no scanned source are reported as unconfigured.
- Explicit requested source IDs that do not appear in the scan are reported as not scanned; the report exposes only a one-way source key, never the raw source ID.
- The configured-source coverage ratio is conservative: complete configured sources / all configured scanned sources.
- Requested-type configuration coverage is separate from configured-source scan coverage.
- Empty data returns `insufficient_data` rather than a perfect ratio.
- Coverage output must not copy source URLs/IDs, contribution titles/descriptions/URLs, evidence bodies or provider error text.

## Files

- `src/github_stars_contrib_mcp/domain/audit_coverage.py`
- `src/github_stars_contrib_mcp/application/audit/coverage.py`
- `tests/unit/domain/test_audit_coverage.py`
- `tests/unit/application/test_audit_coverage.py`

## Verification

- synthetic report proves complete/limited/unavailable/failed/truncated/undated states;
- requested-but-unconfigured source types remain explicit;
- explicitly requested but unscanned sources remain explicit via non-reversible source keys;
- aggregate ratios cannot overstate incomplete history;
- empty input is `insufficient_data`;
- secret-looking source/content/evidence strings do not appear in serialized coverage output;
- no repository or adapter dependency exists in the coverage analyzer.

Closes #83 when verified.
