import subprocess
from types import SimpleNamespace

from scripts import system_toggle_tool as module


def test_toggle_wifi_logs_no_adapter(monkeypatch) -> None:
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="NoWiFi", stderr="", returncode=0),
    )

    module.toggle_wifi()


def test_toggle_bluetooth_reports_state(monkeypatch) -> None:
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="On", stderr="", returncode=0),
    )

    module.toggle_bluetooth()


def test_toggle_airplane_mode_handles_access_denied(monkeypatch) -> None:
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="AccessDenied", stderr="", returncode=0),
    )

    module.toggle_airplane_mode()


def test_toggle_airplane_mode_handles_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd="powershell", timeout=1)),
    )

    module.toggle_airplane_mode()


def test_toggle_notifications_uses_configured_uri(monkeypatch) -> None:
    runs = []
    presses = []
    hotkeys = []
    sleeps = []

    monkeypatch.setattr(module.subprocess, "run", lambda cmd, shell=True: runs.append((cmd, shell)))
    monkeypatch.setattr(module.pyautogui, "press", lambda key: presses.append(key))
    monkeypatch.setattr(module.pyautogui, "hotkey", lambda *keys: hotkeys.append(keys))
    monkeypatch.setattr(module.time, "sleep", lambda value: sleeps.append(value))

    module.toggle_notifications()

    assert runs[0][0] == ["start", module.SYSTEM_TOGGLE_SETTINGS.ui.notifications_uri]
    assert presses == ["space"]
    assert hotkeys == [("alt", "f4")]
    assert sleeps == [
        module.SYSTEM_TOGGLE_SETTINGS.ui.open_delay_seconds,
        module.SYSTEM_TOGGLE_SETTINGS.ui.post_toggle_delay_seconds,
    ]


def test_hotkeys_register_expected_shortcuts(monkeypatch) -> None:
    registered = []
    waits = []
    monkeypatch.setattr(module.keyboard, "add_hotkey", lambda key, fn: registered.append((key, fn)))
    monkeypatch.setattr(module.keyboard, "wait", lambda key: waits.append(key))

    module.hotkeys()

    assert registered[0][0] == module.SYSTEM_TOGGLE_SETTINGS.hotkeys.mute
    assert registered[1][0] == module.SYSTEM_TOGGLE_SETTINGS.hotkeys.wifi
    assert registered[2][0] == module.SYSTEM_TOGGLE_SETTINGS.hotkeys.bluetooth
    assert registered[3][0] == module.SYSTEM_TOGGLE_SETTINGS.hotkeys.airplane_mode
    assert registered[4][0] == module.SYSTEM_TOGGLE_SETTINGS.hotkeys.notifications
    assert waits == [module.SYSTEM_TOGGLE_SETTINGS.hotkeys.exit]
