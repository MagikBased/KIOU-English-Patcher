#!/usr/bin/env python3
"""Build the Kiou English Patcher desktop app with PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "KiouEnglishPatcher"


def data_arg(source: str, dest: str) -> str:
    separator = ";" if os.name == "nt" else ":"
    return f"{source}{separator}{dest}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove previous PyInstaller build output first.")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Force a one-file executable. Enabled by default on Windows.",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Force a one-directory app. This is the default on macOS and Linux.",
    )
    args = parser.parse_args()

    try:
        import PyInstaller.__main__  # type: ignore
    except ModuleNotFoundError:
        print("PyInstaller is not installed. Run:", file=sys.stderr)
        print("  python -m pip install -r requirements-packaging.txt", file=sys.stderr)
        return 2

    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build" / "pyinstaller"
    spec_dir = build_dir / "specs"
    if args.clean:
        shutil.rmtree(dist_dir, ignore_errors=True)
        shutil.rmtree(build_dir, ignore_errors=True)

    spec_dir.mkdir(parents=True, exist_ok=True)

    onefile = args.onefile or (sys.platform == "win32" and not args.onedir)
    command = [
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(spec_dir),
        "--paths",
        str(ROOT / "scripts"),
        "--collect-submodules",
        "UnityPy",
        "--collect-data",
        "UnityPy",
        "--collect-submodules",
        "PIL",
        "--add-data",
        data_arg(str(ROOT / "translations" / "local_ui.csv"), "translations"),
        "--add-data",
        data_arg(str(ROOT / "translations" / "remote_ui.csv"), "translations"),
        "--add-data",
        data_arg(str(ROOT / "translations" / "remote_masterdata.csv"), "translations"),
        "--add-data",
        data_arg(str(ROOT / "translations" / "voice_catalog.csv"), "translations"),
        "--add-data",
        data_arg(str(ROOT / "reports" / "remote_patch_report.json"), "reports"),
        "--add-data",
        data_arg(str(ROOT / "patch-pack.json"), "."),
        "--add-data",
        data_arg(str(ROOT / "assets" / "brand"), "assets/brand"),
    ]
    if onefile:
        command.append("--onefile")
    if sys.platform == "darwin":
        command.extend(["--osx-bundle-identifier", "org.kiouenglishpatch.patcher"])
    command.append(str(ROOT / "scripts" / "patcher_gui.py"))

    print("Running PyInstaller...")
    print(" ".join(command))
    PyInstaller.__main__.run(command)

    if sys.platform == "win32":
        if onefile:
            artifact = dist_dir / f"{APP_NAME}.exe"
        else:
            artifact = dist_dir / APP_NAME / f"{APP_NAME}.exe"
    elif sys.platform == "darwin":
        artifact = dist_dir / f"{APP_NAME}.app"
    else:
        artifact = dist_dir / APP_NAME / APP_NAME

    print(f"Build complete: {artifact}")
    if sys.platform != "win32":
        print("Windows .exe builds must be produced on Windows.")
    if sys.platform != "darwin":
        print("macOS .app builds must be produced on macOS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
