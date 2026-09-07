# Phase 09 Verification — Restricted social sources

**Phase:** 09
**Issue:** #35
**PR:** #36
**Implementation CI:** GitHub Actions `tests` run #71 succeeded on `ea80b706ff43529cdd4a2e9c42b8dfa82cd1422c`.

## Requirements

### SOCIAL-01 — X/LinkedIn are optional restricted providers, not scraper targets

Verified by capability modelling and adapter composition. Supported modes are explicit URL ingestion, local export/import and a compliant official API/OAuth extension boundary. There is no scrape/browser/session-cookie mode and unsupported access never falls back to one.

### SOCIAL-02 — Explicit URLs, exports or supported APIs feed the common source-item contract

Verified by unit and contract coverage. Exact X/LinkedIn post URLs and neutral local JSON/CSV exports emit `SourceItem` plus `Evidence` through the existing `SourceAdapter` contract. Official API integrations use the same provider-neutral port and remain deployment-specific until a stable provider contract is intentionally implemented.

### SOCIAL-03 — Unsupported access returns actionable capability status rather than bypass behavior

Verified by profile/unsupported-mode/missing-export tests. Unsupported states return explicit unavailable capability reasons and required user inputs. No hidden browser automation, cookie reuse or scraping bypass is attempted.

## Regression and safety evidence

- Pre-commit passed on run #71.
- Full offline suite `pytest -q tests/unit tests/contract` passed on run #71.
- Replay contract preserves a single candidate when the same explicit URL is discovered again.
- Missing contribution type/date remains review-required.
- Export provider mismatches and remote export paths fail explicitly.
- Remote social HTML, when publicly fetchable, is sanitized and labeled `UNTRUSTED_SOURCE_CONTENT`.
- Stars publication authority is not exposed to either social adapter.

## Exit decision

Phase 09 satisfies SOCIAL-01, SOCIAL-02 and SOCIAL-03. The closeout commit contains planning/documentation state only and must pass the same PR CI before merge.
