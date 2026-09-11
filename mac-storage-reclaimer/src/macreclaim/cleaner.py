"""Reporting and safe deletion of category contents."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from . import history
from .categories import RISK_MANUAL, Category
from .sizing import dir_size


@dataclass
class CategoryReport:
    category: Category
    paths: list[Path]
    total_bytes: int


def scan_category(category: Category, home: Path) -> CategoryReport:
    paths = category.candidate_paths(home)
    total = sum(dir_size(p) for p in paths)
    return CategoryReport(category=category, paths=paths, total_bytes=total)


def scan_all(home: Path | None = None) -> list[CategoryReport]:
    from .categories import get_categories

    home = home or Path.home()
    reports = [scan_category(cat, home) for cat in get_categories()]
    reports.sort(key=lambda r: r.total_bytes, reverse=True)
    return reports


@dataclass
class DeletionResult:
    category_id: str
    path: Path
    freed_bytes: int
    error: str | None = None


def clean_category(report: CategoryReport, dry_run: bool = True) -> list[DeletionResult]:
    """Delete every candidate path in `report`. Never touches manual-risk categories."""
    if report.category.risk == RISK_MANUAL:
        raise ValueError(
            f"'{report.category.id}' is manual-risk; run its own cleanup tool instead "
            f"({report.category.manual_hint})"
        )

    results: list[DeletionResult] = []
    for path in report.paths:
        freed = dir_size(path)
        if dry_run:
            results.append(DeletionResult(report.category.id, path, freed))
            continue
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
            history.log_deletion(report.category.id, path, freed)
            results.append(DeletionResult(report.category.id, path, freed))
        except OSError as exc:
            results.append(DeletionResult(report.category.id, path, 0, error=str(exc)))
    return results
