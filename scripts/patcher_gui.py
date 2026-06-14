#!/usr/bin/env python3
"""Tkinter GUI for the Kiou English patcher."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from PIL import Image, ImageTk

import patcher_core


ROOT = Path(__file__).resolve().parents[1]


class PatcherGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kiou English Patcher")
        self.geometry("1040x780")
        self.minsize(860, 660)

        default_input = ROOT / "KIOU_RELEASE.apk"
        default_output = patcher_core.STATE_ROOT / "output" / "KIOU_RELEASE_english.apk"
        input_text = "" if getattr(sys, "frozen", False) else str(default_input) if default_input.exists() else ""
        steam_detected = patcher_core.detect_steam_install()

        self.input_apk = tk.StringVar(value=input_text)
        self.output_apk = tk.StringVar(value=str(default_output))
        self.package_name = tk.StringVar(value=patcher_core.DEFAULT_PACKAGE)
        self.device_serial = tk.StringVar(value="")
        self.allow_unknown = tk.BooleanVar(value=False)
        self.steam_path = tk.StringVar(value=str(steam_detected) if steam_detected else "")
        self.status_text = tk.StringVar(value="Ready")
        self.device_text = tk.StringVar(value="Device: not checked")
        self.cache_text = tk.StringVar(value="Downloaded data: not checked")
        self.steam_status_text = tk.StringVar(value="Steam install: not checked")
        self.log_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.buttons: list[ttk.Button | tk.Button] = []
        self.step_vars: dict[str, tk.StringVar] = {}
        self.log_text: tk.Text | None = None
        self.device_combo: ttk.Combobox | None = None
        self.tool_labels: dict[str, ttk.Label] = {}
        self.logo_images: list[ImageTk.PhotoImage] = []

        self._build_mode_menu()
        self.after(100, self.drain_log_queue)

    def _clear_ui(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.buttons = []
        self.step_vars = {}
        self.tool_labels = {}
        self.log_text = None
        self.device_combo = None
        for index in range(8):
            self.rowconfigure(index, weight=0)
        self.columnconfigure(0, weight=1)

    def _build_mode_menu(self) -> None:
        self._clear_ui()
        self.geometry("1040x780")
        self.minsize(860, 660)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="Kiou English Patcher", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        ttk.Label(self, text="Choose the version of the game you want to patch.").grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 18)
        )

        cards = ttk.Frame(self)
        cards.grid(row=2, column=0, sticky="nsew", padx=18, pady=12)
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        self._platform_card(
            cards,
            0,
            "Android",
            "APK + downloaded data cache",
            "assets/brand/android-head_3D.png",
            self._build_android_ui,
        )
        self._platform_card(
            cards,
            1,
            "Steam",
            "Steam install folder + downloaded cache",
            "assets/brand/steamLogo_300.jpg",
            self._build_steam_ui,
        )

        ttk.Label(self, textvariable=self.status_text).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))

    def _platform_card(
        self,
        parent: ttk.Frame,
        column: int,
        title: str,
        subtitle: str,
        image_path: str,
        command: Callable[[], None],
    ) -> None:
        frame = ttk.Frame(parent, padding=18, relief="ridge")
        frame.grid(row=0, column=column, sticky="nsew", padx=10, pady=8)
        frame.columnconfigure(0, weight=1)
        image = self.load_logo_image(image_path, (132, 92))
        if image:
            ttk.Label(frame, image=image).grid(row=0, column=0, pady=(4, 12))
        else:
            ttk.Label(frame, text=title, font=("TkDefaultFont", 18, "bold")).grid(row=0, column=0, pady=(32, 34))
        ttk.Label(frame, text=title, font=("TkDefaultFont", 15, "bold")).grid(row=1, column=0, pady=(0, 4))
        ttk.Label(frame, text=subtitle).grid(row=2, column=0, pady=(0, 12))
        button = ttk.Button(frame, text=f"Patch {title}", command=command)
        button.grid(row=3, column=0, sticky="ew")
        self.buttons.append(button)

    def load_logo_image(self, relative_path: str, max_size: tuple[int, int]) -> ImageTk.PhotoImage | None:
        path = patcher_core.ROOT / relative_path
        if not path.is_file():
            return None
        image = Image.open(path)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self.logo_images.append(photo)
        return photo

    def _page_header(self, title: str, command: Callable[[], None]) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        header.columnconfigure(1, weight=1)
        back = ttk.Button(header, text="Back", command=command)
        back.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(header, text=title, font=("TkDefaultFont", 16, "bold")).grid(row=0, column=1, sticky="w")
        self.buttons.append(back)

    def _build_android_ui(self) -> None:
        self._clear_ui()
        self.geometry("1040x780")
        self.minsize(860, 660)
        self.rowconfigure(5, weight=1)
        self._page_header("Kiou English Patcher - Android", self._build_mode_menu)
        self._build_apk_frame(row=1)
        self._build_android_workflow_frame(row=2)
        self._build_tools_frame(row=3)
        self._build_log_frame(row=5)
        ttk.Label(self, textvariable=self.status_text).grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.refresh_tools()
        self.refresh_devices()

    def _build_steam_ui(self) -> None:
        self._clear_ui()
        self.geometry("1040x700")
        self.minsize(860, 620)
        self.rowconfigure(4, weight=1)
        self._page_header("Kiou English Patcher - Steam", self._build_mode_menu)
        self._build_steam_inputs_frame(row=1)
        self._build_steam_workflow_frame(row=2)
        self._build_log_frame(row=4)
        ttk.Label(self, textvariable=self.status_text).grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _build_apk_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Inputs")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Original APK").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(frame, textvariable=self.input_apk).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        browse = ttk.Button(frame, text="Browse", command=self.browse_input)
        browse.grid(row=0, column=2, padx=10, pady=6)
        self.buttons.append(browse)

        ttk.Label(frame, text="Output APK").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(frame, textvariable=self.output_apk).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        save_as = ttk.Button(frame, text="Save As", command=self.browse_output)
        save_as.grid(row=1, column=2, padx=10, pady=6)
        self.buttons.append(save_as)

        ttk.Label(frame, text="Package").grid(row=2, column=0, sticky="w", padx=10, pady=6)
        ttk.Entry(frame, textvariable=self.package_name, width=34).grid(row=2, column=1, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(frame, text="Try untested APK build", variable=self.allow_unknown).grid(
            row=2, column=2, sticky="w", padx=10, pady=6
        )

    def _build_android_workflow_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Guided Workflow")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)

        status_bar = ttk.Frame(frame)
        status_bar.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(8, 4))
        status_bar.columnconfigure(0, weight=1)
        status_bar.columnconfigure(1, weight=1)
        ttk.Label(status_bar, textvariable=self.device_text).grid(row=0, column=0, sticky="w")
        ttk.Label(status_bar, textvariable=self.cache_text).grid(row=0, column=1, sticky="w")
        ttk.Label(status_bar, text="Target").grid(row=0, column=2, sticky="e", padx=(12, 4))
        self.device_combo = ttk.Combobox(status_bar, textvariable=self.device_serial, width=20, state="readonly")
        self.device_combo.grid(row=0, column=3, sticky="e", padx=4)
        refresh_devices = ttk.Button(status_bar, text="Refresh Devices", command=self.refresh_devices)
        refresh_devices.grid(row=0, column=4, sticky="e", padx=4)
        check = ttk.Button(status_bar, text="Check Status", command=self.check_status)
        check.grid(row=0, column=5, sticky="e")
        self.buttons.extend([refresh_devices, check])

        steps: list[tuple[str, str, str, Callable[[], None]]] = [
            ("apk", "1. Patch APK", "Waiting", self.patch_apk),
            ("install", "2. Install Patched APK", "Waiting", self.install_apk),
            ("launch", "3. Launch Game", "Open the game and finish the forced download", self.launch_game),
            ("check_cache", "4. Check Downloaded Data", "Waiting for download", self.check_remote_cache),
            ("remote", "5. Patch Downloaded Data", "Waiting", self.patch_remote_cache),
        ]

        for index, (key, label, initial, command) in enumerate(steps, start=1):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", padx=10, pady=6)
            var = tk.StringVar(value=initial)
            self.step_vars[key] = var
            ttk.Label(frame, textvariable=var).grid(row=index, column=1, sticky="ew", padx=8, pady=6)
            button = ttk.Button(frame, text=label.split(". ", 1)[1], command=command)
            button.grid(row=index, column=2, sticky="ew", padx=10, pady=6)
            self.buttons.append(button)

    def _build_tools_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Tool Paths")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)
        for index, name in enumerate(["adb", "zipalign", "apksigner", "keytool"]):
            ttk.Label(frame, text=name).grid(row=index, column=0, sticky="w", padx=10, pady=3)
            label = ttk.Label(frame, text="")
            label.grid(row=index, column=1, sticky="ew", padx=8, pady=3)
            self.tool_labels[name] = label
        refresh = ttk.Button(frame, text="Refresh Tools", command=self.refresh_tools)
        refresh.grid(row=0, column=2, sticky="ne", rowspan=2, padx=10, pady=3)
        self.buttons.append(refresh)

    def _build_steam_inputs_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Steam Install")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="KIOU Folder").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.steam_path).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        browse = ttk.Button(frame, text="Browse", command=self.browse_steam_path)
        browse.grid(row=0, column=2, padx=6, pady=8)
        auto = ttk.Button(frame, text="Auto Detect", command=self.detect_steam_path)
        auto.grid(row=0, column=3, padx=10, pady=8)
        self.buttons.extend([browse, auto])
        ttk.Label(frame, textvariable=self.steam_status_text).grid(
            row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8)
        )

    def _build_steam_workflow_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Guided Workflow")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        frame.columnconfigure(1, weight=1)
        steps = [
            ("steam_detect", "1. Find Steam Install", "Waiting"),
            ("steam_update", "2. Launch Game and Finish Update", "Launch once, finish the update, then close the game"),
            ("steam_patch", "3. Patch Steam Game", "Waiting"),
        ]
        for index, (key, label, initial) in enumerate(steps):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", padx=10, pady=6)
            var = tk.StringVar(value=initial)
            self.step_vars[key] = var
            ttk.Label(frame, textvariable=var).grid(row=index, column=1, sticky="ew", padx=8, pady=6)
        actions = ttk.Frame(frame)
        actions.grid(row=0, column=2, rowspan=3, sticky="nsew", padx=10, pady=6)
        check = ttk.Button(actions, text="Check Status", command=self.check_steam_status)
        launch = ttk.Button(actions, text="Launch Game", command=self.launch_steam_game)
        patch = ttk.Button(actions, text="Patch Steam Game", command=self.patch_steam_game)
        check.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        launch.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        patch.grid(row=2, column=0, sticky="ew")
        self.buttons.extend([check, launch, patch])

    def _build_log_frame(self, row: int) -> None:
        frame = ttk.LabelFrame(self, text="Log")
        frame.grid(row=row, column=0, sticky="nsew", padx=12, pady=8)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(frame, wrap="word", height=16)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select original APK",
            filetypes=[("Android APK", "*.apk"), ("All files", "*.*")],
        )
        if path:
            self.input_apk.set(path)
            self.step_vars["apk"].set("Ready to patch")

    def browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save patched APK",
            defaultextension=".apk",
            filetypes=[("Android APK", "*.apk"), ("All files", "*.*")],
            initialfile="KIOU_RELEASE_english.apk",
        )
        if path:
            self.output_apk.set(path)

    def browse_steam_path(self) -> None:
        path = filedialog.askdirectory(title="Select the KIOU Steam install folder")
        if path:
            self.steam_path.set(path)
            self.step_vars["steam_detect"].set("Ready to check")

    def detect_steam_path(self) -> None:
        path = patcher_core.detect_steam_install()
        if path:
            self.steam_path.set(str(path))
            self.steam_status_text.set(f"Steam install: {path}")
            self.step_vars["steam_detect"].set("Found")
        else:
            self.steam_status_text.set("Steam install: not found. Use Browse.")
            self.step_vars["steam_detect"].set("Browse required")

    def log(self, message: str) -> None:
        self.log_queue.put(("log", message))

    def drain_log_queue(self) -> None:
        try:
            while True:
                event = self.log_queue.get_nowait()
                kind = event[0]
                if kind == "log":
                    if self.log_text and self.log_text.winfo_exists():
                        self.log_text.insert("end", event[1] + "\n")
                        self.log_text.see("end")
                elif kind == "status":
                    self.status_text.set(event[1])
                elif kind == "step":
                    if event[1] in self.step_vars:
                        self.step_vars[event[1]].set(event[2])
                elif kind == "device":
                    self.device_text.set(event[1])
                elif kind == "cache":
                    self.cache_text.set(event[1])
                elif kind == "steam_status":
                    self.steam_status_text.set(event[1])
                elif kind == "done":
                    self.status_text.set(event[1])
                    self.set_busy(False)
                elif kind == "error":
                    self.status_text.set("Failed")
                    self.set_busy(False)
                    messagebox.showerror("Patcher Error", event[1])
        except queue.Empty:
            pass
        self.after(100, self.drain_log_queue)

    def queue_step(self, key: str, value: str) -> None:
        self.log_queue.put(("step", key, value))

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self.buttons:
            if button.winfo_exists():
                button.configure(state=state)

    def run_worker(self, title: str, target: Callable[[], None]) -> None:
        if self.worker and self.worker.is_alive():
            return
        self.set_busy(True)
        self.status_text.set(title)
        if self.log_text and self.log_text.winfo_exists():
            self.log_text.insert("end", f"\n== {title} ==\n")
            self.log_text.see("end")

        def wrapper() -> None:
            try:
                target()
            except Exception as exc:
                self.log_queue.put(("error", str(exc)))
            else:
                self.log_queue.put(("done", "Ready"))

        self.worker = threading.Thread(target=wrapper, daemon=True)
        self.worker.start()

    def refresh_tools(self) -> None:
        tools = patcher_core.describe_tools()
        for name, label in self.tool_labels.items():
            label.configure(text=tools.get(name) or "Not found")

    def selected_serial(self) -> str:
        return self.device_serial.get().strip()

    def refresh_devices(self) -> None:
        if not self.device_combo:
            return
        try:
            devices = patcher_core.adb_devices()
        except Exception as exc:
            self.device_combo.configure(values=[])
            self.device_serial.set("")
            self.device_text.set(f"Device: {exc}")
            return

        authorized = [device["serial"] for device in devices if device["state"] == "device"]
        self.device_combo.configure(values=authorized)
        current = self.selected_serial()
        if len(authorized) == 1:
            self.device_serial.set(authorized[0])
        elif current not in authorized:
            self.device_serial.set("")

        if not devices:
            self.device_text.set("Device: none detected")
        elif len(authorized) == 1:
            self.device_text.set(f"Device: {authorized[0]}")
        elif len(authorized) > 1:
            self.device_text.set("Device: select a target")
        else:
            self.device_text.set("Device: not authorized")

    def check_status(self) -> None:
        def task() -> None:
            status = patcher_core.guided_status(self.package_name.get(), self.selected_serial())
            self.log(status["message"])
            self.log_queue.put(("device", f"Device: {status['message']}"))
            installed_text = "installed" if status["installed"] else "not installed"
            self.queue_step("install", f"App {installed_text}")
            cache_found = int(status["cache_found"])
            cache_required = int(status["cache_required"])
            self.log_queue.put(("cache", f"Downloaded data: {cache_found}/{cache_required} bundles found"))
            self.queue_step("check_cache", "Complete" if status["cache_ready"] else f"{cache_found}/{cache_required} bundles found")
            if status["cache_ready"]:
                self.queue_step("remote", "Ready to patch")

        self.run_worker("Checking Status", task)

    def patch_apk(self) -> None:
        def task() -> None:
            self.queue_step("apk", "Patching")
            output = patcher_core.patch_apk(
                Path(self.input_apk.get()),
                Path(self.output_apk.get()),
                allow_unknown=self.allow_unknown.get(),
                log=self.log,
            )
            self.queue_step("apk", "Complete")
            self.queue_step("install", "Ready to install")
            self.log(f"Patched APK ready: {output}")

        self.run_worker("Patching APK", task)

    def install_apk(self) -> None:
        def task() -> None:
            self.queue_step("install", "Installing")
            patcher_core.install_apk(Path(self.output_apk.get()), log=self.log, serial=self.selected_serial())
            self.queue_step("install", "Complete")
            self.queue_step("launch", "Ready to launch")

        self.run_worker("Installing APK", task)

    def launch_game(self) -> None:
        def task() -> None:
            patcher_core.launch_app(self.package_name.get(), log=self.log, serial=self.selected_serial())
            self.queue_step("launch", "Launched")
            self.queue_step("check_cache", "Finish forced download, then check")

        self.run_worker("Launching Game", task)

    def check_remote_cache(self) -> None:
        def task() -> None:
            cache = patcher_core.remote_cache_status(self.package_name.get(), self.selected_serial())
            found = int(cache["found"])
            required = int(cache["required"])
            self.log_queue.put(("cache", f"Downloaded data: {found}/{required} bundles found"))
            if cache["ready"]:
                self.queue_step("check_cache", "Complete")
                self.queue_step("remote", "Ready to patch")
                self.log("Downloaded data is ready to patch.")
            else:
                missing = len(cache["missing"])
                self.queue_step("check_cache", f"{found}/{required} bundles found")
                self.queue_step("remote", "Waiting for download")
                self.log(f"Downloaded data is not complete yet. Missing {missing} required bundles.")

        self.run_worker("Checking Downloaded Data", task)

    def patch_remote_cache(self) -> None:
        def task() -> None:
            self.queue_step("remote", "Patching")
            patcher_core.patch_remote_cache(self.package_name.get(), log=self.log, serial=self.selected_serial())
            self.queue_step("remote", "Complete")

        self.run_worker("Patching Downloaded Data", task)

    def check_steam_status(self) -> None:
        def task() -> None:
            status = patcher_core.steam_manifest_status(Path(self.steam_path.get()))
            self.log_queue.put(("steam_status", f"Steam install: {status['install_dir']}"))
            self.queue_step("steam_detect", "Found")
            found = int(status["remote_found"])
            required = int(status["remote_bundles"])
            self.queue_step("steam_update", "Update appears complete" if status["remote_ready"] else f"{found}/{required} downloaded")
            self.queue_step("steam_patch", "Ready to patch" if status["remote_ready"] else "Waiting for first update")
            self.log(
                f"Steam status: {status['local_bundles']} local bundles; "
                f"{found}/{required} downloaded remote bundles."
            )

        self.run_worker("Checking Steam Install", task)

    def launch_steam_game(self) -> None:
        def task() -> None:
            patcher_core.launch_steam_game(log=self.log)
            self.queue_step("steam_update", "Let the update finish, then close the game")
            self.queue_step("steam_patch", "Waiting for game to close")

        self.run_worker("Launching Steam Game", task)

    def patch_steam_game(self) -> None:
        def task() -> None:
            self.queue_step("steam_detect", "Checking")
            patcher_core.steam_manifest_status(Path(self.steam_path.get()))
            self.queue_step("steam_detect", "Found")
            self.queue_step("steam_update", "Assuming update is complete")
            self.queue_step("steam_patch", "Patching")
            report = patcher_core.patch_steam_install(Path(self.steam_path.get()), log=self.log)
            self.queue_step("steam_patch", "Complete")
            self.log(f"Steam patch report: {report}")

        self.run_worker("Patching Steam Game", task)


def main() -> int:
    app = PatcherGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
