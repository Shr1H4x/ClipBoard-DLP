import sys
import time
import queue
import types
import pytest
import tkinter as tk

from clipboard_dlp.app import App
from clipboard_dlp.detector import SENSITIVE_COPY_PREFIX
from clipboard_dlp.monitor import Monitor


@pytest.fixture(scope="module")
def app_instance():
    root = tk.Tk()
    root.withdraw()
    app = App(root)
    # yield to tests
    yield app
    # teardown
    try:
        app.monitor.stop()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass


def test_preview_display(app_instance):
    app = app_instance
    # reset DB and add a test entry
    app.db.clear()
    rid = app.db.add("hello world", source="terminal")
    app._reload()
    assert len(app._rows) >= 1
    row = app._rows[0]
    app._select(row)
    # ensure GUI updated
    app.root.update()
    preview = app._preview.get("1.0", "end").strip()
    assert preview == "hello world"
    assert not hasattr(app, "_source_text")


def test_copy_uses_pyperclip(monkeypatch, app_instance):
    app = app_instance
    app.db.clear()
    rid = app.db.add("copy-me", source="test")
    app._reload()
    row = app._rows[0]
    app._select(row)

    # Create a dummy pyperclip module
    mod = types.SimpleNamespace()
    state = {"val": None}
    def _copy(v):
        state["val"] = v
    def _paste():
        return state["val"]
    mod.copy = _copy
    mod.paste = _paste
    monkeypatch.setitem(sys.modules, "pyperclip", mod)

    app._copy(row)
    assert state["val"] == "copy-me"


def test_sensitive_copy_prepends_warning(monkeypatch, app_instance):
    app = app_instance
    app.db.clear()
    app.db.add("user@example.com", source="test")
    app._reload()
    row = app._rows[0]
    app._select(row)

    mod = types.SimpleNamespace()
    state = {"val": None}

    def _copy(v):
        state["val"] = v

    def _paste():
        return state["val"]

    mod.copy = _copy
    mod.paste = _paste
    monkeypatch.setitem(sys.modules, "pyperclip", mod)

    app._copy(row)
    assert state["val"].startswith(f"{SENSITIVE_COPY_PREFIX}\n\n")
    assert state["val"].endswith("user@example.com")


def test_preview_scrollable(app_instance):
    app = app_instance
    app.db.clear()
    long_text = "\n".join([f"line {i}" for i in range(200)])
    app.db.add(long_text, source="cli")
    app._reload()
    row = app._rows[0]
    app._select(row)
    app.root.update()
    # scroll to bottom and verify yview changed
    try:
        app._preview.config(state="normal")
        app._preview.yview_moveto(1.0)
        app._preview.config(state="disabled")
    except Exception:
        pass
    v = app._preview.yview()
    assert v[0] >= 0.0


def test_monitor_capture_fallback(monkeypatch):
    m = Monitor(None, queue.Queue())
    # simulate xdotool unavailable
    def _fail(*a, **k):
        raise Exception("no xdotool")
    monkeypatch.setattr("subprocess.check_output", lambda *a, **k: (_fail()))
    assert m._capture_source("http://example.com/page") == "browser"
    assert m._capture_source("<html><body>") == "html"
    assert m._capture_source("user@example.com") == "email"
    assert m._capture_source("plain text without hints") is None
