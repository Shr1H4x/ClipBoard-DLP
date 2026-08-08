# How to run

```bash
PYTHONPATH=src python3 -m clipboard_dlp.app
```

Or, after `pip install -e .` (or `pip install -r requirements.txt`):

```bash
clipboard-dlp-gui
```

## Closing the window

- **Windows** — the window hides to the system tray and keeps monitoring.
  Restore via the tray icon (or reopen with the same command).
- **Linux / macOS** — you're asked whether to keep running in the background.
  If yes, the window minimizes to the taskbar (and the tray icon is also
  created when the desktop supports it). All clipboard activity keeps being
  stored in the same database, so history is still there when you reopen.

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/
```
