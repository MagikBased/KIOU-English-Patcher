#!/usr/bin/env python3
"""Inventory Unity asset bundles and extract likely text records.

This is intentionally read-only. It scans bundles from the extracted APK,
records object types/names, and writes Japanese-containing string candidates
to reports for translation triage.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import UnityPy


JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")


def iter_strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16-le"):
            try:
                text = value.decode(encoding)
            except UnicodeDecodeError:
                continue
            if JAPANESE_RE.search(text):
                yield path + f"[{encoding}]", text
                break
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from iter_strings(child, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from iter_strings(child, f"{path}[{index}]")


def short_text(text: str, limit: int = 500) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def read_object_data(obj: Any) -> tuple[Any | None, str | None]:
    try:
        return obj.read(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def object_name(data: Any) -> str:
    if data is None:
        return ""
    return getattr(data, "name", None) or getattr(data, "m_Name", None) or ""


def get_typetree(obj: Any) -> tuple[Any | None, str | None]:
    try:
        return obj.read_typetree(), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def scan_bundle(bundle_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    env = UnityPy.load(str(bundle_path))
    counts: Counter[str] = Counter()
    objects: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    assetbundle_name = ""

    for obj in env.objects:
        type_name = obj.type.name
        counts[type_name] += 1
        data, read_error = read_object_data(obj)
        name = object_name(data)
        if type_name == "AssetBundle" and name:
            assetbundle_name = name

        record = {
            "bundle_file": bundle_path.name,
            "path_id": obj.path_id,
            "type": type_name,
            "name": name,
        }
        if read_error:
            record["read_error"] = read_error
        objects.append(record)

        if type_name == "TextAsset" and data is not None:
            script = getattr(data, "script", None) or getattr(data, "m_Script", None)
            for field_path, text in iter_strings(script, "script"):
                if JAPANESE_RE.search(text):
                    candidates.append(
                        {
                            **record,
                            "field": field_path,
                            "text": short_text(text),
                            "length": len(text),
                        }
                    )

        if type_name == "MonoBehaviour":
            tree, tree_error = get_typetree(obj)
            if tree_error:
                continue
            for field_path, text in iter_strings(tree):
                if JAPANESE_RE.search(text):
                    candidates.append(
                        {
                            **record,
                            "field": field_path,
                            "text": short_text(text),
                            "length": len(text),
                        }
                    )

    summary = {
        "bundle_file": bundle_path.name,
        "assetbundle_name": assetbundle_name,
        "size": bundle_path.stat().st_size,
        "object_count": len(objects),
        "type_counts": dict(sorted(counts.items())),
        "candidate_count": len(candidates),
    }
    return summary, candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bundles-dir",
        default="extracted/apk/assets/Bundles/Local",
        type=Path,
        help="Directory containing Unity bundle files.",
    )
    parser.add_argument(
        "--glob",
        default="*.bundle",
        help="File glob to scan under --bundles-dir. Use '*' for downloaded caches with extensionless files.",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        type=Path,
        help="Directory to write inventory and candidate reports.",
    )
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    bundle_paths = sorted(path for path in args.bundles_dir.rglob(args.glob) if path.is_file())

    summaries: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for index, bundle_path in enumerate(bundle_paths, start=1):
        print(f"[{index}/{len(bundle_paths)}] {bundle_path.name}")
        try:
            summary, bundle_candidates = scan_bundle(bundle_path)
        except Exception as exc:
            errors.append({"bundle_file": bundle_path.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        summaries.append(summary)
        candidates.extend(bundle_candidates)

    inventory_path = args.reports_dir / "bundle_inventory.json"
    inventory_path.write_text(
        json.dumps({"summaries": summaries, "errors": errors}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    candidates_jsonl_path = args.reports_dir / "text_candidates.jsonl"
    with candidates_jsonl_path.open("w", encoding="utf-8") as fp:
        for candidate in candidates:
            fp.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    candidates_csv_path = args.reports_dir / "text_candidates.csv"
    fieldnames = ["bundle_file", "path_id", "type", "name", "field", "length", "text"]
    with candidates_csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)

    print(f"Wrote {inventory_path}")
    print(f"Wrote {candidates_jsonl_path}")
    print(f"Wrote {candidates_csv_path}")
    print(f"Found {len(candidates)} Japanese text candidates across {len(summaries)} bundles")
    if errors:
        print(f"Encountered {len(errors)} bundle errors; see {inventory_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
