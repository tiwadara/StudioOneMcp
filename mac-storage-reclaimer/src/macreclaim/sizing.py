"""Directory/file size scanning helpers."""

from __future__ import annotations

import os
from pathlib import Path

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def human_readable(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in _UNITS:
        if size < 1024 or unit == _UNITS[-1]:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


def parse_size(text: str) -> int:
    """Parse a human size string like '500MB', '1.5GB', '2048' into bytes."""
    text = text.strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in sorted(multipliers.items(), key=lambda kv: -len(kv[0])):
        if text.endswith(suffix):
            number = text[: -len(suffix)].strip()
            return int(float(number) * mult)
    return int(float(text))


def dir_size(path: Path) -> int:
    """Sum of apparent file sizes under `path`, following no symlinks.

    Silently skips entries that vanish or are unreadable (permission
    errors, race conditions) rather than aborting the whole scan.
    """
    total = 0
    try:
        if path.is_symlink():
            return 0
        if path.is_file():
            return path.stat(follow_symlinks=False).st_size
        if not path.is_dir():
            return 0
    except OSError:
        return 0

    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def path_size(path: Path) -> int:
    """Size of a single file or directory tree."""
    return dir_size(path)
