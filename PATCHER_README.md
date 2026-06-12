# Kiou English APK Patcher

This patcher applies the current English text patch to a user-provided Kiou APK and signs the result with a local debug patch key. It does not include or redistribute the APK or downloaded game assets.

## Requirements

- Python 3
- Tkinter for Python. This is included with the standard Windows and macOS Python installers. Some Linux distros package it separately as `python3-tk`.
- Android platform/build tools: `adb`, `zipalign`, `apksigner`, `keytool`
- A legally obtained Kiou APK matching the tested build

The GUI and Python backend work on Linux, macOS, and Windows. The shell scripts are still useful on Linux/macOS, but Windows users should use the Python GUI.

The patcher looks for Android tools in `PATH`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and common Android SDK install paths. On Windows, installing Android Studio and the Android SDK Build-Tools is usually enough.

Set up Python dependencies from this repository:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## GUI

Launch the cross-platform GUI:

```bash
.venv/bin/python scripts/patcher_gui.py
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python scripts\patcher_gui.py
```

The GUI can patch the APK, install it with ADB, and patch downloaded remote data after the game finishes its additional data download.

## Native Desktop Builds

The project includes PyInstaller build helpers for native desktop artifacts:

- Windows: `dist\KiouEnglishPatcher.exe`
- macOS: `dist/KiouEnglishPatcher.app`
- Linux: `dist/KiouEnglishPatcher/KiouEnglishPatcher`

PyInstaller builds for the OS it is running on. Build the Windows `.exe` on Windows, and build the macOS `.app` on macOS.

On Windows PowerShell or Command Prompt:

```bat
build_windows.bat
```

On macOS:

```bash
chmod +x build_macos.command
./build_macos.command
```

On Linux:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

The packaged app still expects Android SDK tools to be installed on the user's machine. It searches `PATH`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and common Android SDK install locations.

These local builds are unsigned. Windows may show a SmartScreen warning, and macOS Gatekeeper may require right-clicking the app and choosing Open unless you later sign and notarize the app with an Apple Developer account.

There is also a GitHub Actions workflow at `.github/workflows/build-desktop.yml`. It can produce downloadable Windows, macOS, and Linux artifacts from GitHub-hosted native runners.

## GitHub Releases

To publish a release with desktop builds, commit and push the patcher files, then create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `Build Desktop Patcher` workflow will build and attach these release assets:

- `KiouEnglishPatcher.exe`
- `KiouEnglishPatcher-macOS.zip`
- `KiouEnglishPatcher-Linux-x86_64.tar.gz`

You can also run the workflow manually from the GitHub Actions tab. Leave `release_tag` blank to only build downloadable workflow artifacts. Set `release_tag` to a tag such as `v0.1.0` to create or update that GitHub Release.

The release assets are patchers only. Do not attach the original APK, patched APKs, downloaded game assets, or extracted game files.

Packaged app state, reports, temporary files, and the local signing key are written to:

```text
~/.kiou-english-patcher
```

## Patch the APK

Run the patcher with your original APK path:

```bash
scripts/patch_apk.sh /path/to/KIOU_RELEASE.apk output/KIOU_RELEASE_english.apk
```

The script will:

- verify the APK hash against the tested build
- patch bundled Unity UI text using `translations/local_ui.csv`
- remove stale APK signatures
- rebuild, zipalign, and sign the patched APK
- write a report to `output/local_ui_patch_report.json`

The tested APK SHA256 is:

```text
c23f77caacf7cb988bcbf1b9d91ec5708eef6cc6056faee38f0d8ea778ec898f
```

To try an untested APK build anyway:

```bash
ALLOW_UNKNOWN=1 scripts/patch_apk.sh /path/to/KIOU_RELEASE.apk output/KIOU_RELEASE_english.apk
```

Untested builds may fail to patch or may patch only partially if Unity bundle contents changed.

## Install the Patched APK

Install with ADB:

```bash
adb install -r output/KIOU_RELEASE_english.apk
```

If Android reports a signature mismatch, uninstall the existing original app first, then install the patched APK:

```bash
adb uninstall com.neconome.shogi
adb install output/KIOU_RELEASE_english.apk
```

Uninstalling removes the app's local data. Keep that in mind before replacing an existing install.

## Patch Downloaded Remote Data

Some UI text lives in Unity bundles downloaded after first launch. After installing the patched APK, launch the game once and let the additional data download finish. Then connect the device with USB debugging enabled and run:

```bash
scripts/patch_remote_cache.sh
```

That script will:

- stop the app
- pull the downloaded remote bundles needed by `reports/remote_patch_report.json`
- patch them using `translations/remote_ui.csv`
- push patched `__data` files plus matching YooAsset cache metadata
- relaunch the app
- write a report to `output/remote_cache_patch_report.json`

If the script says required bundles are missing, launch the game, finish the additional data download, then retry.

The default package is `com.neconome.shogi`. To patch a different package name:

```bash
scripts/patch_remote_cache.sh com.example.package
```

## Current Limitations

- The APK patch is version-locked to the tested APK hash above unless `ALLOW_UNKNOWN=1` is used.
- The remote cache patch targets the current known downloaded bundle hash set in `reports/remote_patch_report.json`.
- A future game update may require rebuilding the translation CSVs and remote patch report.
- Image/icon text is not replaced by this APK patcher yet; exported atlases are available separately for manual editing work.
