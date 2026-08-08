# Clipboard DLP — Windows Troubleshooting & Debugging Notes

This document records every problem found while getting the **Clipboard DLP** Windows
executable (`dist\ClipboardDLP.exe`) to build and run correctly, how each issue was
debugged, and the differences between the Windows and Linux behaviour of the code.

---

## 1. Problem: the .exe would not start (`ImportError`)

### Symptom

Running `ClipboardDLP.exe` immediately failed with:

```
Traceback (most recent call last):
  File "app.py", line 12, in <module>
ImportError: attempted relative import with no known parent package
```

### Root cause

`src\clipboard_dlp\app.py` is a **package module**. It imports its siblings with
relative imports:

```python
from .constants import (DB_PATH, BG, ...)
from .db import ClipDB
from .monitor import Monitor
from .widgets import VSBtn, ClipRow
from .detector import detect_sensitive, ...
from .dialogs import NotifyDialog, ConfirmDialog, ExportDialog, VSDialog
```

Relative imports only work when the module is loaded **as part of the package**
(`clipboard_dlp.app`). The PyInstaller spec used `app.py` directly as the entry script:

```python
a = Analysis(['src\\clipboard_dlp\\app.py'], pathex=['.\\src'], ...)
```

PyInstaller executes the script as a top-level `__main__` module, so there is no
parent package and every `from .x import ...` fails.

### Fix

1. Created a top-level launcher `main.py` that imports the package properly:

   ```python
   import os
   import sys

   sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

   from clipboard_dlp.app import main

   if __name__ == "__main__":
       main()
   ```

2. Pointed the spec at the launcher:

   ```python
   a = Analysis(['main.py'], pathex=['.\\src'], ...)
   ```

### Lesson

Never point PyInstaller at a module that uses relative imports. Use a separate
top-level entry-point script and keep `pathex` pointed at the `src` directory so the
package resolves as `clipboard_dlp`.

---

## 2. Problem: YARA rules not found in the frozen build

### Symptom

The rule files shipped with the app (`yara\*.yar`) were not where the code looked for
them, so YARA detection silently fell back to regex-only.

### Root cause

`detector.py` loads rules relative to the module file:

```python
here = os.path.dirname(__file__)
default_dir = os.path.join(here, "yara")
```

In a frozen exe, `__file__` points into the extraction directory
(`%TEMP%\_MEIxxxx\clipboard_dlp\`), but the spec bundled the folder at the top level:

```python
datas=[('.\\src\\clipboard_dlp\\yara', 'yara')]   # lands at _MEIxxxx\yara
```

### Fix

Bundle the rules under the package path so the `__file__`-relative lookup works:

```python
datas=[('.\\src\\clipboard_dlp\\yara', 'clipboard_dlp\\yara')]
```

---

## 3. Problem: optional runtime dependencies missing

### Symptom

Features silently degraded in the exe (no tray icon, no clipboard capture, no source
capture, no notifications). The build log
(`build\ClipboardDLP\warn-ClipboardDLP.txt`) listed:

```
missing module named pyperclip - imported by clipboard_dlp.monitor (optional)
missing module named pystray  - imported by clipboard_dlp.app (delayed, optional)
missing module named psutil   - imported by clipboard_dlp.monitor (optional)
missing module named win32gui / win32process - imported by clipboard_dlp.monitor
missing module named PIL      - imported by clipboard_dlp.app (delayed, optional)
missing module named plyer / win10toast - imported by clipboard_dlp.notifier
```

### Root cause

The requirements from `requirements.txt` were not installed in the Python
environment used to build (`pystray`, `pillow`, `pyperclip`, `psutil`, `pywin32`,
`plyer`...). Because every import in the code is guarded with `try/except`, the
app still started, but the monitor could not read the clipboard at all.

### Fix

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm ClipboardDLP.spec
```

Check `build\ClipboardDLP\warn-*.txt` after every build for newly missing modules.

---

## 4. Problem: "the app runs but copied data never shows up" (longest investigation)

### Symptom

After fixing the import error the exe stayed alive, the window appeared, but no new
clipboard entries appeared in the UI and the SQLite history did not grow.

### What the app is supposed to do

| Component | Role |
|---|---|
| `Monitor` (thread) | Polls the clipboard every 0.6 s |
| `clipboard.paste()` | Reads clipboard text (pyperclip on Windows) |
| `Monitor._capture_source()` | Best-effort window title / process source |
| `ClipDB.add()` | INSERT into `history` table |
| `Monitor._run_once()` | Paste → dedup → source → add → notify → queue |
| `App._poll()` | Drains the queue and appends rows to the UI |
| `App._reload()` | Loads all rows from the DB at startup |

DB location on Windows:
`%LOCALAPPDATA%\clipboard_dlp\clipboard_history.db`

### Debugging steps that found the truth

1. **Checked the database directly**
   ```powershell
   Test-Path "$env:LOCALAPPDATA\clipboard_dlp\clipboard_history.db"
   ```
   The file existed and contained the packaged seed data, but nothing new.

2. **Live end-to-end test** — launched the exe, copied text via `pyperclip.copy()`,
   waited, re-queried the DB. Nothing appeared. This reproduced the bug.

3. **Added file-based instrumentation** to `Monitor` (`monitor.py`) writing to
   `%LOCALAPPDATA%\clipboard_dlp\debug.log`:
   ```python
   def _debug_log(msg): ...  # append msg to debug.log
   ```
   Logged: `paste ->`, `db.last ->`, `DEDUP`, `source ->`, `add -> rid=`, plus a
   `try/except` around each poll cycle so hidden exceptions would be written too.

4. **Bootloader debug** — set `debug=True` and `console=True` in the spec and
   rebuilt. The bootloader log showed the full startup sequence:
   ```
   [PYI-6964:DEBUG] this is parent process of onefile application.
   [PYI-5844:DEBUG] this is child process of onefile application (main application process).
   ...
   [PYI-5844:DEBUG] LOADER: running main.py
   ```

5. **Key discoveries**
   - **Onefile exes are two processes.** The bootloader (parent) spawns a child that
     runs the actual app. Checking `MainWindowTitle` on the wrong PID (the parent)
     reported "no window" even though the child had one. The window title of the
     child was `Clipboard DLP Monitor`.
   - **The app worked all along.** The instrumentation log proved it:
     ```
     paste -> 'MARKER_UNIQUE_777777'
     ws: parts=['ClipboardDLP.exe', 'Clipboard DLP Monitor']
     source -> 'ClipboardDLP.exe - Clipboard DLP Monitor'
     add -> rid=12 path='C:\Users\allte\AppData\Local\clipboard_dlp\clipboard_history.db'
     ```
   - **Killing the parent PID orphans the child.** `proc.terminate()` / `taskkill /PID`
     only killed the parent; the child (the monitor) kept running, kept polling the
     clipboard, and kept re-adding rows — which made later test runs look "broken"
     (dedup matched rows the orphan had just written, logs interleaved, rows appeared
     and disappeared between checks). Use `taskkill /PID <pid> /T /F` to kill the tree.
   - **Red herring:** a second DB under
     `%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python...\LocalCache\Local\clipboard_dlp`
     (created by the Microsoft Store build of Python) looked like a separate DB, but
     the Store Python's `LOCALAPPDATA` resolves to the same real path — it was just a
     leftover directory, not the problem.

6. **Final clean verification** — killed all stale `ClipboardDLP` processes, wiped
   the DB, launched one fresh exe, copied a unique marker string and searched every
   `*.db` on the system for it. The marker was found in the one real database:

   ```
   HIT: C:\Users\allte\AppData\Local\clipboard_dlp\clipboard_history.db
   ```

### Fix applied

The monitor loop was made crash-safe. The original code let any exception kill the
thread silently; now each poll cycle is wrapped so an unexpected error is written to
`%LOCALAPPDATA%\clipboard_dlp\error.log` and the loop keeps going:

```python
def run(self):
    while not self._stop.is_set():
        try:
            self._run_once()
        except Exception:
            import traceback
            _error_log(traceback.format_exc())
            time.sleep(self.interval)
```

### Debugging techniques used (summary)

- File-based logging instead of `print()` (windowed exes have no visible stdout).
- `debug=True` / `console=True` in the spec for bootloader output.
- `Get-Process ClipboardDLP | Select MainWindowTitle` to verify the GUI actually
  opened (check the **child** PID).
- Searching every `*.db` on the system for a unique marker to prove where rows land.
- `taskkill /PID <pid> /T /F` to kill onefile process trees.

---

## 5. Windows vs Linux differences in this codebase

| Area | Windows | Linux |
|---|---|---|
| Clipboard read (`clipboard.py` `paste()`) | `pyperclip.paste()` (ctypes/win32) | `wl-paste` (Wayland) or `xclip`/`xsel` subprocesses, 2 s timeouts |
| Clipboard write (`copy()`) | `pyperclip.copy()` | `wl-copy` / `xclip -i` |
| Window/source capture (`Monitor._window_source()`) | `win32gui.GetForegroundWindow()` + `GetWindowText()` + `win32process.GetWindowThreadProcessId()` + `psutil.Process(pid).name()` | `xdotool getactivewindow / getwindowname / getwindowpid` + `/proc/<pid>/comm` or `ps` |
| Notifications (`notifier.py`) | `win10toast.ToastNotifier` then `plyer` fallback | `notify-send --print-id` + D-Bus `CloseNotification` (duration cap), `zenity`, `plyer` |
| Data directory (`constants.py`) | `%LOCALAPPDATA%\clipboard_dlp` | `~/.local/share/clipboard_dlp` (XDG) |
| Fonts (`constants.py`) | `Segoe UI`, `Consolas`, `Segoe UI Symbol` | `DejaVu Sans`, `DejaVu Sans Mono` |
| DB file permissions (`db.py`) | skipped (`chmod` N/A on Windows) | `os.chmod(path, 0o600)` |
| Tray icon (`app.py`) | `pystray` win32 backend | `pystray` X11/GTK backends |
| Console/stdio | `console=False` — stdout/stderr are `None`; crashes are silent or a modal error dialog | normally run from a terminal |

### Known platform-specific test failures on Windows

`pytest` result: **43 passed, 2 failed** (both failures are Linux-only tests):

- `tests/test_notifier.py::test_notify_schedules_close_for_printed_id` — mocks
  `notify-send` and D-Bus, which do not exist on Windows.
- `tests/test_ui.py::test_monitor_capture_fallback` — asserts `_capture_source()`
  returns `"browser"` when subprocesses fail; on Windows the real win32 path is used
  and returns the actual window title (e.g. `ClipboardDLP.exe - Clipboard DLP Monitor`).

Run tests on Windows with the src layout on the path:

```powershell
$env:PYTHONPATH = ".\src"
python -m pytest -q
```

---

## 6. Key functions involved

| Function | File | Purpose |
|---|---|---|
| `main()` | `main.py` (launcher) / `app.py` | Entry point; creates `tk.Tk()` root |
| `App.__init__()` | `app.py` | Builds UI, opens `ClipDB`, starts `Monitor`, starts `_poll`/`_clock` |
| `App._reload()` | `app.py` | Loads all rows from DB at startup |
| `App._poll()` | `app.py` | Drains monitor queue → adds rows to UI |
| `Monitor.run()` / `_run_once()` | `monitor.py` | Poll loop with crash-safe wrapper |
| `clipboard.paste()` / `copy()` | `clipboard.py` | Platform clipboard access with hard timeouts |
| `Monitor._capture_source()` / `_window_source()` | `monitor.py` | Window title/process source capture |
| `ClipDB.add()` / `last()` / `list()` | `db.py` | SQLite history storage |
| `detect_sensitive()` | `detector.py` | Regex (+ optional YARA) detection |
| `notify()` | `notifier.py` | Cross-platform desktop notifications |
| `constants.py` | `constants.py` | DB path, UI palette, platform fonts |

---

## 7. Final state / how to rebuild

```powershell
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Build (spec: entry = main.py, pathex = .\src, datas = clipboard_dlp\yara)
python -m PyInstaller --clean --noconfirm ClipboardDLP.spec

# 3. Verify: launch and check the window + DB
.\dist\ClipboardDLP.exe
# DB: %LOCALAPPDATA%\clipboard_dlp\clipboard_history.db
# Error log (if the monitor ever fails): %LOCALAPPDATA%\clipboard_dlp\error.log
```

**Golden rules for Windows packaging:**

1. Entry script must not use relative imports → use `main.py`.
2. `datas` targets must match runtime `__file__`-relative lookups.
3. Install every dependency in `requirements.txt` before building; inspect
   `warn-*.txt` afterwards.
4. Windowed exes hide all output → write diagnostics to a file.
5. Onefile exes are parent + child processes → kill with `taskkill /T /F`, and
   check the child PID for window titles.
