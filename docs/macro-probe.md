# Macro probe (issue #3)

**Question:** surface-XML `<Command>` mappings don't fire macros. Does calling
`Host.GUI.Commands.interpretCommand("Macros", "Macro <base64>")` **from a device
script** fire them? NeanderthalMan/studio-one-mcp says yes on Studio One 5.5.2.
This probe checks it on your version before we build the bridge on it.

How it works: the `StudioOneMCP Probe` device (`studio-one-devices/MCPProbe/`) is a
control-surface script. The CLI writes `request.json` to a mailbox folder and
presses MIDI note 119 (the "doorbell"). The script wakes up, runs the request
and writes `response.json`.

## Run it (about 5 minutes)

Quit any MCP client that runs `studio-one-mcp` first, because it owns the
`StudioOneMCP` virtual port.

```bash
pip install -e .
python -m studio_one_mcp.probe install     # copies the device into User Devices
```

1. Restart Studio One.
2. In another terminal, run `python -m studio_one_mcp.probe hold` so the port exists.
3. **Preferences ▸ External Devices ▸ Add… ▸ StudioOneMCP ▸ StudioOneMCP Probe**,
   then set **Receive From = StudioOneMCP** and **Send To = None**.
4. Stop `hold` (Ctrl+C), then:

```bash
python -m studio_one_mcp.probe ping                      # is it alive?
python -m studio_one_mcp.probe run Edit Undo --check     # does a built-in report as enabled?
python -m studio_one_mcp.probe macros                    # macros, by title
python -m studio_one_mcp.probe run-macro "Tempo +1%"     # the test that matters
```

Pick a macro whose effect you can see (the comment on issue #3 used *Tempo +1%*).

## Reading the results

| Result | Meaning |
|---|---|
| `run-macro` → `executed: true` **and you see the effect** | #3 is unblocked: build the script bridge |
| `found: true, executed: true`, no visible effect | Same block as the surface path. Fall back to keystrokes |
| `found: false` | Title mismatch. Copy it exactly from `macros` |
| "isn't loaded" | No `status.json`: the device didn't load, or `ProbeConfig.js` is wrong. Check **View ▸ Console** |
| "never heard the doorbell" | Loaded, but the note doesn't arrive. Check Receive From, or retry with `--channel 1` |

Using an IAC bus instead of the virtual port works too: pass `--port "IAC Driver Bus 1"`
and select that bus as Receive From.

Remove afterwards: delete the device from External Devices and the
`User Devices/MCPProbe` folder.
