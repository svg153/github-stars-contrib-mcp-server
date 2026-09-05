# State — v0.3.0

## Current position
- **Phase:** 08 — Speaker and event discovery
- **Plan:** 01
- **Status:** ready after Phase 07 PR #31 merges
- **Epic:** #16
- **Phase issue:** #32
- **Next branch:** `gsd/phase-08-speaker-event-adapters`

## Progress
- Requirements complete: 26
- Phases complete: 7/13 after PR #31 merges
- Seeded issues: #16-#23, #32

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

## Phase 06 evidence
- Implementation PR: #30
- CI: GitHub Actions `tests` run #53 succeeded on `4bd53fbcc7d15869838d585368cfd2ad6adb3d6c` before rebase merge.
- Verification: `.planning/phases/06-github-adapter/VERIFICATION.md`.

## Phase 07 evidence
- Implementation PR: #31
- CI: GitHub Actions `tests` run #56 succeeded on `9342ca2921b997d3d88414cc94219aaaf85d0530` before GSD closeout.
- Verification: `.planning/phases/07-youtube-adapter/VERIFICATION.md`.

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
- GitHub discovery uses supported REST endpoints with API version `2026-03-10`; raw public-event scraping is not a discovery path.
- Routine GitHub activity is default-denied; repositories/notable PR/issue activity require explicit opt-in while owned non-draft releases are accepted.
- `GITHUB_DISCOVERY_TOKEN` is isolated from Stars credentials; anonymous access is an explicit limited capability.
- YouTube discovery prefers Data API v3 uploads playlists plus batched video metadata rather than search/list scraping.
- `YOUTUBE_API_KEY` is optional and isolated from Stars credentials; missing credentials fall back only to the public Atom channel feed when a canonical channel ID is known.
- YouTube HTML scraping and ownership inference from individual video URLs are explicitly excluded.
- Small-model execution is a first-class constraint: no phase plan should leave architecture/product decisions to the executor.

## Blockers
None for Phase 08 after PR #31 merges.

## Handoff
Execute `.planning/phases/08-speaker-event-adapters/08-01-PLAN.md` from the merged Phase 07 main. Normalize speaker/session evidence first, then add Sessionize-style and Pretalx-style public adapters. Speaker ownership requires verified identity evidence rather than fuzzy-name-only matching. Generic event pages are explicit/verified URLs only, pass through safe fetch/untrusted-content handling, and never recurse into a crawl.
