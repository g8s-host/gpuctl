"""SQLite-backed desired-state store for the SSH backend.

Pure storage. The reconciler/health-check logic decides what to *do* with the
state; this module only persists it.

Schema is created on first connect; small enough to keep inline (no migration
framework). If you change a column, write a small migration in
``_migrate()``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from gpuctl.backend.errors import JobAlreadyExistsError, JobNotFoundError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    namespace       TEXT NOT NULL,
    kind            TEXT NOT NULL,
    node            TEXT NOT NULL,
    container_name  TEXT NOT NULL,
    container_id    TEXT,
    spec_json       TEXT NOT NULL,
    labels_json     TEXT NOT NULL,
    status          TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(name, namespace)
);
CREATE INDEX IF NOT EXISTS idx_jobs_namespace ON jobs(namespace);
CREATE INDEX IF NOT EXISTS idx_jobs_node      ON jobs(node);

CREATE TABLE IF NOT EXISTS nodes_runtime (
    name             TEXT PRIMARY KEY,
    last_seen        TEXT NOT NULL,
    gpu_count_real   INTEGER,
    docker_version   TEXT
);
"""


@dataclass(frozen=True)
class JobRow:
    id: int
    name: str
    namespace: str
    kind: str
    node: str
    container_name: str
    container_id: str | None
    spec_json: str
    labels_json: str
    status: str
    created_at: str
    updated_at: str

    @property
    def labels(self) -> dict[str, str]:
        return json.loads(self.labels_json)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StateStore:
    """Thread-safe SQLite wrapper. Designed for single-process CLI use,
    but a coarse RLock guards multi-thread access from ``list_jobs`` fanout.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = (
                Path(os.environ.get("GPUCTL_STATE_DIR", "~/.gpuctl")).expanduser()
                / "state.db"
            )
        self._path = Path(db_path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self._path),
            isolation_level=None,  # autocommit; we manage txns explicitly
            check_same_thread=False,
            timeout=5.0,
        )
        self._conn.row_factory = sqlite3.Row
        # WAL: better concurrent readers/single writer; busy_timeout: wait on lock.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        # File perms: 0600 — contains internal scheduling state, not secrets,
        # but be defensive.
        try:
            os.chmod(self._path, 0o600)
        except OSError:  # pragma: no cover (Windows / unusual fs)
            pass
        self._migrate()

    def _migrate(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    # ---------- jobs ----------

    def insert_job(
        self,
        *,
        name: str,
        namespace: str,
        kind: str,
        node: str,
        container_name: str,
        spec_json: str,
        labels: dict[str, str],
        status: str,
    ) -> JobRow:
        ts = _now()
        try:
            with self._tx() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO jobs (
                        name, namespace, kind, node, container_name,
                        container_id, spec_json, labels_json, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        namespace,
                        kind,
                        node,
                        container_name,
                        spec_json,
                        json.dumps(labels, sort_keys=True),
                        status,
                        ts,
                        ts,
                    ),
                )
                row_id = cur.lastrowid
        except sqlite3.IntegrityError as exc:
            raise JobAlreadyExistsError(name, namespace) from exc
        return self._get_by_id(row_id)

    def set_container_id(self, job_id: int, container_id: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE jobs SET container_id=?, updated_at=? WHERE id=?",
                (container_id, _now(), job_id),
            )

    def update_status(self, name: str, namespace: str, status: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE jobs SET status=?, updated_at=? WHERE name=? AND namespace=?",
                (status, _now(), name, namespace),
            )

    def delete_job(self, name: str, namespace: str) -> None:
        with self._tx() as conn:
            conn.execute(
                "DELETE FROM jobs WHERE name=? AND namespace=?", (name, namespace)
            )

    def get_job(self, name: str, namespace: str) -> JobRow:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE name=? AND namespace=?", (name, namespace)
            ).fetchone()
        if row is None:
            raise JobNotFoundError(name, namespace)
        return _row(row)

    def list_jobs(
        self, namespace: str, labels: dict[str, str] | None = None
    ) -> list[JobRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE namespace=? ORDER BY created_at DESC",
                (namespace,),
            ).fetchall()
        result = [_row(r) for r in rows]
        if labels:
            return [r for r in result if _labels_match(r.labels, labels)]
        return result

    def list_jobs_on_node(self, node: str) -> list[JobRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE node=?", (node,)
            ).fetchall()
        return [_row(r) for r in rows]

    def used_gpus_per_node(self) -> dict[str, int]:
        """Sum gpu requirements per node from currently-tracked specs.

        Reads the gpu_count out of each row's spec_json. Cheap for small
        clusters (linear over rows); revisit if we ever go past O(10^4) jobs.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT node, spec_json FROM jobs WHERE status NOT IN ('Succeeded','Failed','Lost')"
            ).fetchall()
        usage: dict[str, int] = {}
        for r in rows:
            try:
                spec = json.loads(r["spec_json"])
            except json.JSONDecodeError:
                continue
            usage[r["node"]] = usage.get(r["node"], 0) + int(spec.get("gpu_count", 0))
        return usage

    # ---------- nodes_runtime ----------

    def touch_node(
        self, name: str, *, gpu_count_real: int | None, docker_version: str | None
    ) -> None:
        ts = _now()
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO nodes_runtime (name, last_seen, gpu_count_real, docker_version)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    last_seen=excluded.last_seen,
                    gpu_count_real=excluded.gpu_count_real,
                    docker_version=excluded.docker_version
                """,
                (name, ts, gpu_count_real, docker_version),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # internal -----

    def _get_by_id(self, job_id: int) -> JobRow:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE id=?", (job_id,)
            ).fetchone()
        if row is None:  # pragma: no cover (would mean txn lost between INSERT and SELECT)
            raise RuntimeError(f"row {job_id} not found after insert")
        return _row(row)


def _row(r: sqlite3.Row) -> JobRow:
    return JobRow(
        id=r["id"],
        name=r["name"],
        namespace=r["namespace"],
        kind=r["kind"],
        node=r["node"],
        container_name=r["container_name"],
        container_id=r["container_id"],
        spec_json=r["spec_json"],
        labels_json=r["labels_json"],
        status=r["status"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def _labels_match(have: dict[str, str], want: dict[str, str]) -> bool:
    return all(have.get(k) == v for k, v in want.items())
