import scripts.trash_tool as module


def test_clear_folder_ignores_missing_directory(tmp_path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module.send2trash, "send2trash", lambda path: calls.append(path))

    module.clear_folder(tmp_path / "missing")

    assert calls == []


def test_clear_folder_trashes_items(tmp_path, monkeypatch) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    calls = []
    monkeypatch.setattr(module.send2trash, "send2trash", lambda path: calls.append(path))

    module.clear_folder(tmp_path)

    assert set(calls) == {str(first), str(second)}


def test_clear_downloads_uses_configured_downloads_dir(monkeypatch, tmp_path) -> None:
    captured = []
    fake_home = tmp_path
    monkeypatch.setattr(module.pathlib.Path, "home", lambda: fake_home)
    monkeypatch.setattr(module, "clear_folder", lambda path: captured.append(path))

    module.clear_downloads()

    assert captured == [fake_home / module.TRASH_TOOL_SETTINGS.paths.downloads_dir_name]


def test_empty_recycle_bin_handles_already_empty(monkeypatch) -> None:
    class AlreadyEmptyError(Exception):
        def __init__(self):
            self.hresult = module.TRASH_TOOL_SETTINGS.shell.already_empty_hresult[0]

    monkeypatch.setattr(module.shell, "SHEmptyRecycleBin", lambda *_: (_ for _ in ()).throw(AlreadyEmptyError()))

    module.empty_recycle_bin()


def test_hotkeys_registers_expected_shortcuts(monkeypatch) -> None:
    registered = []
    waits = []
    monkeypatch.setattr(module.keyboard, "add_hotkey", lambda key, fn: registered.append((key, fn)))
    monkeypatch.setattr(module.keyboard, "wait", lambda key: waits.append(key))

    module.hotkeys()

    assert registered[0][0] == module.TRASH_TOOL_SETTINGS.hotkeys.clear_downloads
    assert registered[1][0] == module.TRASH_TOOL_SETTINGS.hotkeys.empty_recycle_bin
    assert waits == [module.TRASH_TOOL_SETTINGS.hotkeys.exit]
