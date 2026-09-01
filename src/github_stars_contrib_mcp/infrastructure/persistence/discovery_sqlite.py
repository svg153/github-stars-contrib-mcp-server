"""SQLite persistence adapter for discovery state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from github_stars_contrib_mcp.domain.discovery import (
    CandidateContribution,
    CandidateState,
    DiscoveryRun,
    Evidence,
    ReviewDecision,
    SourceRecord,
)

SCHEMA_VERSION = 1


def _json_dumps(value: Any) -> str:
    """Serialize JSON fields deterministically for durable local state."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(value: str | None, default: Any) -> Any:
    return default if value is None else json.loads(value)


class SQLiteDiscoveryRepository:
    """Single local adapter implementing the discovery repository ports."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._active_connection: sqlite3.Connection | None = None
        self._bootstrap()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection_scope(self) -> Iterator[sqlite3.Connection]:
        if self._active_connection is not None:
            yield self._active_connection
            return

        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _bootstrap(self) -> None:
        with self._connection_scope() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    ownership TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    evidence_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cursors (
                    source_id TEXT PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
                    cursor_json TEXT
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                    external_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    contribution_type TEXT,
                    date TEXT,
                    state TEXT NOT NULL,
                    duplicate_state TEXT NOT NULL,
                    ownership_confidence REAL NOT NULL,
                    contribution_confidence REAL NOT NULL,
                    provenance_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                    source_item_id TEXT,
                    url TEXT,
                    text_excerpt TEXT,
                    data_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS discovery_runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    source_ids_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    edited_fields_json TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS publications (
                    candidate_id TEXT PRIMARY KEY REFERENCES candidates(id) ON DELETE CASCADE,
                    client_id TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            row = connection.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
                )
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(
                    f"Unsupported discovery schema version: {row['version']}"
                )

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Group repository operations into one atomic discovery transaction."""

        if self._active_connection is not None:
            raise RuntimeError("Nested discovery transactions are not supported")

        connection = self._connect()
        self._active_connection = connection
        try:
            connection.execute("BEGIN")
            yield
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._active_connection = None
            connection.close()

    def upsert_source(self, source: SourceRecord) -> SourceRecord:
        payload = source.model_dump(mode="json")
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO sources(
                    id, source_type, url, ownership, enabled, evidence_json,
                    metadata_json, created_at, updated_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_type=excluded.source_type,
                    url=excluded.url,
                    ownership=excluded.ownership,
                    enabled=excluded.enabled,
                    evidence_json=excluded.evidence_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at,
                    schema_version=excluded.schema_version
                """,
                (
                    payload["id"],
                    payload["source_type"],
                    payload["url"],
                    payload["ownership"],
                    int(payload["enabled"]),
                    _json_dumps(payload["evidence"]),
                    _json_dumps(payload["metadata"]),
                    payload["created_at"],
                    payload["updated_at"],
                    payload["schema_version"],
                ),
            )
        return source

    def get_source(self, source_id: str) -> SourceRecord | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            ).fetchone()
        if row is None:
            return None
        return SourceRecord.model_validate(
            {
                "id": row["id"],
                "source_type": row["source_type"],
                "url": row["url"],
                "ownership": row["ownership"],
                "enabled": bool(row["enabled"]),
                "evidence": _json_loads(row["evidence_json"], []),
                "metadata": _json_loads(row["metadata_json"], {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "schema_version": row["schema_version"],
            }
        )

    def list_sources(self, *, enabled_only: bool = False) -> list[SourceRecord]:
        query = "SELECT id FROM sources"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY id"
        with self._connection_scope() as connection:
            ids = [row["id"] for row in connection.execute(query).fetchall()]
        return [source for source_id in ids if (source := self.get_source(source_id))]

    def get_cursor(self, source_id: str) -> dict[str, Any] | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                "SELECT cursor_json FROM cursors WHERE source_id = ?", (source_id,)
            ).fetchone()
        if row is None or row["cursor_json"] is None:
            return None
        return json.loads(row["cursor_json"])

    def save_cursor(self, source_id: str, cursor: dict[str, Any] | None) -> None:
        payload = None if cursor is None else _json_dumps(cursor)
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO cursors(source_id, cursor_json) VALUES (?, ?)
                ON CONFLICT(source_id) DO UPDATE SET cursor_json=excluded.cursor_json
                """,
                (source_id, payload),
            )

    def save_candidate(
        self,
        candidate: CandidateContribution,
        evidence: Sequence[Evidence] = (),
    ) -> CandidateContribution:
        candidate_payload = candidate.model_dump(mode="json")
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO candidates(
                    id, source_id, external_id, title, url, description,
                    contribution_type, date, state, duplicate_state,
                    ownership_confidence, contribution_confidence,
                    provenance_json, created_at, updated_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id=excluded.source_id,
                    external_id=excluded.external_id,
                    title=excluded.title,
                    url=excluded.url,
                    description=excluded.description,
                    contribution_type=excluded.contribution_type,
                    date=excluded.date,
                    state=excluded.state,
                    duplicate_state=excluded.duplicate_state,
                    ownership_confidence=excluded.ownership_confidence,
                    contribution_confidence=excluded.contribution_confidence,
                    provenance_json=excluded.provenance_json,
                    updated_at=excluded.updated_at,
                    schema_version=excluded.schema_version
                """,
                (
                    candidate_payload["id"],
                    candidate_payload["source_id"],
                    candidate_payload["external_id"],
                    candidate_payload["title"],
                    candidate_payload["url"],
                    candidate_payload["description"],
                    candidate_payload["contribution_type"],
                    candidate_payload["date"],
                    candidate_payload["state"],
                    candidate_payload["duplicate_state"],
                    candidate_payload["ownership_confidence"],
                    candidate_payload["contribution_confidence"],
                    _json_dumps(candidate_payload["provenance"]),
                    candidate_payload["created_at"],
                    candidate_payload["updated_at"],
                    candidate_payload["schema_version"],
                ),
            )
            for item in evidence:
                payload = item.model_dump(mode="json")
                existing = connection.execute(
                    "SELECT candidate_id FROM evidence WHERE id = ?",
                    (payload["id"],),
                ).fetchone()
                if (
                    existing is not None
                    and existing["candidate_id"] != candidate_payload["id"]
                ):
                    raise ValueError(
                        "Evidence IDs are immutable across candidates: "
                        f"{payload['id']}"
                    )
                connection.execute(
                    """
                    INSERT INTO evidence(
                        id, candidate_id, source_id, source_item_id, url,
                        text_excerpt, data_json, captured_at, schema_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        candidate_id=excluded.candidate_id,
                        source_id=excluded.source_id,
                        source_item_id=excluded.source_item_id,
                        url=excluded.url,
                        text_excerpt=excluded.text_excerpt,
                        data_json=excluded.data_json,
                        captured_at=excluded.captured_at,
                        schema_version=excluded.schema_version
                    """,
                    (
                        payload["id"],
                        candidate_payload["id"],
                        payload["source_id"],
                        payload["source_item_id"],
                        payload["url"],
                        payload["text_excerpt"],
                        _json_dumps(payload["data"]),
                        payload["captured_at"],
                        payload["schema_version"],
                    ),
                )
        return candidate

    def get_candidate(self, candidate_id: str) -> CandidateContribution | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
        if row is None:
            return None
        return CandidateContribution.model_validate(
            {
                "id": row["id"],
                "source_id": row["source_id"],
                "external_id": row["external_id"],
                "title": row["title"],
                "url": row["url"],
                "description": row["description"],
                "contribution_type": row["contribution_type"],
                "date": row["date"],
                "state": row["state"],
                "duplicate_state": row["duplicate_state"],
                "ownership_confidence": row["ownership_confidence"],
                "contribution_confidence": row["contribution_confidence"],
                "provenance": _json_loads(row["provenance_json"], {}),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "schema_version": row["schema_version"],
            }
        )

    def list_candidates(
        self, *, states: set[CandidateState] | None = None
    ) -> list[CandidateContribution]:
        params: tuple[str, ...] = ()
        query = "SELECT id FROM candidates"
        if states:
            ordered = sorted(state.value for state in states)
            query += f" WHERE state IN ({','.join('?' for _ in ordered)})"
            params = tuple(ordered)
        query += " ORDER BY id"
        with self._connection_scope() as connection:
            ids = [row["id"] for row in connection.execute(query, params).fetchall()]
        return [
            candidate
            for candidate_id in ids
            if (candidate := self.get_candidate(candidate_id))
        ]

    def list_evidence(self, candidate_id: str) -> list[Evidence]:
        with self._connection_scope() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence WHERE candidate_id = ? ORDER BY id",
                (candidate_id,),
            ).fetchall()
        return [
            Evidence.model_validate(
                {
                    "id": row["id"],
                    "source_id": row["source_id"],
                    "source_item_id": row["source_item_id"],
                    "url": row["url"],
                    "text_excerpt": row["text_excerpt"],
                    "data": _json_loads(row["data_json"], {}),
                    "captured_at": row["captured_at"],
                    "schema_version": row["schema_version"],
                }
            )
            for row in rows
        ]

    def record_review(self, decision: ReviewDecision) -> None:
        payload = decision.model_dump(mode="json")
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO reviews(
                    candidate_id, decision, reason, edited_fields_json,
                    decided_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["candidate_id"],
                    payload["decision"],
                    payload["reason"],
                    _json_dumps(payload["edited_fields"]),
                    payload["decided_at"],
                    payload["schema_version"],
                ),
            )

    def record_publication(
        self, candidate_id: str, client_id: str, result: dict[str, Any]
    ) -> None:
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO publications(candidate_id, client_id, result_json)
                VALUES (?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    client_id=excluded.client_id,
                    result_json=excluded.result_json,
                    published_at=CURRENT_TIMESTAMP
                """,
                (candidate_id, client_id, _json_dumps(result)),
            )

    def save_run(self, run: DiscoveryRun) -> DiscoveryRun:
        payload = run.model_dump(mode="json")
        with self._connection_scope() as connection:
            connection.execute(
                """
                INSERT INTO discovery_runs(
                    id, status, source_ids_json, summary_json, errors_json,
                    started_at, finished_at, schema_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    source_ids_json=excluded.source_ids_json,
                    summary_json=excluded.summary_json,
                    errors_json=excluded.errors_json,
                    finished_at=excluded.finished_at,
                    schema_version=excluded.schema_version
                """,
                (
                    payload["id"],
                    payload["status"],
                    _json_dumps(payload["source_ids"]),
                    _json_dumps(payload["summary"]),
                    _json_dumps(payload["errors"]),
                    payload["started_at"],
                    payload["finished_at"],
                    payload["schema_version"],
                ),
            )
        return run

    def get_run(self, run_id: str) -> DiscoveryRun | None:
        with self._connection_scope() as connection:
            row = connection.execute(
                "SELECT * FROM discovery_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return DiscoveryRun.model_validate(
            {
                "id": row["id"],
                "status": row["status"],
                "source_ids": _json_loads(row["source_ids_json"], []),
                "summary": _json_loads(row["summary_json"], {}),
                "errors": _json_loads(row["errors_json"], []),
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "schema_version": row["schema_version"],
            }
        )
