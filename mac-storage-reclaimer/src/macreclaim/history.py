"""Append-only log of what macreclaim has deleted."""

from __future__ import annotations

import datetime
from pathlib import Path

LOG_DIR = Path("~/.macreclaim").expanduser()
LOG_FILE = LOG_DIR / "history.log"


def log_deletion(category_id: str, path: Path, freed_bytes: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    with LOG_FILE.open("a") as fh:
        fh.write(f"{timestamp}\t{category_id}\t{freed_bytes}\t{path}\n")
