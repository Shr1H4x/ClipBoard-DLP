"""UI and path constants for clipboard_dlp"""
from __future__ import annotations

import os
import sys

# ── PATHS ──────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(os.path.abspath(__file__))

# Prefer an XDG/user data directory for storing the history DB so sensitive
# clipboard contents are kept under the user's home directory rather than
# the package installation directory. If an existing packaged DB is found and
# no user DB exists, copy it across on first launch.
if sys.platform.startswith("win"):
    _DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "clipboard_dlp"
    )
elif sys.platform == "darwin":
    _DATA_DIR = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", "clipboard_dlp"
    )
else:
    _XDG = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    _DATA_DIR = os.path.join(_XDG, "clipboard_dlp")

os.makedirs(_DATA_DIR, exist_ok=True)

# Allow explicit isolation, e.g. tests and debugging: CLIPBOARD_DLP_DB=/tmp/x.db
_ENV_DB = os.environ.get("CLIPBOARD_DLP_DB")
if _ENV_DB:
    _USER_DB = _ENV_DB
else:
    _USER_DB = os.path.join(_DATA_DIR, "clipboard_history.db")

_PKG_DB = os.path.join(_BASE, "logs", "clipboard_history.db")

if os.path.exists(_PKG_DB) and not os.path.exists(_USER_DB):
	try:
		import shutil
		shutil.copy2(_PKG_DB, _USER_DB)
	except Exception:
		pass

DB_PATH = _USER_DB

# ── COLORS ─────────────────────────────────────────────────────────────────
# Refined dark dashboard palette (GitHub-dark inspired): coherent surfaces,
# a single blue accent, semantic status colors that are actually colored.
BG          = "#0d1117"   # window background
BG_PANEL    = "#161b22"   # toolbar / preview / dialog surfaces
BG_INPUT    = "#21262d"   # text fields
BG_DIALOG   = "#161b22"   # dialog body
BG_ITEM     = "#11161d"   # list rows
BG_HOVER    = "#1c2128"   # row / button hover
BG_SEL      = "#1d2e4d"   # selected row
BG_BTN      = "#2f81f7"   # primary button
BG_BTN_HOV  = "#3d8bfd"
BG_BTN_SEC  = "#21262d"   # secondary button
BG_BTN_HOV2 = "#30363d"
BG_DANGER   = "#da3633"   # destructive / alert
BG_DNG_HOV  = "#f85149"
BG_ACCENT   = "#2f81f7"   # accent line / title glyph
BG_STAT     = "#10151c"   # status bar
BG_TITLE    = "#21262d"   # dialog title bar

FG          = "#e6edf3"   # primary text
FG2         = "#c9d1d9"   # secondary text
FG3         = "#8b949e"   # muted text
FG_SEL      = "#ffffff"   # selected text
FG_ACCENT   = "#2f81f7"   # accent text
FG_GREEN    = "#3fb950"
FG_YELLOW   = "#d29922"
FG_RED      = "#f85149"
FG_PURPLE   = "#bc8cff"
FG_ORANGE   = "#db6d28"

BORDER      = "#30363d"   # subtle border
BORDER2     = "#8b949e"   # active/focus border
SEP         = "#21262d"   # separator line

# Platform-aware font families: Segoe UI/Consolas are Windows-only, so pick
# widely available fallbacks on Linux/macOS to keep the UI readable.
if sys.platform.startswith("win"):
    _UI_FAMILY   = "Segoe UI"
    _MONO_FAMILY = "Consolas"
    _ICON_FAMILY = "Segoe UI Symbol"
elif sys.platform == "darwin":
    _UI_FAMILY   = "Helvetica Neue"
    _MONO_FAMILY = "Menlo"
    _ICON_FAMILY = "Apple Symbols"
else:
    _UI_FAMILY   = "DejaVu Sans"
    _MONO_FAMILY = "DejaVu Sans Mono"
    _ICON_FAMILY = "DejaVu Sans"

FONT_UI     = (_UI_FAMILY,   9)
FONT_UI_B   = (_UI_FAMILY,   9,  "bold")
FONT_UI_S   = (_UI_FAMILY,   8)
FONT_MONO   = (_MONO_FAMILY, 9)
FONT_MONO_S = (_MONO_FAMILY, 8)
FONT_TITLE  = (_UI_FAMILY,  11,  "bold")
FONT_ICON   = (_ICON_FAMILY, 12, "bold")
