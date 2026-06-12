#!/usr/bin/env python3
"""Cross-platform patcher backend for the Kiou English patch."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from apply_bundle_translations import load_translations as load_bundle_translations
from apply_bundle_translations import patch_bundle as patch_remote_bundle
from apply_local_ui_translations import load_translations as load_local_translations
from apply_local_ui_translations import patch_bundle as patch_local_bundle
from apply_masterdata_translations import load_translations as load_masterdata_translations
from apply_masterdata_translations import patch_bundle as patch_masterdata_bundle
from apply_voice_catalog_translations import load_translations as load_voice_catalog_translations
from apply_voice_catalog_translations import patch_bundle as patch_voice_catalog_bundle
from push_patched_remote_bundles import HASH_RE, app_cache_info_bytes
from verify_apk import SUPPORTED_APK_SHA256, sha256_file


def resource_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parents[1]


def state_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / ".kiou-english-patcher"
    return resource_root()


ROOT = resource_root()
STATE_ROOT = state_root()
DEFAULT_PACKAGE = "com.neconome.shogi"
MASTERDATA_BUNDLE = (
    "77466306cf3a4254b1dac34dde0a9942__"
    "remote_assets__project_masterdata_runtimemasterdata.bundle"
)
VOICE_CATALOG_BUNDLE = (
    "2f0426ad7cc63c421dbf20786c35cfa0__"
    "remote_assets__project_sound_generated_voice_catalog_g.bundle"
)
KEY_ALIAS = "kiou_patch"
KEY_PASS = "kioupatch"
LogFn = Callable[[str], None]


class PatcherError(RuntimeError):
    """Raised for user-actionable patcher failures."""


def adb_tool() -> str:
    return required_tools(["adb"])["adb"]


def default_log(message: str) -> None:
    print(message, flush=True)


def exe_names(name: str) -> list[str]:
    if os.name != "nt":
        return [name]
    suffixes = [".bat", ".cmd", ".exe", ""]
    return [name + suffix if not name.lower().endswith(suffix) else name for suffix in suffixes]


def search_android_sdk_tool(name: str) -> Path | None:
    roots = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        str(Path.home() / "AppData" / "Local" / "Android" / "Sdk") if os.name == "nt" else None,
        str(Path.home() / "Library" / "Android" / "sdk") if sys.platform == "darwin" else None,
        str(Path.home() / "Android" / "Sdk"),
    ]
    for root_text in roots:
        if not root_text:
            continue
        sdk_root = Path(root_text)
        if not sdk_root.exists():
            continue
        candidates: list[Path] = []
        if name == "adb":
            candidates += [sdk_root / "platform-tools" / candidate for candidate in exe_names("adb")]
        elif name in {"zipalign", "apksigner"}:
            build_tools = sdk_root / "build-tools"
            if build_tools.exists():
                for version_dir in sorted(build_tools.iterdir(), reverse=True):
                    if version_dir.is_dir():
                        candidates += [version_dir / candidate for candidate in exe_names(name)]
        for path in candidates:
            if path.is_file():
                return path
    return None


def find_tool(name: str) -> str | None:
    for candidate in exe_names(name):
        path = shutil.which(candidate)
        if path:
            return path

    sdk_tool = search_android_sdk_tool(name)
    if sdk_tool:
        return str(sdk_tool)

    if name == "keytool":
        roots = [
            os.environ.get("JAVA_HOME"),
            str(STATE_ROOT / "android-studio" / "jbr"),
            str(ROOT / "android-studio" / "jbr"),
        ]
        if os.name == "nt":
            roots += [
                r"C:\Program Files\Android\Android Studio\jbr",
                r"C:\Program Files\Android\Android Studio\jre",
            ]
        elif sys.platform == "darwin":
            roots += [
                "/Applications/Android Studio.app/Contents/jbr/Contents/Home",
                "/Applications/Android Studio.app/Contents/jre/Contents/Home",
            ]
        else:
            roots += [
                "/opt/android-studio/jbr",
                "/usr/local/android-studio/jbr",
                str(Path.home() / "android-studio" / "jbr"),
            ]
        for root_text in roots:
            if not root_text:
                continue
            for candidate in exe_names("keytool"):
                path = Path(root_text) / "bin" / candidate
                if path.is_file():
                    return str(path)
    return None


def required_tools(names: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        path = find_tool(name)
        if path:
            found[name] = path
        else:
            missing.append(name)
    if missing:
        raise PatcherError("Missing required tools: " + ", ".join(missing))
    return found


def describe_tools() -> dict[str, str | None]:
    return {name: find_tool(name) for name in ["adb", "zipalign", "apksigner", "keytool"]}


def run(
    command: list[str],
    log: LogFn = default_log,
    check: bool = True,
    cwd: Path = STATE_ROOT,
) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(str(part) for part in command))
    process = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = process.stdout.strip()
    if output:
        log(output)
    if check and process.returncode != 0:
        raise PatcherError(f"Command failed with exit code {process.returncode}: {command[0]}")
    return process


def run_quiet(command: list[str], cwd: Path = STATE_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def adb_devices() -> list[dict[str, str]]:
    adb = adb_tool()
    result = run_quiet([adb, "devices"])
    if result.returncode != 0:
        raise PatcherError(result.stdout.strip() or "Unable to list ADB devices.")

    devices: list[dict[str, str]] = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        devices.append({"serial": parts[0], "state": parts[1]})
    return devices


def device_status(serial: str | None = None) -> dict[str, object]:
    serial = (serial or "").strip()
    devices = adb_devices()
    authorized = [device for device in devices if device["state"] == "device"]
    unauthorized = [device for device in devices if device["state"] == "unauthorized"]
    offline = [device for device in devices if device["state"] == "offline"]

    if serial:
        selected = next((device for device in devices if device["serial"] == serial), None)
        if selected is None:
            message = f"Selected device not found: {serial}"
            ready = False
        elif selected["state"] == "device":
            message = f"Connected: {serial}"
            ready = True
        else:
            message = f"Selected device {serial} is {selected['state']}."
            ready = False
    elif not devices:
        message = "No ADB device detected."
        ready = False
    elif len(authorized) == 1:
        message = f"Connected: {authorized[0]['serial']}"
        ready = True
    elif len(authorized) > 1:
        message = f"{len(authorized)} devices connected. Select a target device."
        ready = False
    elif unauthorized:
        message = "Device detected but USB debugging is not authorized."
        ready = False
    elif offline:
        message = "Device detected but offline. Reconnect it or restart ADB."
        ready = False
    else:
        message = "No authorized ADB device detected."
        ready = False
    return {
        "devices": devices,
        "authorized": authorized,
        "ready": ready,
        "message": message,
        "selected_serial": serial,
    }


def adb_base_command(serial: str | None = None) -> list[str]:
    command = [adb_tool()]
    serial = (serial or os.environ.get("ADB_DEVICE_SERIAL") or "").strip()
    if serial:
        command += ["-s", serial]
    return command


def require_ready_device(serial: str | None = None) -> None:
    status = device_status(serial)
    if not status["ready"]:
        raise PatcherError(str(status["message"]))


def app_installed(package: str = DEFAULT_PACKAGE, serial: str | None = None) -> bool:
    package = package.strip() or DEFAULT_PACKAGE
    result = run_quiet(adb_base_command(serial) + ["shell", "pm", "path", package])
    return result.returncode == 0 and bool(result.stdout.strip())


def launch_app(package: str = DEFAULT_PACKAGE, log: LogFn = default_log, serial: str | None = None) -> None:
    package = package.strip() or DEFAULT_PACKAGE
    require_ready_device(serial)
    run(
        adb_base_command(serial) + ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
        log=log,
    )


def remote_cache_status(package: str = DEFAULT_PACKAGE, serial: str | None = None) -> dict[str, object]:
    package = package.strip() or DEFAULT_PACKAGE
    require_ready_device(serial)
    rows = remote_bundle_rows()
    found = 0
    missing: list[str] = []
    for hash_value in sorted(rows):
        remote = (
            f"/sdcard/Android/data/{package}/files/Bundles/Remote/"
            f"BundleFiles/{hash_value[:2]}/{hash_value}/__data"
        )
        result = run_quiet(adb_base_command(serial) + ["shell", "test", "-f", remote])
        if result.returncode == 0:
            found += 1
        else:
            missing.append(hash_value)
    return {
        "required": len(rows),
        "found": found,
        "missing": missing,
        "ready": found == len(rows),
    }


def guided_status(package: str = DEFAULT_PACKAGE, serial: str | None = None) -> dict[str, object]:
    package = package.strip() or DEFAULT_PACKAGE
    status = device_status(serial)
    if not status["ready"]:
        status.update(
            {
                "installed": False,
                "cache_required": len(remote_bundle_rows()),
                "cache_found": 0,
                "cache_ready": False,
            }
        )
        return status

    installed = app_installed(package, serial)
    cache = (
        remote_cache_status(package, serial)
        if installed
        else {"required": len(remote_bundle_rows()), "found": 0, "ready": False}
    )
    status.update(
        {
            "installed": installed,
            "cache_required": cache["required"],
            "cache_found": cache["found"],
            "cache_ready": cache["ready"],
        }
    )
    return status


def safe_extract_apk(apk_path: Path, dest_dir: Path) -> None:
    dest_dir = dest_dir.resolve()
    with zipfile.ZipFile(apk_path, "r") as archive:
        for info in archive.infolist():
            target = (dest_dir / info.filename).resolve()
            if not str(target).startswith(str(dest_dir) + os.sep):
                raise PatcherError(f"Refusing unsafe APK zip path: {info.filename}")
        archive.extractall(dest_dir)


def remove_apk_signatures(apk_dir: Path) -> None:
    meta_inf = apk_dir / "META-INF"
    if not meta_inf.exists():
        return
    for path in meta_inf.iterdir():
        if not path.is_file():
            continue
        if path.name == "MANIFEST.MF" or path.suffix.upper() in {".RSA", ".DSA", ".EC", ".SF"}:
            path.unlink()


def iter_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def repack_apk(original_apk: Path, apk_dir: Path, output_apk: Path) -> None:
    original_infos: dict[str, zipfile.ZipInfo] = {}
    with zipfile.ZipFile(original_apk, "r") as original:
        for info in original.infolist():
            if not info.is_dir():
                original_infos[info.filename] = info

    output_apk.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_apk, "w", allowZip64=True) as out:
        for file_path in iter_files(apk_dir):
            arcname = file_path.relative_to(apk_dir).as_posix()
            original_info = original_infos.get(arcname)
            info = zipfile.ZipInfo(arcname)
            if original_info:
                info.date_time = original_info.date_time
                info.compress_type = original_info.compress_type
                info.external_attr = original_info.external_attr
                info.create_system = original_info.create_system
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = stat.S_IMODE(file_path.stat().st_mode)
                info.external_attr = (mode or 0o644) << 16
            out.writestr(info, file_path.read_bytes())


def ensure_keystore(keytool: str, keystore: Path, log: LogFn) -> None:
    if keystore.exists():
        result = run(
            [
                keytool,
                "-list",
                "-keystore",
                str(keystore),
                "-storepass",
                KEY_PASS,
                "-alias",
                KEY_ALIAS,
            ],
            log=log,
            check=False,
        )
        if result.returncode == 0:
            return
        log("Existing patch keystore is not usable with this patcher; regenerating it.")
        keystore.unlink()

    keystore.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            keytool,
            "-genkeypair",
            "-keystore",
            str(keystore),
            "-storepass",
            KEY_PASS,
            "-keypass",
            KEY_PASS,
            "-alias",
            KEY_ALIAS,
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "10000",
            "-dname",
            "CN=Kiou English Patch,O=Fan Patch,C=US",
        ],
        log=log,
    )


def patch_apk(
    input_apk: Path,
    output_apk: Path,
    allow_unknown: bool = False,
    log: LogFn = default_log,
) -> Path:
    input_apk = input_apk.expanduser().resolve()
    output_apk = output_apk.expanduser().resolve()
    if not input_apk.is_file():
        raise PatcherError(f"APK not found: {input_apk}")

    tools = required_tools(["zipalign", "apksigner", "keytool"])

    digest = sha256_file(input_apk)
    log(f"APK SHA256: {digest}")
    if digest in SUPPORTED_APK_SHA256:
        log(f"Supported build: {SUPPORTED_APK_SHA256[digest]}")
    elif allow_unknown:
        log("Unsupported or untested APK build. Continuing because allow-unknown is enabled.")
    else:
        raise PatcherError("Unsupported or untested APK build. Enable allow-unknown to try anyway.")

    work_dir = STATE_ROOT / "work" / "gui_apk_patcher"
    extracted_dir = work_dir / "extracted_apk"
    patched_dir = work_dir / "patched_apk"
    unsigned_apk = STATE_ROOT / "output" / "KIOU_RELEASE_english-unsigned.apk"
    aligned_apk = STATE_ROOT / "output" / "KIOU_RELEASE_english-aligned.apk"
    report = STATE_ROOT / "output" / "local_ui_patch_report.json"
    keystore = STATE_ROOT / "work" / "kiou_patch_debug.keystore"

    shutil.rmtree(work_dir, ignore_errors=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (STATE_ROOT / "output").mkdir(parents=True, exist_ok=True)

    log("Extracting APK...")
    safe_extract_apk(input_apk, extracted_dir)

    log("Removing stale APK signatures...")
    remove_apk_signatures(extracted_dir)

    log("Applying local English translations...")
    translations = load_local_translations(ROOT / "translations" / "local_ui.csv")
    if not translations:
        raise PatcherError("No local translations loaded.")
    shutil.rmtree(patched_dir, ignore_errors=True)
    shutil.copytree(extracted_dir, patched_dir)

    reports: list[dict[str, object]] = []
    bundles_dir = patched_dir / "assets" / "Bundles" / "Local"
    for bundle_path in sorted(bundles_dir.glob("*.bundle")):
        bundle_report = patch_local_bundle(bundle_path, translations)
        if bundle_report:
            reports.append(bundle_report)
            log(
                f"{bundle_report['bundle_file']}: "
                f"{bundle_report['replacements']} replacements in "
                f"{len(bundle_report['changed_objects'])} objects"
            )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Patched {len(reports)} local bundles with {sum(int(r['replacements']) for r in reports)} replacements")

    log("Repacking APK...")
    repack_apk(input_apk, patched_dir, unsigned_apk)

    log("Zipaligning APK...")
    output_apk.parent.mkdir(parents=True, exist_ok=True)
    for stale in [aligned_apk, output_apk, Path(str(output_apk) + ".idsig")]:
        stale.unlink(missing_ok=True)
    run([tools["zipalign"], "-p", "-f", "4", str(unsigned_apk), str(aligned_apk)], log=log)

    log("Signing APK...")
    ensure_keystore(tools["keytool"], keystore, log)
    run(
        [
            tools["apksigner"],
            "sign",
            "--ks",
            str(keystore),
            "--ks-key-alias",
            KEY_ALIAS,
            "--ks-pass",
            f"pass:{KEY_PASS}",
            "--key-pass",
            f"pass:{KEY_PASS}",
            "--out",
            str(output_apk),
            str(aligned_apk),
        ],
        log=log,
    )
    run([tools["apksigner"], "verify", "--verbose", str(output_apk)], log=log)
    log(f"Wrote {output_apk}")
    log(f"Local translation report: {report}")
    return output_apk


def remote_bundle_rows() -> dict[str, str]:
    report_path = ROOT / "reports" / "remote_patch_report.json"
    rows = json.loads(report_path.read_text(encoding="utf-8"))
    selected: dict[str, str] = {}
    for row in rows:
        name = row["bundle_file"]
        hash_value = name.split("__", 1)[0]
        selected[hash_value] = name
    return selected


def push_patched_remote_files(adb_command: list[str], patched_dir: Path, report: Path, package: str, log: LogFn) -> None:
    files = sorted(path for path in patched_dir.rglob("*") if path.is_file())
    changed = {row["bundle_file"] for row in json.loads(report.read_text(encoding="utf-8"))}
    pushed = 0
    pushed_info = 0
    for path in files:
        if path.name not in changed:
            continue
        match = HASH_RE.match(path.name)
        if not match:
            continue
        hash_value = match.group(1)
        remote_dir = (
            f"/sdcard/Android/data/{package}/files/Bundles/Remote/"
            f"BundleFiles/{hash_value[:2]}/{hash_value}"
        )
        remote_data = f"{remote_dir}/__data"
        log(f"{hash_value} -> {remote_data}")
        run(adb_command + ["push", str(path), remote_data], log=log)
        pushed += 1

        fd, info_name = tempfile.mkstemp(prefix=f"{hash_value}.", suffix=".__info")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(app_cache_info_bytes(path))
            run(adb_command + ["push", info_name, f"{remote_dir}/__info"], log=log)
            pushed_info += 1
        finally:
            Path(info_name).unlink(missing_ok=True)
    log(f"Pushed {pushed} patched bundles")
    log(f"Pushed {pushed_info} matching cache info files")


def patch_remote_cache(package: str = DEFAULT_PACKAGE, log: LogFn = default_log, serial: str | None = None) -> Path:
    adb = adb_tool()
    package = package.strip() or DEFAULT_PACKAGE
    require_ready_device(serial)

    work_dir = STATE_ROOT / "work" / "gui_remote_cache_patcher"
    source_dir = work_dir / "source_bundles"
    patched_dir = work_dir / "patched_bundles"
    report = STATE_ROOT / "output" / "remote_cache_patch_report.json"

    shutil.rmtree(work_dir, ignore_errors=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    log("Checking connected devices...")
    run([adb, "devices"], log=log)

    log("Stopping app before cache patch...")
    run(adb_base_command(serial) + ["shell", "am", "force-stop", package], log=log, check=False)

    missing: list[str] = []
    log("Pulling downloaded remote bundles...")
    for hash_value, name in sorted(remote_bundle_rows().items()):
        remote = (
            f"/sdcard/Android/data/{package}/files/Bundles/Remote/"
            f"BundleFiles/{hash_value[:2]}/{hash_value}/__data"
        )
        dest = source_dir / name
        log(f"{hash_value} -> {dest}")
        result = run(adb_base_command(serial) + ["pull", remote, str(dest)], log=log, check=False)
        if result.returncode != 0:
            missing.append(hash_value)

    if missing:
        raise PatcherError(
            f"Missing {len(missing)} required downloaded bundles. "
            "Launch the game, let additional data download finish, then retry."
        )

    log("Applying remote English translations...")
    translations = load_bundle_translations(ROOT / "translations" / "remote_ui.csv")
    if not translations:
        raise PatcherError("No remote translations loaded.")
    shutil.copytree(source_dir, patched_dir)

    reports: list[dict[str, object]] = []
    for bundle_path in sorted(path for path in patched_dir.rglob("*") if path.is_file()):
        bundle_report = patch_remote_bundle(bundle_path, translations)
        if bundle_report:
            reports.append(bundle_report)
            log(
                f"{bundle_report['bundle_file']}: "
                f"{bundle_report['replacements']} replacements in "
                f"{len(bundle_report['changed_objects'])} objects"
            )

    masterdata_translations_path = ROOT / "translations" / "remote_masterdata.csv"
    masterdata_bundle = patched_dir / MASTERDATA_BUNDLE
    if masterdata_translations_path.exists() and masterdata_bundle.exists():
        log("Applying master-data English translations...")
        masterdata_translations = load_masterdata_translations(masterdata_translations_path)
        masterdata_report = patch_masterdata_bundle(
            masterdata_bundle,
            masterdata_bundle,
            masterdata_translations,
        )
        reports.append(masterdata_report)
        log(
            f"{masterdata_report['bundle_file']}: "
            f"{masterdata_report['replacements']} master-data replacements"
        )

    voice_catalog_translations_path = ROOT / "translations" / "voice_catalog.csv"
    voice_catalog_bundle = patched_dir / VOICE_CATALOG_BUNDLE
    if voice_catalog_translations_path.exists() and voice_catalog_bundle.exists():
        log("Applying voice-dialogue English translations...")
        voice_catalog_translations = load_voice_catalog_translations(voice_catalog_translations_path)
        voice_catalog_report = patch_voice_catalog_bundle(
            voice_catalog_bundle,
            voice_catalog_bundle,
            voice_catalog_translations,
        )
        reports.append(voice_catalog_report)
        log(
            f"{voice_catalog_report['bundle_file']}: "
            f"{voice_catalog_report['replacements']} voice-dialogue replacements"
        )

    report.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Patched {len(reports)} remote bundles with {sum(int(r['replacements']) for r in reports)} replacements")

    log("Pushing patched remote cache with matching metadata...")
    push_patched_remote_files(adb_base_command(serial), patched_dir, report, package, log)

    log("Launching app...")
    launch_app(package, log=log, serial=serial)
    log(f"Remote cache patch complete. Report: {report}")
    return report


def install_apk(apk_path: Path, log: LogFn = default_log, replace: bool = True, serial: str | None = None) -> None:
    require_ready_device(serial)
    apk_path = apk_path.expanduser().resolve()
    if not apk_path.is_file():
        raise PatcherError(f"APK not found: {apk_path}")
    command = adb_base_command(serial) + ["install"]
    if replace:
        command.append("-r")
    command.append(str(apk_path))
    run(command, log=log)
