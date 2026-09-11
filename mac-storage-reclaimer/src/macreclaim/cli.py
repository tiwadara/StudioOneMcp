from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .categories import RISK_MANUAL, get_categories
from .cleaner import clean_category, scan_all, scan_category
from .finders import find_large_files, find_node_modules
from .sizing import human_readable, parse_size


def cmd_scan(args: argparse.Namespace) -> int:
    reports = scan_all()
    total = sum(r.total_bytes for r in reports)
    print(f"{'CATEGORY':<24}{'RISK':<10}{'SIZE':>10}   DESCRIPTION")
    for r in reports:
        if r.total_bytes == 0:
            continue
        print(
            f"{r.category.id:<24}{r.category.risk:<10}"
            f"{human_readable(r.total_bytes):>10}   {r.category.description}"
        )
        if r.category.risk == RISK_MANUAL and r.category.manual_hint:
            print(f"{'':<24}{'':<10}{'':>10}   -> run: {r.category.manual_hint}")
    print(f"\nTotal reclaimable (all categories): {human_readable(total)}")
    return 0


def _select_categories(args: argparse.Namespace) -> list[str]:
    if args.only:
        return [c.strip() for c in args.only.split(",") if c.strip()]
    reports = scan_all()
    candidates = [r for r in reports if r.total_bytes > 0]
    if args.safe_only:
        return [r.category.id for r in candidates if r.category.risk == "safe"]

    print("Select categories to clean:\n")
    for i, r in enumerate(candidates, 1):
        print(f"  [{i}] {r.category.id:<24}{r.category.risk:<10}{human_readable(r.total_bytes):>10}")
    raw = input("\nEnter numbers (comma-separated), or 'safe' for all safe ones, or blank to cancel: ").strip()
    if not raw:
        return []
    if raw.lower() == "safe":
        return [r.category.id for r in candidates if r.category.risk == "safe"]
    chosen = []
    for token in raw.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        idx = int(token) - 1
        if 0 <= idx < len(candidates):
            chosen.append(candidates[idx].category.id)
    return chosen


def cmd_clean(args: argparse.Namespace) -> int:
    ids = _select_categories(args)
    if not ids:
        print("Nothing selected.")
        return 0

    home = Path.home()
    freed_total = 0
    for cat_id in ids:
        try:
            from .categories import get_category

            category = get_category(cat_id)
        except KeyError:
            print(f"Unknown category: {cat_id}", file=sys.stderr)
            continue
        if category.risk == RISK_MANUAL:
            print(f"Skipping '{cat_id}' (manual-risk) — run: {category.manual_hint}")
            continue

        report = scan_category(category, home)
        if report.total_bytes == 0:
            continue

        if not args.dry_run and not args.yes:
            answer = input(
                f"Delete {human_readable(report.total_bytes)} from "
                f"'{category.id}' ({len(report.paths)} items)? [y/N] "
            ).strip().lower()
            if answer != "y":
                print(f"Skipped '{category.id}'.")
                continue

        results = clean_category(report, dry_run=args.dry_run)
        freed = sum(r.freed_bytes for r in results if not r.error)
        errors = [r for r in results if r.error]
        freed_total += freed
        verb = "Would free" if args.dry_run else "Freed"
        print(f"{verb} {human_readable(freed)} from '{category.id}'")
        for err in errors:
            print(f"  ! {err.path}: {err.error}", file=sys.stderr)

    verb = "Would free" if args.dry_run else "Total freed"
    print(f"\n{verb}: {human_readable(freed_total)}")
    return 0


def cmd_node_modules(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser()
    hits = find_node_modules(root)
    total = 0
    for h in hits:
        print(f"{human_readable(h.size_bytes):>10}   {h.path}")
        total += h.size_bytes
    print(f"\n{len(hits)} node_modules directories, {human_readable(total)} total")
    return 0


def cmd_large_files(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser()
    min_bytes = parse_size(args.min_size)
    hits = find_large_files(root, min_bytes)
    for h in hits[: args.limit]:
        print(f"{human_readable(h.size_bytes):>10}   {h.path}")
    if len(hits) > args.limit:
        print(f"... and {len(hits) - args.limit} more (raise --limit to see them)")
    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    target = args.path or str(Path.home())
    for tool, cmd in (("dust", ["dust", target]), ("ncdu", ["ncdu", target])):
        if shutil.which(tool):
            return subprocess.call(cmd)
    print(
        "Neither 'dust' nor 'ncdu' is installed. Install one for full visual "
        "disk exploration:\n\n  brew install dust\n  brew install ncdu\n",
        file=sys.stderr,
    )
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macreclaim", description="Find and reclaim disk space on macOS."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Report reclaimable space by category")
    p_scan.set_defaults(func=cmd_scan)

    p_clean = sub.add_parser("clean", help="Delete reclaimable space")
    p_clean.add_argument("--only", help="Comma-separated category ids to clean")
    p_clean.add_argument("--safe-only", action="store_true", help="Only clean 'safe' risk categories")
    p_clean.add_argument("--yes", action="store_true", help="Don't prompt before each category")
    p_clean.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    p_clean.set_defaults(func=cmd_clean)

    p_nm = sub.add_parser("node-modules", help="Find node_modules directories and their sizes")
    p_nm.add_argument("path", nargs="?", default=str(Path.home()))
    p_nm.set_defaults(func=cmd_node_modules)

    p_lf = sub.add_parser("large-files", help="Find files over a size threshold")
    p_lf.add_argument("path", nargs="?", default=str(Path.home()))
    p_lf.add_argument("--min-size", default="500MB")
    p_lf.add_argument("--limit", type=int, default=50)
    p_lf.set_defaults(func=cmd_large_files)

    p_explore = sub.add_parser("explore", help="Launch dust/ncdu for full visual disk exploration")
    p_explore.add_argument("path", nargs="?", default=None)
    p_explore.set_defaults(func=cmd_explore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
