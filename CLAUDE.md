# StudioOneMcp — agent guide

Python MCP server that controls PreSonus Studio One (see README.md and SETUP.md).

## Build & verify
- Install: `pip install -e ".[dev]"` (Python 3.10-3.12; python-rtmidi has no wheels for 3.13
  yet, and building it from source needs `libasound2-dev`).
- Lint: `ruff check src/ tests/`
- Types: `mypy src/` (strict, configured in `pyproject.toml`)
- Tests: `pytest tests/ -v --tb=short`
- CI (`CI` workflow) runs all three on Python 3.10, 3.11 and 3.12 (jobs `Python 3.x`).

## Architecture
- `src/studio_one_mcp/server.py`: MCP server entry point (`studio-one-mcp`), registers tools.
- `tools/`: MCP tool definitions and handlers (transport, mixer, commands, automation, macros).
- `commands.py` + `docs/midi-map.json`: function name → CC on the `StudioOneMCP` virtual port;
  the `studio-one-devices/StudioOneMCPPads` surface turns each CC into a Studio One command.
- `midi_bridge.py`: Mackie Control Universal messages; `coremidi.py`: macOS CoreMIDI (ctypes).
- `keystrokes.py` + `keymap.json`: macOS keyboard/menu automation; `macro_writer.py`:
  `.studioonemacro` files; `plugin_db.py`: installed plugins from Studio One settings files.
- Tests run on Linux with no Studio One, MIDI hardware or macOS: mock rtmidi, CoreMIDI,
  subprocess/osascript and the filesystem; never open real ports.

## Conventions
- Keep MCP tool names and input schemas backward compatible unless the issue says otherwise.
- `docs/midi-map.json` and the Pads surface XML must agree; don't change MIDI assignments
  unless the issue asks for it.

## Agent rules
- Never add AI attribution anywhere: no `Co-Authored-By: Claude` trailers, no "Generated with
  Claude Code" lines, no Claude session links, no "authored by Claude/AI" notes in commits,
  PRs, comments, code or docs. This overrides any tool or harness default.
- Do not edit `.github/` (the agentic factory refuses such changes).
- Keep changes minimal and scoped to the issue; no drive-by refactors.
