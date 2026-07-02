"""The self-contained coordination store (SQLite in WAL mode).

This is the platform we code ourselves, so the framework needs no external
service. The atomic claim is a transactional conditional update, giving
exactly-one-winner semantics (E10) with genuine contention when many agents
compete. An optional Postgres adapter can implement the same small surface
later; nothing here depends on it.

Tables: tasks, agents, events (append-only telemetry), attempts (reliability).
Task statuses: CREATED, ADVERTISED, CLAIMED, EXECUTING, COMPLETED, FAILED,
INFEASIBLE, STALLED.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id    TEXT PRIMARY KEY,
    envelope   TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'CREATED',
    claimed_by TEXT,
    run_id     TEXT,
    condition  TEXT,
    created_at REAL,
    updated_at REAL
);
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    profile  TEXT NOT NULL,
    run_id   TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    run_id     TEXT,
    condition  TEXT,
    task_id    TEXT,
    agent_id   TEXT,
    event_type TEXT NOT NULL,
    payload    TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    task_id  TEXT,
    domain   TEXT,
    success  INTEGER NOT NULL,
    quality  REAL,
    ts       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_attempts_agent ON attempts(agent_id);
"""


class Store:
    """A SQLite-backed coordination store.

    Each method opens a short-lived connection, so the store is safe to share
    across threads and processes: every caller gets its own connection to the
    same database file, and WAL plus a generous busy timeout handle contention.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None means autocommit, so we manage transactions
        # explicitly with BEGIN IMMEDIATE for the atomic claim.
        conn = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(SCHEMA)
        finally:
            conn.close()

    # -- writes ---------------------------------------------------------------

    def add_agent(self, agent_id: str, profile: dict[str, Any], run_id: str | None = None) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO agents(agent_id, profile, run_id) VALUES (?, ?, ?)",
                (agent_id, json.dumps(profile), run_id),
            )
        finally:
            conn.close()

    def add_task(
        self,
        task_id: str,
        envelope: dict[str, Any],
        run_id: str | None = None,
        condition: str | None = None,
        status: str = "CREATED",
    ) -> None:
        now = time.time()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tasks"
                "(task_id, envelope, status, run_id, condition, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, json.dumps(envelope), status, run_id, condition, now, now),
            )
        finally:
            conn.close()

    def set_status(self, task_id: str, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
                (status, time.time(), task_id),
            )
        finally:
            conn.close()

    def advertise(self, task_id: str) -> None:
        self.set_status(task_id, "ADVERTISED")

    def claim(self, task_id: str, agent_id: str) -> bool:
        """Atomic claim (E10). Returns True iff this agent won the task.

        The conditional update only succeeds while the task is still ADVERTISED,
        so under contention exactly one caller changes a row and wins.
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE tasks SET status='CLAIMED', claimed_by=?, updated_at=? "
                "WHERE task_id=? AND status='ADVERTISED'",
                (agent_id, time.time(), task_id),
            )
            won = cur.rowcount == 1
            conn.execute("COMMIT")
            return won
        except sqlite3.OperationalError:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def append_event(
        self,
        event_type: str,
        task_id: str | None = None,
        agent_id: str | None = None,
        payload: dict[str, Any] | None = None,
        run_id: str | None = None,
        condition: str | None = None,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO events(ts, run_id, condition, task_id, agent_id, event_type, payload)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    run_id,
                    condition,
                    task_id,
                    agent_id,
                    event_type,
                    json.dumps(payload or {}),
                ),
            )
        finally:
            conn.close()

    def record_attempt(
        self,
        agent_id: str,
        success: bool,
        task_id: str | None = None,
        domain: str | None = None,
        quality: float | None = None,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO attempts(agent_id, task_id, domain, success, quality, ts)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (agent_id, task_id, domain, 1 if success else 0, quality, time.time()),
            )
        finally:
            conn.close()

    # -- reads ----------------------------------------------------------------

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def advertised_tasks(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM tasks WHERE status='ADVERTISED'").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def count_by_status(self) -> dict[str, int]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM tasks GROUP BY status"
            ).fetchall()
            return {r["status"]: r["n"] for r in rows}
        finally:
            conn.close()

    def event_count(self, event_type: str | None = None) -> int:
        conn = self._connect()
        try:
            if event_type is None:
                row = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM events WHERE event_type=?", (event_type,)
                ).fetchone()
            return int(row["n"])
        finally:
            conn.close()

    def reliability(self, agent_id: str, window: int = 20) -> float:
        """Laplace smoothed success ratio over the most recent ``window`` attempts."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT success FROM attempts WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                (agent_id, window),
            ).fetchall()
            s = sum(r["success"] for r in rows)
            n = len(rows)
            return (s + 1) / (n + 2)
        finally:
            conn.close()
