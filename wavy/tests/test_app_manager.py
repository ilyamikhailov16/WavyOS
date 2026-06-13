import pytest
from scripts.app_manager import AppManager, OperationStatus


@pytest.fixture
def mock_registry(monkeypatch):
    # Mock _build_registry_cache to avoid reading real registry
    monkeypatch.setattr(AppManager, "_build_registry_cache", lambda self: None)


@pytest.fixture
def manager(mock_registry):
    am = AppManager()
    am._exe_cache = {
        "notepad": "C:\\Windows\\notepad.exe",
        "discord": "C:\\Users\\User\\AppData\\Local\\Discord\\Update.exe",
    }
    am._uninstall_cache = {
        "discord": '"C:\\Users\\User\\AppData\\Local\\Discord\\Update.exe" --uninstall'
    }
    am._exe_norm = {
        "notepad": "C:\\Windows\\notepad.exe",
        "discord": "C:\\Users\\User\\AppData\\Local\\Discord\\Update.exe",
    }
    am._uninstall_norm = {
        "discord": '"C:\\Users\\User\\AppData\\Local\\Discord\\Update.exe" --uninstall'
    }
    return am


def test_resolve_app_name(manager):
    assert manager._resolve_app_name("notepad") == "notepad.exe"
    # test fallback
    assert manager._resolve_app_name("unknown_app") == "unknown_app"


def test_launch_app_uri(manager, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "scripts.app_manager.os.startfile", lambda uri: calls.append(uri)
    )
    res = manager.launch_app("ms-settings:")
    assert res.status == OperationStatus.SUCCESS
    assert calls == ["ms-settings:"]


def test_launch_app_success(manager, monkeypatch):
    class FakeProcess:
        def __init__(self, *args, **kwargs):
            self.pid = 1234

        def poll(self):
            return None  # Still running

    monkeypatch.setattr("scripts.app_manager.subprocess.Popen", FakeProcess)
    monkeypatch.setattr("scripts.app_manager.time.sleep", lambda s: None)
    monkeypatch.setattr(manager, "_is_process_running", lambda exe: True)

    res = manager.launch_app("notepad")
    assert res.status == OperationStatus.SUCCESS
    assert res.data["pid"] == 1234


def test_close_app(manager, monkeypatch):
    def fake_run(cmd, timeout=None):
        if cmd[0] == "taskkill":
            return 0, "Success", ""
        return 1, "", "Error"

    monkeypatch.setattr(manager, "_run", fake_run)
    res = manager.close_app("notepad")
    assert res.status == OperationStatus.SUCCESS


def test_is_app_running(manager, monkeypatch):
    monkeypatch.setattr(
        manager, "_is_process_running", lambda exe: exe == "notepad.exe"
    )

    res1 = manager.is_app_running("notepad")
    assert res1.status == OperationStatus.SUCCESS
    assert res1.data["running"] is True

    res2 = manager.is_app_running("discord")
    assert res2.status == OperationStatus.SUCCESS
    assert res2.data["running"] is False


def test_uninstall_app_via_winget(manager, monkeypatch):
    def fake_run(cmd, timeout=None):
        if cmd[0] == "winget":
            return 0, "Successfully uninstalled", ""
        return 1, "", ""

    monkeypatch.setattr(manager, "_run", fake_run)
    monkeypatch.setattr(
        manager, "_lookup_uninstall_str", lambda x: None
    )  # mock no registry left

    res = manager.uninstall_app("discord")
    assert res.status == OperationStatus.SUCCESS
    assert res.data["method"] == "winget"


def test_list_running_apps(manager, monkeypatch):
    def fake_run(cmd, timeout=None):
        return (
            0,
            '"System Idle Process","0","Services","0","8 K"\n"System","4","Services","0","136 K"\n"notepad.exe","123","Console","1","5 K"',
            "",
        )

    monkeypatch.setattr(manager, "_run", fake_run)

    res = manager.list_running_apps()
    assert res.status == OperationStatus.SUCCESS
    assert "notepad.exe" in res.data["processes"]
    assert "System" in res.data["processes"]
