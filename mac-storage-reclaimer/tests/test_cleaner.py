from pathlib import Path

import pytest

from macreclaim.categories import Category, RISK_MANUAL, RISK_SAFE
from macreclaim.cleaner import clean_category, scan_category


def _make_category(patterns):
    return Category(
        id="test-cat",
        name="test",
        description="test",
        risk=RISK_SAFE,
        patterns=patterns,
    )


def test_scan_category_sums_sizes(tmp_path: Path):
    (tmp_path / "Library" / "Caches" / "app1").mkdir(parents=True)
    (tmp_path / "Library" / "Caches" / "app1" / "f.bin").write_bytes(b"1" * 10)
    (tmp_path / "Library" / "Caches" / "app2").mkdir(parents=True)
    (tmp_path / "Library" / "Caches" / "app2" / "f.bin").write_bytes(b"1" * 20)

    cat = _make_category(["Library/Caches/*"])
    report = scan_category(cat, tmp_path)
    assert report.total_bytes == 30
    assert len(report.paths) == 2


def test_clean_category_dry_run_does_not_delete(tmp_path: Path):
    target = tmp_path / "Library" / "Caches" / "app1"
    target.mkdir(parents=True)
    (target / "f.bin").write_bytes(b"1" * 10)

    cat = _make_category(["Library/Caches/*"])
    report = scan_category(cat, tmp_path)
    results = clean_category(report, dry_run=True)

    assert target.exists()
    assert results[0].freed_bytes == 10


def test_clean_category_deletes_and_logs(tmp_path, monkeypatch):
    target = tmp_path / "Library" / "Caches" / "app1"
    target.mkdir(parents=True)
    (target / "f.bin").write_bytes(b"1" * 10)

    log_dir = tmp_path / "log-home"
    log_dir.mkdir()
    monkeypatch.setattr("macreclaim.history.LOG_DIR", log_dir)
    monkeypatch.setattr("macreclaim.history.LOG_FILE", log_dir / "history.log")

    cat = _make_category(["Library/Caches/*"])
    report = scan_category(cat, tmp_path)
    results = clean_category(report, dry_run=False)

    assert not target.exists()
    assert results[0].freed_bytes == 10
    assert (log_dir / "history.log").exists()
    assert "test-cat" in (log_dir / "history.log").read_text()


def test_clean_category_refuses_manual_risk(tmp_path: Path):
    cat = Category(
        id="manual-cat",
        name="manual",
        description="manual",
        risk=RISK_MANUAL,
        manual_hint="brew cleanup",
        dynamic_paths=lambda: [],
    )
    report = scan_category(cat, tmp_path)
    with pytest.raises(ValueError):
        clean_category(report, dry_run=False)
