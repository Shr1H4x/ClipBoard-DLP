# Usage Guide — Clipboard DLP

This document shows practical workflows for the prototype: running the CLI, launching the GUI history app, analyzing text, and exporting data.

1) CLI quick commands

```bash
# show info
python -m clipboard_dlp.cli info

# analyze a text string
python -m clipboard_dlp.cli analyze --text "sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# list docs
python -m clipboard_dlp.cli show-docs
```

2) Launch the GUI history (Tkinter)

If you installed into a venv or used `pip install -e .`, you can run:

```bash
python -m clipboard_dlp.gui
```

The GUI monitors the clipboard (requires `pyperclip`), stores plain text copies into an sqlite database under `logs/clipboard_history.db`, and lets you:

- Pause/resume monitoring
- Copy a previous entry back to the clipboard
- Delete a single entry
- Clear all history
- Export history as CSV

Privacy note: This prototype stores raw clipboard text in the local sqlite DB. If you want the DLP-style behavior (metadata-only), do not enable the GUI history or clear the DB regularly.

3) Exporting and reporting

From the GUI use `Export CSV` to save a human-readable history. For programmatic access, open `logs/clipboard_history.db` and run queries.

4) Running tests

```bash
pytest -q
```
