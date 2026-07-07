from __future__ import annotations

import threading
import time
import queue
from typing import Optional
import re
import subprocess
import os
import sys

try:
    import pyperclip
except Exception:
    pyperclip = None

from .detector import detect_sensitive, strip_sensitive_copy_prefix, summarize_detections
from .notifier import notify


class Monitor(threading.Thread):
    def __init__(self, db, q: queue.Queue, interval=0.6, notifications=True, notify_cooldown=2.0):
        super().__init__(daemon=True)
        self.db, self.q, self.interval = db, q, interval
        self._stop   = threading.Event()
        self._paused = threading.Event()
        self._last   = None
        self._last_lock = threading.Lock()
        self._last_ts = 0.0
        self._cooldown = 0

        # Notification settings
        self.notifications_enabled = notifications
        self._notify_cooldown = notify_cooldown
        self._last_notify_ts = 0.0
        self._notify_lock = threading.Lock()

    def run(self):
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.2); continue
            try:
                text = pyperclip.paste() if pyperclip else None
            except Exception:
                text = None
            if not (text and isinstance(text, str)):
                time.sleep(self.interval); continue
            text = strip_sensitive_copy_prefix(text)
            norm = text.replace("\r\n", "\n")
            with self._last_lock:
                last = self._last
                last_ts = self._last_ts
            now = time.time()
            if last is not None and norm == (last.replace("\r\n", "\n")) and (now - last_ts) < self._cooldown:
                time.sleep(self.interval); continue
            try:
                db_last = self.db.last()
            except Exception:
                db_last = None
            if db_last is not None and norm == db_last.replace("\r\n", "\n"):
                with self._last_lock:
                    self._last = text
                    self._last_ts = now
                time.sleep(self.interval); continue

            # attempt to capture source (best-effort)
            source = self._capture_source(text)
            rid = self.db.add(text, source=source)
            # run detection (regex + optional yara)
            try:
                detections = detect_sensitive(text)
            except Exception:
                detections = []
            with self._last_lock:
                self._last = text
                self._last_ts = now

            # Fire a desktop notification for sensitive detections (throttled)
            if detections:
                self._maybe_notify(detections)

            # Put detections alongside the record so UI can react
            self.q.put((rid, text, detections))
            time.sleep(self.interval)

    def _maybe_notify(self, detections) -> None:
        if not self.notifications_enabled:
            return
        now = time.time()
        with self._notify_lock:
            if (now - self._last_notify_ts) < self._notify_cooldown:
                return
            self._last_notify_ts = now
        summary = summarize_detections(detections)
        body = f"Detected: {summary}" if summary else "Sensitive data detected in clipboard"
        try:
            notify("⚠️ Sensitive data copied", body)
        except Exception:
            # Notifications must never crash the monitor thread
            pass

    def set_notifications_enabled(self, enabled: bool) -> None:
        self.notifications_enabled = bool(enabled)

    def _capture_source(self, text: str) -> str | None:
        """Best-effort source capture.

        1) Try to read the active window/process via `xdotool` (X11).
        2) Fallback to simple content heuristics (URLs, html, email).
        Returns a short string like 'firefox - StackOverflow - ...' or 'browser' or None.
        """
        # Windows: try pywin32 + psutil (best-effort, optional dependencies)
        if os.name == 'nt' or sys.platform == 'win32':
            try:
                try:
                    import win32gui
                    import win32process
                except Exception:
                    win32gui = win32process = None
                try:
                    import psutil
                except Exception:
                    psutil = None

                if win32gui and win32process:
                    hwnd = win32gui.GetForegroundWindow()
                    name = win32gui.GetWindowText(hwnd) or None
                    pid = None
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    except Exception:
                        pid = None
                    proc = None
                    if pid and psutil:
                        try:
                            proc = psutil.Process(pid).name()
                        except Exception:
                            proc = None
                    parts = [p for p in (proc, name) if p]
                    if parts:
                        return " - ".join(parts)
            except Exception:
                pass

        # Try xdotool (fast, but not always installed)
        try:
            wid = subprocess.check_output(["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL).strip()
            name = subprocess.check_output(["xdotool", "getwindowname", wid], stderr=subprocess.DEVNULL).decode(errors='ignore').strip()
            pid = subprocess.check_output(["xdotool", "getwindowpid", wid], stderr=subprocess.DEVNULL).strip()
            proc = None
            try:
                proc = open(f"/proc/{int(pid)}/comm").read().strip()
            except Exception:
                try:
                    proc = subprocess.check_output(["ps", "-p", pid.decode(), "-o", "comm="], stderr=subprocess.DEVNULL).decode().strip()
                except Exception:
                    proc = None
            parts = [p for p in (proc, name) if p]
            if parts:
                return " - ".join(parts)
        except Exception:
            pass

        # Heuristic fallback
        try:
            if re.search(r'https?://', text):
                return 'browser'
            if '<html' in text.lower() or '<div' in text.lower() or text.strip().startswith('<!DOCTYPE html'):
                return 'html'
            if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
                return 'email'
        except Exception:
            pass
        return None

    def stop(self):   self._stop.set()
    def pause(self):  self._paused.set()
    def resume(self): self._paused.clear()
    def toggle(self):
        self.resume() if self._paused.is_set() else self.pause()

    @property
    def paused(self): return self._paused.is_set()

    def mark_seen(self, text: str):
        now = time.time()
        with self._last_lock:
            self._last = text
            self._last_ts = now
