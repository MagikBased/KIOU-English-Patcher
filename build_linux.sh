#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt -r requirements-packaging.txt
.venv/bin/python scripts/build_desktop_app.py --clean --onedir
echo
echo "Linux build output: dist/KiouEnglishPatcher/KiouEnglishPatcher"
