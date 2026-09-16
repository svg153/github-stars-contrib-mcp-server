# #63 — Privacy-safe product quality metrics — Plan

## Goal
Provide deterministic local product-quality reporting over the existing discovery/review state so real-world validation and later audit/reconciliation work can be evaluated without leaking contribution content or turning publication volume into a target.

## Scope
1. Define privacy-safe reporting facts and a query port containing only categorical dimensions, counts and timestamps required for metrics.
2. Add an SQLite reporting adapter that derives those facts from the existing discovery database without exposing contribution/source content or stable IDs.
3. Add a deterministic aggregation use case with explicit numerator/denominator definitions, bounded percentile summaries, and `insufficient_data` for empty denominators.
4. Expose one read-only MCP tool that returns the local report and accepts an optional timezone-aware `as_of` value for reproducible queue-age reporting.
5. Add synthetic regression coverage for known ratios, empty/partial state behavior, and deliberate secret/private-content non-leakage.
6. Document metric definitions and the separation between operational telemetry and product-quality metrics.
7. Mark metrics whose required evidence is not yet persisted as `unavailable` with reasons instead of inventing proxies.

## Files / boundaries
- `domain/product_metrics.py`: privacy-safe fact model only.
- `domain/ports/product_metrics.py`: read-model query port.
- `infrastructure/persistence/product_metrics_sqlite.py`: SQLite projection into safe facts.
- `application/use_cases/get_product_metrics.py`: deterministic metric definitions and aggregation.
- `tools/product_metrics.py`: read-only MCP surface.
- `docs/product-metrics.md`: formulas, privacy boundary and interpretation.
- tests under `tests/unit/application`, `tests/unit/infrastructure`, and tool-level unit tests.

The implementation must not change candidate lifecycle, source trust, review policy, dedupe policy, or publication authority.

## Metric semantics
- Every ratio exposes numerator, denominator, value, status and human-readable definition.
- Zero denominator => `value: null`, `status: insufficient_data`.
- Acceptance by adapter/type uses the latest decisive review outcome (`approve` or `reject`); deferred outcomes are excluded.
- Queue age covers current `review_ready`/`deferred` candidates only.
- Time-to-first-decision uses candidate creation to first persisted review action.
- Source capability/error/rate-limit rates come from persisted discovery-run summaries rather than logs.
- Audit yield (#64), reconciliation findings (#66), curated FP/FN labels and dry-run→publish conversion remain unavailable until their required evidence exists.

## Privacy requirements
The report must not contain candidate IDs, source IDs, titles, descriptions, URLs, page/evidence text, tokens, review reasons, edited values or private content. Synthetic tests must attempt to seed these values and prove they do not reach the reporting snapshot.

## Verification
- `pre-commit run --all-files --show-diff-on-failure`
- offline pytest suite through repository CI
- repository quality check through repository CI
- deterministic synthetic metric assertions
- explicit privacy non-leak regression fixture

## Exit criteria
#63 is complete when CI is green, formulas are documented, empty/partial data cannot look like high quality, the MCP report is read-only, and the privacy regression proves contribution/private content is absent from the reporting facts.
