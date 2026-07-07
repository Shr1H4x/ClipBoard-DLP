from __future__ import annotations

import sys
import shutil
import subprocess

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


def _notify_linux(title: str, message: str, timeout: int) -> bool:
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-u", "critical", "-t", str(timeout * 1000),
                 "-a", APP_NAME, title, message],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False
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

    if _plyer_notification is not None:
        try:
            _plyer_notification.notify(
                title=title, message=message, app_name=APP_NAME, timeout=timeout
            )
            return True
        except Exception:
            pass

    platform = sys.platform
    if platform.startswith("win"):
        return _notify_windows(title, message, timeout)
    if platform == "darwin":
        return _notify_macos(title, message, timeout)
    return _notify_linux(title, message, timeout)
