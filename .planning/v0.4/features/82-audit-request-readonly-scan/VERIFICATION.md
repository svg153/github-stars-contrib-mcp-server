# #82 — Bounded audit requests and read-only historical scans — Verification

**Parent epic:** #64
**PR:** #86
**Verified implementation head:** `ffde779db047efe9602fa0d99da517f9ef1330af`
**GitHub Actions:** tests run #129 — success

## Acceptance evidence

### Deterministic audit window and filters
**Result:** verified.

- `AuditRequest` normalizes naive/aware datetimes to UTC.
- Equal or reversed windows fail validation.
- source IDs, source types and contribution types normalize deterministically.
- date/source/type filters are covered by synthetic tests.

### Historical scan cannot corrupt normal incremental state
**Result:** verified.

- `HistoricalAuditScanner` receives only the `SourceRepository` read surface it needs.
- Every adapter starts with an ephemeral `None` cursor.
- Audit never calls repository `get_cursor` or `save_cursor`.
- The spy repository test raises immediately if either incremental cursor operation is attempted.
- The scanner does not save candidates, discovery runs, review decisions or publications.

### Provider limitations stay visible
**Result:** verified.

- AVAILABLE, LIMITED and UNAVAILABLE capability states are preserved in per-source results.
- Missing adapters become explicit unavailable results.
- Adapter/security/parse failures are classified rather than hidden.

### Hard bounds are represented honestly
**Result:** verified.

- per-source item and batch bounds are request-controlled within safe model limits.
- hitting a bound sets `TRUNCATED`; it is not reported as complete coverage.
- undated observations are counted and excluded from a time-bounded finding set.

## CI evidence

Run #129 passed:
- pre-commit;
- Ruff check/format;
- full offline tests;
- repository quality check.

## Exit gate

#82 satisfies its acceptance criteria. The audit execution boundary is read-only, bounded and reusable by #83 coverage accounting without creating a second discovery-state mutation path.
