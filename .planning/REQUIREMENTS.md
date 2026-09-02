# Requirements — v0.3.0

## Domain and persistence
- [x] **DOMAIN-01** — Provider-neutral source, candidate, evidence, provenance, run and review models are versioned.
- [x] **DOMAIN-02** — Candidate lifecycle transitions are explicit and invalid transitions fail deterministically.
- [x] **DOMAIN-03** — Local persistence round-trips discovery state with repeatable schema bootstrap/migration.
- [x] **DOMAIN-04** — Domain/application code depends on repository ports, not SQLite or MCP.

## Identity and source registry
- [x] **IDENT-01** — Existing Stars links/contributions can bootstrap likely sources without arbitrary crawling.
- [x] **IDENT-02** — Ownership states distinguish explicit, verified, inferred, rejected and disabled sources.
- [x] **IDENT-03** — URL/source canonicalization prevents duplicate registrations.
- [x] **IDENT-04** — Inferred ownership never silently becomes verified.

## Safe fetch
- [ ] **SAFE-01** — Private/link-local/loopback targets and unsafe redirects are blocked.
- [ ] **SAFE-02** — Requests enforce timeout, byte, redirect and content-type limits.
- [ ] **SAFE-03** — Fetched content is untrusted evidence and cannot alter agent control flow.
- [ ] **SAFE-04** — Secrets/tokens never enter fetched-content prompts, evidence or ordinary logs.

## Discovery orchestration
- [ ] **DISC-01** — Provider-neutral adapters emit source items without Stars API coupling.
- [ ] **DISC-02** — Discovery runs isolate adapter failures and persist deterministic summaries.
- [ ] **DISC-03** — Source items normalize into validated candidates plus evidence/provenance.
- [ ] **DISC-04** — Incremental cursors resume idempotently.

## Source adapters
- [ ] **RSS-01** — RSS/Atom produces article/blog candidates.
- [ ] **RSS-02** — Trusted personal sites can discover feeds/bounded content through safe fetch.
- [ ] **RSS-03** — Feed IDs/timestamps support incremental sync and duplicate suppression.
- [ ] **GH-01** — GitHub discovery uses supported APIs and trusted account identity.
- [ ] **GH-02** — Eligibility rules avoid treating routine activity as Stars contributions.
- [ ] **GH-03** — GitHub candidates carry canonical evidence and explainable eligibility.
- [ ] **GH-04** — Pagination/rate limits do not create duplicates.
- [ ] **YT-01** — Trusted YouTube channels sync via supported API/feed mechanisms.
- [ ] **YT-02** — Videos normalize with canonical channel/video evidence.
- [ ] **YT-03** — Missing credentials/quota produces explicit limited capability, never scraping.
- [ ] **SPEAK-01** — A provider-neutral session/event contract supports public speaker platforms.
- [ ] **SPEAK-02** — Sessionize/Pretalx-style public sources can produce talk/workshop candidates.
- [ ] **SPEAK-03** — Generic event-page extraction is limited to trusted URLs and reviewable evidence.
- [ ] **SOCIAL-01** — X/LinkedIn are optional restricted providers, not scraper targets.
- [ ] **SOCIAL-02** — Explicit URLs, exports or supported APIs feed the common source-item contract.
- [ ] **SOCIAL-03** — Unsupported access returns actionable capability status rather than bypass behavior.

## Deduplication and confidence
- [ ] **DEDUPE-01** — Candidates are compared with existing Stars entries before review and publish.
- [ ] **DEDUPE-02** — Stable source IDs, canonical URL and normalized title/date/type create deterministic fingerprints.
- [ ] **DEDUPE-03** — Similarity/confidence is explainable and advisory rather than sole publish authority.
- [ ] **DEDUPE-04** — Ambiguous matches remain reviewable conflicts instead of silent merges.

## Review and publication
- [ ] **REVIEW-01** — MCP/application tools list candidates with source, evidence, confidence and duplicate state.
- [ ] **REVIEW-02** — Users can approve, reject, edit or defer with auditable decisions.
- [ ] **PUB-01** — Publication performs a fresh duplicate/policy check immediately before Stars REST.
- [ ] **PUB-02** — Published records retain candidate/evidence provenance and result/client ID.
- [ ] **PUB-03** — Default policy requires explicit persisted approval.

## Skills and agents
- [ ] **AGENT-01** — `discover-my-contributions` bootstraps/syncs and returns a review queue.
- [ ] **AGENT-02** — `sync-source` targets one trusted source and reports capabilities/errors.
- [ ] **AGENT-03** — `review-candidates` presents evidence and records decisions.
- [ ] **AGENT-04** — `publish-approved` publishes only candidates satisfying deterministic policy.
- [ ] **AGENT-05** — Agent instructions treat fetched content as data and cannot delegate policy/write authority to model text.

## Quality and release
- [ ] **QUAL-01** — Deterministic unit/contract tests cover domain rules and adapters.
- [ ] **QUAL-02** — A labeled evaluation corpus measures extraction, eligibility, duplicate and confidence behavior.
- [ ] **OBS-01** — Privacy-safe telemetry reports run/source/candidate counts, latency and failure classes.
- [ ] **DOC-01** — Docs state setup, source support, credentials, privacy and unsupported automation.
- [ ] **REL-01** — v0.3.0 has offline tests, MCP smoke evidence and an end-to-end dry-run/publish-path verification.

## Traceability
| Phase | Requirements |
| --- | --- |
| 01 | DOMAIN-01, DOMAIN-02, DOMAIN-03, DOMAIN-04 |
| 02 | IDENT-01, IDENT-02, IDENT-03, IDENT-04 |
| 03 | SAFE-01, SAFE-02, SAFE-03, SAFE-04 |
| 04 | DISC-01, DISC-02, DISC-03, DISC-04 |
| 05 | RSS-01, RSS-02, RSS-03 |
| 06 | GH-01, GH-02, GH-03, GH-04 |
| 07 | YT-01, YT-02, YT-03 |
| 08 | SPEAK-01, SPEAK-02, SPEAK-03 |
| 09 | SOCIAL-01, SOCIAL-02, SOCIAL-03 |
| 10 | DEDUPE-01, DEDUPE-02, DEDUPE-03, DEDUPE-04 |
| 11 | REVIEW-01, REVIEW-02, PUB-01, PUB-02, PUB-03 |
| 12 | AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05 |
| 13 | QUAL-01, QUAL-02, OBS-01, DOC-01, REL-01 |
