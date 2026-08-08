from __future__ import annotations

import os
import sys
import time
import shutil
import subprocess
import threading

APP_NAME = "Clipboard DLP"

try:
    from plyer import notification as _plyer_notification
except Exception:
    _plyer_notification = None


def _escape_applescript(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _notify_windows(title: str, message: str, timeout: int) -> bool:
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=timeout, threaded=True)
        return True
    except Exception:
        return False


def _notify_macos(title: str, message: str, timeout: int) -> bool:
    try:
        script = (
            f'display notification "{_escape_applescript(message)}" '
            f'with title "{_escape_applescript(title)}"'
        )
        subprocess.run(
            ["osascript", "-e", script],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _close_notification(nid: str) -> bool:
    """Close a notification by id via the D-Bus notifications spec."""
    if not nid:
        return False
    for tool, args in (
        ("dbus-send", ["dbus-send", "--session", "--dest=org.freedesktop.Notifications",
                       "--type=method_call", "/org/freedesktop/Notifications",
                       "org.freedesktop.Notifications.CloseNotification",
                       f"uint32:{nid}"]),
        ("gdbus", ["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications",
                   "--object-path", "/org/freedesktop/Notifications",
                   "--method", "org.freedesktop.Notifications.CloseNotification",
                   nid]),
    ):
        if not shutil.which(tool):
            continue
        try:
            r = subprocess.run(args, capture_output=True, timeout=10)
            if r.returncode == 0:
                return True
        except Exception:
            continue
    return False


def _schedule_close(nid: str, delay: int) -> None:
    """Close the notification after `delay` seconds in a background thread.

    Many notification daemons (GNOME Shell, KDE Plasma in some modes) ignore
    the timeout passed by the sender, so the only reliable way to honor the
    duration cap is to actively close the notification via D-Bus.
    """
    def _worker():
        try:
            time.sleep(max(1, int(delay)))
        except Exception:
            time.sleep(5)
        _close_notification(nid)
    threading.Thread(target=_worker, daemon=True).start()


def _notify_linux(title: str, message: str, timeout: int) -> bool:
    # Cap duration: notifications should never persist indefinitely.
    timeout = max(1, min(int(timeout), 5))
    backends = (
        # --print-id lets us enforce the duration cap with CloseNotification,
        # since several daemons ignore -t entirely.
        (("notify-send", "--print-id", "-u", "normal", "-t", str(timeout * 1000),
          "-a", APP_NAME, title, message), True),
        (("zenity", "--notification", "--title", title, "--text", message), False),
    )
    for cmd, has_id in backends:
        if not shutil.which(cmd[0]):
            continue
        try:
            # NOTE: urgency "critical" makes GNOME ignore the timeout and
            # keeps the notification on screen until dismissed — use
            # "normal" so the 5s cap is actually honored.
            r = subprocess.run(cmd, capture_output=True, timeout=10)
            if r.returncode != 0:
                continue
            if has_id:
                nid = getattr(r, "stdout", b"").decode(errors="ignore").strip()
                if nid.isdigit() and os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
                    _schedule_close(nid, timeout)
            return True
        except Exception:
            continue
    return False


def notify(title: str, message: str, timeout: int = 5) -> bool:
    """Best-effort cross-platform desktop notification.

    Never raises. Returns True if some backend was successfully invoked.
    Deliberately does NOT include the raw sensitive value in the body —
    only type labels — since OS notifications can appear on lock screens
    or be logged by the notification center.
    """
    if not title or not message:
        return False

    # Notifications must never persist indefinitely.
    timeout = max(1, min(int(timeout), 5))

    platform = sys.platform
    if platform.startswith("win"):
        if _notify_windows(title, message, timeout):
            return True
    elif platform == "darwin":
        if _notify_macos(title, message, timeout):
            return True
    else:
        # Linux backend first: it enforces the duration cap via D-Bus
        # CloseNotification, which plyer cannot do.
        if _notify_linux(title, message, timeout):
            return True

    # Last-resort fallback only.
    if _plyer_notification is not None:
        try:
            _plyer_notification.notify(
                title=title, message=message, app_name=APP_NAME, timeout=timeout
            )
            return True
        except Exception:
            pass
    return False
