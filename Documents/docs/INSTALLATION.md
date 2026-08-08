# Installation, Setup, and Running — Clipboard DLP

This guide covers cloning the repository, creating a Python virtual environment, installing dependencies, running the CLI demo, and running tests.

**Prerequisites**
- Python 3.10 or newer
- Git
- On Linux: `xclip` or `xsel` for clipboard backend

**Clone the repository**

```bash
git clone https://github.com/Shr1H4x/clipboard-security-tool.git
cd clipboard-security-tool
```

**Create and activate a virtual environment**

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Install dependencies**

Method A — using `requirements.txt` (quick):

```bash
pip install -r requirements.txt
```

Method B — editable install (development):

```bash
pip install -e .
```

If you installed with `pyproject.toml`/`pip install -e .`, the `clipboard-dlp` CLI entry will be available.

**Platform-specific notes**
- Linux: Install `xclip` or `xsel` if the clipboard backend is needed:

```bash
sudo apt install xclip
# or
sudo apt install xsel
```

- Windows: Full hook-based monitoring (WM_CLIPBOARDUPDATE) requires `pywin32` (not bundled in this prototype). The CLI demo works cross-platform with `pyperclip`.

**Run the CLI demo**

You can run the packaged CLI if you installed the project, or run the module directly.

Using the installed script:

```bash
clipboard-dlp info
clipboard-dlp analyze --text "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
```

Or using Python module directly:

```bash
python -m clipboard_dlp.cli info
python -m clipboard_dlp.cli analyze --text "sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
```

**View available docs**

```bash
python -m clipboard_dlp.cli show-docs
```

**Run tests**

```bash
pytest -q
```

**Quick debug / verbose run**

If you want to test analyzer manually from a Python REPL:

```python
from clipboard_dlp import analyzer
print(analyzer.detect('test@example.com'))
```

**Packaging and distribution**

This project includes a simple `pyproject.toml`. To build a wheel:

```bash
python -m pip install --upgrade build
python -m build
```

For a standalone binary on Windows/Linux, consider using `PyInstaller` (example not included in this prototype).

**Next steps**
- Edit `config.yaml` (when added) to tune detection thresholds
- Implement `monitor.py` and GUI components in `src/clipboard_dlp/` for real-time monitoring

If you want, I can update `README.md` with a short install quickstart and add a GitHub Actions workflow to run tests on push.
