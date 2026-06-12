#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
WORK_DIR="$ROOT/work/remote_cache_patcher"
SOURCE_DIR="$WORK_DIR/source_bundles"
PATCHED_DIR="$WORK_DIR/patched_bundles"
REPORT="$ROOT/output/remote_cache_patch_report.json"
UI_REPORT="$WORK_DIR/remote_ui_patch_report.json"
MASTERDATA_REPORT="$WORK_DIR/remote_masterdata_patch_report.json"
VOICE_CATALOG_REPORT="$WORK_DIR/voice_catalog_patch_report.json"
MASTERDATA_BUNDLE="77466306cf3a4254b1dac34dde0a9942__remote_assets__project_masterdata_runtimemasterdata.bundle"
VOICE_CATALOG_BUNDLE="2f0426ad7cc63c421dbf20786c35cfa0__remote_assets__project_sound_generated_voice_catalog_g.bundle"
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
TRANSLATION_ARGS=(--translations "$ROOT/translations/remote_ui.csv")
"$PYTHON" "$ROOT/scripts/apply_bundle_translations.py" \
  --source-dir "$SOURCE_DIR" \
  --patched-dir "$PATCHED_DIR" \
  "${TRANSLATION_ARGS[@]}" \
  --report "$UI_REPORT"

if [[ -f "$ROOT/translations/remote_masterdata.csv" && -f "$PATCHED_DIR/$MASTERDATA_BUNDLE" ]]; then
  echo "Applying master-data English translations..."
  "$PYTHON" "$ROOT/scripts/apply_masterdata_translations.py" \
    --source-bundle "$PATCHED_DIR/$MASTERDATA_BUNDLE" \
    --output-bundle "$PATCHED_DIR/$MASTERDATA_BUNDLE" \
    --translations "$ROOT/translations/remote_masterdata.csv" \
    --report "$MASTERDATA_REPORT"
fi

if [[ -f "$ROOT/translations/voice_catalog.csv" && -f "$PATCHED_DIR/$VOICE_CATALOG_BUNDLE" ]]; then
  echo "Applying voice-dialogue English translations..."
  "$PYTHON" "$ROOT/scripts/apply_voice_catalog_translations.py" \
    --source-bundle "$PATCHED_DIR/$VOICE_CATALOG_BUNDLE" \
    --output-bundle "$PATCHED_DIR/$VOICE_CATALOG_BUNDLE" \
    --translations "$ROOT/translations/voice_catalog.csv" \
    --report "$VOICE_CATALOG_REPORT"
fi

"$PYTHON" - "$REPORT" "$UI_REPORT" "$MASTERDATA_REPORT" "$VOICE_CATALOG_REPORT" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
rows: list[dict[str, object]] = []
for report_arg in sys.argv[2:]:
    report = Path(report_arg)
    if report.exists():
        rows.extend(json.loads(report.read_text(encoding="utf-8")))
output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
PY

echo "Pushing patched remote cache with matching metadata..."
"$PYTHON" "$ROOT/scripts/push_patched_remote_bundles.py" \
  --patched-dir "$PATCHED_DIR" \
  --report "$REPORT" \
  --package "$PACKAGE"

echo "Launching app..."
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
echo "Remote cache patch complete. Report: $REPORT"
