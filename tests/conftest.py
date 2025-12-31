"""Test configuration to ensure src package is importable when running pytest from repo root."""

import sys
from pathlib import Path

# Add repository root to sys.path for src imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
