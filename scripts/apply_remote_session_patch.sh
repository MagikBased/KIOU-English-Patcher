#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE="${1:-com.neconome.shogi}"
WAIT_SECONDS="${2:-12}"

adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep "$WAIT_SECONDS"

"$ROOT/scripts/patch_remote_cache.sh" "$PACKAGE"
