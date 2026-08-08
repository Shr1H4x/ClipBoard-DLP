# How to Run

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Desktop Dashboard (GUI)

```bash
PYTHONPATH=src python3 -m clipboard_dlp.app
```

Or, after `pip install -e .`:

```bash
clipboard-dlp-gui
```

## Command-Line Interface

```bash
PYTHONPATH=src python3 -m clipboard_dlp.cli --help
```

Or, after `pip install -e .`:

```bash
clipboard-dlp info
clipboard-dlp analyze --text "user@example.com"
clipboard-dlp backup
clipboard-dlp show-docs
```

## Linux Clipboard Backend

The clipboard layer calls external tools with hard timeouts (never blocks):

- Wayland: `wl-clipboard` (`wl-paste` / `wl-copy`)
- X11: `xclip` or `xsel`
- Optional (source application capture): `xdotool`

```bash
sudo apt install wl-clipboard xclip xsel xdotool
```

## Data Location

Clipboard history is stored in a SQLite database:

| OS | Path |
|---|---|
| Linux | `~/.local/share/clipboard_dlp/clipboard_history.db` |
| Windows | `%LOCALAPPDATA%\clipboard_dlp\clipboard_history.db` |
| macOS | `~/Library/Application Support/clipboard_dlp/clipboard_history.db` |

- Daily automatic backups land in `backups/` next to the database (10 kept).
- Set `CLIPBOARD_DLP_DB=/path/to.db` to override the database location
  (useful for tests or isolated runs).

## Closing the window

- **Windows** — the window hides to the system tray and keeps monitoring.
  Restore via the tray icon (or reopen with the same command).
- **Linux / macOS** — you're asked whether to keep running in the background.
  If yes, the window minimizes to the taskbar (and the tray icon is also
  created when the desktop supports it). All clipboard activity keeps being
  stored in the same database, so history is still there when you reopen.

## Building for Windows

Requires Python 3.10+ and the Windows launcher (`py`):

```
scripts\build_windows.bat
```

Produces `dist\ClipboardDLP.exe` via PyInstaller (uses `packaging\ClipboardDLP.spec`).

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/
# or
./tests/run_tests.sh
```
