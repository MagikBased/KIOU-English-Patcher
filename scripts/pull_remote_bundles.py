#!/usr/bin/env python3
"""Pull selected remote Unity bundles from an Android device cache.

The game's remote cache stores each bundle at:
  /sdcard/Android/data/<package>/files/Bundles/Remote/BundleFiles/<hh>/<hash>/__data

This helper reads reports/remote_bundle_map.json, selects entries by hash, exact
bundle name, or keyword regex, and saves them as <hash>__<bundle_name>.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PACKAGE = "com.neconome.shogi"


def load_bundle_map(path: Path) -> list[dict[str, str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        {"hash": str(row["hash"]), "bundle_name": str(row["bundle_name"])}
        for row in rows
        if row.get("hash") and row.get("bundle_name")
    ]


def select_rows(
    rows: list[dict[str, str]],
    hashes: set[str],
    names: set[str],
    keyword_patterns: list[str],
) -> list[dict[str, str]]:
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in keyword_patterns]
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        bundle_hash = row["hash"]
        bundle_name = row["bundle_name"]
        if (
            bundle_hash in hashes
            or bundle_name in names
            or any(regex.search(bundle_name) for regex in regexes)
        ):
            if bundle_hash not in seen:
                selected.append(row)
                seen.add(bundle_hash)
    return selected


def adb_command(serial: str | None, args: list[str]) -> list[str]:
    command = ["adb"]
    if serial:
        command.extend(["-s", serial])
    command.extend(args)
    return command


def pull_bundle(row: dict[str, str], output_dir: Path, package: str, serial: str | None) -> bool:
    bundle_hash = row["hash"]
    bundle_name = row["bundle_name"]
    remote_path = (
        f"/sdcard/Android/data/{package}/files/Bundles/Remote/BundleFiles/"
        f"{bundle_hash[:2]}/{bundle_hash}/__data"
    )
    output_path = output_dir / f"{bundle_hash}__{bundle_name}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        adb_command(serial, ["pull", remote_path, str(output_path)]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode == 0:
        print(f"pulled {bundle_hash} {bundle_name}")
        return True
    print(f"missing {bundle_hash} {bundle_name}")
    print(result.stdout.strip())
    return False


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-map", type=Path, default=Path("reports/remote_bundle_map.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("downloaded/remote_selected_bundles"))
    parser.add_argument("--manifest", type=Path, default=Path("reports/remote_selected_bundles.json"))
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--serial", help="ADB device serial. Use this when more than one device is connected.")
    parser.add_argument("--hash", dest="hashes", action="append", default=[])
    parser.add_argument("--name", dest="names", action="append", default=[])
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Case-insensitive regex matched against bundle names.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = load_bundle_map(args.bundle_map)
    selected = select_rows(rows, set(args.hashes), set(args.names), args.keyword)
    if not selected:
        raise SystemExit("No bundles matched.")

    print(f"Selected {len(selected)} bundles")
    for row in selected:
        print(f"{row['hash']} {row['bundle_name']}")

    if args.dry_run:
        return 0

    pulled: list[dict[str, Any]] = []
    for row in selected:
        ok = pull_bundle(row, args.output_dir, args.package, args.serial)
        pulled.append({**row, "pulled": ok})

    write_manifest(args.manifest, pulled)
    print(f"Wrote {args.manifest}")
    print(f"Pulled {sum(1 for row in pulled if row['pulled'])}/{len(pulled)} bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
