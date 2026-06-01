import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT_DIR = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _load_root_config() -> dict:
    config_path = ROOT_DIR / "config.json"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _load_api_token() -> str:
    for env_name in ("WAVYOS_API_TOKEN", "OPENROUTER_API_KEY"):
        token = os.environ.get(env_name, "").strip()
        if token:
            return token

    token_path = ROOT_DIR / "token.txt"
    if token_path.exists():
        try:
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except OSError:
            pass

    return _load_root_config().get("api", {}).get("token", "")


class LLMProcessorSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_retries: int = 3
    retry_sleep: int = 1


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

    opera: list[str] = [
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
    yandex: list[str] = [
        "~/AppData/Local/Yandex/YandexBrowser/Application/browser.exe",
        "C:/Program Files/Yandex/YandexBrowser/Application/browser.exe",
        "C:/Program Files (x86)/Yandex/YandexBrowser/Application/browser.exe",
    ]

    def for_browser(self, browser_name: str) -> list[Path]:
        raw_paths = getattr(self, browser_name, [])
        return [Path(path).expanduser() for path in raw_paths]


class ProcessNamesSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    chromium: set[str] = {
        "chrome.exe",
        "msedge.exe",
        "opera.exe",
        "browser.exe",
    }
    chrome: set[str] = {"chrome.exe"}
    edge: set[str] = {"msedge.exe"}
    firefox: set[str] = {"firefox.exe"}
    opera: set[str] = {"opera.exe", "launcher.exe"}
    yandex: set[str] = {"browser.exe"}

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
    progid_to_browser: dict[str, str] = {
        "MSEdgeHTM": "edge",
        "ChromeHTML": "chrome",
        "FirefoxURL": "firefox",
        "FirefoxHTML": "firefox",
    }


class BrowserRuntimeSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    display_names: dict[str, str] = {
        "chromium": "Playwright Chromium",
        "firefox": "Playwright Firefox",
        "webkit": "Playwright WebKit",
        "chrome": "Google Chrome",
        "edge": "Microsoft Edge",
        "opera": "Opera",
        "yandex": "Yandex Browser",
    }
    launch_commands: dict[str, list[str]] = {
        "chrome": ["cmd", "/c", "start", "chrome"],
        "edge": ["cmd", "/c", "start", "msedge"],
        "firefox": ["cmd", "/c", "start", "firefox"],
    }
    playwright_channels: dict[str, str] = {
        "chrome": "chrome",
        "edge": "msedge",
    }

    def display_name_for(self, browser_name: str) -> str:
        return self.display_names.get(browser_name, browser_name)

    def launch_command_for(self, browser_name: str) -> list[str] | None:
        command = self.launch_commands.get(browser_name)
        return list(command) if command else None

    def playwright_channel_for(self, browser_name: str) -> str | None:
        return self.playwright_channels.get(browser_name)

class CustomBrowserSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str = ""
    engine: Literal["chromium", "firefox"] = "chromium"
    search_preset: str = ""  # "" = inherit from website name

class BrowserSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeouts: TimeoutsSettings = TimeoutsSettings()
    presets: BrowserPresetCatalogSettings = BrowserPresetCatalogSettings()
    paths: BrowserPathsSettings = BrowserPathsSettings()
    process_names: ProcessNamesSettings = ProcessNamesSettings()
    registry: BrowserRegistrySettings = BrowserRegistrySettings()
    runtime: BrowserRuntimeSettings = BrowserRuntimeSettings()
    custom: CustomBrowserSettings = CustomBrowserSettings()


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
    fps: float = _load_root_config().get("screen_tool", {}).get("fps_recording_edit")


class ScriptRunnerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_script_path: Path = Path(
        _load_root_config().get("script_runner", {}).get("base_dir")
        or (ROOT_DIR / "scripts")
    )
    timeout: float = (
        _load_root_config().get("script_runner", {}).get("timeout")
        or 300
    )
    is_async: bool = (
        _load_root_config().get("script_runner", {}).get("is_async", True)
    )
    strict: bool = (
        _load_root_config().get("script_runner", {}).get("strict", False)
    )


class EnergySaverPowerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled_threshold: int = 100
    disabled_threshold: int = 0
    enabled_lower_refresh_rate_hz: int = (
        _load_root_config().get("energy_saver", {}).get("enabled_lower_refresh_rate_hz_edit", 60)
    )

    @property
    def enabled_refresh_rate_hz(self) -> int:
        return self.enabled_lower_refresh_rate_hz


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


class DesktopManagerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_key: str = (
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    )
    registry_value: str = "Desktop"
    fallback_folder: str = "Desktop"
    file_encoding: str = "utf-8"


class AppManagerSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    registry_uninstall_paths: list[tuple[str, str]] = [
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
        (r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
        (r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU"),
    ]
    skip_exe_names: tuple[str, ...] = (
        "uninst",
        "setup",
        "install",
        "update",
        "crash",
        "squirrel",
    )
    winget_timeout_s: int = (
        _load_root_config().get("app_manager", {}).get("winget_timeout_s", 120)
    )
    uninstall_timeout_s: int = (
        _load_root_config().get("app_manager", {}).get("uninstall_timeout_s", 120)
    )
    launch_wait_s: float = (
        _load_root_config().get("app_manager", {}).get("launch_wait_s", 1.0)
    )
    subprocess_encoding: str = (
        _load_root_config().get("app_manager", {}).get("subprocess_encoding", "utf-8")
    )

    # Custom launch: alias → (path_to_exe_with_%ENV%, arguments).
    # Used for applications that cannot be launched directly.
    special_launch: dict[str, tuple[str, list[str]]] = {
        "roblox": (r"%LOCALAPPDATA%\Roblox\Versions\RobloxPlayerLauncher.exe", []),
        "роблокс": (r"%LOCALAPPDATA%\Roblox\Versions\RobloxPlayerLauncher.exe", []),
        "roblox studio": (
            r"%LOCALAPPDATA%\Roblox\Versions\RobloxStudioLauncher.exe",
            [],
        ),
    }

    # Known paths for applications that do not register in standard registry hives.
    # Key — app_name.lower(), value — list of paths (first existing one is used).
    known_paths: dict[str, list[str]] = {
        "steam": [
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
        ],
        "стим": [
            r"C:\Program Files (x86)\Steam\steam.exe",
            r"C:\Program Files\Steam\steam.exe",
        ],
        "riot client": [
            r"C:\Riot Games\Riot Client\RiotClientServices.exe",
        ],
    }

class LoggingSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: str = "INFO"
    format: str = "%(levelname)s - %(message)s"


@lru_cache(maxsize=1)
def _load_root_config() -> dict:
    config_path = ROOT_DIR / "config.json"
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


class AvatarSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool = _load_root_config().get("avatar", {}).get("enabled", True)
    window_title: str = _load_root_config().get("avatar", {}).get(
        "window_title", "WavyOS Avatar"
    )
    window_width: int = _load_root_config().get("avatar", {}).get("window_width", 360)
    window_height: int = _load_root_config().get("avatar", {}).get(
        "window_height", 460
    )
    topmost: bool = _load_root_config().get("avatar", {}).get("topmost", True)
    tick_interval_seconds: float = _load_root_config().get("avatar", {}).get(
        "tick_interval_seconds", 0.15
    )
    transient_state_seconds: float = _load_root_config().get("avatar", {}).get(
        "transient_state_seconds", 1.5
    )
    error_state_seconds: float = _load_root_config().get("avatar", {}).get(
        "error_state_seconds", 3.0
    )
    idle_status_text: str = "Жду команд"
    listening_status_text: str = "Слушаю"
    thinking_status_text: str = "Думаю"
    executing_status_text: str = "Выполняю"
    speaking_status_text: str = "Отвечаю"
    success_status_text: str = "Команда выполнена"
    unknown_status_text: str = "Не удалось распознать команду"
    error_status_text: str = "Произошла ошибка"
    image_path: Path = ROOT_DIR / _load_root_config().get("avatar", {}).get(
        "image_path", "src/images/mascot.png"
    )
    assets_dir: Path = ROOT_DIR / _load_root_config().get(
        "avatar", {}
    ).get("assets_dir", "avatar/assets")
    manifest_path: Path = ROOT_DIR / _load_root_config().get("avatar", {}).get(
        "manifest_path", "avatar/assets/avatar_manifest.json"
    )
    animation_enabled: bool = _load_root_config().get("avatar", {}).get(
        "animation_enabled", True
    )


class LLMSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_for_stt: bool = _load_root_config().get("use_llm_for_stt", False)
    base_url: str = (
        _load_root_config()
        .get("api", {})
        .get("base_url", "https://openrouter.ai/api/v1")
    )
    token: str = Field(default_factory=_load_api_token)
    model: str = _load_root_config().get("api", {}).get("model", "openrouter/free")


class STTSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str = _load_root_config().get("stt", {}).get("model", "medium")
    language: str = _load_root_config().get("stt", {}).get("language", "ru")
    compute_type: str = (
        _load_root_config().get("stt", {}).get("compute_type", "float32")
    )
    device: str = _load_root_config().get("stt", {}).get("device", "cuda")
    silero_sensitivity: float = _load_root_config().get("stt", {}).get("silero_sensitivity", 0.6)
    webrtc_sensitivity: int = _load_root_config().get("stt", {}).get("webrtc_sensitivity", 3)
    silero_use_onnx: bool = True
    silero_deactivity_detection: bool = _load_root_config().get("stt", {}).get("silero_deactivity_detection", False)
    post_speech_silence_duration: float = _load_root_config().get("stt", {}).get("post_speech_silence_duration", 2.0)
    min_gap_between_recordings: float = _load_root_config().get("stt", {}).get("min_gap_between_recordings", 1.0)
    min_length_of_recording: float = _load_root_config().get("stt", {}).get("min_length_of_recording", 1.0)
    pre_recording_buffer_duration: float = _load_root_config().get("stt", {}).get("pre_recording_buffer_duration", 0.2)
    no_log_file: bool = True
    spinner: bool = False


class TTSSettings(BaseModel):
    supported_engines: tuple[str, ...] = ("edge", "gtts", "piper")
    piper_voice_path: str = str(ROOT_DIR / "tts/models/piper/ru_RU-irina-medium.onnx")
    gtts_speed: float = 1.2
    language: str = "ru"


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_processor: LLMProcessorSettings = LLMProcessorSettings()
    browser: BrowserSettings = BrowserSettings()
    screen_tool: ScreenToolSettings = ScreenToolSettings()
    script_runner: ScriptRunnerSettings = ScriptRunnerSettings()
    energy_saver: EnergySaverSettings = EnergySaverSettings()
    system_toggle: SystemToggleSettings = SystemToggleSettings()
    trash_tool: TrashToolSettings = TrashToolSettings()
    desktop_manager: DesktopManagerSettings = DesktopManagerSettings()
    app_manager: AppManagerSettings = AppManagerSettings()
    logging: LoggingSettings = LoggingSettings()
    avatar: AvatarSettings = AvatarSettings()
    llm: LLMSettings = LLMSettings()
    stt: STTSettings = STTSettings()
    tts: TTSSettings = TTSSettings()


settings = Settings()
