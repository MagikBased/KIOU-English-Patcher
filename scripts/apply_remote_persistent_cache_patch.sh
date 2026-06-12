#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
LAUNCH_AFTER="${2:-1}"

adb shell am force-stop "$PACKAGE" >/dev/null

"$ROOT/.venv/bin/python" "$ROOT/scripts/push_patched_remote_bundles.py" \
  --patched-dir "$ROOT/patched/remote_target_bundles" \
  --report "$ROOT/reports/remote_patch_report.json" \
  --package "$PACKAGE"

if [[ "$LAUNCH_AFTER" != "0" ]]; then
  adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
fi

echo "Persistent cache patch applied with matching __data and __info files."
