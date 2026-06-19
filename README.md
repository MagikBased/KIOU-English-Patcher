# Kiou English Patcher

Desktop patcher for applying the current English patch to a user-provided Kiou Android APK, or to the Steam version's local install and downloaded Unity data cache.

This project does not include, distribute, or download the original game APK, patched APKs, downloaded game assets, or extracted game files. You must provide your own legally obtained APK.

## Warning

Modifying KIOU game files may violate KIOU's terms of service or other rules set by the game publisher/platform. Use this patcher at your own risk. The project is provided for fan translation purposes and cannot guarantee account safety, compatibility with future updates, or acceptance by the game's official services.

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

For Android, you need:

- A legally obtained Kiou APK.
- Android Studio or a JDK installed so Java `keytool` is available.
- USB debugging enabled if patching a phone.
- An emulator or phone visible to ADB.

The Android page has an `Install / Repair Android Tools` button. It downloads Google's official Android SDK command-line tools after you confirm the Android SDK license prompt, then installs `platform-tools` and `build-tools` into the patcher's private SDK folder:

```text
~/.kiou-english-patcher/android-sdk
```

The patcher also looks for existing Android tools in `PATH`, `ANDROID_HOME`, `ANDROID_SDK_ROOT`, and common Android SDK install locations. It needs:

- `adb`
- `zipalign`
- `apksigner`
- `keytool`

Steam users do not need these Android tools.

The tested APK SHA256 is:

```text
c23f77caacf7cb988bcbf1b9d91ec5708eef6cc6056faee38f0d8ea778ec898f
```

Untested APK builds may fail or patch only partially if the game files changed.

For Steam, you need:

- KIOU installed through Steam.
- The game launched once so it can finish its first update/download. The patcher can launch it for you.
- The game closed before clicking `Patch Steam Game`.

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

When the app starts, choose `Android` or `Steam`.

### Android

The GUI walks through the normal patch process:

1. Select your original APK with `Browse`.
2. If any Android tools show `Not found`, click `Install / Repair Android Tools`.
3. Click `Patch APK`.
4. Choose the target emulator or phone from the `Target` dropdown.
5. Click `Install Patched APK`.
6. Click `Launch Game`.
7. Let the game finish its forced additional-data download.
8. Return to the patcher and click `Check Downloaded Data`.
9. When all required bundles are found, click `Patch Downloaded Data`.

If more than one phone or emulator is connected, you must choose the intended target from the `Target` dropdown. Otherwise ADB cannot know where to install or patch.

The downloaded-data step is required because some English text lives outside the APK in Unity bundles that the game downloads after first launch. A fresh install, emulator reset, app data clear, or game asset update may require running `Patch Downloaded Data` again after the game finishes downloading.

If a game update restores Japanese text, click `Update Patch Data` first, then run `Patch Downloaded Data` again. The patcher reads the current in-game downloaded manifest and maps patch targets by bundle name, so hash-only server updates do not require a new GUI download.

### Steam

The Steam workflow patches files in your local Steam install:

1. Install KIOU in Steam.
2. Open the patcher and choose `Steam`.
3. Use `Auto Detect` or `Browse` to select the KIOU install folder.
4. Click `Launch Game`, or launch KIOU from Steam yourself.
5. Let the game finish its first update/download, then close the game.
6. Click `Check Status`.
7. Click `Patch Steam Game`.

If `Check Status` says the first update is not finished, launch the game once and let the in-game update/download complete. A newly installed Steam copy may not have the remote bundle manifest until after that first launch.

The Steam patcher backs up overwritten files under:

```text
~/.kiou-english-patcher/work/steam_patcher/backups
```

Use `Uninstall Patch` on the Steam page to restore backed-up original files for the selected KIOU install. This is available only after the Steam patcher has patched the game at least once.

Steam game updates may restore original Japanese files. If that happens, launch the game once after the update finishes, close it, then run `Patch Steam Game` again.

If Steam receives new text/content, click `Update Patch Data` before patching. The patcher uses the latest Steam `Remote_asset-*.bytes` manifest it finds after the game's update finishes.

## Patch Data Updates

The desktop app includes a bundled patch data pack, but newer translations can be installed without downloading a new GUI.

Use these buttons in the GUI:

- `Update Patch Data`: downloads the latest patch data pack from this project's GitHub Releases.
- `Import ZIP`: installs a patch data ZIP manually, useful if the automatic download is blocked.

Patch data is data-only. It contains CSV/JSON translation data and target bundle names, not executable code. Installed patch data is stored under:

```text
~/.kiou-english-patcher/patch-data/current
```

The GUI falls back to its bundled patch data if no installed pack exists.

## Install Notes

If Android reports a signature mismatch, uninstall the existing original app first, then install the patched APK from the GUI.

Uninstalling the app removes its local data.

## Where Files Are Written

Packaged desktop builds write temporary files, reports, and the local patch signing key to:

```text
~/.kiou-english-patcher
```

## Brand Assets

The platform selection icons use official Android and Steam brand assets:

- Android robot image from the Android Developers brand guidelines. The Android robot is reproduced from work created and shared by Google and used according to the Creative Commons 3.0 Attribution License.
- Steam logo image from the Steamworks Branding Guidelines. ©2026 Valve Corporation. Steam and the Steam logo are trademarks and/or registered trademarks of Valve Corporation in the U.S. and/or other countries.

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

## Publishing Patch Data

Patch data can be released separately from the GUI. After updating translation CSVs or the remote patch report, build a data pack:

```bash
.venv/bin/python scripts/build_patch_data_pack.py --version 0.1.10
```

This writes:

```text
dist/patch-data/KIOU-English-PatchData-v0.1.10.zip
dist/patch-data/patch-data-index.json
```

Attach both files to a GitHub Release. The GUI's `Update Patch Data` button checks:

```text
https://github.com/MagikBased/KIOU-English-Patcher/releases/latest/download/patch-data-index.json
```

Using the GitHub CLI, upload both files to the release that should be treated as latest:

```bash
gh release upload v0.1.10 \
  dist/patch-data/KIOU-English-PatchData-v0.1.10.zip \
  dist/patch-data/patch-data-index.json \
  --clobber
```

If `Update Patch Data` shows that no online patch data is published, the latest release is missing `patch-data-index.json`. Upload the two files above or use `Import ZIP` locally.

Use a normal GUI release for engine changes. Use a patch-data release when only translations, target bundle names, or other data-only patch inputs changed.

## Current Limitations

- The APK patch is version-locked to the tested APK hash unless `Try untested APK build` is enabled.
- The downloaded-data patch resolves current Android/Steam bundle hashes from the game's manifest, but new or changed text still requires updated patch data.
- Image/icon text is not replaced by this patcher yet.
- Steam support is experimental and targets the current Steam build/cache layout.
