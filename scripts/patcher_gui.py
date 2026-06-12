#!/usr/bin/env python3
"""Tkinter GUI for the Kiou English APK patcher."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import patcher_core


ROOT = Path(__file__).resolve().parents[1]


class PatcherGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kiou English Patcher")
        self.geometry("980x760")
        self.minsize(820, 640)

        default_input = ROOT / "KIOU_RELEASE.apk"
        default_output = patcher_core.STATE_ROOT / "output" / "KIOU_RELEASE_english.apk"
        input_text = "" if getattr(sys, "frozen", False) else str(default_input) if default_input.exists() else ""

        self.input_apk = tk.StringVar(value=input_text)
        self.output_apk = tk.StringVar(value=str(default_output))
        self.package_name = tk.StringVar(value=patcher_core.DEFAULT_PACKAGE)
        self.device_serial = tk.StringVar(value="")
        self.allow_unknown = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Ready")
        self.device_text = tk.StringVar(value="Device: not checked")
        self.cache_text = tk.StringVar(value="Downloaded data: not checked")
        self.log_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.buttons: list[ttk.Button] = []
        self.step_vars: dict[str, tk.StringVar] = {}

        self._build_ui()
        self.refresh_tools()
        self.refresh_devices()
        self.after(100, self.drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        pad = {"padx": 12, "pady": 8}
        ttk.Label(self, text="Kiou English Patcher", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, sticky="w", **pad
        )

        self._build_apk_frame(row=1)
        self._build_workflow_frame(row=2)
        self._build_tools_frame(row=3)
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

    def _build_workflow_frame(self, row: int) -> None:
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
        self.buttons.append(refresh_devices)
        self.buttons.append(check)

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
        self.tool_labels: dict[str, ttk.Label] = {}
        for index, name in enumerate(["adb", "zipalign", "apksigner", "keytool"]):
            ttk.Label(frame, text=name).grid(row=index, column=0, sticky="w", padx=10, pady=3)
            label = ttk.Label(frame, text="")
            label.grid(row=index, column=1, sticky="ew", padx=8, pady=3)
            self.tool_labels[name] = label
        refresh = ttk.Button(frame, text="Refresh Tools", command=self.refresh_tools)
        refresh.grid(row=0, column=2, sticky="ne", rowspan=2, padx=10, pady=3)
        self.buttons.append(refresh)

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

    def log(self, message: str) -> None:
        self.log_queue.put(("log", message))

    def drain_log_queue(self) -> None:
        try:
            while True:
                event = self.log_queue.get_nowait()
                kind = event[0]
                if kind == "log":
                    self.log_text.insert("end", event[1] + "\n")
                    self.log_text.see("end")
                elif kind == "status":
                    self.status_text.set(event[1])
                elif kind == "step":
                    self.step_vars[event[1]].set(event[2])
                elif kind == "device":
                    self.device_text.set(event[1])
                elif kind == "cache":
                    self.cache_text.set(event[1])
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
            button.configure(state=state)

    def run_worker(self, title: str, target: Callable[[], None]) -> None:
        if self.worker and self.worker.is_alive():
            return
        self.set_busy(True)
        self.status_text.set(title)
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


def main() -> int:
    app = PatcherGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
