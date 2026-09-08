# State — v0.3.0

## Current position
- **Phase:** 13 — Evaluation, observability, docs and release
- **Plan:** 01
- **Status:** Phase 12 verified on PR #42; ready after merge
- **Epic:** #16
- **Phase issue:** #43
- **Next branch:** `gsd/phase-13-quality-release`

## Progress
- Requirements complete: 46/51
- Phases complete: 12/13 after PR #42 merges
- Seeded/JIT issues: #16-#23, #32, #35, #37, #39, #41, #43

## Phase evidence
- Phase 01: PR #25; verification `.planning/phases/01-discovery-domain-and-persistence/VERIFICATION.md`.
- Phase 02: PR #26; tests run #35; verification `.planning/phases/02-identity-and-source-registry/VERIFICATION.md`.
- Phase 03: PR #27; tests run #38; verification `.planning/phases/03-safe-fetch-boundary/VERIFICATION.md`.
- Phase 04: PR #28; tests run #42; verification `.planning/phases/04-discovery-orchestration/VERIFICATION.md`.
- Phase 05: PR #29; tests run #47; verification `.planning/phases/05-rss-and-website-adapters/VERIFICATION.md`.
- Phase 06: PR #30; tests run #53; verification `.planning/phases/06-github-adapter/VERIFICATION.md`.
- Phase 07: PR #31; tests run #57 final; verification `.planning/phases/07-youtube-adapter/VERIFICATION.md`.
- Phase 08: PR #33; tests run #66; verification `.planning/phases/08-speaker-event-adapters/VERIFICATION.md`.
- Phase 09: PR #36; tests run #71; verification `.planning/phases/09-restricted-social-sources/VERIFICATION.md`.
- Phase 10: PR #38; tests run #77; verification `.planning/phases/10-dedupe-confidence/VERIFICATION.md`.
- Phase 11: PR #40; implementation head `150f5e1ab03d111f1ae8ccdfceb6edcf5eb5888b`; tests run #83; verification `.planning/phases/11-review-publish-mcp/VERIFICATION.md`.
- Phase 12: PR #42; implementation/gate head `c0b7f5dd79096fec2afeecbcf35c9bf1e095e58e`; tests run #86 includes `tests/skills` and `scripts/quality_check.py`; verification `.planning/phases/12-agent-skills/VERIFICATION.md`.

## Locked decisions
- MCP/Stars REST is the publication boundary; adapters never write Stars directly.
- SQLite is the local discovery store.
- Review-before-publish is mandatory in v0.3.0.
- Publication requires persisted approval and a fresh Stars duplicate/policy recheck immediately before write.
- `publish_approved_candidates` defaults to `dry_run=true`; approval and real publication are separate calls.
- X/LinkedIn scraping, browser-session reuse, cookie extraction and anti-bot bypasses are not core or fallback paths.
- Safe fetch precedes arbitrary trusted-web adapters; private/link-local/loopback/unsafe redirects remain blocked.
- Fetched remote content is `UNTRUSTED_SOURCE_CONTENT`: evidence only, never instruction/tool/policy/write authority.
- Discovery orchestration isolates provider failures and commits cursor progress only with the persisted work it represents.
- Adapters emit provider-neutral items; missing type/date data remains review-required rather than model-inferred authority.
- RSS/Atom parsing rejects DTD/entity declarations before XML parsing.
- Trusted website discovery is ownership-gated and bounded; it is not a crawler.
- Rediscovery cannot reset reviewed/rejected/approved/published candidates or overwrite human edits.
- GitHub discovery uses supported REST APIs; routine activity is default-denied and eligibility is explainable.
- `GITHUB_DISCOVERY_TOKEN` is isolated from Stars credentials; anonymous access is explicit limited capability.
- YouTube discovery prefers Data API v3, with public Atom fallback only when a canonical channel ID is known; HTML scraping is excluded.
- Speaker/session ownership requires exact verified identity/provider IDs; fuzzy-name-only matching cannot establish ownership.
- Sessionize/Pretalx use public event data only; unavailable APIs do not trigger scraping fallbacks.
- Generic event-page discovery requires explicit/verified `EVENT_PAGE`, one bounded safe fetch and reviewable untrusted evidence.
- Stars uses `SPEAKING`; talk/workshop/keynote detail remains evidence-backed metadata.
- Restricted social profile URLs are not contributions; exact post URLs, local neutral exports or a compliant supplied API adapter are required.
- Social exports stay local; API/OAuth secrets are runtime-only and never persisted in discovery metadata/evidence/cursors.
- Duplicate identity separates provider/source, canonical URL and structured-content fingerprints; free-text descriptions are not identity keys.
- Current Stars entries participate in dedupe during discovery and again immediately before publish; Stars lookup failure leaves state `UNKNOWN`.
- Ownership confidence and contribution confidence are separate deterministic signals with inspectable reasons and no publication authority.
- Reusable skills are thin MCP orchestration only. They do not duplicate provider HTTP or publication business rules.
- The `publish-approved` skill mandates dry-run first and explicit current-interaction intent before a real publish.
- Small-model execution is first-class: phase plans must not leave unresolved architecture/product decisions to the executor.

## Blockers
None for Phase 13 once PR #42 merges.

## Handoff
Merge verified PR #42, then execute `.planning/phases/13-quality-release/13-01-PLAN.md` using issue #43 on branch `gsd/phase-13-quality-release`. Add the labeled public-safe evaluation corpus, privacy-safe discovery telemetry, truthful capability/security docs and reproducible release gates. Do not claim credentialed Stars mutation evidence unless an explicit usable token is available; offline publish dry-run evidence is mandatory regardless.
