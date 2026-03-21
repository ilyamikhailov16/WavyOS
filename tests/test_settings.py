from config import settings


def test_browser_presets_exposed_via_global_settings() -> None:
    preset_names = settings.browser.presets.names()

    assert "google" in preset_names
    assert "yandex" in preset_names
    assert settings.browser.presets.google.url.startswith("https://")


def test_browser_paths_are_available_for_custom_browsers() -> None:
    opera_paths = settings.browser.paths.for_browser("opera")
    yandex_paths = settings.browser.paths.for_browser("yandex")

    assert opera_paths
    assert yandex_paths
    assert all(path.__class__.__name__ == "WindowsPath" or path.__class__.__name__ == "PosixPath" for path in opera_paths)


def test_other_script_settings_are_available() -> None:
    assert settings.screen_tool.hotkeys.toggle_recording == "F9"
    assert settings.energy_saver.power.enabled_refresh_rate_hz > 0
    assert settings.system_toggle.ui.airplane_mode_timeout_seconds > 0
    assert settings.trash_tool.paths.downloads_dir_name == "Downloads"
