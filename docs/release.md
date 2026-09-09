# Release process

The package version is defined in `pyproject.toml`. GitHub releases are created from the exact `main` commit validated by the `Release` workflow.

## Normal release path

A release is represented by a marker file named `.release/vX.Y.Z.json`. The marker version must match `pyproject.toml`.

1. Bump `pyproject.toml` and related version references as needed.
2. Add the matching release marker, for example `.release/v0.3.1.json`.
3. Open a release PR and wait for the normal repository CI to pass.
4. Merge the release PR to `main`.
5. The `Release` workflow runs from that immutable merge SHA, validates the canonical `vX.Y.Z` tag, reruns offline quality gates, builds wheel + sdist, verifies both distributions, uploads them as a workflow artifact, creates an annotated immutable tag and creates the GitHub Release with generated notes and both distributions attached.

Changing a release marker later is not a retry mechanism: once a tag exists the workflow refuses to move or replace it.

## Manual recovery path

`workflow_dispatch` remains available for failures that occurred before tag creation. Run it from the `main` branch and supply the canonical matching tag, such as `v0.3.1`. The same version validation, quality gates and packaging checks run before tag creation.

If a failure occurs after the tag has already been pushed but before the GitHub Release is created, do not move the tag. Inspect the failed run and preserve the immutable tag; complete the GitHub Release against that existing tag rather than pointing the version at a different commit.

## What the release proves

A successful release proves that the tagged source passed the deterministic offline repository checks and produced valid Python wheel/sdist artifacts. It does **not** claim a credentialed GitHub Stars mutation test unless the separate opt-in integration workflow was intentionally run with an authorized `STARS_API_TOKEN` and mutation enabled.

## PyPI

PyPI publication is intentionally not part of the current release workflow. Do not add long-lived package-index passwords or tokens to the repository. If PyPI distribution is desired, configure PyPI Trusted Publishing/OIDC for this repository first, then add a separate publication job/environment with explicit protections.
