# #82 — Bounded audit requests and read-only historical scans — Summary

**Parent epic:** #64  
**PR:** #86  
**Verified implementation head:** `ffde779db047efe9602fa0d99da517f9ef1330af`  
**GitHub Actions:** tests run #129 — success

## Delivered

- `AuditRequest` with UTC-normalized date bounds, deterministic source/type filters and hard per-source scan limits.
- Read-only `HistoricalAuditScanner` that reuses existing provider adapters directly.
- Audit scans start from ephemeral adapter cursors and never read or write persisted incremental cursors.
- Source results distinguish searched, limited, unavailable, failed and truncated execution.
- Undated items remain explicit and are excluded from a bounded historical window rather than silently included.
- Synthetic tests cover date/source/type filtering, provider capability, hard truncation and cursor isolation.

## Boundary preserved

This slice does not compare observations against Stars, persist audit findings/candidates, create review decisions or publish anything. Those concerns remain split into #83, #84 and #85.

## Validation

- Initial run #127 stopped at Ruff/pre-commit only.
- The exact Ruff annotation and formatting changes were applied without behavior changes.
- Run #129 passed pre-commit, the full offline test suite and repository quality checks.

## Next

#83 derives privacy-safe coverage and blind-spot accounting from this read-only scan report.
