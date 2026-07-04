"""UI and path constants for clipboard_dlp"""
from __future__ import annotations

import os

# ── PATHS ──────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))

# Prefer an XDG/user data directory for storing the history DB so sensitive
# clipboard contents are kept under the user's home directory rather than
# the package installation directory. Fallback to the package 'logs' dir if
# necessary. If an existing packaged DB is found and no user DB exists, try
# to migrate it.
_XDG = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
_DATA_DIR = os.path.join(_XDG, "clipboard_dlp")
os.makedirs(_DATA_DIR, exist_ok=True)

# Candidate locations
_USER_DB = os.path.join(_DATA_DIR, "clipboard_history.db")
_PKG_DB = os.path.join(_BASE, "logs", "clipboard_history.db")

if os.path.exists(_PKG_DB) and not os.path.exists(_USER_DB):
	try:
		import shutil
		os.makedirs(os.path.dirname(_USER_DB), exist_ok=True)
		shutil.copy2(_PKG_DB, _USER_DB)
	except Exception:
		# If migration fails, ignore and continue using user DB path (it will be created on demand)
		pass

DB_PATH = _USER_DB

# ── PALETTE  (Grayscale) ───────────────────────────────────────────────
# Strict grayscale theme: black, white and shades of gray only
BG          = "#000000"   # main background (black)
BG_PANEL    = "#1a1a1a"   # sidebar / panel
BG_ITEM     = "#222222"   # list item normal
BG_HOVER    = "#2a2a2a"   # list item hover
BG_SEL      = "#444444"   # list item selected
BG_INPUT    = "#2a2a2a"   # input / search field
BG_DIALOG   = "#1a1a1a"   # modal background
BG_BTN      = "#333333"   # primary button
BG_BTN_HOV  = "#3b3b3b"
BG_BTN_SEC  = "#2f2f2f"   # secondary button
BG_BTN_HOV2 = "#474747"
BG_DANGER   = "#800000"   # danger (maroon)
BG_DNG_HOV  = "#a00000"   # danger hover (brighter maroon)

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
