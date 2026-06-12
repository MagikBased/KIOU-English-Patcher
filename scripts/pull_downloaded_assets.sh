#!/usr/bin/env bash
set -euo pipefail

PACKAGE="${1:-com.neconome.shogi}"
OUT_DIR="${2:-downloaded/device}"

mkdir -p "$OUT_DIR"

echo "Checking adb devices..."
adb devices -l

echo "Listing likely external app data paths..."
adb shell "find /sdcard/Android/data/$PACKAGE -maxdepth 8 -type f 2>/dev/null | sed -n '1,200p'" || true

echo "Pulling /sdcard/Android/data/$PACKAGE ..."
adb pull "/sdcard/Android/data/$PACKAGE" "$OUT_DIR/external" || true

echo "Trying run-as internal app data access..."
if adb shell "run-as $PACKAGE sh -c 'pwd >/dev/null'" >/dev/null 2>&1; then
  adb shell "run-as $PACKAGE sh -c 'find files cache code_cache -maxdepth 8 -type f 2>/dev/null'" \
    | sed 's/\r$//' > "$OUT_DIR/internal_file_list.txt"
  while IFS= read -r relpath; do
    [ -n "$relpath" ] || continue
    mkdir -p "$OUT_DIR/internal/$(dirname "$relpath")"
    adb exec-out "run-as $PACKAGE cat '$relpath'" > "$OUT_DIR/internal/$relpath" || true
  done < "$OUT_DIR/internal_file_list.txt"
else
  echo "run-as is unavailable; APK is probably not debuggable."
fi

echo "Pulled files:"
find "$OUT_DIR" -type f -printf '%s %p\n' | sort -nr | sed -n '1,100p'
