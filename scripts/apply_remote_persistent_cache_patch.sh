#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
LAUNCH_AFTER="${2:-1}"

"$ROOT/scripts/patch_remote_cache.sh" "$PACKAGE"

if [[ "$LAUNCH_AFTER" == "0" ]]; then
  adb shell am force-stop "$PACKAGE" >/dev/null
fi
