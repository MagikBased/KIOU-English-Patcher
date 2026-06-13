# Kiou English Patcher

Desktop patcher for applying the current English patch to a user-provided Kiou Android APK and its downloaded Unity data cache.

This project does not include, distribute, or download the original game APK, patched APKs, downloaded game assets, or extracted game files. You must provide your own legally obtained APK.

## Download

Most users should download the latest desktop patcher from:

```text
https://github.com/MagikBased/KIOU-English-Patcher/releases/latest
```

Choose the file for your computer:

- Windows: `KiouEnglishPatcher.exe`
- macOS: `KiouEnglishPatcher-macOS.zip`
- Linux: `KiouEnglishPatcher-Linux-x86_64.tar.gz`

These builds are unsigned. Windows may show a SmartScreen warning, and macOS Gatekeeper may require right-clicking the app and choosing `Open`.

## Before You Start

You need:

- A legally obtained Kiou APK.
- Android Studio or Android SDK Platform Tools installed.
- USB debugging enabled if patching a phone.
- An emulator or phone visible to ADB.

The patcher looks for Android tools in `PATH`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and common Android SDK install locations. It needs:

- `adb`
- `zipalign`
- `apksigner`
- `keytool`

The tested APK SHA256 is:

```text
c23f77caacf7cb988bcbf1b9d91ec5708eef6cc6056faee38f0d8ea778ec898f
```

Untested APK builds may fail or patch only partially if the game files changed.

## Running the Patcher

### Windows

Download `KiouEnglishPatcher.exe`, then double-click it.

If Windows blocks it, choose `More info`, then `Run anyway`.

### macOS

Download `KiouEnglishPatcher-macOS.zip`, unzip it, then open `KiouEnglishPatcher.app`.

If macOS blocks it, right-click the app and choose `Open`.

### Linux

Download `KiouEnglishPatcher-Linux-x86_64.tar.gz`, then run:

```bash
tar -xzf KiouEnglishPatcher-Linux-x86_64.tar.gz
./KiouEnglishPatcher/KiouEnglishPatcher
```

The packaged Linux build is built on Ubuntu 22.04 and expects glibc 2.35 or newer. If your distribution is older, run from source instead.

## Guided Patch Flow

The GUI walks through the normal patch process:

1. Select your original APK with `Browse`.
2. Click `Patch APK`.
3. Choose the target emulator or phone from the `Target` dropdown.
4. Click `Install Patched APK`.
5. Click `Launch Game`.
6. Let the game finish its forced additional-data download.
7. Return to the patcher and click `Check Downloaded Data`.
8. When all required bundles are found, click `Patch Downloaded Data`.

If more than one phone or emulator is connected, you must choose the intended target from the `Target` dropdown. Otherwise ADB cannot know where to install or patch.

The downloaded-data step is required because some English text lives outside the APK in Unity bundles that the game downloads after first launch. A fresh install, emulator reset, app data clear, or game asset update may require running `Patch Downloaded Data` again after the game finishes downloading.

## Install Notes

If Android reports a signature mismatch, uninstall the existing original app first, then install the patched APK from the GUI.

Uninstalling the app removes its local data.

## Where Files Are Written

Packaged desktop builds write temporary files, reports, and the local patch signing key to:

```text
~/.kiou-english-patcher
```

## Developer Setup

To run the GUI from source:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/patcher_gui.py
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\patcher_gui.py
```

## Local Desktop Builds

PyInstaller builds for the OS it is running on. Build the Windows `.exe` on Windows, and build the macOS `.app` on macOS.

Windows:

```bat
build_windows.bat
```

macOS:

```bash
chmod +x build_macos.command
./build_macos.command
```

Linux:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

## Publishing Releases

GitHub Actions builds release assets when a version tag is pushed:

```bash
git tag v0.1.2
git push origin v0.1.2
```

The workflow attaches:

- `KiouEnglishPatcher.exe`
- `KiouEnglishPatcher-macOS.zip`
- `KiouEnglishPatcher-Linux-x86_64.tar.gz`

Release assets should contain the patcher only. Do not attach the original APK, patched APKs, downloaded game assets, or extracted game files.

## Current Limitations

- The APK patch is version-locked to the tested APK hash unless `Try untested APK build` is enabled.
- The downloaded-data patch targets the currently known remote bundle hash set in `reports/remote_patch_report.json`.
- A future game update may require rebuilding the translation CSVs and remote patch report.
- Image/icon text is not replaced by this patcher yet.
