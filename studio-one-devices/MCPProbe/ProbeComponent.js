// StudioOneMCP Probe component: answers one request at a time through a
// mailbox folder (path in ProbeConfig.js, written by `python -m
// studio_one_mcp.probe install`):
//
//   status.json    probe → client   {probe, session, startedAt, ticks, lastTick}
//   request.json   client → probe   {id, op, args}, one line of JSON
//   response.json  probe → client   {id, ok, result | error}
//
// Studio One gives scripts no sockets and no usable timer, so the client
// presses the doorbell note after writing a request (see MCPProbe.surface.xml).
//
// Two rules, from NeanderthalMan/studio-one-mcp's notes on Studio One 5.5.2:
// never throw out of a component method (it becomes a modal Scripting Error
// dialog, even when caught), and never call a host member without checking it
// exists first. Errors are returned as values.

include_file("resource://com.presonus.musicdevices/sdk/controlsurfacecomponent.js");
include_file("ProbeConfig.js");

const kProbeVersion = 1;
const kMaxCommands = 5000;

function has(obj, key, type) {
    try { return obj !== null && obj !== undefined && typeof obj[key] === type; }
    catch (_) { return false; }
}

function log(msg) {
    if (has(Host, "Console", "object") && has(Host.Console, "writeLine", "function"))
        Host.Console.writeLine("StudioOneMCP Probe: " + msg);
}

class Mailbox {
    constructor(dirUrl) { this.dir = dirUrl.slice(-1) === "/" ? dirUrl : dirUrl + "/"; }
    url(name) { return Host.Url(this.dir + name); }
    read(name) {
        let f = null;
        try {
            if (!Host.IO.File(this.url(name)).exists()) return null;
            f = Host.IO.openTextFile(this.url(name), "utf-8");
            if (!f) return null;
            const text = f.readLine();
            return typeof text === "string" && text ? JSON.parse(text.replace(/^﻿/, "")) : null;
        } catch (_) {
            return null; // half-written or not JSON yet; the client presses again
        } finally { if (f) f.close(); }
    }
    write(name, value) {
        let f = null;
        try {
            f = Host.IO.createTextFile(this.url(name), "utf-8");
            if (!f) return false;
            f.writeString(JSON.stringify(value) + "\n");
            return true;
        } catch (_) {
            return false;
        } finally { if (f) f.close(); }
    }
}

function commands() {
    return has(Host, "GUI", "object") && has(Host.GUI, "Commands", "object") ? Host.GUI.Commands : null;
}

class ProbeComponent extends PreSonus.ControlSurfaceComponent {
    onInit(hostComponent) {
        super.onInit(hostComponent);
        this.tickParam = hostComponent.paramList.addParam("probeTick");
        this.session = String(Date.now()) + "-" + Math.floor(Math.random() * 1e9);
        this.startedAt = Date.now();
        this.ticks = 0;
        this.lastId = null;
        this.box = null;
        try {
            const cfg = typeof ProbeConfig === "object" ? ProbeConfig : null;
            if (cfg && typeof cfg.mailbox === "string" && cfg.mailbox.indexOf("file:///") === 0)
                this.box = new Mailbox(cfg.mailbox);
            else
                log("ProbeConfig.js missing or invalid; reinstall with `python -m studio_one_mcp.probe install`");
        } catch (e) {
            log("init failed: " + e);
        }
        this.writeStatus();
    }

    paramChanged(param) {
        if (param === this.tickParam) {
            try { this.onTick(); } catch (e) { log("tick failed: " + e); }
            return;
        }
        super.paramChanged(param);
    }

    writeStatus() {
        if (!this.box) return;
        this.box.write("status.json", {
            probe: kProbeVersion, session: this.session, startedAt: this.startedAt,
            ticks: this.ticks, lastTick: this.ticks ? Date.now() : null,
        });
    }

    onTick() {
        this.ticks++;
        this.writeStatus();
        if (!this.box) return;
        const req = this.box.read("request.json");
        if (!req || typeof req.id !== "string" || req.id === this.lastId) return;
        this.lastId = req.id; // repeat presses for the same request are ignored
        let result;
        try { result = this.handle(String(req.op), req.args || {}); }
        catch (e) { result = { error: String(e && e.message || e) }; }
        const reply = result && typeof result.error === "string"
            ? { id: req.id, session: this.session, ok: false, error: result.error }
            : { id: req.id, session: this.session, ok: true, result: result };
        this.box.write("response.json", reply);
    }

    handle(op, args) {
        switch (op) {
            case "ping": return this.ping();
            case "listCommands": return this.listCommands(args);
            case "command": return this.command(args);
            default: return { error: "unknown op: " + op };
        }
    }

    ping() {
        const c = commands();
        return {
            probe: kProbeVersion,
            ticks: this.ticks,
            commands: !!c,
            findCommand: has(c, "findCommand", "function"),
            interpretCommand: has(c, "interpretCommand", "function"),
            newCommandIterator: has(c, "newCommandIterator", "function"),
        };
    }

    listCommands(args) {
        const c = commands();
        if (!has(c, "newCommandIterator", "function")) return { error: "Host.GUI.Commands.newCommandIterator is not available" };
        const filter = args.filter ? String(args.filter).toLowerCase() : null;
        const it = c.newCommandIterator();
        const out = [];
        let seen = 0;
        while (it && has(it, "done", "function") && !it.done() && seen < kMaxCommands) {
            const cmd = it.next();
            seen++;
            if (!cmd) break;
            const entry = { category: String(cmd.category), name: String(cmd.name) };
            if (filter && (entry.category + " " + entry.name).toLowerCase().indexOf(filter) < 0) continue;
            out.push(entry);
        }
        return { seen: seen, commands: out };
    }

    // Reports each step separately, so a failure says where it stopped:
    // found (findCommand), enabled (interpretCommand with checkOnly), executed.
    command(args) {
        if (!args.category || !args.name) return { error: "category and name are required" };
        const c = commands();
        if (!has(c, "findCommand", "function") || !has(c, "interpretCommand", "function"))
            return { error: "Host.GUI.Commands is not available" };
        const category = String(args.category);
        const name = String(args.name);
        const found = !!c.findCommand(category, name);
        if (!found) return { found: false };
        const enabled = !!c.interpretCommand(category, name, true);
        if (args.checkOnly) return { found: true, enabled: enabled };
        const executed = !!c.interpretCommand(category, name);
        return { found: true, enabled: enabled, executed: executed };
    }
}

function createProbeComponent() {
    return new ProbeComponent();
}
