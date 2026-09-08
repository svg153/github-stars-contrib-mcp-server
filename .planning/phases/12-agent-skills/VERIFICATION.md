# Phase 12 Verification — Reusable skills and agent workflows

## Evidence
- Issue: #41
- Pull request: #42
- Verified implementation/gate head: `c0b7f5dd79096fec2afeecbcf35c9bf1e095e58e`
- GitHub Actions workflow: `tests` run #86 — success
- Pre-commit: passed
- Offline test gate: `pytest -q tests/unit tests/contract tests/skills` — passed
- Repository quality gate: `python scripts/quality_check.py` — passed

## Requirement verification

### AGENT-01 — discover-my-contributions
The skill uses `bootstrap_sources`, source management/discovery MCP tools and candidate list/detail tools to produce a review queue. It explicitly stops before review approval or publication and never converts confidence into approval.

### AGENT-02 — sync-source
The skill targets an exact configured source ID and reports supported capability/provider failures. Direct provider HTTP, scraping, browser automation, cookie/session reuse and bypass behavior are prohibited by both instructions and static contract tests.

### AGENT-03 — review-candidates
The skill requires candidate detail/evidence inspection and explicit human approve/edit/reject/defer choices before calling `review_candidate`. Duplicate and both confidence dimensions remain visible; the skill never publishes.

### AGENT-04 — publish-approved
The skill operates only on persisted approved IDs, always calls `publish_approved_candidates(..., dry_run=true)` first and permits `dry_run=false` only after explicit current-interaction user intent. It does not call `review_candidate` or combine approval with publication.

### AGENT-05 — untrusted content has no authority
All four skills and the host-neutral agent identify fetched/provider text as `UNTRUSTED_SOURCE_CONTENT`. Source text cannot issue instructions, request credentials/tools, change policy or acquire Stars write authority. Static contracts prevent direct provider implementations in skill files.

## Exit gate
Run #86 is the first Phase 12 gate that includes the skill contract suite and repository quality check in normal CI. Phase 12 is verified on that implementation/gate head. The subsequent GSD closeout commit is documentation/state reconciliation only and must also pass the normal PR workflow before merge.
