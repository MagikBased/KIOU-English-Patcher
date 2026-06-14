#!/usr/bin/env python3
"""Patch RuntimeMasterData TextAsset strings without re-encoding binary data."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import struct
from pathlib import Path
from typing import Any

import UnityPy


def align4(value: int) -> int:
    return value + (-value % 4)


def read_unity_string(raw: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(raw):
        raise ValueError(f"Unity string length at offset {offset} is outside object data")
    length = struct.unpack_from("<i", raw, offset)[0]
    if length < 0 or offset + 4 + length > len(raw):
        raise ValueError(f"Invalid Unity string length {length} at offset {offset}")
    start = offset + 4
    end = start + length
    return raw[start:end], align4(end)


def write_unity_string(value: bytes) -> bytes:
    raw = struct.pack("<i", len(value)) + value
    return raw + (b"\x00" * (-len(raw) % 4))


def load_translations(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        translations: dict[str, str] = {}
        for row in reader:
            source = row.get("source")
            target = row.get("target")
            if not source or not target or source == target:
                continue
            translations[source] = target
        return translations


def patch_masterdata_payload(payload: bytes, translations: dict[str, str]) -> tuple[bytes, list[dict[str, Any]]]:
    replacements: list[dict[str, Any]] = []
    patched = payload

    for source, target in sorted(translations.items(), key=lambda item: len(item[0]), reverse=True):
        source_bytes = source.encode("utf-8")
        target_bytes = target.encode("utf-8")
        source_pattern = (
            struct.pack("<i", -(len(source_bytes) + 1))
            + struct.pack("<i", len(source))
            + source_bytes
        )
        target_pattern = (
            struct.pack("<i", -(len(target_bytes) + 1))
            + struct.pack("<i", len(target))
            + target_bytes
        )

        count = patched.count(source_pattern)
        if count == 0:
            continue
        patched = patched.replace(source_pattern, target_pattern)
        replacements.append(
            {
                "source": source,
                "target": target,
                "replacements": count,
                "source_bytes": len(source_bytes),
                "target_bytes": len(target_bytes),
            }
        )

    return patched, replacements


def patch_bundle(bundle_path: Path, output_path: Path, translations: dict[str, str]) -> dict[str, Any]:
    env = UnityPy.load(bundle_path.read_bytes())
    changed_objects: list[dict[str, Any]] = []
    found_masterdata = False

    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        object_raw = obj.get_raw_data()
        name_raw, script_offset = read_unity_string(object_raw, 0)
        if name_raw.decode("utf-8", "replace") != "RuntimeMasterData":
            continue
        found_masterdata = True
        script_raw, end_offset = read_unity_string(object_raw, script_offset)
        if end_offset != len(object_raw):
            raise ValueError(
                f"Unexpected trailing RuntimeMasterData bytes: {len(object_raw) - end_offset}"
            )

        patched_script, replacements = patch_masterdata_payload(script_raw, translations)
        if not replacements:
            continue

        patched_object = write_unity_string(name_raw) + write_unity_string(patched_script)
        obj.set_raw_data(patched_object)
        changed_objects.append(
            {
                "path_id": obj.path_id,
                "type": "TextAsset",
                "name": "RuntimeMasterData",
                "replacements": sum(int(item["replacements"]) for item in replacements),
                "script_bytes_before": len(script_raw),
                "script_bytes_after": len(patched_script),
                "strings": replacements,
            }
        )

    if not found_masterdata:
        raise ValueError(f"No RuntimeMasterData TextAsset found in {bundle_path}")

    if not changed_objects:
        if output_path != bundle_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundle_path, output_path)
        return {
            "bundle_file": output_path.name,
            "replacements": 0,
            "changed_objects": [],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(env.file.save(packer="original"))
    return {
        "bundle_file": output_path.name,
        "replacements": sum(int(item["replacements"]) for obj in changed_objects for item in obj["strings"]),
        "changed_objects": changed_objects,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--output-bundle", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--copy-info-from", type=Path)
    args = parser.parse_args()

    translations = load_translations(args.translations)
    if not translations:
        raise SystemExit(f"No non-empty translations loaded from {args.translations}")

    report = patch_bundle(args.source_bundle, args.output_bundle, translations)
    if args.copy_info_from:
        shutil.copy2(args.copy_info_from, args.output_bundle.with_name(args.output_bundle.name + ".__info"))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps([report], ensure_ascii=False, indent=2), encoding="utf-8")

    if report["changed_objects"]:
        changed = report["changed_objects"][0]
        print(
            f"{args.output_bundle.name}: {report['replacements']} replacements, "
            f"{changed['script_bytes_before']} -> {changed['script_bytes_after']} script bytes"
        )
    else:
        print(f"{args.output_bundle.name}: 0 replacements; already patched or no matching strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
