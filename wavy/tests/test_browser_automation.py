from pathlib import Path

import scripts.browser_automation as module


def test_resolve_config_uses_preset_values() -> None:
    url, selector = module.resolve_config("google")

    assert url == module.PRESETS.google.url
    assert selector == module.PRESETS.google.input_selector


def test_resolve_config_prefers_explicit_selector_over_preset() -> None:
    url, selector = module.resolve_config("google", input_selector="#custom-search")

    assert url == module.PRESETS.google.url
    assert selector == "#custom-search"


def test_resolve_config_adds_https_if_missing() -> None:
    url, selector = module.resolve_config("example.com")

    assert url == "https://example.com"
    assert selector is None


def test_resolve_config_keeps_http() -> None:
    url, selector = module.resolve_config("http://example.com")

    assert url == "http://example.com"
    assert selector is None


def test_build_direct_search_url_from_preset() -> None:
    result = module.build_direct_search_url("google", "playwright python", None, None)

    assert result == "https://www.google.com/search?q=playwright+python"


def test_build_direct_search_url_disabled_for_custom_selector() -> None:
    result = module.build_direct_search_url(
        "google", "playwright python", "#custom", None
    )

    assert result is None


def test_map_progid_to_browser_handles_known_and_custom_values() -> None:
    assert module.map_progid_to_browser("ChromeHTML") == "chrome"
    assert module.map_progid_to_browser("OperaStable") == "opera"
    assert module.map_progid_to_browser("YandexHTML") == "yandex"
    assert module.map_progid_to_browser("UnknownBrowser") is None


def test_get_launch_command_for_standard_browser() -> None:
    assert module.get_launch_command_for_browser("firefox") == [
        "cmd",
        "/c",
        "start",
        "firefox",
    ]


def test_get_launch_command_for_custom_browser_uses_executable(monkeypatch) -> None:
    monkeypatch.setattr(
        module, "find_custom_browser_executable", lambda _: Path("C:/Opera/opera.exe")
    )

    result = module.get_launch_command_for_browser("opera")

    assert result == ["C:\\Opera\\opera.exe"] or result == ["C:/Opera/opera.exe"]


def test_resolve_browser_launch_options_for_explicit_edge() -> None:
    engine, launch_kwargs, label, browser_key = module.resolve_browser_launch_options(
        "edge", headed=True
    )

    assert engine == "chromium"
    assert launch_kwargs["channel"] == "msedge"
    assert launch_kwargs["headless"] is False
    assert label == "Microsoft Edge"
    assert browser_key == "edge"


def test_resolve_browser_launch_options_for_default_known_browser(monkeypatch) -> None:
    monkeypatch.setattr(
        module, "get_windows_default_browser_progid", lambda: "ChromeHTML"
    )

    engine, launch_kwargs, label, browser_key = module.resolve_browser_launch_options(
        "default", headed=False
    )

    assert engine == "chromium"
    assert launch_kwargs["channel"] == "chrome"
    assert launch_kwargs["headless"] is True
    assert label == "Google Chrome"
    assert browser_key == "chrome"


def test_resolve_browser_launch_options_falls_back_when_default_browser_unknown(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        module, "get_windows_default_browser_progid", lambda: "UnknownHTML"
    )

    engine, launch_kwargs, label, browser_key = module.resolve_browser_launch_options(
        "default", headed=False
    )

    assert engine == "chromium"
    assert launch_kwargs == {"headless": True}
    assert label == "Playwright Chromium"
    assert browser_key == "chromium"


def test_open_url_in_existing_browser_uses_launch_command(monkeypatch) -> None:
    popen_calls = []

    monkeypatch.setattr(module, "find_running_browser_window", lambda _: 100)
    monkeypatch.setattr(
        module,
        "get_launch_command_for_browser",
        lambda _: ["cmd", "/c", "start", "chrome"],
    )
    monkeypatch.setattr(module.subprocess, "Popen", lambda cmd: popen_calls.append(cmd))

    result = module.open_url_in_existing_browser("chrome", "https://example.com")

    assert result is True
    assert popen_calls == [["cmd", "/c", "start", "chrome", "https://example.com"]]


def test_open_url_in_existing_browser_returns_false_without_window(monkeypatch) -> None:
    monkeypatch.setattr(module, "find_running_browser_window", lambda _: None)

    assert module.open_url_in_existing_browser("chrome", "https://example.com") is False
