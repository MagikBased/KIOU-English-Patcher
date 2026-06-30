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
MASTERDATA_BUNDLE_NAME="remote_assets__project_masterdata_runtimemasterdata.bundle"
VOICE_CATALOG_BUNDLE_NAME="remote_assets__project_sound_generated_voice_catalog_g.bundle"
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

echo "Pulling remote bundles selected from current downloaded manifest..."
"$PYTHON" - "$ROOT/reports/remote_patch_report.json" "$SOURCE_DIR" "$PACKAGE" <<'PY'
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve().parents[1] / "scripts"))
from patch_yooasset_remote_manifest import parse_manifest

report_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
package = sys.argv[3]

wanted: set[str] = {
    "remote_assets__project_masterdata_runtimemasterdata.bundle",
    "remote_assets__project_sound_generated_voice_catalog_g.bundle",
}
for row in json.loads(report_path.read_text(encoding="utf-8")):
    bundle_file = row["bundle_file"]
    if "__" in bundle_file:
        wanted.add(bundle_file.split("__", 1)[1])

manifest_root = f"/sdcard/Android/data/{package}/files/Bundles/Remote/ManifestFiles"
manifest_result = subprocess.run(
    ["adb", "shell", "find", manifest_root, "-maxdepth", "1", "-name", "Remote_asset-*.bytes", "-type", "f"],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
def version_key(value: str) -> tuple[tuple[int, ...], str]:
    name = Path(value).name
    parts = re.findall(r"\d+", name)
    return tuple(int(part) for part in parts) if parts else (0,), name

manifest_paths = [line.strip() for line in manifest_result.stdout.splitlines() if line.strip()]
remote_manifest = max(manifest_paths, key=version_key) if manifest_result.returncode == 0 and manifest_paths else ""
if not remote_manifest:
    print("Downloaded data manifest was not found. Launch the game and finish the update download.", file=sys.stderr)
    sys.exit(1)

manifest_path = out_dir.parent / "manifest" / Path(remote_manifest).name
manifest_path.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["adb", "pull", remote_manifest, str(manifest_path)], check=True)
manifest = parse_manifest(manifest_path.read_bytes())
by_name = {bundle.bundle_name: bundle for bundle in manifest.bundles}
missing_names = sorted(name for name in wanted if name not in by_name)
if missing_names:
    print("Downloaded data manifest is missing required bundles:", file=sys.stderr)
    for name in missing_names[:20]:
        print(name, file=sys.stderr)
    sys.exit(1)

missing: list[str] = []
for bundle_name in sorted(wanted):
    bundle = by_name[bundle_name]
    hash_value = bundle.file_hash
    name = f"{hash_value}__{bundle_name}"
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
print(f"Pulled {len(wanted)} remote bundles")
PY

echo "Applying remote English translations..."
TRANSLATION_ARGS=(--translations "$ROOT/translations/remote_ui.csv")
"$PYTHON" "$ROOT/scripts/apply_bundle_translations.py" \
  --source-dir "$SOURCE_DIR" \
  --patched-dir "$PATCHED_DIR" \
  "${TRANSLATION_ARGS[@]}" \
  --report "$UI_REPORT"

MASTERDATA_MATCH=("$PATCHED_DIR"/*__"$MASTERDATA_BUNDLE_NAME")
if [[ -f "$ROOT/translations/remote_masterdata.csv" && -f "${MASTERDATA_MATCH[0]}" ]]; then
  echo "Applying master-data English translations..."
  "$PYTHON" "$ROOT/scripts/apply_masterdata_translations.py" \
    --source-bundle "${MASTERDATA_MATCH[0]}" \
    --output-bundle "${MASTERDATA_MATCH[0]}" \
    --translations "$ROOT/translations/remote_masterdata.csv" \
    --report "$MASTERDATA_REPORT"
fi

VOICE_CATALOG_MATCH=("$PATCHED_DIR"/*__"$VOICE_CATALOG_BUNDLE_NAME")
if [[ -f "$ROOT/translations/voice_catalog.csv" && -f "${VOICE_CATALOG_MATCH[0]}" ]]; then
  echo "Applying voice-dialogue English translations..."
  "$PYTHON" "$ROOT/scripts/apply_voice_catalog_translations.py" \
    --source-bundle "${VOICE_CATALOG_MATCH[0]}" \
    --output-bundle "${VOICE_CATALOG_MATCH[0]}" \
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
