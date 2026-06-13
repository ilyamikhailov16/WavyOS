import pytest
from scripts import turn_off


def test_shutdown_windows(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.sys, "platform", "win32")
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown()
    assert calls == ["shutdown /s /t 0"]


def test_shutdown_linux(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.sys, "platform", "linux")
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown()
    assert calls == ["shutdown now"]


def test_shutdown_mac(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.sys, "platform", "darwin")
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown()
    assert calls == ["shutdown now"]


def test_shutdown_unsupported(monkeypatch, caplog):
    calls = []
    monkeypatch.setattr(turn_off.sys, "platform", "unsupported")
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown()
    assert not calls
    assert "Unsupported operating system" in caplog.text


def test_shutdown_with_timer_negative():
    with pytest.raises(ValueError, match="Time cannot be negative"):
        turn_off.shutdown_with_timer(-1)


def test_shutdown_with_timer_windows(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr(turn_off.platform, "system", lambda: "Windows")
    monkeypatch.setattr(turn_off.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown_with_timer(5)

    assert sleeps == [300]
    assert calls == ["shutdown /s /t 1"]


def test_shutdown_with_timer_linux(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.platform, "system", lambda: "Linux")
    monkeypatch.setattr(turn_off.time, "sleep", lambda s: None)
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown_with_timer(1)

    assert calls == ["sudo shutdown now"]


def test_shutdown_with_timer_mac(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(turn_off.time, "sleep", lambda s: None)
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    turn_off.shutdown_with_timer(2)

    assert calls == ["osascript -e 'tell app \"System Events\" to shut down'"]


def test_shutdown_with_timer_keyboard_interrupt_windows(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.platform, "system", lambda: "Windows")

    def fake_sleep(s):
        raise KeyboardInterrupt()

    monkeypatch.setattr(turn_off.time, "sleep", fake_sleep)
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    with pytest.raises(SystemExit) as exc:
        turn_off.shutdown_with_timer(5)

    assert exc.value.code == 0
    assert calls == ["shutdown /a"]


def test_shutdown_with_timer_keyboard_interrupt_linux(monkeypatch):
    calls = []
    monkeypatch.setattr(turn_off.platform, "system", lambda: "Linux")

    def fake_sleep(s):
        raise KeyboardInterrupt()

    monkeypatch.setattr(turn_off.time, "sleep", fake_sleep)
    monkeypatch.setattr(turn_off.os, "system", lambda cmd: calls.append(cmd))

    with pytest.raises(SystemExit) as exc:
        turn_off.shutdown_with_timer(5)

    assert exc.value.code == 0
    assert not calls
