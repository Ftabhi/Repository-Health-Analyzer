"""Utility helper functions."""
from datetime import datetime


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    from pathlib import Path
    Path(path).mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
