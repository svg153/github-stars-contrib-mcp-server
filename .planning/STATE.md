# State — v0.3.0

## Current position
- **Phase:** 06 — GitHub discovery adapter
- **Plan:** 01
- **Status:** ready after Phase 05 PR #29 merges
- **Epic:** #16
- **Phase issue:** #22
- **Next branch:** `gsd/phase-06-github-adapter`

## Progress
- Requirements complete: 19
- Phases complete: 5/13 after PR #29 merges
- Seeded issues: #16-#23

## Phase 01 evidence
- Implementation PR: #25
- CI: GitHub Actions `tests` succeeded before merge.
- Verification: `.planning/phases/01-discovery-domain-and-persistence/VERIFICATION.md`.

## Phase 02 evidence
- Implementation PR: #26
- CI: GitHub Actions `tests` run #35 succeeded before merge.
- Verification: `.planning/phases/02-identity-and-source-registry/VERIFICATION.md`.

## Phase 03 evidence
- Implementation PR: #27
- CI: GitHub Actions `tests` run #38 succeeded on `7bd1bbfd6e58c8bca3d261fd5e0d67d6dd8f8120`.
- Verification: `.planning/phases/03-safe-fetch-boundary/VERIFICATION.md`.

## Phase 04 evidence
- Implementation PR: #28
- CI: GitHub Actions `tests` run #42 succeeded on `f53f4f93502cf56a710b355408deff8ee5c009a5`.
- Verification: `.planning/phases/04-discovery-orchestration/VERIFICATION.md`.

## Phase 05 evidence
- Implementation PR: #29
- CI: GitHub Actions `tests` run #47 succeeded on `a9dd8d243b6fd7f6b96eea2d08ec6298f884b82c`.
- Verification: `.planning/phases/05-rss-and-website-adapters/VERIFICATION.md`.

## Decisions
- MCP/Stars REST is the publication boundary.
- SQLite is the local discovery store.
- Review-before-publish is mandatory in v0.3.0.
- X/LinkedIn scraping is not required or permitted as a core path.
- Safe fetch precedes arbitrary trusted-web adapters.
- Fetched remote content is evidence only and never instruction authority.
- Discovery orchestration isolates provider failures and commits cursor progress only with the persisted work it represents.
- Adapters emit provider-neutral items; Stars publication remains outside the discovery adapter boundary.
- Missing type/date data is review-required rather than inferred by the orchestrator.
- RSS/Atom parsing is dependency-light and rejects DTD/entity declarations before XML parsing.
- Trusted website discovery is ownership-gated and bounded to structured metadata plus trusted feeds; it is not a crawler.
- Rediscovery cannot reset reviewed/rejected/approved/published candidates or overwrite human edits.
- Small-model execution is a first-class constraint: no phase plan should leave architecture/product decisions to the executor.

## Blockers
None for Phase 06 after PR #29 merges.

## Handoff
Execute `.planning/phases/06-github-adapter/06-01-PLAN.md` from the merged Phase 05 main. Use official GitHub REST APIs, keep the dedicated discovery token separate from Stars credentials, default-deny routine activity, and persist explainable eligibility reason codes with canonical evidence.
