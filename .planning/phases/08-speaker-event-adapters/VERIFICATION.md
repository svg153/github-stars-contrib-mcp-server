# Phase 08 Verification — Speaker and event discovery

## Overall result
**VERIFIED**

- PR: #33
- Verified head: `75472bc99148a891f4cc9c9ae7361546aade22a4`
- GitHub Actions workflow: `tests` run #66 — success
- Pre-commit: passed
- Offline test command: `pytest -q tests/unit tests/contract`
- Tests: 296 passed
- Coverage: 83.74%

## Requirement evidence

### SPEAK-01 — Provider-neutral session/event contract
**PASS**

- `src/github_stars_contrib_mcp/application/discovery/session_normalizer.py` normalizes session title, description, event, date, URLs, speaker identity and evidence-backed session kind.
- Exact verified identity/profile identifiers are used to establish speaker ownership; unrelated agenda items and fuzzy-name-only matches remain excluded.
- Unit tests cover normalization, supported session types and ownership boundaries.

### SPEAK-02 — Sessionize/Pretalx public sources
**PASS**

- `src/github_stars_contrib_mcp/infrastructure/adapters/sessionize_source.py` consumes explicitly registered public Sessionize-style JSON data and emits stable session/event evidence with incremental fingerprints.
- `src/github_stars_contrib_mcp/infrastructure/adapters/pretalx_source.py` consumes public Pretalx-style submissions/schedule data, preserves stable IDs/URLs and handles schedule updates without duplicate replay.
- Missing verified speaker matches or supported public data do not become contribution candidates through guessing or scraping fallbacks.
- Unit and contract fixtures cover public data, identity matching, incremental replay and schedule changes.

### SPEAK-03 — Bounded generic event-page extraction
**PASS**

- `src/github_stars_contrib_mcp/infrastructure/adapters/event_page_source.py` accepts only explicit/verified `EVENT_PAGE` sources.
- Event pages pass through `ContentFetcher` and the untrusted-content boundary before JSON-LD/OpenGraph/visible metadata becomes evidence.
- The adapter performs one bounded fetch and does not recursively crawl or follow cross-origin evidence URLs.
- Prompt-injection and cross-origin fixtures remain evidence-only and cannot alter control flow or trigger further fetching.

## Exit gate
Phase 08 satisfies its exit criteria: public speaker platforms produce explainable, evidence-backed candidates, speaker ownership is conservative and verified, and generic event discovery remains bounded to trusted URLs without recursive scraping.
