"""UI and path constants for clipboard_dlp"""
from __future__ import annotations

import os

# ── PATHS ──────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))

# Prefer an XDG/user data directory for storing the history DB so sensitive
# clipboard contents are kept under the user's home directory rather than
# the package installation directory. If an existing packaged DB is found and
# no user DB exists, copy it across on first launch.
_XDG = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
_DATA_DIR = os.path.join(_XDG, "clipboard_dlp")

os.makedirs(_DATA_DIR, exist_ok=True)

# Candidate locations
_USER_DB = os.path.join(_DATA_DIR, "clipboard_history.db")
_PKG_DB = os.path.join(_BASE, "logs", "clipboard_history.db")

if os.path.exists(_PKG_DB) and not os.path.exists(_USER_DB):
	try:
		import shutil
		shutil.copy2(_PKG_DB, _USER_DB)
	except Exception:
		pass

DB_PATH = _USER_DB

BG          = "#0f1115"
BG_PANEL    = "#151a22"
BG_INPUT    = "#1a2029"
BG_DIALOG   = "#171b23"
BG_ITEM     = "#141922"
BG_HOVER    = "#1b2330"
BG_SEL      = "#22304a"
BG_BTN      = "#2457a6"
BG_BTN_HOV  = "#2d65bf"
BG_BTN_SEC  = "#2a313d"
BG_BTN_HOV2 = "#38404f"
BG_DANGER   = "#8b2f2f"
BG_DNG_HOV  = "#a63a3a"

FG          = "#ffffff"   # primary text (white)
FG2         = "#d0d0d0"   # secondary / dim
FG3         = "#9a9a9a"   # muted
FG_SEL      = "#ffffff"   # selected text
FG_ACCENT   = "#d0d0d0"   # accent (gray)
FG_GREEN    = "#cfcfcf"   # neutral gray
FG_YELLOW   = "#cfcfcf"
FG_RED      = "#cfcfcf"
FG_PURPLE   = "#cfcfcf"
FG_ORANGE   = "#cfcfcf"

BORDER      = "#444444"   # subtle border
BORDER2     = "#666666"   # active/focus border
SEP         = "#2b2b2b"   # separator line

FONT_UI     = ("Segoe UI",    9)
FONT_UI_B   = ("Segoe UI",    9,  "bold")
FONT_UI_S   = ("Segoe UI",    8)
FONT_MONO   = ("Consolas",    9)
FONT_MONO_S = ("Consolas",    8)
FONT_TITLE  = ("Segoe UI",   11,  "bold")
FONT_ICON   = ("DejaVu Sans", 12, "bold")
