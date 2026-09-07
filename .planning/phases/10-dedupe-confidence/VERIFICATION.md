# Phase 10 Verification — Deduplication, confidence and conflict handling

**Phase:** 10
**Issue:** #37
**PR:** #38
**Implementation CI:** GitHub Actions `tests` run #77 succeeded on `a91dee0fcda44df255561fbb0ee95610a9a2f414`.

## Requirements

### DEDUPE-01 — Candidates are compared with existing Stars entries before review and publish

Verified for the discovery-to-review boundary by orchestration and contract tests. A paginated snapshot of current Stars contributions is loaded once per discovery run through `StarsAPIPort`; each newly discovered candidate is compared with that snapshot before it can become `REVIEW_READY`. When Stars is unavailable, duplicate state is `UNKNOWN` and the candidate remains `DISCOVERED`. The final pre-publish recheck remains intentionally assigned to PUB-01 in Phase 11.

### DEDUPE-02 — Stable source IDs, canonical URL and normalized title/date/type create deterministic fingerprints

Verified by fingerprint unit tests. Provider identity (`source_id` + `external_id`), canonical URL, and normalized structured content are represented by separate SHA-256 fingerprints. URL canonicalization removes fragments/common tracking parameters and normalizes identity-relevant URL structure; content fingerprints require title/date/type rather than free-form descriptions.

### DEDUPE-03 — Similarity/confidence is explainable and advisory rather than sole publish authority

Verified by confidence tests and persisted provenance metadata. Ownership and contribution confidence are scored independently with inspectable bands/reason lists. Duplicate ambiguity can reduce contribution confidence without modifying ownership confidence. Confidence does not approve or publish a candidate.

### DEDUPE-04 — Ambiguous matches remain reviewable conflicts instead of silent merges

Verified by unit/contract cases for exact, likely and unknown outcomes. Exact Stars/local matches transition to `BLOCKED_DUPLICATE`; likely normalized title/type/date matches transition to `REVIEW_READY` with `duplicate_state=LIKELY`, reason and target metadata; no automatic merge occurs. Same-run candidates participate in the local duplicate set.

## Regression and safety evidence

- Pre-commit passed on run #77.
- Full offline suite passed on run #77.
- Stars pagination is fetched once per discovery run and has a defensive page-count ceiling.
- Canonically equivalent URLs with tracking differences are exact duplicates.
- Persisted queue entries and candidates emitted earlier in the same run are checked for exact/likely conflicts.
- Stars access failure cannot silently produce `CLEAR` or `REVIEW_READY`.
- Rediscovery preservation still prevents automated discovery from overwriting non-`DISCOVERED` lifecycle decisions.
- No publication authority was added to discovery adapters or confidence logic.

## Exit decision

Phase 10 satisfies DEDUPE-01, DEDUPE-02, DEDUPE-03 and DEDUPE-04 for the discovery/review boundary. PUB-01 deliberately owns the separate fresh duplicate/policy check immediately before publication in Phase 11. The closeout commit contains planning/documentation state in addition to the already validated implementation and must pass the same PR CI before merge.
