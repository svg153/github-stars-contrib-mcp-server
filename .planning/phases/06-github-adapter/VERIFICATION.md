# Phase 06 Verification — GitHub discovery adapter

**Issue:** #22
**PR:** #30
**Verified head:** `afff707e3d40f2aceb94bfa2ccb37de95d46c47a`
**GitHub Actions:** `tests` run #51 — success

## Requirement evidence

### GH-01 — Supported APIs and trusted identity
**Result:** verified.

- `GitHubSourceAdapter` uses supported GitHub REST endpoints and sends `X-GitHub-Api-Version: 2026-03-10` plus `application/vnd.github+json`.
- Discovery starts from a trusted GitHub username carried by the source registry; malformed/non-profile GitHub source URLs are unavailable.
- `GITHUB_DISCOVERY_TOKEN` is optional and dedicated. `STARS_API_TOKEN` is never implicitly reused.
- Offline request fixtures assert API headers, pagination and token behavior.

### GH-02 — Low-noise eligibility
**Result:** verified.

- Eligibility is default-deny and emits explicit reason codes.
- Routine commit/push/star/watch/fork-event/branch/tag activity is rejected.
- Forked, archived or foreign repositories are rejected.
- Repository candidates require explicit source metadata opt-in.
- Notable PR/issue activity requires explicit configuration and matching trusted authorship.

### GH-03 — Canonical evidence and explainability
**Result:** verified.

- Accepted items emit canonical HTTPS `github.com` URLs and stable GitHub REST/node-backed external IDs.
- Evidence persists eligibility `reason_code`, repository identity and GitHub IDs.
- The SQLite contract asserts the persisted candidate provenance adapter is `github` and evidence contains `owned_release`.

### GH-04 — Pagination/rate limits without duplicates
**Result:** verified.

- Repository lists follow GitHub `Link` pagination.
- Release requests persist per-repository ETags and send `If-None-Match` on replay.
- 429 and exhausted 403 responses classify as `RATE_LIMIT`; rejected credentials classify as `AUTH` and make capability unavailable.
- Cursor state includes deterministic recent IDs and sorted release ETags.
- The contract's second run receives 304 and persists zero additional candidates.

## CI evidence

- Pre-commit: passed.
- Ruff check: passed.
- Ruff format: passed.
- `pytest -q tests/unit tests/contract`: 273 passed.
- Coverage: 84.04%.

## Exit gate

Phase 06 exits successfully: supported GitHub APIs produce explainable, low-noise candidates with stable evidence and tested pagination/rate-limit/idempotency behavior. No raw GitHub event scraping or automatic significance inference was introduced.
