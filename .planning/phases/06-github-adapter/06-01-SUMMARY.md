# Phase 06 Summary — GitHub discovery adapter

**Issue:** #22
**PR:** #30
**Status:** implemented and verified

## Delivered
- Added conservative, explainable GitHub eligibility rules with explicit reason codes and default-deny behavior for unknown/routine activity.
- Added a GitHub REST discovery adapter using API version `2026-03-10`, canonical `github.com` evidence URLs and stable REST/node-backed external IDs.
- Added owned-release discovery plus explicitly opted-in repository and notable PR/issue discovery without raw event scraping.
- Added Link pagination, per-repository release ETags, recent-ID cursor suppression and explicit rate-limit/auth classification.
- Added optional `GITHUB_DISCOVERY_TOKEN`; Stars credentials are never reused implicitly for GitHub discovery.
- Added truthful capability states: token-backed discovery is available, anonymous public discovery is limited, rejected credentials become unavailable.
- Registered GitHub discovery in DI alongside RSS/web adapters and kept Stars publication outside the discovery boundary.
- Added offline unit and SQLite contract coverage, and made both `tests/unit` and `tests/contract` part of the always-on CI gate.

## Verification
- GitHub Actions `tests` run #51 succeeded on `afff707e3d40f2aceb94bfa2ccb37de95d46c47a`.
- Pre-commit passed, including Ruff check and Ruff format.
- `pytest -q tests/unit tests/contract`: 273 tests passed.
- Total offline-suite coverage: 84.04%.
- The contract test verifies GitHub REST -> eligibility -> orchestrator -> SQLite, canonical evidence/reason codes, ETag cursor persistence and zero duplicate candidates on replay.

## Decisions
- Routine commits, pushes, stars, watches, branch/tag activity and fork events are not Stars candidates.
- Owned non-draft releases are eligible by default; repositories require explicit opt-in.
- Notable PR/issue activity requires an explicitly configured supported API path and trusted authorship.
- GitHub discovery uses supported REST endpoints rather than public-event scraping.
- Anonymous public discovery remains supported as a truthful limited mode instead of forcing credentials.
- GitHub discovery credentials remain isolated from Stars credentials.
