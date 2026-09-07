# Phase 10 Summary — Deduplication, confidence and conflict handling

## Outcome

Phase 10 adds deterministic duplicate detection and explainable confidence before candidates can enter review. Discovery now snapshots current GitHub Stars contributions once per run, compares candidates against both Stars and the persisted/same-run SQLite queue, blocks exact duplicates, exposes likely conflicts for human review, and refuses to mark candidates review-ready when Stars cannot be checked.

## Delivered

- Added separate deterministic fingerprints for provider/source identity, canonical URL and normalized title/date/type content.
- Added URL canonicalization that normalizes scheme/host/default ports, query ordering and trailing slash while removing fragments and common tracking parameters.
- Added a paginated Stars snapshot loaded once per discovery run through the existing `StarsAPIPort`.
- Added exact duplicate matching against current Stars entries and persisted/same-run candidates.
- Added conservative likely-conflict matching using normalized title/type and publication date proximity; likely matches are never auto-merged.
- Added separate deterministic ownership and contribution confidence scores, bands and reason lists.
- Persisted fingerprint, duplicate reason/target and confidence explanations in candidate provenance metadata without adding a SQLite schema migration.
- Integrated duplicate/confidence assessment before `REVIEW_READY`: exact matches become `BLOCKED_DUPLICATE`; likely matches remain reviewable conflicts; Stars-unavailable candidates remain `DISCOVERED` with duplicate state `UNKNOWN`.
- Added unit, DI and contract coverage for pagination, canonicalization, exact/likely/unknown outcomes, same-run dedupe and confidence separation.

## Safety decisions

- Stars availability is a review gate: if the authoritative current contribution set cannot be read, discovery does not infer `CLEAR` from local state alone.
- `LIKELY` is advisory and visible to review; it never triggers an automatic merge or silent discard.
- Ownership confidence and contribution confidence remain distinct signals and neither is publication authority.
- Content fingerprints require structured title/date/type and deliberately avoid free-text descriptions.
- The Stars snapshot has a defensive pagination ceiling and provider failures degrade to explicit `UNKNOWN` state rather than bypass behavior.
- Publication remains outside discovery and Phase 11 must rerun duplicate/policy checks immediately before any Stars write.

## Verification

- PR: #38
- Implementation head validated by GitHub Actions: `a91dee0fcda44df255561fbb0ee95610a9a2f414`
- CI run: #77 (`tests`) — success
- Pre-commit passed.
- Full offline unit/contract suite passed.
- Phase verification details: `VERIFICATION.md`.

## Next

Phase 11 / issue #39 adds auditable candidate review plus guarded MCP publication workflows with a fresh pre-publish duplicate/policy recheck and dry-run by default.
