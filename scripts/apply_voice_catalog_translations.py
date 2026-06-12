#!/usr/bin/env python3
"""Patch Kiou voice_catalog.g TextAsset serif strings by cueName."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

import UnityPy


def load_translations(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        translations: dict[str, dict[str, str]] = {}
        for row in reader:
            cue_name = row.get("cueName", "")
            source = row.get("source", "")
            target = row.get("target", "")
            if not cue_name or not source or not target or source == target:
                continue
            translations[cue_name] = {"source": source, "target": target}
        return translations


def patch_bundle(bundle_path: Path, output_path: Path, translations: dict[str, dict[str, str]]) -> dict[str, Any]:
    env = UnityPy.load(str(bundle_path))
    found_catalog = False
    changed_objects: list[dict[str, Any]] = []

    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if getattr(data, "m_Name", None) != "voice_catalog.g":
            continue

        found_catalog = True
        script = data.m_Script
        if isinstance(script, bytes):
            script = script.decode("utf-8")
        root = json.loads(script)

        replacements: list[dict[str, str]] = []
        for entry in root.get("entries", []):
            cue_name = entry.get("cueName", "")
            current = entry.get("serif", "")
            translation = translations.get(cue_name)
            if not translation or current != translation["source"]:
                continue
            entry["serif"] = translation["target"]
            replacements.append(
                {
                    "cueName": cue_name,
                    "source": translation["source"],
                    "target": translation["target"],
                }
            )

        if not replacements:
            continue

        data.m_Script = json.dumps(root, ensure_ascii=False, indent=4)
        data.save()
        changed_objects.append(
            {
                "path_id": obj.path_id,
                "type": "TextAsset",
                "name": "voice_catalog.g",
                "replacements": len(replacements),
                "strings": replacements,
            }
        )

    if not found_catalog:
        raise ValueError(f"No voice_catalog.g TextAsset found in {bundle_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not changed_objects:
        if output_path != bundle_path:
            shutil.copy2(bundle_path, output_path)
        return {
            "bundle_file": output_path.name,
            "replacements": 0,
            "changed_objects": [],
        }

    output_path.write_bytes(env.file.save(packer="original"))
    return {
        "bundle_file": output_path.name,
        "replacements": sum(int(item["replacements"]) for item in changed_objects),
        "changed_objects": changed_objects,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--output-bundle", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    translations = load_translations(args.translations)
    if not translations:
        raise SystemExit(f"No non-empty translations loaded from {args.translations}")

    report = patch_bundle(args.source_bundle, args.output_bundle, translations)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps([report], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{args.output_bundle.name}: {report['replacements']} voice-catalog replacements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
