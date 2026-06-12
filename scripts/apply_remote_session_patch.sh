#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
WAIT_SECONDS="${2:-12}"

adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep "$WAIT_SECONDS"

"$ROOT/.venv/bin/python" "$ROOT/scripts/push_patched_remote_bundles.py" \
  --patched-dir "$ROOT/patched/remote_target_bundles" \
  --report "$ROOT/reports/remote_patch_report.json" \
  --package "$PACKAGE"

echo "Session patch applied with matching cache metadata."
