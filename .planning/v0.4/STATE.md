# State — v0.4 real-world contribution intelligence

## Current position
- **Initiative:** #61 — Real-world contribution intelligence and operator UX
- **Audit epic:** #64 — Missing-contribution audit
- **Executed audit slice:** #82 — Bounded audit requests and read-only historical scans
- **Implementation evidence:** PR #86; tests run #129
- **Next autonomous P0:** #83 — Source coverage accounting and historical blind-spot reporting
- **Real-world validation:** #62 remains pending an explicitly authorized real profile/source set and credentials where required.

## Progress
- #63 privacy-safe product/discovery quality metrics merged in PR #81; final tests run #125.
- #64 is decomposed into focused slices #82-#85.
- #82 implementation and regression/isolation coverage are verified on PR #86.
- #83 is next and should consume `AuditScanReport` rather than rescan sources or mutate discovery state.
- #84 will compare reconstructed observations with current Stars using the existing duplicate/conflict machinery.
- #85 will provide explicit review handoff plus audit-yield/coverage integration into #63 metrics.
- #62 should consume sanitized product metrics and audit findings once an authorized environment is available.

## Locked decisions
- Product metrics are derived deterministically from persisted local discovery state; they are not mutable analytics counters.
- The reporting read model excludes candidate/source IDs, titles, descriptions, URLs, evidence bodies, tokens, edited values and private content.
- A zero denominator is `insufficient_data`, never a perfect-quality result.
- Metrics that lack persisted evidence are `unavailable` with an explicit reason; no proxy is invented.
- Product metrics are operator evidence only and cannot grant approval/publication authority or become publication-volume KPIs.
- Operational Prometheus telemetry remains separate from product-quality metrics.
- Dry-run-to-publish conversion stays unavailable until a safe correlation model exists, and must remain diagnostic rather than an optimization target.
- Historical audit is read-only: it does not persist candidates/runs/reviews/publications or touch normal incremental discovery cursors.
- Audit adapters start from ephemeral cursors and use hard per-source batch/item limits.
- Undated historical items and provider capability limits reduce audit certainty explicitly rather than being treated as complete coverage.
- Audit comparison/review/publication remain separate stages; #82 introduces no Stars mutation path.

## Handoff
Use `.planning/v0.4/features/82-audit-request-readonly-scan/` for #82 execution evidence. Implement #83 as a pure coverage/blind-spot derivation over `AuditScanReport`: searched, limited, unavailable, failed and truncated source states must remain explicit and privacy-safe. Do not rescan sources or introduce Stars comparison in #83.
