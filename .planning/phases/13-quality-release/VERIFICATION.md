# Phase 13 Verification — Quality, observability, docs and release proof

## Evidence
- Issue: #43
- Pull request: #45
- Evaluation/telemetry first-slice head: `f66aaeaa886a98051713b6c22c96ff1b5b865e2a`
- First-slice GitHub Actions: `tests` run #90 — success
- Release implementation head: `f8dd62791259f0fa9f690cb607bcd80c7c3b9526`
- Release implementation GitHub Actions: `tests` run #91 — success
- Package version observed in `pyproject.toml`: `0.3.1`; internal roadmap milestone remains named v0.3.0.

## Reproducible offline gates
The repository/CI executes the following release-relevant checks without provider secrets:

```bash
python scripts/quality_check.py
pytest -q tests/evals/test_discovery_eval.py tests/evals/test_release_flow.py
pytest -q tests/unit/observability/test_discovery_observability.py
pytest -q tests/unit/test_server.py tests/unit/tools/test_discovery_tools.py
pytest -q tests/skills/test_skill_contracts.py
python -m compileall -q src
make test
```

GitHub Actions run #91 passed with pre-commit, the offline pytest suite (which includes the eval/release-flow fixtures) and the repository quality check on the release implementation head.

## Requirement verification

### QUAL-01 — deterministic automated coverage
The repository retains deterministic domain/adapter/unit/contract coverage from Phases 01-12, and the Phase 13 CI runs the complete offline test suite plus repository quality checks. The release-flow fixture adds one explicit cross-layer regression path rather than relying only on isolated unit tests.

### QUAL-02 — labeled evaluation corpus
`tests/evals/fixtures/discovery_cases.json` and `tests/evals/test_discovery_eval.py` provide labeled public-safe cases spanning supported discovery families, positive/negative eligibility, exact/likely duplicate behavior, confidence outcomes, noise and prompt-injection-style content. `docs/evals/discovery-quality.md` documents interpretation and extension of the corpus.

### OBS-01 — privacy-safe telemetry
`src/github_stars_contrib_mcp/observability/discovery.py` and its unit tests expose bounded run/source/candidate telemetry. Allowed dimensions cover source type, capability/status, counts, duplicate class, duration and error class; content, prompts, credentials and unnecessary URLs are not telemetry dimensions. High-cardinality run IDs are kept out of Prometheus labels.

### DOC-01 — truthful setup/capability/security docs
README documents the end-user journey, discovery credentials and platform-specific SQLite location. `docs/sources/README.md` documents the capability matrix and explicit X/LinkedIn restrictions. `docs/security/discovery-threat-model.md` covers SSRF, prompt injection, secret handling, ownership confusion, duplicate races, restricted-social boundaries, local privacy and residual risks. CHANGELOG records the milestone without incorrectly downgrading package version 0.3.1.

### REL-01 — offline smoke and publish-path proof
`tests/unit/test_server.py` and `tests/unit/tools/test_discovery_tools.py` provide MCP/tool smoke evidence. `tests/evals/test_release_flow.py` performs a single offline source → discovery → review-ready candidate → explicit approval → publish dry-run path using SQLite and a fake Stars API. It asserts the publish result is `dry_run` and that no Stars `upsert_contribution` call occurs.

A real credentialed Stars mutation test is **not claimed**: no explicit authorized `STARS_API_TOKEN` was available to this verification environment. Existing integration/mutation workflows remain opt-in and are the correct place to perform that external verification when credentials are deliberately supplied.

## Exit assessment
All five Phase 13 requirements are verified by deterministic offline evidence and truthful documentation. The milestone exit condition is met without X/LinkedIn scraping, without model-controlled publication and without loss of provenance. Phase 13 is verified and ready to merge by rebase.
