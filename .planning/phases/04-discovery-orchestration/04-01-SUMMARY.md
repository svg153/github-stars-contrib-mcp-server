# Phase 04 Summary — Discovery orchestration

**Issue:** #20
**PR:** #28
**Status:** implemented and verified

## Delivered
- Added a provider-neutral `SourceAdapter` protocol with explicit capability states, atomic batches and classified provider errors.
- Added deterministic `SourceItem` normalization into `CandidateContribution` while preserving evidence/provenance and refusing to invent missing type or publication date data.
- Added `DiscoveryOrchestrator` for enabled-source execution, exact adapter resolution, capability checks, per-source failure isolation and deterministic run summaries.
- Persisted candidate + evidence + cursor checkpoints in one SQLite transaction per adapter batch.
- Added diagnostics-only `dry_run` behavior that persists run evidence but does not mutate candidate or cursor state.
- Added additive discovery composition around SQLite and `SafeHTTPFetcher` without registering MCP tools.
- Added offline fake-adapter tests covering contract shape, normalization, idempotency, rollback, cursor semantics, partial failure and DI composition.

## Verification
- GitHub Actions `tests` run #42 succeeded on `f53f4f93502cf56a710b355408deff8ee5c009a5`.
- Pre-commit passed, including Ruff check and Ruff format.
- `pytest -q tests/unit`: 247 tests passed.
- Total unit-suite coverage: 84.13%.
- Detailed requirement evidence is recorded in `VERIFICATION.md`.

## Decisions
- Adapters emit provider-neutral source data; they never call Stars publication APIs.
- A batch is the atomic persistence/checkpoint boundary.
- `UNAVAILABLE` capability blocks a source explicitly; `LIMITED` remains runnable so providers can expose degraded supported modes.
- Unknown provider exceptions are isolated and recorded instead of aborting unrelated sources.
- Missing semantic data remains review-required rather than guessed.
