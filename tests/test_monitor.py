import queue
import time
import pytest

from clipboard_dlp import monitor as mon_mod
from clipboard_dlp.monitor import Monitor


class FakeDB:
    def __init__(self):
        self.rows = []
        self.added = []

    def add(self, text, source=None):
        self.rows.append(text)
        self.added.append((text, source))
        return len(self.rows) - 1

    def last(self):
        return self.rows[-1] if self.rows else None


@pytest.fixture
def fake_paste(monkeypatch):
    def _set(texts):
        seq = iter(texts)
        monkeypatch.setattr(mon_mod, "safe_paste", lambda: next(seq, None))
    return _set


def _run(monkeypatch, texts, **monitor_kw):
    db = FakeDB()
    q = queue.Queue()
    seq = iter(texts)
    monkeypatch.setattr(mon_mod, "safe_paste", lambda: next(seq, None))
    m = Monitor(db, q, interval=0.05, **monitor_kw)
    m.start()
    time.sleep(0.4)
    m.stop()
    return m, db, q


def test_stores_each_new_text_and_queues(monkeypatch):
    m, db, q = _run(monkeypatch, ["one", "two"])
    assert db.rows == ["one", "two"]
    got = [q.get_nowait() for _ in range(q.qsize())]
    assert [r[1] for r in got] == ["one", "two"]
    assert all(isinstance(r[2], list) for r in got)


def test_repeated_text_deduplicated(monkeypatch):
    m, db, q = _run(monkeypatch, ["dup", "dup", "dup", "other"])
    assert db.rows == ["dup", "other"]


def test_sensitive_copy_triggers_notification(monkeypatch):
    calls = []
    monkeypatch.setattr(mon_mod, "notify",
                        lambda t, b, timeout=5: calls.append((t, b)) or True)
    m, db, q = _run(monkeypatch, ["user@example.com"])
    assert db.rows == ["user@example.com"]
    assert len(calls) == 1
    assert calls[0][0] == "⚠️ Sensitive data copied"
    assert "Email address" in calls[0][1]


def test_notifications_can_be_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(mon_mod, "notify",
                        lambda t, b, timeout=5: calls.append((t, b)) or True)
    m, db, q = _run(monkeypatch, ["user@example.com"], notifications=False)
    assert db.rows == ["user@example.com"]
    assert calls == []


def test_notify_cooldown_throttles(monkeypatch):
    calls = []
    monkeypatch.setattr(mon_mod, "notify",
                        lambda t, b, timeout=5: calls.append((t, b)) or True)
    m, db, q = _run(monkeypatch, ["a@x.com", "b@y.com"], notify_cooldown=5.0)
    assert len(db.rows) == 2
    assert len(calls) == 1


def test_mark_seen_updates_last(monkeypatch):
    m = Monitor(None, queue.Queue())
    m.mark_seen("abc")
    assert m._last == "abc"
