"""Ad-hoc scans that don't fit the fixed category list: node_modules sprawl
and plain "what's big" file search.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .sizing import dir_size

# Directories we never descend into while searching, because they're either
# huge+irrelevant or another category already covers them.
_SKIP_DIR_NAMES = {".git", "node_modules", ".Trash", "Library"}


@dataclass
class NodeModulesHit:
    path: Path
    size_bytes: int
    mtime: float


def find_node_modules(root: Path) -> list[NodeModulesHit]:
    """Find node_modules directories under `root`, without descending into
    ones already found (a nested node_modules is counted in its parent's
    size, not listed separately)."""
    hits: list[NodeModulesHit] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if entry.name == "node_modules":
                        try:
                            mtime = entry.stat(follow_symlinks=False).st_mtime
                        except OSError:
                            mtime = 0.0
                        hits.append(
                            NodeModulesHit(
                                path=Path(entry.path),
                                size_bytes=dir_size(Path(entry.path)),
                                mtime=mtime,
                            )
                        )
                        continue
                    if entry.name in _SKIP_DIR_NAMES or entry.name.startswith("."):
                        continue
                    stack.append(Path(entry.path))
        except OSError:
            continue
    hits.sort(key=lambda h: h.size_bytes, reverse=True)
    return hits


@dataclass
class LargeFileHit:
    path: Path
    size_bytes: int


def find_large_files(root: Path, min_size_bytes: int) -> list[LargeFileHit]:
    hits: list[LargeFileHit] = []
    stack = [root]
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
                            size = entry.stat(follow_symlinks=False).st_size
                            if size >= min_size_bytes:
                                hits.append(LargeFileHit(Path(entry.path), size))
                    except OSError:
                        continue
        except OSError:
            continue
    hits.sort(key=lambda h: h.size_bytes, reverse=True)
    return hits
