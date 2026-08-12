# Running Clipboard DLP

This document explains how to run Clipboard DLP on Linux and Windows (detailed step-by-step). It covers prerequisites, installation, running the GUI, optional features, and troubleshooting.

**Quick overview**
- The app is implemented in Python and uses `tkinter` for UI and `pyperclip` for clipboard access.
- The codebase root contains a `requirements.txt` and a `src/` package. The DB is stored in a per-user data directory (platform-specific).

---

## Linux

Prerequisites
- Python 3.8+ (system `python3`)
- `python3-venv` for virtual environments (optional but recommended)
- `tkinter` (`python3-tk` on Debian/Ubuntu)

Install system packages (Debian/Ubuntu example):
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk
```

Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies
```bash
pip install -r requirements.txt
```

Optional (YARA scanning)
- If you want YARA-based detection, install `yara-python` (may require libyara headers):
```bash
pip install yara-python
```

Run the GUI application
```bash
PYTHONPATH=src python3 -m clipboard_dlp.app
```

Run the CLI (analyze example)
```bash
PYTHONPATH=src python3 -m clipboard_dlp.cli analyze --text "my secret"
```

Check where the DB is stored
```bash
PYTHONPATH=src python3 -c "from clipboard_dlp.constants import DB_PATH; print(DB_PATH)"
```

Notes
- On Linux the app tries to capture the active window/process using `xdotool`. If `xdotool` is not installed this feature is skipped and the app falls back to content heuristics.
- The DB file is created under your user data directory (e.g. `~/.local/share/clipboard_dlp/clipboard_history.db`). The code attempts to set POSIX file permissions (`600`) for privacy.

---

## Windows

Prerequisites
- Python 3.8+ (download from python.org). Ensure `tkinter` is included (standard Windows installer typically includes it).
- Optional: `pywin32` and `psutil` for better source (active window/process) capture.

Create and activate a virtual environment (PowerShell)
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Or (cmd.exe)
```cmd
py -3 -m venv .venv
.\.venv\Scripts\activate.bat
```

Install Python dependencies
```powershell
pip install -r requirements.txt
# Optional Windows extras
pip install pywin32 psutil
```

Run the GUI application
- PowerShell:
```powershell
$env:PYTHONPATH = "src"
py -3 -m clipboard_dlp.app
```
- cmd.exe:
```cmd
set PYTHONPATH=src
py -3 -m clipboard_dlp.app
```

Notes
- On Windows the app will attempt to use `pywin32` (`win32gui` / `win32process`) and `psutil` to find the active window/process. If these libraries are not installed the app falls back to content heuristics (URLs / email / html detection).
- The POSIX `chmod(0o600)` call is skipped on Windows; the DB is stored in the appropriate per-user data directory (e.g. `%APPDATA%\clipboard_dlp\clipboard_history.db` when `platformdirs` is installed).

---

## Optional & advanced

- Add YARA rules in `src/clipboard_dlp/yara/` (files ending in `.yar` / `.yara`) to enable additional pattern matching if you installed `yara-python`.
- To run the unit tests:
```bash
pytest
```
or use the included script:
```bash
./tests/run_tests.sh
```

## Troubleshooting

- Blank UI or no clipboard access: ensure `tkinter` and `pyperclip` are installed and your Python distribution includes GUI support.
- Active window/process not captured: on Linux install `xdotool`; on Windows install `pywin32` and `psutil`.
- DB path unexpected: run the DB_PATH print command above to locate the database file.

## Security notes

- The app stores clipboard history locally; this can include sensitive information. The DB is stored in a per-user data directory and the app tries to restrict file permissions on POSIX systems.
- Be careful when exporting or sharing the DB/CSV — exported files contain full clipboard contents by default.

---

If you want, I can add a short `docs/INSTALLATION.md` variant with screenshots or create a packaged Windows installer script. Tell me which you prefer.