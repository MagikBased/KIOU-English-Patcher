#!/usr/bin/env python3
"""Extract Kiou voice catalog lines into a translation CSV template."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import UnityPy


def is_voice_catalog_name(name: str) -> bool:
    return name == "voice_catalog.g" or (name.startswith("voice_catalog_") and name.endswith(".g"))


def load_voice_entries(bundle_path: Path) -> list[dict[str, str]]:
    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if not is_voice_catalog_name(getattr(data, "m_Name", "")):
            continue
        script = data.m_Script
        if isinstance(script, bytes):
            script = script.decode("utf-8")
        root = json.loads(script)
        return root["entries"]
    raise ValueError(f"No voice-catalog TextAsset found in {bundle_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    entries = load_voice_entries(args.source_bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["cueName", "source", "target"])
        writer.writeheader()
        for entry in entries:
            source = entry.get("serif", "")
            if not source:
                continue
            writer.writerow(
                {
                    "cueName": entry.get("cueName", ""),
                    "source": source,
                    "target": "",
                }
            )

    print(f"Wrote {args.output}")
    print(f"Extracted {sum(1 for entry in entries if entry.get('serif'))} voice lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
