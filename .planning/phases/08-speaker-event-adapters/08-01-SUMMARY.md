# Phase 08 Summary — Speaker and event discovery

**Issue:** #32
**PR:** #33
**Status:** implemented and verified

## Delivered
- Added provider-neutral session/event normalization with evidence-backed talk/workshop/keynote metadata and Stars `SPEAKING` output.
- Added exact verified speaker-identity matching; fuzzy-name-only similarity cannot establish ownership.
- Added Sessionize-style public JSON discovery with stable session evidence and incremental fingerprints.
- Added Pretalx-style public submissions/schedule discovery with stable IDs and schedule-change handling.
- Added explicit `EVENT_PAGE` discovery for bounded JSON-LD/OpenGraph/visible metadata extraction through safe fetch and the untrusted-content boundary.
- Registered speaker/event adapters in the default discovery runtime and added offline unit/contract coverage for identity, incremental sync, prompt injection and cross-origin behavior.

## Verification
- GitHub Actions `tests` run #66 succeeded on `75472bc99148a891f4cc9c9ae7361546aade22a4`.
- Pre-commit passed, including Ruff check and Ruff format.
- `pytest -q tests/unit tests/contract`: 296 tests passed.
- Total offline-suite coverage: 83.74%.
- Detailed requirement evidence is recorded in `VERIFICATION.md`.

## Decisions
- Event listing alone never proves that the user is a speaker; ownership requires verified identity evidence.
- Sessionize/Pretalx adapters consume public event data only and never fall back to scraping when a public API/schedule is unavailable.
- Generic event pages must be explicit/verified `EVENT_PAGE` sources and perform one bounded fetch only; no recursive or cross-origin crawl is allowed.
- Fetched event content remains untrusted evidence and cannot trigger tools, fetches or publication actions.
