from pathlib import Path

from macreclaim.sizing import dir_size, human_readable, parse_size


def test_human_readable():
    assert human_readable(0) == "0B"
    assert human_readable(1023) == "1023B"
    assert human_readable(1024) == "1.0KB"
    assert human_readable(1024 * 1024 * 5) == "5.0MB"


def test_parse_size():
    assert parse_size("500MB") == 500 * 1024**2
    assert parse_size("1.5GB") == int(1.5 * 1024**3)
    assert parse_size("2048") == 2048
    assert parse_size("10KB") == 10 * 1024


def test_dir_size_sums_nested_files(tmp_path: Path):
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "b.txt").write_bytes(b"y" * 250)
    assert dir_size(tmp_path) == 350


def test_dir_size_missing_path_is_zero(tmp_path: Path):
    assert dir_size(tmp_path / "does-not-exist") == 0


def test_dir_size_single_file(tmp_path: Path):
    f = tmp_path / "file.bin"
    f.write_bytes(b"z" * 42)
    assert dir_size(f) == 42
