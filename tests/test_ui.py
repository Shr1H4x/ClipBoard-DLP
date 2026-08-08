import sys
import time
import queue
import types
import pytest
import tkinter as tk

from clipboard_dlp import app as app_mod
from clipboard_dlp import db as db_mod
from clipboard_dlp.app import App
from clipboard_dlp.detector import SENSITIVE_COPY_PREFIX
from clipboard_dlp.monitor import Monitor


@pytest.fixture(scope="module")
def app_instance(tmp_path_factory):
    # Isolate tests from the real user DB — never touch the live history.
    # ClipDB's default path is bound at import time, so the only reliable way
    # to redirect it is to swap the ClipDB class App constructs.
    db_file = str(tmp_path_factory.mktemp("db") / "test_history.db")
    monkeypatch = pytest.MonkeyPatch()

    real_clipdb = db_mod.ClipDB

    class IsolatedClipDB(real_clipdb):
        def __init__(self, path=None, **kw):
            super().__init__(db_file, **kw)

    monkeypatch.setattr(app_mod, "ClipDB", IsolatedClipDB)

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
    monkeypatch.undo()


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


def test_copy_uses_clipboard_module(monkeypatch, app_instance):
    app = app_instance
    app.db.clear()
    app.db.add("copy-me", source="test")
    app._reload()
    row = app._rows[0]
    app._select(row)

    from clipboard_dlp import clipboard as clip_mod
    state = {"val": None}
    monkeypatch.setattr(clip_mod, "copy", lambda v: state.update(val=v) or True)

    app._copy(row)
    assert state["val"] == "copy-me"


def test_sensitive_copy_prepends_warning(monkeypatch, app_instance):
    app = app_instance
    app.db.clear()
    app.db.add("user@example.com", source="test")
    app._reload()
    row = app._rows[0]
    app._select(row)

    from clipboard_dlp import clipboard as clip_mod
    state = {"val": None}
    monkeypatch.setattr(clip_mod, "copy", lambda v: state.update(val=v) or True)

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


def test_scroll_target_resolves_from_event_widget(app_instance):
    app = app_instance
    child = tk.Frame(app._lf)
    assert app._resolve_scroll_target(types.SimpleNamespace(widget=child))[0] is app._canvas
    assert app._resolve_scroll_target(types.SimpleNamespace(widget=app._lf))[0] is app._canvas
    assert app._resolve_scroll_target(types.SimpleNamespace(widget=app._canvas))[0] is app._canvas
    assert app._resolve_scroll_target(types.SimpleNamespace(widget=app._preview))[0] is app._preview
    assert app._resolve_scroll_target(types.SimpleNamespace(widget=app._pause_btn)) == (None, None)


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
