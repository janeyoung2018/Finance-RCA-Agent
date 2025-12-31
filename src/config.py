from pathlib import Path

# Project root is two levels up from this file (src/config.py -> src -> repo root)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Default settings for RCA runs
DEFAULT_COMPARISON = "plan"  # options: plan | prior
TOP_CONTRIBUTORS = 5
