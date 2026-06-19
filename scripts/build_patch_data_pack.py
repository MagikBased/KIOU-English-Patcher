#!/usr/bin/env python3
"""Build a data-only patch pack ZIP and update index for GitHub Releases."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_file(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing required patch data file: {path}")
    archive.write(path, arcname)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", help="Patch data version. Defaults to patch-pack.json pack_version.")
    parser.add_argument(
        "--release-base-url",
        default="https://github.com/MagikBased/KIOU-English-Patcher/releases/latest/download",
        help="Base URL where the ZIP will be uploaded.",
    )
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist" / "patch-data")
    args = parser.parse_args()

    metadata_path = ROOT / "patch-pack.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    version = args.version or str(metadata.get("pack_version") or metadata.get("version"))
    if not version:
        raise SystemExit("Patch data version is required.")
    metadata["pack_version"] = version

    args.out_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"KIOU-English-PatchData-v{version}.zip"
    zip_path = args.out_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("patch-pack.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        for relative in [
            "translations/local_ui.csv",
            "translations/remote_ui.csv",
            "translations/remote_masterdata.csv",
            "translations/voice_catalog.csv",
            "reports/remote_patch_report.json",
        ]:
            add_file(archive, ROOT / relative, relative)

    digest = sha256_file(zip_path)
    index = {
        "latest": version,
        "url": f"{args.release_base_url.rstrip('/')}/{zip_name}",
        "sha256": digest,
        "min_patcher_version": str(metadata.get("min_patcher_version") or "0.1.9"),
        "notes": metadata.get("notes", ""),
    }
    index_path = args.out_dir / "patch-data-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {zip_path}")
    print(f"Wrote {index_path}")
    print(f"SHA256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
