#!/usr/bin/env python3
"""Check whether a user-supplied APK matches a tested Kiou build."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


SUPPORTED_APK_SHA256 = {
    "c23f77caacf7cb988bcbf1b9d91ec5708eef6cc6056faee38f0d8ea778ec898f": "KIOU_RELEASE.apk",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--allow-unknown", action="store_true")
    args = parser.parse_args()

    if not args.apk.is_file():
        print(f"APK not found: {args.apk}", file=sys.stderr)
        return 2

    digest = sha256_file(args.apk)
    print(f"APK SHA256: {digest}")
    if digest in SUPPORTED_APK_SHA256:
        print(f"Supported build: {SUPPORTED_APK_SHA256[digest]}")
        return 0

    print("Unsupported or untested APK build.", file=sys.stderr)
    if args.allow_unknown:
        print("Continuing because --allow-unknown was set.", file=sys.stderr)
        return 0

    print("Use --allow-unknown to try patching anyway.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
