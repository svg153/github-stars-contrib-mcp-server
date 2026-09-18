# #82 — Bounded audit requests and read-only historical scans — Plan

## Goal

Add the first execution slice of epic #64: a deterministic historical audit request model plus an isolated scanner that reuses existing source adapters without mutating normal discovery state.

## Locked decisions

- Historical audit is read-only.
- The scanner must not read or write the repository's incremental cursors.
- The scanner must not persist candidates, reviews, runs or publications.
- Adapters are reused directly with an ephemeral cursor starting at `None`.
- Audit windows are explicit UTC-normalized start/end bounds.
- Source/type filters are deterministic.
- Items without a source publication date do not silently enter a time-bounded result; they are counted as undated.
- Hard per-source batch/item limits must surface truncation.
- LIMITED/UNAVAILABLE provider capability is preserved in the report rather than treated as successful complete coverage.
- Stars comparison, coverage aggregation, finding taxonomy and review handoff remain later child issues #83-#85.

## Files

- `src/github_stars_contrib_mcp/domain/audit.py`
- `src/github_stars_contrib_mcp/application/audit/__init__.py`
- `src/github_stars_contrib_mcp/application/audit/historical_scan.py`
- `tests/unit/domain/test_audit.py`
- `tests/unit/application/test_historical_audit_scan.py`

## Verification

- request rejects empty/reversed windows;
- filter normalization is deterministic;
- source/date/type filters are enforced;
- LIMITED/UNAVAILABLE sources remain explicit;
- item limits produce TRUNCATED status;
- repository cursor methods are never called;
- full repository CI remains green.

Closes #82 when verified.
