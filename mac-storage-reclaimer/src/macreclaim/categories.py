"""Known reclaimable-space categories on macOS.

Each Category describes a location, how risky it is to delete, and (for
"manual" categories) which real tool owns cleaning it up instead of us.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

RISK_SAFE = "safe"
RISK_CAUTION = "caution"
RISK_MANUAL = "manual"


@dataclass
class Category:
    id: str
    name: str
    description: str
    risk: str
    # Glob patterns relative to $HOME, or absolute paths. Each match is a
    # candidate that gets removed in full (file or directory tree).
    patterns: list[str] = field(default_factory=list)
    manual_hint: Optional[str] = None
    # For categories whose location can't be expressed as a static glob
    # (e.g. "wherever `brew --cache` points").
    dynamic_paths: Optional[Callable[[], list[Path]]] = None

    def candidate_paths(self, home: Path) -> list[Path]:
        if self.dynamic_paths is not None:
            return [p for p in self.dynamic_paths() if p.exists()]
        found: list[Path] = []
        for pattern in self.patterns:
            base = Path(pattern)
            if base.is_absolute():
                found.extend(p for p in Path("/").glob(str(base.relative_to("/"))) if p.exists())
            else:
                found.extend(p for p in home.glob(pattern) if p.exists())
        return found


def _brew_cache_paths() -> list[Path]:
    brew = shutil.which("brew")
    if not brew:
        return []
    try:
        out = subprocess.run(
            [brew, "--cache"], capture_output=True, text=True, timeout=10, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return []
    return [Path(out)] if out else []


def _docker_data_paths() -> list[Path]:
    # Docker Desktop's backing disk image on macOS.
    candidates = [
        Path("~/Library/Containers/com.docker.docker/Data/vms/0/data")
        .expanduser(),
        Path("~/Library/Group Containers/group.com.docker/Data/vms/0/data")
        .expanduser(),
    ]
    return [p for p in candidates if p.exists()]


CATEGORIES: list[Category] = [
    Category(
        id="user-caches",
        name="Application caches",
        description="~/Library/Caches/* — per-app caches, regenerated on demand",
        risk=RISK_SAFE,
        patterns=["Library/Caches/*"],
    ),
    Category(
        id="user-logs",
        name="Application logs",
        description="~/Library/Logs/*",
        risk=RISK_SAFE,
        patterns=["Library/Logs/*"],
    ),
    Category(
        id="xcode-derived-data",
        name="Xcode DerivedData",
        description="Build intermediates Xcode regenerates on next build",
        risk=RISK_SAFE,
        patterns=["Library/Developer/Xcode/DerivedData/*"],
    ),
    Category(
        id="xcode-archives",
        name="Xcode Archives",
        description="Archived .xcarchive builds kept for App Store submission/dSYMs",
        risk=RISK_CAUTION,
        patterns=["Library/Developer/Xcode/Archives/*"],
    ),
    Category(
        id="xcode-device-support",
        name="Xcode iOS Device Support",
        description="Per-OS-version symbol caches for devices you've debugged on",
        risk=RISK_SAFE,
        patterns=["Library/Developer/Xcode/iOS DeviceSupport/*"],
    ),
    Category(
        id="ios-simulators",
        name="iOS Simulator devices",
        description="Simulator device state; deleting removes simulator data/apps",
        risk=RISK_CAUTION,
        patterns=["Library/Developer/CoreSimulator/Devices/*"],
    ),
    Category(
        id="npm-cache",
        name="npm cache",
        description="~/.npm/_cacache — re-downloaded on next install",
        risk=RISK_SAFE,
        patterns=[".npm/_cacache"],
    ),
    Category(
        id="yarn-cache",
        name="Yarn cache",
        description="Yarn's package cache",
        risk=RISK_SAFE,
        patterns=["Library/Caches/Yarn/*", ".cache/yarn/*"],
    ),
    Category(
        id="pnpm-store",
        name="pnpm store",
        description="pnpm's content-addressable package store",
        risk=RISK_SAFE,
        patterns=["Library/pnpm/store/*", ".local/share/pnpm/store/*"],
    ),
    Category(
        id="pip-cache",
        name="pip cache",
        description="~/Library/Caches/pip",
        risk=RISK_SAFE,
        patterns=["Library/Caches/pip"],
    ),
    Category(
        id="go-build-cache",
        name="Go build cache",
        description="~/Library/Caches/go-build",
        risk=RISK_SAFE,
        patterns=["Library/Caches/go-build"],
    ),
    Category(
        id="cargo-cache",
        name="Cargo registry cache",
        description="Downloaded crate sources/indexes, re-fetched on demand",
        risk=RISK_SAFE,
        patterns=[".cargo/registry/*"],
    ),
    Category(
        id="gradle-cache",
        name="Gradle cache",
        description="~/.gradle/caches",
        risk=RISK_SAFE,
        patterns=[".gradle/caches/*"],
    ),
    Category(
        id="trash",
        name="Trash",
        description="~/.Trash — files you've already asked macOS to delete",
        risk=RISK_SAFE,
        patterns=[".Trash/*"],
    ),
    Category(
        id="mail-downloads",
        name="Mail downloaded attachments",
        description="Mail.app's local attachment cache",
        risk=RISK_SAFE,
        patterns=[
            "Library/Containers/com.apple.mail/Data/Library/Mail Downloads/*"
        ],
    ),
    Category(
        id="ios-backups",
        name="iOS device backups",
        description="Full local backups of iPhones/iPads made via Finder/iTunes",
        risk=RISK_CAUTION,
        patterns=["Library/Application Support/MobileSync/Backup/*"],
    ),
    Category(
        id="homebrew-cache",
        name="Homebrew download cache",
        description="Downloaded bottles/sources; clean with `brew cleanup`",
        risk=RISK_MANUAL,
        manual_hint="brew cleanup -s && brew autoremove",
        dynamic_paths=_brew_cache_paths,
    ),
    Category(
        id="docker",
        name="Docker Desktop disk image",
        description="Docker's VM disk (images/containers/volumes); clean with `docker system prune`",
        risk=RISK_MANUAL,
        manual_hint="docker system prune -a --volumes",
        dynamic_paths=_docker_data_paths,
    ),
]


def get_categories() -> list[Category]:
    return list(CATEGORIES)


def get_category(category_id: str) -> Category:
    for cat in CATEGORIES:
        if cat.id == category_id:
            return cat
    raise KeyError(category_id)
