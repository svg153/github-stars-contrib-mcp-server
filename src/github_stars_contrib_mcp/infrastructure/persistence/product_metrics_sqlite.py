"""Privacy-safe SQLite read model for product/discovery quality metrics."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from github_stars_contrib_mcp.domain.product_metrics import (
    CandidateMetricFact,
    ProductMetricsSnapshot,
    ReviewMetricFact,
    RunMetricFact,
    RunSourceMetricFact,
)


def _datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _dimension(value: Any, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    normalized = str(value).strip().lower()
    return normalized[:64] if normalized else fallback


def _json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _review_fact(row: sqlite3.Row) -> ReviewMetricFact:
    provenance = _json_object(row["provenance_json"])
    edited = _json_object(row["edited_fields_json"])
    created_at = _datetime(row["candidate_created_at"])
    decided_at = _datetime(row["decided_at"])
    if created_at is None or decided_at is None:
        raise ValueError("review metric timestamps must be present")
    return ReviewMetricFact(
        decision=_dimension(row["decision"]),
        edited=bool(edited),
        source_type=_dimension(row["source_type"]),
        adapter=_dimension(provenance.get("adapter")),
        contribution_type=_dimension(row["contribution_type"]),
        candidate_created_at=created_at,
        decided_at=decided_at,
    )


class SQLiteProductMetricsQuery:
    """Read only safe dimensions/counts from the discovery SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def snapshot(self) -> ProductMetricsSnapshot:
        if not self.db_path.exists():
            return ProductMetricsSnapshot()

        connection = self._connect()
        try:
            candidate_rows = connection.execute(
                """
                SELECT
                    s.source_type,
                    c.contribution_type,
                    c.state,
                    c.duplicate_state,
                    c.created_at,
                    c.updated_at,
                    c.provenance_json
                FROM candidates c
                LEFT JOIN sources s ON s.id = c.source_id
                ORDER BY c.id
                """
            ).fetchall()
            review_rows = connection.execute(
                """
                SELECT
                    r.id,
                    r.candidate_id,
                    r.decision,
                    r.edited_fields_json,
                    r.decided_at,
                    c.created_at AS candidate_created_at,
                    c.contribution_type,
                    c.provenance_json,
                    s.source_type
                FROM reviews r
                JOIN candidates c ON c.id = r.candidate_id
                LEFT JOIN sources s ON s.id = c.source_id
                ORDER BY r.candidate_id, r.decided_at, r.id
                """
            ).fetchall()
            run_rows = connection.execute(
                """
                SELECT status, summary_json, started_at, finished_at
                FROM discovery_runs
                ORDER BY started_at, id
                """
            ).fetchall()
            source_types = {
                row["id"]: _dimension(row["source_type"])
                for row in connection.execute(
                    "SELECT id, source_type FROM sources"
                ).fetchall()
            }
        finally:
            connection.close()

        candidates: list[CandidateMetricFact] = []
        for row in candidate_rows:
            provenance = _json_object(row["provenance_json"])
            created_at = _datetime(row["created_at"])
            updated_at = _datetime(row["updated_at"])
            if created_at is None or updated_at is None:
                continue
            candidates.append(
                CandidateMetricFact(
                    source_type=_dimension(row["source_type"]),
                    adapter=_dimension(provenance.get("adapter")),
                    contribution_type=_dimension(row["contribution_type"]),
                    state=_dimension(row["state"]),
                    duplicate_state=_dimension(row["duplicate_state"]),
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )

        review_actions: list[ReviewMetricFact] = []
        first_reviews: list[ReviewMetricFact] = []
        latest_reviews: list[ReviewMetricFact] = []
        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in review_rows:
            grouped.setdefault(str(row["candidate_id"]), []).append(row)
            review_actions.append(_review_fact(row))
        for rows in grouped.values():
            first_reviews.append(_review_fact(rows[0]))
            latest_reviews.append(_review_fact(rows[-1]))

        runs: list[RunMetricFact] = []
        run_sources: list[RunSourceMetricFact] = []
        for row in run_rows:
            summary = _json_object(row["summary_json"])
            started_at = _datetime(row["started_at"])
            if started_at is None:
                continue
            runs.append(
                RunMetricFact(
                    status=_dimension(row["status"]),
                    dry_run=bool(summary.get("dry_run", False)),
                    candidates_seen=max(0, int(summary.get("candidates_seen", 0) or 0)),
                    source_count=max(0, int(summary.get("sources_total", 0) or 0)),
                    started_at=started_at,
                    finished_at=_datetime(row["finished_at"]),
                )
            )
            sources = summary.get("sources", {})
            if not isinstance(sources, dict):
                continue
            for source_id, raw in sources.items():
                payload = raw if isinstance(raw, dict) else {}
                run_sources.append(
                    RunSourceMetricFact(
                        source_type=source_types.get(str(source_id), "unknown"),
                        adapter=_dimension(payload.get("adapter")),
                        capability=_dimension(payload.get("capability")),
                        status=_dimension(payload.get("status")),
                        error_kind=_dimension(payload.get("error_kind"), fallback="none"),
                        candidate_count=max(0, int(payload.get("candidates", 0) or 0)),
                    )
                )

        return ProductMetricsSnapshot(
            candidates=tuple(candidates),
            review_actions=tuple(review_actions),
            latest_reviews=tuple(latest_reviews),
            first_reviews=tuple(first_reviews),
            run_sources=tuple(run_sources),
            runs=tuple(runs),
        )
