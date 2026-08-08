import sys
import types
import pytest

from clipboard_dlp import notifier


@pytest.fixture(autouse=True)
def no_plyer(monkeypatch):
    monkeypatch.setattr(notifier, "_plyer_notification", None)


def _fake_run(calls, returncodes, stdout=b"42\n"):
    def run(cmd, **kw):
        calls.append((cmd, kw))
        return types.SimpleNamespace(returncode=returncodes.pop(0), stdout=stdout)
    return run


def test_empty_title_or_message_rejected():
    assert notifier.notify("", "body") is False
    assert notifier.notify("title", "") is False


def test_linux_no_backend_returns_false(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(notifier.shutil, "which", lambda *a: None)
    assert notifier.notify("t", "m") is False


def test_notify_send_success(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    calls = []
    monkeypatch.setattr(notifier.shutil, "which",
                        lambda n: "/usr/bin/notify-send" if n == "notify-send" else None)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run(calls, [0]))
    assert notifier.notify("t", "m") is True
    assert calls[0][0][0] == "notify-send"


def test_notify_send_failure_falls_back_to_zenity(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    calls = []
    def which(n):
        return "/usr/bin/notify-send" if n == "notify-send" else "/usr/bin/zenity"
    monkeypatch.setattr(notifier.shutil, "which", which)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run(calls, [1, 0]))
    assert notifier.notify("t", "m") is True
    assert calls[1][0][0] == "zenity"


def test_all_backends_fail_returns_false(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    calls = []
    def which(n):
        return "/usr/bin/notify-send" if n == "notify-send" else "/usr/bin/zenity"
    monkeypatch.setattr(notifier.shutil, "which", which)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run(calls, [1, 1]))
    assert notifier.notify("t", "m") is False


def test_duration_capped_at_5_seconds(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    calls = []
    monkeypatch.setattr(notifier.shutil, "which",
                        lambda n: "/usr/bin/notify-send" if n == "notify-send" else None)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run(calls, [0]))
    notifier.notify("t", "m", timeout=99)
    assert "-t" in calls[0][0]
    assert calls[0][0][calls[0][0].index("-t") + 1] == "5000"


def test_plyer_used_when_available(monkeypatch):
    calls = []

    class FakePlyer:
        @staticmethod
        def notify(**kw):
            calls.append(kw)

    monkeypatch.setattr(notifier, "_plyer_notification", FakePlyer)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(notifier.shutil, "which", lambda *a: None)
    assert notifier.notify("t", "m") is True
    assert calls and calls[0]["title"] == "t"


def test_notify_schedules_close_for_printed_id(monkeypatch):
    scheduled = []
    monkeypatch.setattr(notifier, "_schedule_close",
                        lambda nid, delay: scheduled.append((nid, delay)))
    monkeypatch.setattr(sys, "platform", "linux")
    calls = []
    monkeypatch.setattr(notifier.shutil, "which",
                        lambda n: "/usr/bin/notify-send" if n == "notify-send" else None)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run(calls, [0], stdout=b"42\n"))
    assert notifier.notify("t", "m") is True
    assert "--print-id" in calls[0][0]
    assert scheduled == [("42", 5)]


def test_no_id_printed_skips_scheduling(monkeypatch):
    scheduled = []
    monkeypatch.setattr(notifier, "_schedule_close",
                        lambda nid, delay: scheduled.append((nid, delay)))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(notifier.shutil, "which",
                        lambda n: "/usr/bin/notify-send" if n == "notify-send" else None)
    monkeypatch.setattr(notifier.subprocess, "run",
                        _fake_run([], [0], stdout=b"not-a-number\n"))
    assert notifier.notify("t", "m") is True
    assert scheduled == []


def test_close_notification_via_dbus_send(monkeypatch):
    calls = []
    monkeypatch.setattr(notifier.shutil, "which",
                        lambda n: "/usr/bin/dbus-send" if n == "dbus-send" else None)
    monkeypatch.setattr(notifier.subprocess, "run",
                        lambda *a, **k: (calls.append(a[0]),
                                         types.SimpleNamespace(returncode=0))[1])
    assert notifier._close_notification("42") is True
    assert any("CloseNotification" in a for a in calls[0])
    assert "uint32:42" in calls[0]


def test_close_notification_gdbus_fallback(monkeypatch):
    calls = []
    def which(n):
        return None if n == "dbus-send" else "/usr/bin/gdbus"
    monkeypatch.setattr(notifier.shutil, "which", which)
    monkeypatch.setattr(notifier.subprocess, "run",
                        lambda *a, **k: (calls.append(a[0]),
                                         types.SimpleNamespace(returncode=0))[1])
    assert notifier._close_notification("7") is True
    assert calls[0][0] == "gdbus"
    assert any("CloseNotification" in a for a in calls[0])


def test_close_notification_no_tools(monkeypatch):
    monkeypatch.setattr(notifier.shutil, "which", lambda *a: None)
    assert notifier._close_notification("42") is False
    assert notifier._close_notification("") is False
