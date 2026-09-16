# State — v0.4 real-world contribution intelligence

## Current position
- **Initiative:** #61 — Real-world contribution intelligence and operator UX
- **Executed feature:** #63 — Privacy-safe product/discovery quality metrics
- **Implementation evidence:** PR #81; tests run #124
- **Next autonomous P0:** #64 — Missing-contribution audit
- **Real-world validation:** #62 remains pending an explicitly authorized real profile/source set and credentials where required.

## Progress
- #63 implementation and regression/privacy coverage are complete on PR #81.
- #64 is the next P0 that can be decomposed and implemented without publishing or mutating a real Stars profile.
- #62 should consume sanitized product metrics and real-world findings once an authorized environment is available.

## Locked decisions
- Product metrics are derived deterministically from persisted local discovery state; they are not mutable analytics counters.
- The reporting read model excludes candidate/source IDs, titles, descriptions, URLs, evidence bodies, tokens, edited values and private content.
- A zero denominator is `insufficient_data`, never a perfect-quality result.
- Metrics that lack persisted evidence are `unavailable` with an explicit reason; no proxy is invented.
- Product metrics are operator evidence only and cannot grant approval/publication authority or become publication-volume KPIs.
- Operational Prometheus telemetry remains separate from product-quality metrics.
- Dry-run-to-publish conversion stays unavailable until a safe correlation model exists, and must remain diagnostic rather than an optimization target.

## Handoff
Use `.planning/v0.4/features/63-product-quality-metrics/` for #63 execution evidence. Before implementing #64, read its issue and create a JIT packet that defines bounded audit scope, source coverage, uncertainty, comparison semantics and review handoff without bypassing the existing dedupe/review/publication boundaries.
