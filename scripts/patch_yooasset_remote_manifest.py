#!/usr/bin/env python3
"""Patch a YooAsset binary manifest for modified remote cache bundles.

The script reads a YooAsset PackageManifest binary, updates bundle records for
patched bundle files, writes a new manifest/hash pair, and prepares matching
sandbox cache entries (__data + __info) under the new FileHash paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


FILE_MAGIC = 0x594F4F
HASH_RE = re.compile(r"^([0-9a-f]{32})__(.+)$")


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, size: int) -> bytes:
        if self.pos + size > len(self.data):
            raise EOFError(f"Manifest ended at {self.pos}, need {size} more bytes")
        chunk = self.data[self.pos : self.pos + size]
        self.pos += size
        return chunk

    def bool(self) -> bool:
        return self.read(1) == b"\x01"

    def u16(self) -> int:
        return struct.unpack("<H", self.read(2))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.read(4))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self.read(8))[0]

    def string(self) -> str:
        size = self.u16()
        if size == 0:
            return ""
        return self.read(size).decode("utf-8")

    def string_array(self) -> list[str]:
        count = self.u16()
        return [self.string() for _ in range(count)]

    def i32_array(self) -> list[int]:
        count = self.u16()
        return [self.i32() for _ in range(count)]


class Writer:
    def __init__(self):
        self.parts: list[bytes] = []

    def data(self) -> bytes:
        return b"".join(self.parts)

    def bool(self, value: bool) -> None:
        self.parts.append(b"\x01" if value else b"\x00")

    def u16(self, value: int) -> None:
        self.parts.append(struct.pack("<H", value))

    def i32(self, value: int) -> None:
        self.parts.append(struct.pack("<i", value))

    def u32(self, value: int) -> None:
        self.parts.append(struct.pack("<I", value))

    def i64(self, value: int) -> None:
        self.parts.append(struct.pack("<q", value))

    def string(self, value: str) -> None:
        encoded = value.encode("utf-8")
        if len(encoded) > 0xFFFF:
            raise ValueError(f"String too long for YooAsset manifest: {value[:80]!r}")
        self.u16(len(encoded))
        self.parts.append(encoded)

    def string_array(self, values: list[str]) -> None:
        if len(values) > 0xFFFF:
            raise ValueError("String array too long for YooAsset manifest")
        self.u16(len(values))
        for value in values:
            self.string(value)

    def i32_array(self, values: list[int]) -> None:
        if len(values) > 0xFFFF:
            raise ValueError("Int32 array too long for YooAsset manifest")
        self.u16(len(values))
        for value in values:
            self.i32(value)


@dataclass
class AssetEntry:
    address: str
    asset_path: str
    asset_guid: str
    asset_tags: list[str]
    bundle_id: int
    dependent_bundle_ids: list[int]


@dataclass
class BundleEntry:
    bundle_name: str
    unity_crc: int
    file_hash: str
    file_crc: int
    file_size: int
    is_encrypted: bool
    tags: list[str]
    dependent_bundle_ids: list[int]


@dataclass
class Manifest:
    file_version: str
    enable_addressable: bool
    support_extensionless: bool
    location_to_lower: bool
    include_asset_guid: bool
    replace_asset_path_with_address: bool
    output_name_style: int
    build_bundle_type: int
    build_pipeline: str
    package_name: str
    package_version: str
    package_note: str
    assets: list[AssetEntry]
    bundles: list[BundleEntry]


def parse_manifest(data: bytes) -> Manifest:
    reader = Reader(data)
    magic = reader.u32()
    if magic != FILE_MAGIC:
        raise ValueError(f"Unexpected manifest magic: 0x{magic:08x}")

    manifest = Manifest(
        file_version=reader.string(),
        enable_addressable=reader.bool(),
        support_extensionless=reader.bool(),
        location_to_lower=reader.bool(),
        include_asset_guid=reader.bool(),
        replace_asset_path_with_address=reader.bool(),
        output_name_style=reader.i32(),
        build_bundle_type=reader.i32(),
        build_pipeline=reader.string(),
        package_name=reader.string(),
        package_version=reader.string(),
        package_note=reader.string(),
        assets=[],
        bundles=[],
    )

    for _ in range(reader.i32()):
        manifest.assets.append(
            AssetEntry(
                address=reader.string(),
                asset_path=reader.string(),
                asset_guid=reader.string(),
                asset_tags=reader.string_array(),
                bundle_id=reader.i32(),
                dependent_bundle_ids=reader.i32_array(),
            )
        )

    for _ in range(reader.i32()):
        manifest.bundles.append(
            BundleEntry(
                bundle_name=reader.string(),
                unity_crc=reader.u32(),
                file_hash=reader.string(),
                file_crc=reader.u32(),
                file_size=reader.i64(),
                is_encrypted=reader.bool(),
                tags=reader.string_array(),
                dependent_bundle_ids=reader.i32_array(),
            )
        )

    if reader.pos != len(data):
        raise ValueError(f"Unparsed manifest bytes remain: {len(data) - reader.pos}")
    return manifest


def serialize_manifest(manifest: Manifest) -> bytes:
    writer = Writer()
    writer.u32(FILE_MAGIC)
    writer.string(manifest.file_version)
    writer.bool(manifest.enable_addressable)
    writer.bool(manifest.support_extensionless)
    writer.bool(manifest.location_to_lower)
    writer.bool(manifest.include_asset_guid)
    writer.bool(manifest.replace_asset_path_with_address)
    writer.i32(manifest.output_name_style)
    writer.i32(manifest.build_bundle_type)
    writer.string(manifest.build_pipeline)
    writer.string(manifest.package_name)
    writer.string(manifest.package_version)
    writer.string(manifest.package_note)

    writer.i32(len(manifest.assets))
    for asset in manifest.assets:
        writer.string(asset.address)
        writer.string(asset.asset_path)
        writer.string(asset.asset_guid)
        writer.string_array(asset.asset_tags)
        writer.i32(asset.bundle_id)
        writer.i32_array(asset.dependent_bundle_ids)

    writer.i32(len(manifest.bundles))
    for bundle in manifest.bundles:
        writer.string(bundle.bundle_name)
        writer.u32(bundle.unity_crc)
        writer.string(bundle.file_hash)
        writer.u32(bundle.file_crc)
        writer.i64(bundle.file_size)
        writer.bool(bundle.is_encrypted)
        writer.string_array(bundle.tags)
        writer.i32_array(bundle.dependent_bundle_ids)
    return writer.data()


def yooasset_crc_hex(data: bytes) -> str:
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return crc.to_bytes(4, "little").hex()


def file_crc_u32(path: Path) -> int:
    crc = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_info_file(path: Path, file_crc: int, file_size: int) -> None:
    path.write_bytes(struct.pack("<Iq", file_crc, file_size))


def load_changed_files(report_path: Path | None, patched_dir: Path, glob: str) -> list[Path]:
    if report_path:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        names = {row["bundle_file"] for row in report}
        return sorted(path for name in names for path in [patched_dir / name] if path.is_file())
    return sorted(path for path in patched_dir.glob(glob) if path.is_file())


def bundle_name_from_file(path: Path) -> tuple[str, str]:
    match = HASH_RE.match(path.name)
    if not match:
        raise ValueError(f"Patched bundle filename must start with '<32hex>__': {path.name}")
    return match.group(1), match.group(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--patched-dir", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--glob", default="*")
    parser.add_argument("--out-dir", default=Path("patched/remote_manifest_cache"), type=Path)
    args = parser.parse_args()

    original_data = args.manifest.read_bytes()
    manifest = parse_manifest(original_data)
    roundtrip = serialize_manifest(manifest)
    if roundtrip != original_data:
        raise RuntimeError("Manifest parser failed byte-for-byte round-trip check")

    bundle_by_hash = {bundle.file_hash: bundle for bundle in manifest.bundles}
    changed_paths = load_changed_files(args.report, args.patched_dir, args.glob)
    if not changed_paths:
        raise RuntimeError("No patched bundle files selected")

    cache_root = args.out_dir / "BundleFiles"
    manifest_root = args.out_dir / "ManifestFiles"
    manifest_root.mkdir(parents=True, exist_ok=True)

    updates: list[dict[str, object]] = []
    for bundle_path in changed_paths:
        old_hash, expected_bundle_name = bundle_name_from_file(bundle_path)
        bundle = bundle_by_hash.get(old_hash)
        if bundle is None:
            raise KeyError(f"No manifest bundle has FileHash {old_hash} for {bundle_path.name}")
        if bundle.bundle_name != expected_bundle_name:
            print(
                f"warning: filename bundle name differs for {old_hash}: "
                f"{expected_bundle_name!r} != {bundle.bundle_name!r}"
            )

        new_hash = file_md5(bundle_path)
        new_crc = file_crc_u32(bundle_path)
        new_size = bundle_path.stat().st_size

        bundle.file_hash = new_hash
        bundle.file_crc = new_crc
        bundle.file_size = new_size

        target_dir = cache_root / new_hash[:2] / new_hash
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "__data").write_bytes(bundle_path.read_bytes())
        write_info_file(target_dir / "__info", new_crc, new_size)

        updates.append(
            {
                "bundle_name": bundle.bundle_name,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "file_crc": new_crc,
                "file_crc_hex": f"{new_crc:08x}",
                "file_size": new_size,
                "cache_dir": str(target_dir),
            }
        )

    patched_data = serialize_manifest(manifest)
    manifest_name = args.manifest.name
    patched_manifest = manifest_root / manifest_name
    patched_hash = manifest_root / manifest_name.replace(".bytes", ".hash")
    patched_manifest.write_bytes(patched_data)
    patched_hash.write_text(yooasset_crc_hex(patched_data), encoding="ascii")
    (args.out_dir / "bundle_updates.json").write_text(
        json.dumps(updates, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Round-trip OK for {args.manifest}")
    print(f"Updated {len(updates)} bundle records")
    print(f"Wrote {patched_manifest}")
    print(f"Wrote {patched_hash} = {patched_hash.read_text(encoding='ascii')}")
    print(f"Prepared cache files under {cache_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
