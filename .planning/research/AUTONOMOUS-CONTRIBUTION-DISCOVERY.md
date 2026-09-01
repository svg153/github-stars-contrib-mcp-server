# Research synthesis — autonomous contribution discovery

This captures the implementation conclusions from the prior Medium-led investigation and repository/API research so execution agents do not need to repeat product research.

## Desired behavior
Use existing Stars profile data and trusted public identity links to infer likely owned sources, sync them, normalize contribution candidates, deduplicate them, show evidence/confidence and publish only reviewed candidates.

## Source hierarchy

### Tier A — first-class
- RSS/Atom: open, incremental, stable and easy to test.
- Personal websites: only registered/trusted domains; prefer feed/structured metadata over crawling.
- GitHub: official APIs, stable canonical URLs and strong identity signal.
- YouTube: official Data API plus public channel-feed fallback where appropriate; expose quota/credential limits.
- Public conference/session systems: provider adapters for stable public APIs/data (Sessionize/Pretalx-style), plus bounded trusted event pages.

### Tier B — restricted/conditional
- X/Twitter and LinkedIn: no bypass scraping dependency. Accept official APIs when available to the user, exported data, explicit post URLs or compliant external connectors.
- Generic web search: optional lead generation only; findings require trusted evidence and review before becoming candidates.

## Architecture conclusions
1. Source adapters emit neutral source items/evidence, never Stars payloads.
2. Normalization belongs to application/domain services.
3. Persist evidence/candidate state before any model enrichment.
4. LLM use is bounded to extraction/classification where deterministic metadata is insufficient.
5. Source ownership confidence is separate from contribution confidence.
6. Dedupe uses canonical source IDs/URLs first; fuzzy similarity is advisory.
7. Existing Stars contributions always participate in duplicate detection.
8. Human review is the v0.3.0 default; reconsider auto-publish only after measured false-positive data.

## Candidate minimum fields
Stable ID, proposed Stars type/title/description/url/date, source ID/type, external item ID, evidence list, provenance versions, ownership confidence, contribution confidence, duplicate status/reasons, lifecycle state, review decision/edits and publication result/client ID.

## Security conclusions
- Fetch only registered/trusted origins unless the user explicitly adds a source.
- Block SSRF/private targets and unsafe redirects before requests.
- Cap bytes, redirects and processing time.
- Never expose bearer tokens/environment values to fetched-content prompts.
- Source content is evidence; any embedded instruction is hostile and ignored.
- Publication requires persisted approval plus a fresh duplicate/policy check.
- Logs/metrics store IDs, provider, timings and result classes, not full page bodies/prompts.

## Workflow conclusions
Provide thin workflows: `discover-my-contributions`, `sync-source`, `review-candidates`, `publish-approved`. They compose deterministic MCP/application capabilities and contain no provider parsing or direct Stars write logic.

Reference supplied during research: https://share.google/7f0d4hoAOz1YqOMxA
