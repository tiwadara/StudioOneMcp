from pathlib import Path

from macreclaim.finders import find_large_files, find_node_modules


def test_find_node_modules_finds_top_level(tmp_path: Path):
    proj = tmp_path / "proj"
    nm = proj / "node_modules"
    nm.mkdir(parents=True)
    (nm / "pkg.js").write_bytes(b"x" * 100)

    hits = find_node_modules(tmp_path)
    assert len(hits) == 1
    assert hits[0].path == nm
    assert hits[0].size_bytes == 100


def test_find_node_modules_does_not_descend_into_nested_node_modules(tmp_path: Path):
    proj = tmp_path / "proj"
    nm = proj / "node_modules"
    nested_nm = nm / "some-pkg" / "node_modules"
    nested_nm.mkdir(parents=True)
    (nested_nm / "f.js").write_bytes(b"x" * 50)
    (nm / "top.js").write_bytes(b"y" * 20)

    hits = find_node_modules(tmp_path)
    assert len(hits) == 1
    assert hits[0].path == nm
    assert hits[0].size_bytes == 70


def test_find_large_files_respects_threshold(tmp_path: Path):
    (tmp_path / "small.bin").write_bytes(b"1" * 10)
    (tmp_path / "big.bin").write_bytes(b"1" * 1000)

    hits = find_large_files(tmp_path, min_size_bytes=100)
    assert len(hits) == 1
    assert hits[0].path.name == "big.bin"
