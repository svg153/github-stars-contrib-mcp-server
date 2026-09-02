# Phase 04 Verification — Discovery orchestration

**Issue:** #20
**PR:** #28
**Verified head:** `f53f4f93502cf56a710b355408deff8ee5c009a5`
**CI:** GitHub Actions `tests` run #42 — success

## Requirement evidence

### DISC-01 — Provider-neutral adapters emit source items without Stars API coupling
- `domain/ports/source_adapter.py` defines `SourceAdapter`, `SourceBatch`, `AdapterEmission`, capability and classified error contracts using only discovery-domain types.
- `tests/unit/domain/test_source_adapter_contract.py` proves a fake provider can satisfy the runtime protocol offline.
- Discovery DI composes adapters without modifying MCP tool registration or Stars publication paths.

### DISC-02 — Discovery runs isolate adapter failures and persist deterministic summaries
- `DiscoveryOrchestrator` executes sources independently and classifies `SourceAdapterError` kinds.
- A failing adapter does not roll back candidates from a successful independent source.
- Tests cover partial status, auth classification, source counts and persisted run diagnostics.

### DISC-03 — Source items normalize into validated candidates plus evidence/provenance
- `normalizer.py` maps structured fields deterministically and records adapter/normalizer provenance.
- Missing contribution type or publication date is not fabricated; the candidate remains review-required with explicit reasons.
- Evidence is persisted alongside each candidate and source IDs are validated before persistence.

### DISC-04 — Incremental cursors resume idempotently
- The orchestrator loads the existing source cursor before invoking an adapter.
- Candidate/evidence writes and cursor advancement share one repository transaction per batch.
- Re-running the same fake batches leaves two stable candidates rather than duplicating them.
- The rollback test deliberately causes the second evidence write in a batch to fail and proves both candidates and the cursor are rolled back.

## CI evidence
- Pre-commit: success.
- Unit tests: 247 passed.
- Coverage: 84.13% total.
- No network credentials are required for the Phase 04 tests.

## Exit assessment
Phase 04 exit criteria are satisfied: a fake adapter runs end-to-end into persisted candidates/evidence, source failures are isolated, cursors checkpoint atomically and re-runs are idempotent.
