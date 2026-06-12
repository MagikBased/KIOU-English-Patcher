#!/usr/bin/env python3
"""Repack an extracted APK tree while preserving original entry compression."""

from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-apk", default="KIOU_RELEASE.apk", type=Path)
    parser.add_argument("--apk-dir", default="patched/apk", type=Path)
    parser.add_argument("--output", default="patched/KIOU_RELEASE_english-unsigned.apk", type=Path)
    args = parser.parse_args()

    original_infos: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(args.original_apk, "r") as original:
        for info in original.infolist():
            if not info.is_dir():
                original_infos[info.filename] = info

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", allowZip64=True) as out:
        for file_path in iter_files(args.apk_dir):
            arcname = file_path.relative_to(args.apk_dir).as_posix()
            original_info = original_infos.get(arcname)

            info = zipfile.ZipInfo(arcname)
            if original_info:
                info.date_time = original_info.date_time
                info.compress_type = original_info.compress_type
                info.external_attr = original_info.external_attr
                info.create_system = original_info.create_system
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = stat.S_IMODE(file_path.stat().st_mode)
                info.external_attr = (mode or 0o644) << 16

            out.writestr(info, file_path.read_bytes())

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
