"""Clipboard access with hard timeouts.

pyperclip can block indefinitely on Linux (wl-paste/xclip wait for the
clipboard owner, and wl-copy daemonizes keeping pipes open), which would
stall the monitor thread. We therefore prefer direct tool calls with
subprocess timeouts on Linux and only fall back to pyperclip where no
native tool is available (Windows/macOS use pyperclip directly).
"""
from __future__ import annotations

import os
import sys
import subprocess
from typing import Optional

try:
    import pyperclip
except Exception:
    pyperclip = None


_TIMEOUT = 2.0


def _tool(name: str) -> Optional[str]:
    import shutil
    return shutil.which(name)


def _is_linux() -> bool:
    return os.name != "nt" and sys.platform != "darwin"


def _wayland() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY"))


def paste() -> Optional[str]:
    """Return current clipboard text, or None on failure/timeout. Never blocks
    for more than a couple of seconds."""
    if _is_linux():
        if _wayland() and _tool("wl-paste"):
            try:
                return subprocess.run(
                    ["wl-paste", "-n", "-t", "text"],
                    capture_output=True, timeout=_TIMEOUT,
                ).stdout.decode(errors="replace") or None
            except Exception:
                pass
        for t in ("xclip", "xsel"):
            if _tool(t):
                try:
                    cmd = ["xclip", "-selection", "clipboard", "-o"] if t == "xclip" \
                        else ["xsel", "--clipboard", "--output"]
                    return subprocess.run(
                        cmd, capture_output=True, timeout=_TIMEOUT,
                    ).stdout.decode(errors="replace") or None
                except Exception:
                    pass
    if pyperclip is not None:
        try:
            return pyperclip.paste()
        except Exception:
            pass
    return None


def copy(text: str) -> bool:
    """Copy text to the clipboard. Returns True on success. Never blocks
    for more than a couple of seconds."""
    if not text:
        return False
    if _is_linux():
        if _wayland() and _tool("wl-copy"):
            try:
                subprocess.run(
                    ["wl-copy"], input=text.encode(), timeout=_TIMEOUT,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
        if _tool("xclip"):
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-i"],
                    input=text.encode(), timeout=_TIMEOUT,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                pass
    if pyperclip is not None:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass
    return False
