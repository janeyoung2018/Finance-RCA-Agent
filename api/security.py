import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, DefaultDict

from fastapi import Header, HTTPException, Request

from src.config import API_KEY, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

_request_log: DefaultDict[str, Deque[float]] = defaultdict(deque)
_lock = Lock()


def require_api_key(x_api_key: str = Header(None)) -> None:
    if not API_KEY:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def rate_limiter(request: Request) -> None:
    if RATE_LIMIT_REQUESTS <= 0:
        return

    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    identifier = request.client.host if request.client else "unknown"

    with _lock:
        entries = _request_log[identifier]
        while entries and entries[0] < window_start:
            entries.popleft()
        if len(entries) >= RATE_LIMIT_REQUESTS:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry later.")
        entries.append(now)
