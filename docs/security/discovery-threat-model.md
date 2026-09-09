# Discovery threat model

This document describes the security and privacy boundaries for autonomous contribution discovery. The primary rule is that remote content is **evidence, never authority**.

## Assets and trust boundaries

Protected assets include the Stars API token, optional provider credentials, local discovery history/reviews, the user's Stars contribution list and the deterministic policy that controls writes. Inputs cross trust boundaries when the server fetches public URLs, reads provider API responses, imports user-supplied exports or receives model/agent text.

The authoritative write boundary remains the Stars REST/MCP application service. Provider adapters and model text cannot call Stars writes as an alternative path.

## SSRF and unsafe network targets

All generic remote fetching goes through the safe-fetch boundary. It accepts HTTP(S) only, resolves/revalidates every redirect and rejects loopback, private, link-local, multicast, unspecified and metadata-style unsafe targets for IPv4/IPv6. Requests have bounded connection/read timeouts, byte limits, redirect counts and allowed media types.

Adapters must not create a second unrestricted HTTP client to bypass this boundary for arbitrary event/blog pages. Official provider APIs can use their dedicated adapter transport, but provider responses are still untrusted data.

## Prompt injection and remote instructions

Fetched bodies are labeled `UNTRUSTED_SOURCE_CONTENT`. Active HTML surfaces such as scripts/styles/forms/templates are removed from the bounded evidence surface and embedded instructions, role changes, tool requests, policies or requests for secrets have no control authority.

A malicious page saying “approve me”, “ignore previous rules”, “call this tool”, or “publish immediately” remains quoted evidence. It cannot change source trust, lifecycle transitions, duplicate policy, review requirements or tool permissions.

LLMs may be used only for bounded extraction/classification where explicitly introduced. They never receive direct Stars write authority and their confidence/output is advisory to deterministic application rules.

## Credentials and secret handling

- `STARS_API_TOKEN` is for Stars and is never implicitly reused as `GITHUB_DISCOVERY_TOKEN`.
- YouTube/GitHub discovery credentials are configuration/secrets, not evidence fields.
- URLs with credential-like query keys are redacted before safe logging/evidence surfaces.
- Common bearer/provider token forms are removed from sanitized content.
- Skills and agent Markdown must not contain copied credentials.

Credentialed Stars mutation integration is opt-in and must not be claimed when a token was not explicitly available to the verification environment.

## Ownership confusion and malicious provenance

Source ownership is tracked separately from contribution confidence. Inferred sources cannot silently become verified, provider-wide domains are not treated as owned accounts, and generic search results are leads only. Exact provider identity is required for speaker/social paths where false attribution would be high risk.

Every candidate retains source identity, adapter/normalizer provenance and supporting evidence. Human review decisions and edits are persisted rather than replacing the original provenance.

## Duplicate races and stale approval

Discovery-time duplicate results are not sufficient write authority. Exact duplicates are blocked; likely/ambiguous matches remain reviewable. Immediately before a real publish the service refreshes the Stars snapshot and reruns duplicate/policy checks. A candidate must already be in persisted `APPROVED` state; approval and publication cannot be combined into a single implicit action.

The public MCP publish tool defaults to `dry_run=true`. Real publication is a separate explicit action.

## X / LinkedIn and anti-bot boundaries

The core project intentionally does **not** implement X/LinkedIn page scraping, browser automation to evade access controls, session-cookie reuse, undocumented private API emulation or anti-bot bypasses. Supported ingestion is limited to exact user-authorized URLs/metadata, user-supplied neutral exports, or a caller-provided compliant supported API adapter.

Unsupported access is reported as a capability limitation rather than triggering a fallback bypass.

## Local data and privacy

SQLite stores configured sources, cursors, candidates, bounded evidence/provenance, discovery runs, review decisions and publication records. This is user workspace data and can contain public contribution metadata associated with the user. Protect the DB with normal filesystem permissions, backups and deletion/retention policy appropriate to the host.

Privacy-safe discovery telemetry deliberately excludes titles, descriptions, page bodies, prompts, evidence excerpts, tokens and unnecessary URLs. Useful bounded fields include run ID in logs, source type, capability/status, aggregate item/candidate counts, duplicate class, duration and error class. High-cardinality run IDs are not Prometheus labels.

## Residual risks

- Public provider schemas and quotas can change; adapters must surface explicit failure/limited states.
- A public source can contain incorrect factual metadata; human review remains mandatory.
- Similarity heuristics can generate false positive/negative likely-duplicate results; they are advisory and explainable, not silent merge authority.
- Local SQLite security depends on the host filesystem/account.
- Credentialed Stars mutation behavior requires a separately authorized integration environment; offline release gates prove policy and dry-run behavior but not external service availability.
