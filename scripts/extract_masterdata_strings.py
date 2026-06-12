#!/usr/bin/env python3
"""Extract readable Japanese strings from the RuntimeMasterData TextAsset."""

from __future__ import annotations

import argparse
import csv
import re
import struct
from pathlib import Path

import UnityPy


JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")


def read_prefixed_utf8(raw: bytes, offset: int, char_count: int) -> tuple[int, str] | None:
    if char_count <= 0 or char_count > 1000:
        return None
    max_end = min(len(raw), offset + char_count * 4 + 1)
    for end in range(offset + char_count, max_end + 1):
        try:
            text = raw[offset:end].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if len(text) == char_count:
            return end, text
        if len(text) > char_count:
            return None
    return None


def iter_prefixed_strings(text: str) -> list[tuple[int, int, str]]:
    raw = text.encode("utf-8", "surrogateescape")
    segments: list[tuple[int, int, str]] = []
    for offset in range(4, len(raw)):
        char_count = struct.unpack("<i", raw[offset - 4 : offset])[0]
        decoded = read_prefixed_utf8(raw, offset, char_count)
        if decoded is None:
            continue
        end, segment = decoded
        if JAPANESE_RE.search(segment):
            segments.append((offset, end, segment))
    return segments


def extract_bundle(bundle_path: Path) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        script = getattr(data, "m_Script", None)
        if isinstance(script, str):
            rows.extend(iter_prefixed_strings(script))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundles-dir", type=Path, default=Path("downloaded/remote_data_bundles"))
    parser.add_argument("--glob", default="*masterdata*.bundle")
    parser.add_argument("--output", type=Path, default=Path("translations/remote_masterdata_template.csv"))
    args = parser.parse_args()

    seen: set[str] = set()
    rows: list[tuple[str, int, int, int, str, str]] = []
    for bundle_path in sorted(args.bundles_dir.rglob(args.glob)):
        for start, end, text in extract_bundle(bundle_path):
            if text in seen:
                continue
            seen.add(text)
            rows.append((bundle_path.name, start, end, len(text), text, ""))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["bundle_file", "offset_start", "offset_end", "length", "source", "target"])
        writer.writerows(rows)

    print(f"Wrote {args.output}")
    print(f"Extracted {len(rows)} unique Japanese master-data strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
