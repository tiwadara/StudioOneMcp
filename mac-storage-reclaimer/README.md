# macreclaim

A command-line tool for reclaiming disk space on macOS. It knows about the
usual space hogs — build caches, Xcode junk, package-manager caches, old
Simulator data, Docker, Trash, stale downloads — reports how much space each
one holds, and deletes only what you approve.

It doesn't reinvent disk scanning: for open-ended "what's actually eating my
disk" exploration it shells out to [`dust`](https://github.com/bootandy/dust)
or [`ncdu`](https://dev.yorhel.nl/ncdu) if you have either installed (`brew
install dust` / `brew install ncdu`), and for Homebrew/Docker cleanup it
defers to their own `brew cleanup` / `docker system prune` commands rather
than reimplementing them.

## Install

Requires Python 3.9+. On macOS:

```bash
cd mac-storage-reclaimer
pip install --user -e .
```

This installs the `macreclaim` command.

## Usage

### See what's reclaimable

```bash
macreclaim scan
```

Lists every known category with its current size on disk, largest first,
along with a risk label:

- **safe** — pure cache/derived data, regenerated automatically, always OK to
  delete
- **caution** — real data that's usually disposable but you might want a
  second look (old iOS backups, big Downloads files)
- **manual** — macreclaim only reports the size; deleting requires the
  category's own tool (Homebrew, Docker) because a raw `rm -rf` on it can
  corrupt state

### Reclaim space

```bash
# interactive: pick categories from a checklist, review, confirm
macreclaim clean

# non-interactive: only touch categories tagged "safe"
macreclaim clean --safe-only --yes

# target specific categories
macreclaim clean --only xcode-derived-data,npm-cache,trash --yes

# see what would be deleted without deleting anything
macreclaim clean --dry-run
```

Every run prints exactly what it deleted (or would delete) and how much
space that freed, and writes a log to `~/.macreclaim/history.log`.

### Find what's actually large, anywhere

```bash
# every node_modules directory under $HOME, with size, oldest first to use
macreclaim node-modules

# files over 500MB under a path, sorted by size
macreclaim large-files ~/Downloads --min-size 500MB
```

### Full visual disk exploration

```bash
macreclaim explore            # defaults to $HOME, uses dust or ncdu if installed
macreclaim explore /Volumes/Data
```

If neither `dust` nor `ncdu` is installed, it tells you which one to
`brew install` rather than falling back to a worse home-grown viewer.

## Categories covered

| id | what it is | risk |
|---|---|---|
| `user-caches` | `~/Library/Caches/*` (per-app caches) | safe |
| `user-logs` | `~/Library/Logs/*` | safe |
| `xcode-derived-data` | `~/Library/Developer/Xcode/DerivedData` | safe |
| `xcode-archives` | `~/Library/Developer/Xcode/Archives` | caution |
| `xcode-device-support` | `~/Library/Developer/Xcode/iOS DeviceSupport` (old device symbol caches) | safe |
| `ios-simulators` | `~/Library/Developer/CoreSimulator/Devices` | caution |
| `npm-cache` | `~/.npm/_cacache` | safe |
| `yarn-cache` | `~/Library/Caches/Yarn`, `~/.cache/yarn` | safe |
| `pnpm-store` | `~/.local/share/pnpm/store`, `~/Library/pnpm/store` | safe |
| `pip-cache` | `~/Library/Caches/pip` | safe |
| `go-build-cache` | `~/Library/Caches/go-build` | safe |
| `cargo-cache` | `~/.cargo/registry` | safe |
| `gradle-cache` | `~/.gradle/caches` | safe |
| `trash` | `~/.Trash` | safe |
| `mail-downloads` | Mail's downloaded attachments cache | safe |
| `ios-backups` | `~/Library/Application Support/MobileSync/Backup` | caution |
| `homebrew-cache` | `$(brew --cache)` — reported only, cleaned via `brew cleanup` | manual |
| `docker` | Docker Desktop's VM disk image — reported only, cleaned via `docker system prune` | manual |

Add more by dropping a `Category` into `src/macreclaim/categories.py`.

## Safety

- Nothing is deleted without `--yes` or interactive confirmation.
- `safe`-tier categories are pure regenerable cache — deleting them can only
  cost you a rebuild/re-download, never real data.
- `caution`-tier categories (old iOS backups, Xcode archives, Simulator
  devices) are listed but require explicit selection; `clean --safe-only`
  never touches them.
- `manual`-tier categories are never deleted by this tool at all — it prints
  the size and the exact command to run yourself.
- Every deletion is logged to `~/.macreclaim/history.log` with timestamp,
  path, and freed bytes.

## Tests

```bash
cd mac-storage-reclaimer
pip install --user -e ".[dev]"
pytest
```

Tests exercise the size-scanning and category logic against temp
directories, so they run on any platform, not just macOS.
