#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
WORK_DIR="$ROOT/work/remote_cache_patcher"
SOURCE_DIR="$WORK_DIR/source_bundles"
PATCHED_DIR="$WORK_DIR/patched_bundles"
REPORT="$ROOT/output/remote_cache_patch_report.json"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

for tool in adb; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 2
  fi
done

mkdir -p "$ROOT/output"
rm -rf "$WORK_DIR"
mkdir -p "$SOURCE_DIR"

echo "Checking connected devices..."
adb devices

echo "Stopping app before cache patch..."
adb shell am force-stop "$PACKAGE" >/dev/null || true

echo "Pulling remote bundles selected by reports/remote_patch_report.json..."
"$PYTHON" - "$ROOT/reports/remote_patch_report.json" "$SOURCE_DIR" "$PACKAGE" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
package = sys.argv[3]

seen: dict[str, str] = {}
for row in json.loads(report_path.read_text(encoding="utf-8")):
    name = row["bundle_file"]
    hash_value = name.split("__", 1)[0]
    seen[hash_value] = name

missing: list[str] = []
for hash_value, name in sorted(seen.items()):
    remote = (
        f"/sdcard/Android/data/{package}/files/Bundles/Remote/"
        f"BundleFiles/{hash_value[:2]}/{hash_value}/__data"
    )
    dest = out_dir / name
    print(f"{hash_value} -> {dest}")
    result = subprocess.run(["adb", "pull", remote, str(dest)])
    if result.returncode != 0:
        missing.append(hash_value)

if missing:
    print(f"Missing {len(missing)} required downloaded bundles.", file=sys.stderr)
    print("Launch the game and let it finish downloading additional data, then retry.", file=sys.stderr)
    sys.exit(1)
print(f"Pulled {len(seen)} remote bundles")
PY

echo "Applying remote English translations..."
"$PYTHON" "$ROOT/scripts/apply_bundle_translations.py" \
  --source-dir "$SOURCE_DIR" \
  --patched-dir "$PATCHED_DIR" \
  --translations "$ROOT/translations/remote_ui.csv" \
  --report "$REPORT"

echo "Pushing patched remote cache with matching metadata..."
"$PYTHON" "$ROOT/scripts/push_patched_remote_bundles.py" \
  --patched-dir "$PATCHED_DIR" \
  --report "$REPORT" \
  --package "$PACKAGE"

echo "Launching app..."
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
echo "Remote cache patch complete. Report: $REPORT"
