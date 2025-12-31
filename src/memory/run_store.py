"""
Minimal in-memory run store for RCA jobs.

Replace with durable storage (DB/Redis) in production.
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional

from fastapi.encoders import jsonable_encoder


@dataclass
class RunRecord:
    run_id: str
    status: str
    message: str
    payload: dict = field(default_factory=dict)
    result: Optional[dict] = None


class RunStore:
    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = Lock()

    def upsert(self, record: RunRecord) -> None:
        with self._lock:
            existing = self._runs.get(record.run_id)
            payload = jsonable_encoder(record.payload) if record.payload is not None else {}
            result = jsonable_encoder(record.result) if record.result is not None else None
            if existing:
                # merge updates while keeping last known payload/result
                payload = payload or existing.payload
                result = result if result is not None else existing.result
                self._runs[record.run_id] = RunRecord(
                    run_id=record.run_id,
                    status=record.status,
                    message=record.message,
                    payload=payload,
                    result=result,
                )
            else:
                self._runs[record.run_id] = RunRecord(
                    run_id=record.run_id,
                    status=record.status,
                    message=record.message,
                    payload=payload,
                    result=result,
                )

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._lock:
            return self._runs.get(run_id)


# Singleton instance for simple use inside the app
run_store = RunStore()
