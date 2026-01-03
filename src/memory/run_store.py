"""
Durable run store for RCA jobs backed by SQLite.

Keeps the simple in-memory API while persisting runs to disk so
background jobs survive process restarts.
"""

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import List, Optional

from fastapi.encoders import jsonable_encoder

from src.config import DATA_DIR


@dataclass
class RunRecord:
    run_id: str
    status: str
    message: str
    payload: dict = field(default_factory=dict)
    result: Optional[dict] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())


class RunStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        env_path = os.getenv("RUN_STORE_PATH")
        self.db_path = Path(env_path) if env_path else (Path(db_path) if db_path else DATA_DIR / "run_store.sqlite")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_records (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT,
                    result TEXT,
                    created_at REAL,
                    updated_at REAL
                )
                """
            )
            self._ensure_columns(conn)
            conn.commit()

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        """Add new columns to existing db without destructive migrations."""
        conn.row_factory = sqlite3.Row
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(run_records)")}  # type: ignore[index]
        required = {
            "run_id",
            "status",
            "message",
            "payload",
            "result",
            "created_at",
            "updated_at",
        }
        missing = required - columns
        for col in missing:
            if col in {"created_at", "updated_at"}:
                conn.execute(f"ALTER TABLE run_records ADD COLUMN {col} REAL")
            else:
                conn.execute(f"ALTER TABLE run_records ADD COLUMN {col} TEXT")

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        result = json.loads(row["result"]) if row["result"] else None
        record = RunRecord(
            run_id=row["run_id"],
            status=row["status"],
            message=row["message"],
            payload=payload,
            result=result,
            created_at=row["created_at"] or time.time(),
            updated_at=row["updated_at"] or time.time(),
        )
        return record

    def upsert(self, record: RunRecord) -> None:
        payload = jsonable_encoder(record.payload) if record.payload is not None else {}
        result = jsonable_encoder(record.result) if record.result is not None else None
        now = time.time()

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                "SELECT run_id, status, message, payload, result, created_at, updated_at FROM run_records WHERE run_id = ?",
                (record.run_id,),
            ).fetchone()

            created_at = record.created_at or now
            if existing:
                existing_record = self._row_to_record(existing)
                payload = payload or existing_record.payload
                result = result if result is not None else existing_record.result
                created_at = existing_record.created_at

            conn.execute(
                """
                INSERT INTO run_records (run_id, status, message, payload, result, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    payload=excluded.payload,
                    result=excluded.result,
                    updated_at=excluded.updated_at
                """,
                (
                    record.run_id,
                    record.status,
                    record.message,
                    json.dumps(payload) if payload is not None else None,
                    json.dumps(result) if result is not None else None,
                    created_at,
                    now,
                ),
            )
            conn.commit()

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT run_id, status, message, payload, result, created_at, updated_at FROM run_records WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def list_runs(self, limit: int = 20, offset: int = 0, status: Optional[str] = None) -> List[RunRecord]:
        query = "SELECT run_id, status, message, payload, result, created_at, updated_at FROM run_records"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_record(row) for row in rows]

    def count_runs(self, status: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) as count FROM run_records"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, tuple(params)).fetchone()
            return int(row["count"]) if row else 0


# Singleton instance for simple use inside the app
run_store = RunStore()
