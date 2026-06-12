#!/usr/bin/env python3
"""Apply CSV string translations to a directory of Unity bundle files."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

import UnityPy


def load_translations(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        translations = {}
        for row in reader:
            source = row.get("source")
            target = row.get("target")
            if not source or not target or source == target:
                continue
            translations[source] = target
            if "\n" in source:
                translations[source.replace("\n", "\r\n")] = target.replace("\n", "\r\n")
        return translations


def replace_strings(value: Any, translations: dict[str, str]) -> tuple[Any, int]:
    if isinstance(value, str):
        target = translations.get(value)
        if target is None:
            return value, 0
        return target, 1
    if isinstance(value, list):
        total = 0
        for index, child in enumerate(value):
            value[index], count = replace_strings(child, translations)
            total += count
        return value, total
    if isinstance(value, dict):
        total = 0
        for key, child in list(value.items()):
            value[key], count = replace_strings(child, translations)
            total += count
        return value, total
    return value, 0


def patch_bundle(bundle_path: Path, translations: dict[str, str]) -> dict[str, Any] | None:
    env = UnityPy.load(str(bundle_path))
    replacements = 0
    changed_objects: list[dict[str, Any]] = []

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        patched_tree, count = replace_strings(tree, translations)
        if count == 0:
            continue
        obj.save_typetree(patched_tree)
        replacements += count
        changed_objects.append({"path_id": obj.path_id, "replacements": count})

    if replacements == 0:
        return None
    bundle_path.write_bytes(env.file.save())
    return {
        "bundle_file": bundle_path.name,
        "replacements": replacements,
        "changed_objects": changed_objects,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--patched-dir", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--glob", default="*")
    parser.add_argument("--report", default="reports/bundle_patch_report.json", type=Path)
    args = parser.parse_args()

    translations = load_translations(args.translations)
    if not translations:
        raise SystemExit(f"No non-empty translations loaded from {args.translations}")

    if args.patched_dir.exists():
        shutil.rmtree(args.patched_dir)
    shutil.copytree(args.source_dir, args.patched_dir)

    reports: list[dict[str, Any]] = []
    for bundle_path in sorted(path for path in args.patched_dir.rglob(args.glob) if path.is_file()):
        report = patch_bundle(bundle_path, translations)
        if report:
            print(
                f"{report['bundle_file']}: "
                f"{report['replacements']} replacements in {len(report['changed_objects'])} objects"
            )
            reports.append(report)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.report}")
    print(f"Patched {len(reports)} bundles with {sum(r['replacements'] for r in reports)} replacements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
