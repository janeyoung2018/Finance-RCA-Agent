"""
Utilities to normalize data structures for JSON serialization.
"""

from typing import Any

import numpy as np


def ensure_serializable(obj: Any) -> Any:
    """
    Recursively convert numpy/pandas scalars to native Python types.
    """
    if isinstance(obj, dict):
        return {k: ensure_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ensure_serializable(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(ensure_serializable(v) for v in obj)

    # numpy scalar to Python scalar
    if isinstance(obj, (np.generic,)):
        return obj.item()

    return obj
