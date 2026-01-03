"""
Durable run store for RCA jobs backed by SQLite.

Keeps the simple in-memory API while persisting runs to disk so
background jobs survive process restarts.
"""

import json
import sqlite3
from dataclasses import dataclass, field
import os
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi.encoders import jsonable_encoder

from src.config import DATA_DIR


@dataclass
class RunRecord:
    run_id: str
    status: str
    message: str
    payload: dict = field(default_factory=dict)
    result: Optional[dict] = None


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
                    result TEXT
                )
                """
            )
            conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        result = json.loads(row["result"]) if row["result"] else None
        return RunRecord(
            run_id=row["run_id"],
            status=row["status"],
            message=row["message"],
            payload=payload,
            result=result,
        )

    def upsert(self, record: RunRecord) -> None:
        payload = jsonable_encoder(record.payload) if record.payload is not None else {}
        result = jsonable_encoder(record.result) if record.result is not None else None

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                "SELECT run_id, status, message, payload, result FROM run_records WHERE run_id = ?",
                (record.run_id,),
            ).fetchone()

            if existing:
                existing_record = self._row_to_record(existing)
                payload = payload or existing_record.payload
                result = result if result is not None else existing_record.result

            conn.execute(
                """
                INSERT INTO run_records (run_id, status, message, payload, result)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    payload=excluded.payload,
                    result=excluded.result
                """,
                (
                    record.run_id,
                    record.status,
                    record.message,
                    json.dumps(payload) if payload is not None else None,
                    json.dumps(result) if result is not None else None,
                ),
            )
            conn.commit()

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT run_id, status, message, payload, result FROM run_records WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_record(row)


# Singleton instance for simple use inside the app
run_store = RunStore()
