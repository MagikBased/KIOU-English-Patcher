#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_APK="${1:-}"
OUTPUT_APK="${2:-$ROOT/output/KIOU_RELEASE_english.apk}"
ALLOW_UNKNOWN="${ALLOW_UNKNOWN:-0}"
PYTHON="$ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

if [[ -z "$INPUT_APK" ]]; then
  echo "Usage: scripts/patch_apk.sh /path/to/KIOU_RELEASE.apk [output.apk]" >&2
  echo "Set ALLOW_UNKNOWN=1 to try patching an untested APK build." >&2
  exit 2
fi

for tool in unzip zipalign apksigner keytool; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 2
  fi
done

VERIFY_ARGS=("$INPUT_APK")
if [[ "$ALLOW_UNKNOWN" == "1" ]]; then
  VERIFY_ARGS+=("--allow-unknown")
fi
"$PYTHON" "$ROOT/scripts/verify_apk.py" "${VERIFY_ARGS[@]}"

WORK_DIR="$ROOT/work/apk_patcher"
EXTRACTED_DIR="$WORK_DIR/extracted_apk"
PATCHED_DIR="$WORK_DIR/patched_apk"
REPORT="$ROOT/output/local_ui_patch_report.json"
UNSIGNED_APK="$ROOT/output/KIOU_RELEASE_english-unsigned.apk"
ALIGNED_APK="$ROOT/output/KIOU_RELEASE_english-aligned.apk"
KEYSTORE="$ROOT/work/kiou_patch_debug.keystore"
KEY_ALIAS="kiou_patch"
KEY_PASS="kioupatch"

rm -rf "$WORK_DIR"
mkdir -p "$EXTRACTED_DIR" "$ROOT/output" "$ROOT/work"

echo "Extracting APK..."
unzip -q "$INPUT_APK" -d "$EXTRACTED_DIR"

echo "Removing stale APK signatures..."
find "$EXTRACTED_DIR/META-INF" -maxdepth 1 -type f \
  \( -name '*.RSA' -o -name '*.DSA' -o -name '*.EC' -o -name '*.SF' -o -name 'MANIFEST.MF' \) \
  -delete 2>/dev/null || true

echo "Applying local English translations..."
"$PYTHON" "$ROOT/scripts/apply_local_ui_translations.py" \
  --source-apk-dir "$EXTRACTED_DIR" \
  --patched-apk-dir "$PATCHED_DIR" \
  --translations "$ROOT/translations/local_ui.csv" \
  --report "$REPORT"

echo "Repacking APK..."
"$PYTHON" "$ROOT/scripts/repack_apk.py" \
  --original-apk "$INPUT_APK" \
  --apk-dir "$PATCHED_DIR" \
  --output "$UNSIGNED_APK"

echo "Zipaligning APK..."
mkdir -p "$(dirname "$OUTPUT_APK")"
rm -f "$ALIGNED_APK" "$OUTPUT_APK" "$OUTPUT_APK.idsig"
zipalign -p -f 4 "$UNSIGNED_APK" "$ALIGNED_APK"

if [[ -f "$KEYSTORE" ]] && ! keytool -list -keystore "$KEYSTORE" -storepass "$KEY_PASS" -alias "$KEY_ALIAS" >/dev/null 2>&1; then
  echo "Existing patch keystore is not usable with this script; regenerating it..."
  rm -f "$KEYSTORE"
fi

if [[ ! -f "$KEYSTORE" ]]; then
  echo "Creating debug patch signing key..."
  keytool -genkeypair \
    -keystore "$KEYSTORE" \
    -storepass "$KEY_PASS" \
    -keypass "$KEY_PASS" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -dname "CN=Kiou English Patch,O=Fan Patch,C=US" >/dev/null
fi

echo "Signing APK..."
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$KEY_ALIAS" \
  --ks-pass "pass:$KEY_PASS" \
  --key-pass "pass:$KEY_PASS" \
  --out "$OUTPUT_APK" \
  "$ALIGNED_APK"

apksigner verify --verbose "$OUTPUT_APK" >/dev/null
echo "Wrote $OUTPUT_APK"
echo "Local translation report: $REPORT"
