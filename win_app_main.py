"""Simple Tkinter front-end for MonitoringService on Windows.

Launch this with PyInstaller (see README) to produce a double-clickable app
that starts/stops monitoring and shows where session logs are written.
"""
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Optional

from monitoring_service import MonitoringService

DEFAULT_TARGET = "1.1.1.1"
DEFAULT_PING_INTERVAL = 1.0
DEFAULT_PING_TIMEOUT = 1.0
DEFAULT_SPEED_INTERVAL = 30.0
DEFAULT_SPEED_DURATION = 10.0
DEFAULT_SPEED_URL = "https://speed.cloudflare.com/__down?bytes=524288"


class MonitorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Internet Connection Tester")
        self.geometry("460x260")
        self.resizable(False, False)

        self.monitor: Optional[MonitoringService] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self._status_updater: Optional[str] = None

        self._build_form()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_form(self) -> None:
        padding_options = {"padx": 10, "pady": 6}

        tk.Label(self, text="Ping target (hostname or IP)").grid(row=0, column=0, sticky="w", **padding_options)
        self.target_entry = tk.Entry(self, width=40)
        self.target_entry.insert(0, DEFAULT_TARGET)
        self.target_entry.grid(row=0, column=1, sticky="we", **padding_options)

        tk.Label(self, text="Ping interval (seconds)").grid(row=1, column=0, sticky="w", **padding_options)
        self.ping_interval_entry = tk.Entry(self, width=10)
        self.ping_interval_entry.insert(0, str(DEFAULT_PING_INTERVAL))
        self.ping_interval_entry.grid(row=1, column=1, sticky="w", **padding_options)

        tk.Label(self, text="Ping timeout (seconds)").grid(row=2, column=0, sticky="w", **padding_options)
        self.ping_timeout_entry = tk.Entry(self, width=10)
        self.ping_timeout_entry.insert(0, str(DEFAULT_PING_TIMEOUT))
        self.ping_timeout_entry.grid(row=2, column=1, sticky="w", **padding_options)

        tk.Label(self, text="Speed check interval (seconds)").grid(row=3, column=0, sticky="w", **padding_options)
        self.speed_interval_entry = tk.Entry(self, width=10)
        self.speed_interval_entry.insert(0, str(DEFAULT_SPEED_INTERVAL))
        self.speed_interval_entry.grid(row=3, column=1, sticky="w", **padding_options)

        tk.Label(self, text="Speed test duration (seconds)").grid(row=4, column=0, sticky="w", **padding_options)
        self.speed_duration_entry = tk.Entry(self, width=10)
        self.speed_duration_entry.insert(0, str(DEFAULT_SPEED_DURATION))
        self.speed_duration_entry.grid(row=4, column=1, sticky="w", **padding_options)

        tk.Label(self, text="Speed download URL").grid(row=5, column=0, sticky="w", **padding_options)
        self.speed_url_entry = tk.Entry(self, width=40)
        self.speed_url_entry.insert(0, DEFAULT_SPEED_URL)
        self.speed_url_entry.grid(row=5, column=1, sticky="we", **padding_options)

        button_frame = tk.Frame(self)
        button_frame.grid(row=6, column=0, columnspan=2, **padding_options)
        self.start_button = tk.Button(button_frame, text="Start monitoring", command=self._start_monitor)
        self.start_button.grid(row=0, column=0, padx=8)
        self.stop_button = tk.Button(button_frame, text="Stop", command=self._stop_monitor, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=8)

        self.status_label = tk.Label(self, text="Idle", anchor="w", justify="left")
        self.status_label.grid(row=7, column=0, columnspan=2, sticky="we", **padding_options)

    def _start_monitor(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            return

        try:
            target = self.target_entry.get().strip()
            ping_interval = float(self.ping_interval_entry.get())
            ping_timeout = float(self.ping_timeout_entry.get())
            speed_interval = float(self.speed_interval_entry.get())
            speed_duration = float(self.speed_duration_entry.get())
            speed_url = self.speed_url_entry.get().strip() or None
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter numeric values for intervals/timeouts.")
            return

        if not target:
            messagebox.showerror("Missing target", "Please enter a hostname or IP to ping.")
            return

        self.monitor = MonitoringService(
            target=target,
            ping_interval=max(0.2, ping_interval),
            ping_timeout=max(0.2, ping_timeout),
            speed_interval=max(5.0, speed_interval),
            speed_blob_url=speed_url,
            speed_test_duration=max(0.0, speed_duration),
            consecutive_failure_threshold=3,
        )

        self.monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
        self.monitor_thread.start()
        self._set_running_state(True)
        self._schedule_status_update()

    def _run_monitor(self) -> None:
        if not self.monitor:
            return
        self.monitor.start()

    def _stop_monitor(self) -> None:
        if not self.monitor:
            return
        self.monitor.stop()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.monitor_thread = None
        self.monitor = None
        self._set_running_state(False)

    def _set_running_state(self, running: bool) -> None:
        self.start_button.config(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL if running else tk.DISABLED)
        if not running and self._status_updater:
            self.after_cancel(self._status_updater)
            self._status_updater = None
        if not running:
            self.status_label.config(text=self._build_status_text())

    def _schedule_status_update(self) -> None:
        self.status_label.config(text=self._build_status_text())
        self._status_updater = self.after(1000, self._schedule_status_update)

    def _build_status_text(self) -> str:
        if not self.monitor:
            return "Idle"

        uptime_ratio = 0.0
        if self.monitor.total_pings:
            uptime_ratio = (self.monitor.success_pings / self.monitor.total_pings) * 100.0

        lines = [
            f"Session started: {self._format_time(self.monitor.session_started_at)}",
            f"Session folder: {self.monitor.platform.sessions_directory()}",
            f"Pings: {self.monitor.total_pings} (success {self.monitor.success_pings}, failed {self.monitor.failed_pings})",
            f"Uptime: {uptime_ratio:.1f}%",
        ]
        if self.monitor.recorder.speeds:
            latest_speed = self.monitor.recorder.speeds[-1]
            lines.append(
                f"Last speed: {latest_speed.direction} {latest_speed.throughput_mbps:.1f} Mbps "
                f"at {self._format_time(latest_speed.timestamp)}"
            )
        else:
            lines.append("Last speed: pending first sample")

        return "\n".join(lines)

    def _on_close(self) -> None:
        if self.monitor:
            self.monitor.stop()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.destroy()

    @staticmethod
    def _format_time(value: Optional[datetime]) -> str:
        if value is None:
            return "not started"
        return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def main() -> None:
    app = MonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
