import subprocess

import scripts.energy_saver_mode as module


def test_open_system_settings_uses_configured_uri(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda cmd, shell, check: calls.append((cmd, shell, check)))

    module.open_system_settings()

    assert calls == [(["start", module.ENERGY_SAVER_SETTINGS.settings_uri], True, True)]


def test_enable_energy_saver_mode_runs_power_commands(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))
    refresh_rates = []
    monkeypatch.setattr(module, "set_refresh_rate", lambda hz: refresh_rates.append(hz) or True)

    result = module.enable_energy_saver_mode()

    assert result is True
    assert len(calls) == 2
    assert refresh_rates == [module.ENERGY_SAVER_SETTINGS.power.enabled_refresh_rate_hz]


def test_enable_energy_saver_mode_handles_subprocess_error(monkeypatch) -> None:
    error = subprocess.CalledProcessError(returncode=1, cmd="powercfg", stderr="denied")
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    assert module.enable_energy_saver_mode() is False


def test_disable_energy_saver_mode_restores_max_refresh_rate(monkeypatch) -> None:
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "get_max_supported_refresh_rate", lambda: 144)
    refresh_rates = []
    monkeypatch.setattr(module, "set_refresh_rate", lambda hz: refresh_rates.append(hz) or True)

    result = module.disable_energy_saver_mode()

    assert result is True
    assert refresh_rates == [144]


def test_hotkeys_register_expected_shortcuts(monkeypatch) -> None:
    registered = []
    waits = []
    monkeypatch.setattr(module.keyboard, "add_hotkey", lambda key, fn: registered.append((key, fn)))
    monkeypatch.setattr(module.keyboard, "wait", lambda key: waits.append(key))

    module.hotkeys()

    assert registered[0][0] == module.ENERGY_SAVER_SETTINGS.hotkeys.open_settings
    assert registered[1][0] == module.ENERGY_SAVER_SETTINGS.hotkeys.enable
    assert registered[2][0] == module.ENERGY_SAVER_SETTINGS.hotkeys.disable
    assert waits == [module.ENERGY_SAVER_SETTINGS.hotkeys.exit]
