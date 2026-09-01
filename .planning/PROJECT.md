# GitHub Stars Contributions MCP Server

## Project identity

A local-first MCP server and contribution discovery toolkit for GitHub Stars. The repository already owns the Stars read/write boundary; milestone **v0.3.0** adds evidence-backed discovery, source synchronization, review and reusable agent/skill workflows so users do not need to manually re-enter contribution data.

## Core value

Turn a user's existing GitHub Stars profile, contribution history and trusted public footprint into a reviewable queue of normalized contribution candidates with provenance, confidence, duplicate detection and safe publication.

## Current milestone

- **Version:** v0.3.0
- **Name:** Autonomous contribution discovery and guided publishing
- **Tracking epic:** #16
- **Planning branch:** `planning/gsd-autonomous-contributions`

## Target journey

1. Read existing Stars profile links and contributions.
2. Bootstrap a registry of likely user-owned sources without arbitrary crawling.
3. Synchronize supported sources: RSS/Atom, personal websites, GitHub, YouTube and public speaker/event sources.
4. Convert source items into `CandidateContribution` records with evidence and provenance.
5. Deduplicate against existing Stars contributions and the local candidate queue.
6. Present confidence, reasons, conflicts and evidence for review.
7. Approve/edit/reject/defer candidates.
8. Publish approved candidates only through the existing Stars REST/MCP path.
9. Offer reusable `discover`, `sync`, `review` and `publish` skills/workflows.

## Locked architecture decisions

1. MCP/Stars REST remains the authoritative publication boundary.
2. Discovery belongs to domain/application services, not MCP tool handlers.
3. Source behavior lives behind provider-neutral ports/adapters.
4. Deterministic code owns source trust, lifecycle, URL canonicalization, dedupe and publish policy.
5. LLMs may perform bounded extraction/classification but never receive direct write authority.
6. Fetched source content is untrusted data and cannot issue instructions to agents.
7. Local SQLite is the default state for sources, runs, candidates, evidence and review decisions.
8. Human review is mandatory before publication in v0.3.0.
9. X/LinkedIn scraping is not a milestone dependency; supported APIs, explicit URLs, exports or compliant external connectors are allowed.
10. Preserve the existing application/domain/infrastructure layout; no rewrite.

## Planning contract

- GitHub Issues are the operational backlog; `.planning/` is authoritative for requirements, dependencies, decisions and task packets.
- Epic #16 owns the milestone. Phases 01-07 are seeded as #17-#23; later phase issues are created just-in-time from `ROADMAP.md`.
- Implementation lands through isolated branches/PRs, never direct to `main`.
- Every plan is deliberately over-specified for small/fast LLM executors: exact files, bounded tasks, commands and done conditions.
- GSD runtime/commands are installed from the official distribution; only project planning artifacts are committed here.

## Constraints

- Python 3.12+ and the official MCP Python SDK v2 line already used by the repository.
- Existing Stars REST behavior must not regress.
- Existing GraphQL profile/link surfaces remain until a supported replacement exists.
- No secrets, raw fetched bodies or model prompts in normal logs.
- Unit/contract tests must be deterministic and offline. Credentialed integration tests may skip, but a skip is unavailable evidence rather than a pass.

## Out of scope

- Browser automation intended to bypass provider controls.
- General-purpose web crawling or search indexing.
- Arbitrary auto-publication from web findings.
- Hosted multi-tenant SaaS operation.
- Inventing contribution types not accepted by GitHub Stars.
