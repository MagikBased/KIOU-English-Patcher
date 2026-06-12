#!/usr/bin/env python3
"""Push patched YooAsset remote bundle cache files back to an Android device."""

from __future__ import annotations

import argparse
import os
import json
import re
import subprocess
import tempfile
import zlib
from pathlib import Path


HASH_RE = re.compile(r"^([0-9a-f]{32})__")


def file_crc_u32(path: Path) -> int:
    crc = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def app_cache_info_bytes(path: Path) -> bytes:
    # This app uses YooAsset's older compact sandbox info format:
    # uint32 data CRC + int64 data size, both little-endian.
    return file_crc_u32(path).to_bytes(4, "little") + path.stat().st_size.to_bytes(8, "little", signed=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patched-dir", required=True, type=Path)
    parser.add_argument("--package", default="com.neconome.shogi")
    parser.add_argument("--glob", default="*")
    parser.add_argument("--report", type=Path, help="Optional patch report; push only changed bundle_file entries.")
    parser.add_argument("--data-only", action="store_true", help="Push only __data files, leaving cache __info unchanged.")
    args = parser.parse_args()

    files = sorted(path for path in args.patched_dir.rglob(args.glob) if path.is_file())
    if args.report:
        changed = {row["bundle_file"] for row in json.loads(args.report.read_text(encoding="utf-8"))}
        files = [path for path in files if path.name in changed]

    pushed = 0
    pushed_info = 0
    for path in files:
        match = HASH_RE.match(path.name)
        if not match:
            continue
        hash_value = match.group(1)
        remote_dir = (
            f"/sdcard/Android/data/{args.package}/files/Bundles/Remote/"
            f"BundleFiles/{hash_value[:2]}/{hash_value}"
        )
        remote_data = f"{remote_dir}/__data"
        print(f"{hash_value} -> {remote_data}")
        subprocess.run(["adb", "push", str(path), remote_data], check=True)
        pushed += 1

        if not args.data_only:
            fd, info_name = tempfile.mkstemp(prefix=f"{hash_value}.", suffix=".__info")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(app_cache_info_bytes(path))
                remote_info = f"{remote_dir}/__info"
                subprocess.run(["adb", "push", info_name, remote_info], check=True)
                pushed_info += 1
            finally:
                Path(info_name).unlink(missing_ok=True)

    print(f"Pushed {pushed} patched bundles")
    if not args.data_only:
        print(f"Pushed {pushed_info} matching cache info files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
