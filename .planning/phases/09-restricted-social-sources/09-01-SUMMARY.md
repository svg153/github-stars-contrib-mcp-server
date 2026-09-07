# Phase 09 Summary — Restricted social sources

## Outcome

Phase 09 adds compliant X/LinkedIn ingestion without introducing a scraper or authenticated-browser dependency. Restricted social findings now enter the same provider-neutral discovery pipeline through explicit user-registered post URLs or local neutral exports, while unsupported access remains explicit and actionable.

## Delivered

- Added deterministic restricted-social capability modelling with no scrape/browser mode.
- Added explicit X/LinkedIn post URL ingestion. Public metadata is optional, bounded by the existing safe-fetch boundary and retained only as untrusted evidence.
- Added local-only neutral JSON/CSV schema v1 import with provider validation, a 10 MB limit and content-hash replay cursors.
- Added an official API/OAuth extension contract through the existing `SourceAdapter` boundary without bundling brittle provider-specific API assumptions.
- Added non-secret credential policy metadata; raw token values and authenticated browser cookies are excluded from source records, evidence, cursors and ordinary logs.
- Registered mutually exclusive social URL/export adapters in the discovery runtime.
- Kept missing contribution type/date review-required instead of inferring values.
- Documented supported modes, neutral export schema and custom official-API adapter requirements.

## Safety decisions

- X/LinkedIn scraping, browser login automation and session-cookie reuse are not fallback paths.
- A profile URL is not contribution evidence. Exact post URLs, user exports or an explicitly supplied compliant API adapter are required.
- Remote social HTML remains `UNTRUSTED_SOURCE_CONTENT` and cannot gain policy or publication authority.
- Local export files are read locally by the adapter and are not transmitted by the discovery pipeline.
- Publication remains outside discovery adapters and still requires later review/policy gates.

## Verification

- PR: #36
- Implementation head validated by GitHub Actions: `ea80b706ff43529cdd4a2e9c42b8dfa82cd1422c`
- CI run: #71 (`tests`) — success
- Pre-commit passed.
- `pytest -q tests/unit tests/contract` passed.
- Phase verification details: `VERIFICATION.md`.

## Next

Phase 10 / issue #37 implements deterministic fingerprints, duplicate matching against Stars plus the local queue, explainable confidence, and reviewable conflict handling.
