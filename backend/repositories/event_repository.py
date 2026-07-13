"""SQLite-backed event repository with monotonic per-run sequence.

The repository is the single source of truth for run events.  Events are
written in the same logical transaction as run state changes and read back
by SSE handlers using ``list_after``.

Storing events as a single append-only table per run allows:

* Page refresh to resume from ``Last-Event-ID``.
* Multi-process deployments to share state via SQLite/Postgres.
* Replay of the full event history for debugging.

The repository is intentionally storage-agnostic: callers depend on
``EventRepository`` and ``RunEvent``, not on SQLite.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunEvent:
    """A durable workbench event.

    Events are intentionally lightweight: ``payload`` is a free-form dict so
    we can evolve schemas without migrating the database.  Discrimination is
    done via ``event_type``.
    """

    __slots__ = (
        "event_id",
        "run_id",
        "sequence",
        "event_type",
        "node",
        "agent",
        "status",
        "message",
        "payload",
        "created_at",
    )

    def __init__(
        self,
        *,
        event_id: str,
        run_id: str,
        sequence: int,
        event_type: str,
        node: str = "",
        agent: str = "",
        status: str = "",
        message: str = "",
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> None:
        self.event_id = event_id
        self.run_id = run_id
        self.sequence = sequence
        self.event_type = event_type
        self.node = node
        self.agent = agent
        self.status = status
        self.message = message
        self.payload = payload or {}
        self.created_at = created_at or utc_now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "node": self.node,
            "agent": self.agent,
            "status": self.status,
            "message": self.message,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class EventRepository:
    """SQLite-backed event store.

    Each run has its own JSONL file for backward compatibility; the SQLite
    database is the authoritative source.  Concurrent writers are
    serialized via a per-process lock; multi-process deployments should
    switch to Postgres.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage txns explicitly
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    node TEXT,
                    agent TEXT,
                    status TEXT,
                    message TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id, sequence)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_run_events_run_seq "
                "ON run_events(run_id, sequence)"
            )

    def append(self, event: RunEvent) -> RunEvent:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO run_events (
                    event_id, run_id, sequence, event_type,
                    node, agent, status, message,
                    payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.sequence,
                    event.event_type,
                    event.node,
                    event.agent,
                    event.status,
                    event.message,
                    _dump_json(event.payload),
                    event.created_at,
                ),
            )
        return event

    def next_sequence(self, run_id: str) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS value "
                "FROM run_events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return int(row["value"]) + 1

    def list_after(
        self,
        *,
        run_id: str,
        after: int = 0,
        limit: int = 500,
    ) -> list[RunEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM run_events
                WHERE run_id = ? AND sequence > ?
                ORDER BY sequence ASC
                LIMIT ?
                """,
                (run_id, after, limit),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def list_all(self, run_id: str) -> list[RunEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM run_events WHERE run_id = ? "
                "ORDER BY sequence ASC",
                (run_id,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def replay(self, run_id: str) -> Iterable[RunEvent]:
        yield from self.list_all(run_id)


def _dump_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)


def _row_to_event(row: sqlite3.Row) -> RunEvent:
    import json

    payload: dict[str, Any] = {}
    raw = row["payload_json"]
    if raw:
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            payload = {}
    return RunEvent(
        event_id=row["event_id"],
        run_id=row["run_id"],
        sequence=int(row["sequence"]),
        event_type=row["event_type"],
        node=row["node"] or "",
        agent=row["agent"] or "",
        status=row["status"] or "",
        message=row["message"] or "",
        payload=payload,
        created_at=row["created_at"],
    )


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:16]}"
