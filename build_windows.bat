@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
)
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-packaging.txt
.\.venv\Scripts\python scripts\build_desktop_app.py --clean --onefile
echo.
echo Windows build output: dist\KiouEnglishPatcher.exe
