# Phase 01 Summary — Discovery domain and persistence

**Issue:** #17  
**PR:** #25  
**Status:** implemented and verified

## Delivered

- Provider-neutral discovery domain models for sources, source items, evidence, provenance, candidates, reviews and runs.
- Versioned schema contract (`schema_version = 1`).
- Explicit candidate lifecycle with typed invalid-transition errors and idempotent same-state transitions.
- Repository ports for sources/cursors, candidates/evidence/reviews/publications, runs and transaction boundaries.
- Local SQLite persistence using stdlib `sqlite3`, foreign keys and deterministic JSON serialization.
- Schema bootstrap/version guard with explicit rejection of unsupported versions.
- Atomic candidate + evidence writes and a reusable multi-operation transaction boundary for later orchestration.
- Immutable evidence ownership across candidates.
- Platform-aware `DISCOVERY_DB_PATH` configuration without filesystem side effects during module import.

## Important implementation decisions

- Discovery domain/application code has no MCP or HTTP dependency.
- SQLite directory creation occurs only when the persistence adapter is constructed.
- Nested discovery transactions are rejected rather than pretending to support savepoints.
- The adapter is intentionally one local repository implementation behind provider-neutral ports so Phase 04 can group candidate, evidence, cursor and run writes atomically.

## Validation

Local focused harness:
- 28 Phase 01 tests passed.
- `python -m compileall -q` passed.

GitHub Actions on head `2ab4f1455a7fc2fbe0de0aea697e92f4545e12aa`:
- dependency installation: passed
- pre-commit: passed
- unit test workflow: passed

## Handoff

Phase 02 may now rely on `SourceRecord`, source/cursor repository operations and SQLite persistence. It must not introduce source fetching; identity/source registry work remains deterministic and offline.
