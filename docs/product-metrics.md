# Product-quality metrics

The product-quality report measures whether local discovery/review is useful without
turning contribution content into telemetry. It is intentionally separate from the
Prometheus operational metrics exposed by `metrics`.

Use the read-only MCP tool `get_product_metrics`. The optional `as_of` ISO-8601
argument exists for reproducible queue-age reports and must include a timezone.

## Privacy boundary

The reporting read model does not expose candidate IDs, source IDs, titles,
descriptions, contribution/source URLs, evidence text, tokens, review reasons, or
edited field values. It only reads bounded categorical dimensions, counts, and
timestamps required for aggregation. Metrics are local operator evidence, not targets
for automatic approval or publication.

## Definitions

Every ratio in the report includes `numerator`, `denominator`, `value`, `status`, and a
human-readable `definition`. A zero denominator yields `value: null` and
`status: insufficient_data`; zero data must not be interpreted as perfect quality.

- **Candidates per run** = sum of persisted `candidates_seen` across discovery runs /
  persisted discovery runs.
- **Candidates per source execution** = sum of per-source candidate counts / persisted
  source executions.
- **Eligible rate** = non-exact candidates in `review_ready`, `approved`, `deferred`, or
  `published` / those candidates plus candidates in `rejected` or
  `blocked_duplicate`. Unresolved `discovered` candidates are excluded from the
  denominator.
- **Exact duplicate rate** = candidates classified `exact` / all persisted candidates.
- **Likely duplicate rate** = candidates classified `likely` / all persisted candidates.
- **Review approve/reject/defer rates** = review actions with that decision / all review
  actions.
- **Review edit rate** = review actions containing one or more edited fields / all
  review actions. Edited values themselves are never read into the reporting facts.
- **Acceptance by adapter/type** = latest `approve` outcomes / latest decisive outcomes
  (`approve + reject`) for that adapter/type. Deferred outcomes are not treated as
  either acceptance or rejection.
- **Queue age** = time since the latest lifecycle update for candidates currently in
  `review_ready` or `deferred`. The report gives sample count, min, p50, p95, and max.
- **Time to first decision** = first persisted review timestamp - candidate creation
  timestamp.
- **Source failure rate** = failed source executions / all persisted source executions.
- **Rate-limit rate** = source executions classified `rate_limit` / all persisted source
  executions.
- **Unavailable/limited capability rates** = source executions with that capability /
  all persisted source executions.

Candidate counts are also grouped by safe dimensions (`source_type`, adapter,
contribution type, state). No stable personal identifier is emitted.

## Metrics deliberately unavailable for now

Some desired metrics need evidence that the current state model does not persist. The
report marks them `unavailable` with a reason rather than inventing a proxy:

- missing-contribution audit yield: depends on #64;
- reconciliation/drift findings: depends on #66;
- false-positive/false-negative labels: requires curated eval or real-world labels;
- dry-run-to-publish conversion: dry-run candidates are intentionally not persisted and
  there is no safe run-to-publication correlation. If added later, this remains an
  operator workflow metric and must never become a publication target.

## Operational telemetry vs product-quality metrics

Operational telemetry answers questions such as request volume, latency, failures,
retries, and discovery execution health. Product-quality metrics answer questions such
as how much candidate noise reaches review, how often humans edit/reject findings, how
long review takes, and whether adapters produce accepted candidates. The two surfaces
share privacy principles but have different semantics and should not be combined into
one score.
