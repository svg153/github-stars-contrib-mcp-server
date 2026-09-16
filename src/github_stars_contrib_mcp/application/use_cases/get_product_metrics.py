"""Deterministic privacy-safe product metric aggregation."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from github_stars_contrib_mcp.domain.ports.product_metrics import ProductMetricsQuery
from github_stars_contrib_mcp.domain.product_metrics import (
    ProductMetricsSnapshot,
    ReviewMetricFact,
)


def _ratio(
    numerator: int,
    denominator: int,
    *,
    definition: str,
) -> dict[str, Any]:
    return {
        "numerator": max(0, numerator),
        "denominator": max(0, denominator),
        "value": (numerator / denominator) if denominator > 0 else None,
        "status": "available" if denominator > 0 else "insufficient_data",
        "definition": definition,
    }


def _counts(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _duration_summary(values: list[float], *, definition: str) -> dict[str, Any]:
    bounded = sorted(max(0.0, value) for value in values)
    if not bounded:
        return {
            "sample_count": 0,
            "min_seconds": None,
            "p50_seconds": None,
            "p95_seconds": None,
            "max_seconds": None,
            "status": "insufficient_data",
            "definition": definition,
        }

    def nearest_rank(percentile: float) -> float:
        index = max(0, math.ceil(percentile * len(bounded)) - 1)
        return bounded[index]

    return {
        "sample_count": len(bounded),
        "min_seconds": bounded[0],
        "p50_seconds": nearest_rank(0.50),
        "p95_seconds": nearest_rank(0.95),
        "max_seconds": bounded[-1],
        "status": "available",
        "definition": definition,
    }


def _acceptance_by(
    reviews: tuple[ReviewMetricFact, ...],
    attribute: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for review in reviews:
        if review.decision not in {"approve", "reject"}:
            continue
        grouped[str(getattr(review, attribute))][review.decision] += 1

    output: dict[str, dict[str, Any]] = {}
    for key in sorted(grouped):
        decisions = grouped[key]
        approved = decisions["approve"]
        rejected = decisions["reject"]
        output[key] = _ratio(
            approved,
            approved + rejected,
            definition=(
                "latest approved outcomes / latest decisive outcomes "
                "(approve + reject); deferred reviews are excluded"
            ),
        )
    return output


class GetProductMetrics:
    """Aggregate local product-quality signals without exposing contribution content."""

    DEFINITIONS_VERSION = "1"

    def __init__(self, query: ProductMetricsQuery) -> None:
        self._query = query

    def generate(self, *, as_of: datetime | None = None) -> dict[str, Any]:
        resolved_as_of = as_of or datetime.now(UTC)
        if resolved_as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        resolved_as_of = resolved_as_of.astimezone(UTC)
        snapshot = self._query.snapshot()
        return self._report(snapshot, resolved_as_of)

    def _report(
        self,
        snapshot: ProductMetricsSnapshot,
        as_of: datetime,
    ) -> dict[str, Any]:
        candidates = snapshot.candidates
        reviews = snapshot.review_actions
        source_runs = snapshot.run_sources
        runs = snapshot.runs

        eligible_states = {"review_ready", "approved", "deferred", "published"}
        noise_states = {"rejected", "blocked_duplicate"}
        eligible = sum(
            1
            for candidate in candidates
            if candidate.state in eligible_states
            and candidate.duplicate_state != "exact"
        )
        noise = sum(1 for candidate in candidates if candidate.state in noise_states)

        exact_duplicates = sum(
            1 for candidate in candidates if candidate.duplicate_state == "exact"
        )
        likely_duplicates = sum(
            1 for candidate in candidates if candidate.duplicate_state == "likely"
        )

        review_counts = Counter(review.decision for review in reviews)
        edited_reviews = sum(1 for review in reviews if review.edited)

        queued = [
            candidate
            for candidate in candidates
            if candidate.state in {"review_ready", "deferred"}
        ]
        queue_ages = [
            max(0.0, (as_of - candidate.updated_at.astimezone(UTC)).total_seconds())
            for candidate in queued
        ]
        first_decision_times = [
            max(
                0.0,
                (
                    review.decided_at.astimezone(UTC)
                    - review.candidate_created_at.astimezone(UTC)
                ).total_seconds(),
            )
            for review in snapshot.first_reviews
        ]

        failed_sources = sum(1 for item in source_runs if item.status == "failed")
        rate_limited_sources = sum(
            1 for item in source_runs if item.error_kind == "rate_limit"
        )
        unavailable_sources = sum(
            1 for item in source_runs if item.capability == "unavailable"
        )
        limited_sources = sum(
            1 for item in source_runs if item.capability == "limited"
        )

        total_run_candidates = sum(run.candidates_seen for run in runs)
        total_source_candidates = sum(item.candidate_count for item in source_runs)

        unavailable = {
            "missing_contribution_audit_yield": {
                "status": "unavailable",
                "reason": "requires the missing-contribution audit capability tracked in #64",
            },
            "drift_reconciliation_findings": {
                "status": "unavailable",
                "reason": "requires reconciliation findings tracked in #66",
            },
            "false_positive_false_negative_labels": {
                "status": "unavailable",
                "reason": "requires curated eval or real-world evidence labels not yet persisted",
            },
            "dry_run_to_publish_conversion": {
                "status": "unavailable",
                "reason": (
                    "dry-run candidates are intentionally not persisted and there is no "
                    "safe run-to-publication correlation; this metric must never be a "
                    "publication target"
                ),
            },
        }

        return {
            "definitions_version": self.DEFINITIONS_VERSION,
            "generated_at": as_of.isoformat(),
            "privacy": {
                "scope": "local aggregate product-quality metrics",
                "excluded_fields": [
                    "candidate_id",
                    "source_id",
                    "title",
                    "description",
                    "url",
                    "evidence",
                    "tokens",
                ],
                "note": (
                    "These metrics describe discovery/review quality; they are not "
                    "targets for automatic approval or publication."
                ),
            },
            "candidates": {
                "total": len(candidates),
                "by_source_type": _counts(
                    [candidate.source_type for candidate in candidates]
                ),
                "by_adapter": _counts([candidate.adapter for candidate in candidates]),
                "by_type": _counts(
                    [candidate.contribution_type for candidate in candidates]
                ),
                "by_state": _counts([candidate.state for candidate in candidates]),
                "per_run": _ratio(
                    total_run_candidates,
                    len(runs),
                    definition=(
                        "sum of persisted discovery-run candidates_seen / "
                        "persisted discovery runs"
                    ),
                ),
                "per_source_execution": _ratio(
                    total_source_candidates,
                    len(source_runs),
                    definition=(
                        "sum of source execution candidate counts / "
                        "persisted source executions"
                    ),
                ),
            },
            "eligibility": {
                "eligible_count": eligible,
                "noise_count": noise,
                "unresolved_count": len(candidates) - eligible - noise,
                "eligible_rate": _ratio(
                    eligible,
                    eligible + noise,
                    definition=(
                        "reviewable/approved/deferred/published non-exact candidates / "
                        "(those candidates + rejected/blocked-duplicate candidates); "
                        "unresolved discovered candidates are excluded"
                    ),
                ),
            },
            "duplicates": {
                "exact_rate": _ratio(
                    exact_duplicates,
                    len(candidates),
                    definition="exact duplicate candidates / all persisted candidates",
                ),
                "likely_rate": _ratio(
                    likely_duplicates,
                    len(candidates),
                    definition="likely duplicate candidates / all persisted candidates",
                ),
            },
            "reviews": {
                "action_count": len(reviews),
                "approve_rate": _ratio(
                    review_counts["approve"],
                    len(reviews),
                    definition="approve review actions / all review actions",
                ),
                "reject_rate": _ratio(
                    review_counts["reject"],
                    len(reviews),
                    definition="reject review actions / all review actions",
                ),
                "defer_rate": _ratio(
                    review_counts["defer"],
                    len(reviews),
                    definition="defer review actions / all review actions",
                ),
                "edit_rate": _ratio(
                    edited_reviews,
                    len(reviews),
                    definition=(
                        "review actions with one or more edited fields / all review actions"
                    ),
                ),
                "acceptance_by_adapter": _acceptance_by(
                    snapshot.latest_reviews, "adapter"
                ),
                "acceptance_by_type": _acceptance_by(
                    snapshot.latest_reviews, "contribution_type"
                ),
                "queue": {
                    "count": len(queued),
                    "age": _duration_summary(
                        queue_ages,
                        definition=(
                            "age since the queued candidate's latest lifecycle update; "
                            "states review_ready and deferred only"
                        ),
                    ),
                },
                "time_to_first_decision": _duration_summary(
                    first_decision_times,
                    definition=(
                        "first persisted review decision timestamp - "
                        "candidate creation timestamp"
                    ),
                ),
            },
            "source_executions": {
                "total": len(source_runs),
                "by_source_type": _counts([item.source_type for item in source_runs]),
                "by_adapter": _counts([item.adapter for item in source_runs]),
                "failure_rate": _ratio(
                    failed_sources,
                    len(source_runs),
                    definition=(
                        "failed source executions / all persisted source executions"
                    ),
                ),
                "rate_limit_rate": _ratio(
                    rate_limited_sources,
                    len(source_runs),
                    definition=(
                        "source executions classified with rate_limit / "
                        "all persisted source executions"
                    ),
                ),
                "unavailable_capability_rate": _ratio(
                    unavailable_sources,
                    len(source_runs),
                    definition=(
                        "source executions with unavailable capability / "
                        "all persisted source executions"
                    ),
                ),
                "limited_capability_rate": _ratio(
                    limited_sources,
                    len(source_runs),
                    definition=(
                        "source executions with limited capability / "
                        "all persisted source executions"
                    ),
                ),
            },
            "runs": {
                "total": len(runs),
                "by_status": _counts([run.status for run in runs]),
                "dry_run_count": sum(1 for run in runs if run.dry_run),
            },
            "unavailable": unavailable,
        }
