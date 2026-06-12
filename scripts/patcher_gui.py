#!/usr/bin/env python3
"""Tkinter GUI for the Kiou English APK patcher."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import patcher_core


ROOT = Path(__file__).resolve().parents[1]


class PatcherGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kiou English Patcher")
        self.geometry("940x680")
        self.minsize(760, 560)

        default_input = ROOT / "KIOU_RELEASE.apk"
        default_output = patcher_core.STATE_ROOT / "output" / "KIOU_RELEASE_english.apk"
        if getattr(sys, "frozen", False):
            default_input_text = ""
        else:
            default_input_text = str(default_input) if default_input.exists() else ""
        self.input_apk = tk.StringVar(value=default_input_text)
        self.output_apk = tk.StringVar(value=str(default_output))
        self.package_name = tk.StringVar(value=patcher_core.DEFAULT_PACKAGE)
        self.allow_unknown = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Ready")
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.refresh_tools()
        self.after(100, self.drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        pad = {"padx": 12, "pady": 8}
        header = ttk.Label(
            self,
            text="Kiou English Patcher",
            font=("TkDefaultFont", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w", **pad)

        apk_frame = ttk.LabelFrame(self, text="APK")
        apk_frame.grid(row=1, column=0, sticky="ew", **pad)
        apk_frame.columnconfigure(1, weight=1)

        ttk.Label(apk_frame, text="Original APK").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(apk_frame, textvariable=self.input_apk).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(apk_frame, text="Browse", command=self.browse_input).grid(row=0, column=2, padx=10, pady=8)

        ttk.Label(apk_frame, text="Output APK").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(apk_frame, textvariable=self.output_apk).grid(row=1, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(apk_frame, text="Save As", command=self.browse_output).grid(row=1, column=2, padx=10, pady=8)

        ttk.Checkbutton(
            apk_frame,
            text="Try untested APK build",
            variable=self.allow_unknown,
        ).grid(row=2, column=1, sticky="w", padx=8, pady=8)

        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="ew", **pad)
        actions.columnconfigure(5, weight=1)

        self.patch_button = ttk.Button(actions, text="Patch APK", command=self.patch_apk)
        self.patch_button.grid(row=0, column=0, padx=(0, 8), pady=4)
        self.install_button = ttk.Button(actions, text="Install APK", command=self.install_apk)
        self.install_button.grid(row=0, column=1, padx=8, pady=4)
        ttk.Label(actions, text="Package").grid(row=0, column=2, padx=(18, 6), pady=4)
        ttk.Entry(actions, textvariable=self.package_name, width=28).grid(row=0, column=3, padx=6, pady=4)
        self.remote_button = ttk.Button(actions, text="Patch Downloaded Data", command=self.patch_remote_cache)
        self.remote_button.grid(row=0, column=4, padx=8, pady=4)
        self.refresh_button = ttk.Button(actions, text="Refresh Tools", command=self.refresh_tools)
        self.refresh_button.grid(row=0, column=6, padx=(8, 0), pady=4)

        self.tools_frame = ttk.LabelFrame(self, text="Tool Paths")
        self.tools_frame.grid(row=3, column=0, sticky="ew", **pad)
        self.tools_frame.columnconfigure(1, weight=1)
        self.tool_labels: dict[str, ttk.Label] = {}
        for row, name in enumerate(["adb", "zipalign", "apksigner", "keytool"]):
            ttk.Label(self.tools_frame, text=name).grid(row=row, column=0, sticky="w", padx=10, pady=4)
            label = ttk.Label(self.tools_frame, text="")
            label.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            self.tool_labels[name] = label

        status = ttk.Label(self, textvariable=self.status_text)
        status.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 0))

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.grid(row=5, column=0, sticky="nsew", **pad)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap="word", height=16)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select original APK",
            filetypes=[("Android APK", "*.apk"), ("All files", "*.*")],
        )
        if path:
            self.input_apk.set(path)
            if not self.output_apk.get():
                self.output_apk.set(str(Path(path).with_name(Path(path).stem + "_english.apk")))

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

    def set_status(self, message: str) -> None:
        self.log_queue.put(("status", message))

    def drain_log_queue(self) -> None:
        try:
            while True:
                kind, message = self.log_queue.get_nowait()
                if kind == "log":
                    self.log_text.insert("end", message + "\n")
                    self.log_text.see("end")
                elif kind == "status":
                    self.status_text.set(message)
                elif kind == "done":
                    self.status_text.set(message)
                    self.set_busy(False)
                elif kind == "error":
                    self.status_text.set("Failed")
                    self.set_busy(False)
                    messagebox.showerror("Patcher Error", message)
        except queue.Empty:
            pass
        self.after(100, self.drain_log_queue)

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in [self.patch_button, self.install_button, self.remote_button, self.refresh_button]:
            button.configure(state=state)

    def run_worker(self, title: str, target) -> None:
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
                self.log_queue.put(("done", "Done"))

        self.worker = threading.Thread(target=wrapper, daemon=True)
        self.worker.start()

    def refresh_tools(self) -> None:
        tools = patcher_core.describe_tools()
        for name, label in self.tool_labels.items():
            path = tools.get(name)
            label.configure(text=path or "Not found")

    def patch_apk(self) -> None:
        def task() -> None:
            output = patcher_core.patch_apk(
                Path(self.input_apk.get()),
                Path(self.output_apk.get()),
                allow_unknown=self.allow_unknown.get(),
                log=self.log,
            )
            self.log(f"Patched APK ready: {output}")

        self.run_worker("Patching APK", task)

    def install_apk(self) -> None:
        def task() -> None:
            patcher_core.install_apk(Path(self.output_apk.get()), log=self.log)

        self.run_worker("Installing APK", task)

    def patch_remote_cache(self) -> None:
        def task() -> None:
            patcher_core.patch_remote_cache(self.package_name.get(), log=self.log)

        self.run_worker("Patching Downloaded Data", task)


def main() -> int:
    app = PatcherGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
