"""Tests for the probe's mailbox client and installer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from studio_one_mcp import probe


def _answering_device(mailbox: Path, result: object = None, ok: bool = True, error: str = ""):
    """A ring() that behaves like the device: reads request.json, writes response.json."""
    calls: list[dict] = []

    def ring() -> None:
        req = json.loads((mailbox / "request.json").read_text())
        calls.append(req)
        reply = {"id": req["id"], "ok": ok}
        reply.update({"result": result} if ok else {"error": error})
        (mailbox / "response.json").write_text(json.dumps(reply) + "\n")

    return ring, calls


def test_call_round_trip(tmp_path: Path) -> None:
    ring, calls = _answering_device(tmp_path, {"found": True, "executed": True})
    r = probe.Probe(tmp_path, ring).call("command", {"category": "Edit", "name": "Undo"})
    assert r == {"found": True, "executed": True}
    assert calls[0]["op"] == "command"
    assert calls[0]["args"] == {"category": "Edit", "name": "Undo"}


def test_request_is_one_line(tmp_path: Path) -> None:
    ring, _ = _answering_device(tmp_path)
    probe.Probe(tmp_path, ring).call("ping")
    assert (tmp_path / "request.json").read_text().count("\n") == 1  # the device reads one line


def test_error_reply_raises(tmp_path: Path) -> None:
    ring, _ = _answering_device(tmp_path, ok=False, error="unknown op: x")
    with pytest.raises(probe.ProbeError, match="unknown op"):
        probe.Probe(tmp_path, ring).call("x")


def test_stale_response_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "response.json").write_text(json.dumps({"id": "old", "ok": True, "result": 1}))
    with pytest.raises(probe.ProbeError):
        probe.Probe(tmp_path, lambda: None).call("ping", timeout=0.2)


@pytest.mark.parametrize(
    ("status", "hint"),
    [(None, "isn't loaded"), ({"ticks": 0}, "never heard the doorbell"), ({"ticks": 3}, "console")],
)
def test_timeout_hints(tmp_path: Path, status: dict | None, hint: str) -> None:
    if status is not None:
        (tmp_path / "status.json").write_text(json.dumps(status))
    with pytest.raises(probe.ProbeError, match=hint):
        probe.Probe(tmp_path, lambda: None).call("ping", timeout=0.1)


def test_install_writes_config(tmp_path: Path) -> None:
    profile = tmp_path / "Studio One 7"
    mailbox = tmp_path / "mail box"
    target = probe.install(profile, mailbox)
    assert (target / "MCPProbe.device").is_file()
    assert (target / "ProbeComponent.js").is_file()
    config = (target / "ProbeConfig.js").read_text()
    assert f'"mailbox": "file://{mailbox.resolve().as_posix()}/"' in config
    assert mailbox.is_dir()
