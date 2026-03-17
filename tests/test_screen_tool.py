from pathlib import Path

import scripts.screen_tool as module


def test_take_screenshot_saves_file(monkeypatch, tmp_path) -> None:
    saved_paths = []

    class FakeImage:
        def save(self, path):
            saved_paths.append(path)

    monkeypatch.setattr(module.pyautogui, "screenshot", lambda: FakeImage())
    monkeypatch.setattr(module, "timestamp", lambda: "20260101_120000")
    monkeypatch.setattr(module.Path, "cwd", lambda: tmp_path)

    module.take_screenshot()

    assert saved_paths == [tmp_path / "screenshot_20260101_120000.png"]


def test_start_recording_starts_thread(monkeypatch) -> None:
    started = []

    class FakeThread:
        def __init__(self, target):
            self.target = target

        def start(self):
            started.append(self.target)

    monkeypatch.setattr(module.threading, "Thread", FakeThread)
    monkeypatch.setattr(module, "recording", False)
    monkeypatch.setattr(module, "record_thread", None)

    module.start_recording()

    assert module.recording is True
    assert started == [module.record_screen]


def test_start_recording_noop_when_already_recording(monkeypatch) -> None:
    monkeypatch.setattr(module, "recording", True)
    monkeypatch.setattr(module.threading, "Thread", lambda target: (_ for _ in ()).throw(AssertionError("should not create thread")))

    module.start_recording()

    assert module.recording is True


def test_stop_recording_turns_flag_off(monkeypatch) -> None:
    monkeypatch.setattr(module, "recording", True)

    module.stop_recording()

    assert module.recording is False


def test_toggle_recording_dispatches(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module, "recording", False)
    monkeypatch.setattr(module, "start_recording", lambda: calls.append("start"))
    monkeypatch.setattr(module, "stop_recording", lambda: calls.append("stop"))

    module.toggle_recording()
    monkeypatch.setattr(module, "recording", True)
    module.toggle_recording()

    assert calls == ["start", "stop"]


def test_hotkeys_registers_and_stops_recording(monkeypatch) -> None:
    registered = []
    waits = []
    stopped = []

    monkeypatch.setattr(module.keyboard, "add_hotkey", lambda key, fn: registered.append((key, fn)))
    monkeypatch.setattr(module.keyboard, "wait", lambda key: waits.append(key))
    monkeypatch.setattr(module, "recording", True)
    monkeypatch.setattr(module, "stop_recording", lambda: stopped.append(True))

    module.hotkeys()

    assert registered[0][0] == module.SCREEN_TOOL_SETTINGS.hotkeys.toggle_recording
    assert registered[1][0] == module.SCREEN_TOOL_SETTINGS.hotkeys.screenshot
    assert waits == [module.SCREEN_TOOL_SETTINGS.hotkeys.exit]
    assert stopped == [True]
