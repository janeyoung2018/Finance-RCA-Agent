import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

# Load .env once at module import (no override of existing env vars).
if load_dotenv:
    load_dotenv()

# Project root is two levels up from this file (src/config.py -> src -> repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

def _int_env(var_name: str, default: int) -> int:
    try:
        return int(os.getenv(var_name, default))
    except (TypeError, ValueError):
        return default

# Default settings for RCA runs
DEFAULT_COMPARISON = "plan"  # options: plan | prior
TOP_CONTRIBUTORS = 5

# Security and operational hardening
API_KEY = os.getenv("API_KEY")
RATE_LIMIT_REQUESTS = _int_env("RATE_LIMIT_REQUESTS", 60)
RATE_LIMIT_WINDOW_SECONDS = _int_env("RATE_LIMIT_WINDOW_SECONDS", 60)
MAX_CONCURRENT_RUNS = max(1, _int_env("MAX_CONCURRENT_RUNS", 2))
MAX_QUEUED_RUNS = max(MAX_CONCURRENT_RUNS, _int_env("MAX_QUEUED_RUNS", 10))
