from config import settings


def test_browser_process_names_contract() -> None:
    process_names = settings.browser.process_names

    assert "chrome.exe" in process_names.chromium
    assert "msedge.exe" in process_names.edge
    assert "browser.exe" in process_names.yandex


def test_browser_preset_search_urls_support_query_placeholder() -> None:
    presets = settings.browser.presets

    assert "{query}" in presets.google.search_url
    assert "{query}" in presets.bing.search_url
    assert "{query}" in presets.duckduckgo.search_url
    assert "{query}" in presets.yandex.search_url
