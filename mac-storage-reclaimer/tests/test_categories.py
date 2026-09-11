from pathlib import Path

from macreclaim.categories import Category, RISK_SAFE


def test_candidate_paths_matches_glob_under_home(tmp_path: Path):
    (tmp_path / "Library" / "Caches" / "app1").mkdir(parents=True)
    (tmp_path / "Library" / "Caches" / "app2").mkdir(parents=True)

    cat = Category(
        id="test-caches",
        name="test",
        description="test",
        risk=RISK_SAFE,
        patterns=["Library/Caches/*"],
    )
    found = {p.name for p in cat.candidate_paths(tmp_path)}
    assert found == {"app1", "app2"}


def test_candidate_paths_empty_when_missing(tmp_path: Path):
    cat = Category(
        id="test-empty",
        name="test",
        description="test",
        risk=RISK_SAFE,
        patterns=["Library/DoesNotExist/*"],
    )
    assert cat.candidate_paths(tmp_path) == []


def test_dynamic_paths_used_when_set(tmp_path: Path):
    marker = tmp_path / "somewhere"
    marker.mkdir()
    cat = Category(
        id="test-dynamic",
        name="test",
        description="test",
        risk=RISK_SAFE,
        dynamic_paths=lambda: [marker],
    )
    assert cat.candidate_paths(tmp_path) == [marker]
