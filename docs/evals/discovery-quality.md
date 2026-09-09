# Discovery quality evaluation

The v0.3.x discovery evaluation is a **regression gate**, not a benchmark claim. It
uses synthetic/public-safe normalized cases so the repository can assert the
deterministic decisions that matter before review and publication.

## What the corpus covers

`tests/evals/fixtures/discovery_cases.json` spans RSS, GitHub, YouTube,
speaker/session data, explicit restricted-social URLs, exact duplicates, likely
conflicts, incomplete/noise candidates and hostile prompt-injection text carried
as evidence.

Every case labels:

- the normalized Stars contribution type, including `null` when metadata is
  intentionally insufficient;
- the expected duplicate class (`clear`, `likely`, or `exact`);
- minimum and maximum ownership/contribution confidence;
- the minimum evidence count required for the decision.

`tests/evals/test_discovery_eval.py` runs the production `Deduplicator` and
`assess_confidence` functions. A changed algorithm therefore has to preserve the
labeled safety/precision behavior or intentionally update the corpus and its
rationale.

## Precision-first interpretation

Exact duplicate regressions are blocking because they can lead to duplicate
publication. Likely matches stay conflicts for human review; they are not
silently merged. Incomplete candidates remain visible but carry lower
contribution confidence instead of having missing facts invented.

The prompt-injection case deliberately contains an instruction to publish and
reveal a token. The evaluation asserts that evidence text does not become a
fingerprint, confidence reason, contribution type, policy decision or write
authority. Fetch-time sanitization and `UNTRUSTED_SOURCE_CONTENT` handling are
covered separately by the safe-fetch tests.

## Scope

This corpus evaluates the post-normalization decision boundary. Provider-specific
parsing/eligibility remains covered by deterministic adapter unit/contract tests.
No private profile, production contribution, access token or browser/session data
is stored in the fixtures.
