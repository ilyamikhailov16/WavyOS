from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class TimeoutsSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_timeout_ms: int = 15000
    default_wait_after_ms: int = 3000


class SearchPresetSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str
    input_selector: str
    search_url: str | None = None


class BrowserPathsSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    opera: list[str] = Field(
        default_factory=lambda: [
            "~/AppData/Local/Programs/Opera/opera.exe",
            "~/AppData/Local/Programs/Opera/launcher.exe",
            "~/AppData/Local/Programs/Opera GX/launcher.exe",
            "C:/Program Files/Opera/opera.exe",
            "C:/Program Files/Opera/launcher.exe",
            "C:/Program Files/Opera GX/opera.exe",
            "C:/Program Files/Opera GX/launcher.exe",
            "C:/Program Files (x86)/Opera/opera.exe",
            "C:/Program Files (x86)/Opera/launcher.exe",
            "C:/Program Files (x86)/Opera GX/opera.exe",
            "C:/Program Files (x86)/Opera GX/launcher.exe",
        ]
    )
    yandex: list[str] = Field(
        default_factory=lambda: [
            "~/AppData/Local/Yandex/YandexBrowser/Application/browser.exe",
            "C:/Program Files/Yandex/YandexBrowser/Application/browser.exe",
            "C:/Program Files (x86)/Yandex/YandexBrowser/Application/browser.exe",
        ]
    )

    def for_browser(self, browser_name: str) -> list[Path]:
        raw_paths = getattr(self, browser_name, [])
        return [Path(path).expanduser() for path in raw_paths]


class ProcessNamesSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    chromium: set[str] = Field(
        default_factory=lambda: {"chrome.exe", "msedge.exe", "opera.exe", "browser.exe"}
    )
    chrome: set[str] = Field(default_factory=lambda: {"chrome.exe"})
    edge: set[str] = Field(default_factory=lambda: {"msedge.exe"})
    firefox: set[str] = Field(default_factory=lambda: {"firefox.exe"})
    opera: set[str] = Field(default_factory=lambda: {"opera.exe", "launcher.exe"})
    yandex: set[str] = Field(default_factory=lambda: {"browser.exe"})

    def for_browser(self, browser_name: str) -> set[str]:
        return set(getattr(self, browser_name, set()))


class BrowserPresetCatalogSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    google: SearchPresetSettings = SearchPresetSettings(
        url="https://www.google.com/",
        input_selector='textarea[name="q"]',
        search_url="https://www.google.com/search?q={query}",
    )
    bing: SearchPresetSettings = SearchPresetSettings(
        url="https://www.bing.com/",
        input_selector='textarea[name="q"], input[name="q"]',
        search_url="https://www.bing.com/search?q={query}",
    )
    duckduckgo: SearchPresetSettings = SearchPresetSettings(
        url="https://duckduckgo.com/",
        input_selector='textarea[name="q"], input[name="q"]',
        search_url="https://duckduckgo.com/?q={query}",
    )
    yandex: SearchPresetSettings = SearchPresetSettings(
        url="https://ya.ru/",
        input_selector='input[name="text"]',
        search_url="https://ya.ru/search/?text={query}",
    )

    def names(self) -> list[str]:
        return sorted(self.model_dump().keys())

    def get(self, preset_name: str | None) -> SearchPresetSettings | None:
        if not preset_name:
            return None
        return getattr(self, preset_name, None)


class BrowserRegistrySettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_browser_progid_key: str = (
        r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
    )
    progid_to_browser: dict[str, str] = Field(
        default_factory=lambda: {
            "MSEdgeHTM": "edge",
            "ChromeHTML": "chrome",
            "FirefoxURL": "firefox",
            "FirefoxHTML": "firefox",
        }
    )


class BrowserRuntimeSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    browser_choices: tuple[str, ...] = (
        "default",
        "chromium",
        "firefox",
        "webkit",
        "chrome",
        "edge",
        "opera",
        "yandex",
    )
    display_names: dict[str, str] = Field(
        default_factory=lambda: {
            "chromium": "Playwright Chromium",
            "firefox": "Playwright Firefox",
            "webkit": "Playwright WebKit",
            "chrome": "Google Chrome",
            "edge": "Microsoft Edge",
            "opera": "Opera",
            "yandex": "Yandex Browser",
        }
    )
    launch_commands: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "chrome": ["cmd", "/c", "start", "chrome"],
            "edge": ["cmd", "/c", "start", "msedge"],
            "firefox": ["cmd", "/c", "start", "firefox"],
        }
    )
    playwright_channels: dict[str, str] = Field(
        default_factory=lambda: {
            "chrome": "chrome",
            "edge": "msedge",
        }
    )

    def display_name_for(self, browser_name: str) -> str:
        return self.display_names.get(browser_name, browser_name)

    def launch_command_for(self, browser_name: str) -> list[str] | None:
        command = self.launch_commands.get(browser_name)
        return list(command) if command else None

    def playwright_channel_for(self, browser_name: str) -> str | None:
        return self.playwright_channels.get(browser_name)


class BrowserSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeouts: TimeoutsSettings = TimeoutsSettings()
    presets: BrowserPresetCatalogSettings = BrowserPresetCatalogSettings()
    paths: BrowserPathsSettings = BrowserPathsSettings()
    process_names: ProcessNamesSettings = ProcessNamesSettings()
    registry: BrowserRegistrySettings = BrowserRegistrySettings()
    runtime: BrowserRuntimeSettings = BrowserRuntimeSettings()


class ScreenToolPathsSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    records_dir_name: str = "screen_records"
    screenshot_prefix: str = "screenshot"
    record_prefix: str = "record"
    record_extension: str = "avi"


class ScreenToolHotkeysSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    toggle_recording: str = "F9"
    screenshot: str = "F12"
    exit: str = "esc"


class ScreenToolSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    paths: ScreenToolPathsSettings = ScreenToolPathsSettings()
    hotkeys: ScreenToolHotkeysSettings = ScreenToolHotkeysSettings()
    video_codec: str = "XVID"
    fps: float = 20.0


class ScriptRunnerDummySettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    script_name: str = "play_sound.py"
    script_directory: str = "C:/"


class ScriptRunnerHotkeysSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_dummy: str = "ctrl+shift+r"
    exit: str = "esc"


class ScriptRunnerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    dummy: ScriptRunnerDummySettings = ScriptRunnerDummySettings()
    hotkeys: ScriptRunnerHotkeysSettings = ScriptRunnerHotkeysSettings()


class EnergySaverPowerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled_threshold: int = 100
    disabled_threshold: int = 0
    enabled_refresh_rate_hz: int = 60


class EnergySaverHotkeysSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    open_settings: str = "ctrl+alt+o"
    enable: str = "ctrl+alt+e"
    disable: str = "ctrl+alt+shift+e"
    exit: str = "esc"


class EnergySaverSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    power: EnergySaverPowerSettings = EnergySaverPowerSettings()
    hotkeys: EnergySaverHotkeysSettings = EnergySaverHotkeysSettings()
    settings_uri: str = "ms-settings:"


class SystemToggleHotkeysSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    mute: str = "ctrl+alt+m"
    wifi: str = "ctrl+alt+w"
    bluetooth: str = "ctrl+alt+b"
    airplane_mode: str = "ctrl+alt+a"
    notifications: str = "ctrl+alt+n"
    exit: str = "esc"


class SystemToggleUiSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    notifications_uri: str = "ms-settings:notifications"
    open_delay_seconds: float = 1.2
    post_toggle_delay_seconds: float = 0.3
    airplane_mode_timeout_seconds: int = 15


class SystemToggleSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    hotkeys: SystemToggleHotkeysSettings = SystemToggleHotkeysSettings()
    ui: SystemToggleUiSettings = SystemToggleUiSettings()


class TrashToolHotkeysSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    clear_downloads: str = "ctrl+shift+d"
    empty_recycle_bin: str = "ctrl+shift+r"
    exit: str = "esc"


class TrashToolShellSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    no_confirmation: int = 0x00000001
    no_progress_ui: int = 0x00000002
    no_sound: int = 0x00000004
    already_empty_hresult: tuple[int, int] = (-2147024809, -2147418113)


class TrashToolPathsSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    downloads_dir_name: str = "Downloads"


class TrashToolSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    hotkeys: TrashToolHotkeysSettings = TrashToolHotkeysSettings()
    shell: TrashToolShellSettings = TrashToolShellSettings()
    paths: TrashToolPathsSettings = TrashToolPathsSettings()


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    browser: BrowserSettings = BrowserSettings()
    screen_tool: ScreenToolSettings = ScreenToolSettings()
    script_runner: ScriptRunnerSettings = ScriptRunnerSettings()
    energy_saver: EnergySaverSettings = EnergySaverSettings()
    system_toggle: SystemToggleSettings = SystemToggleSettings()
    trash_tool: TrashToolSettings = TrashToolSettings()


settings = Settings()
