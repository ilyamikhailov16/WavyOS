from scripts.trash_tool import empty_recycle_bin
from scripts.screen_tool import take_screenshot, start_recording, stop_recording
from scripts.turn_off import shutdown
from scripts.system_toggle_tool import (
    toggle_wifi,
    toggle_notifications,
    toggle_airplane_mode,
    toggle_bluetooth,
    toggle_mute,
)
from scripts.energy_saver_mode import (
    enable_energy_saver_mode,
    disable_energy_saver_mode,
)
from scripts.app_manager import AppManager
from scripts.desktop_manager import DesktopManager
from scripts.script_runner import run_script
from scripts.browser_automation import open_in_browser
from .commands_keys import *
from .commands_schema import *
import string


def build_command_pool(
    app_manager: AppManager, desktop_manager: DesktopManager
) -> dict:
    return {
        CMD_EMPTY_RECYCLE_BIN: empty_recycle_bin,
        CMD_SCREENSHOT: take_screenshot,
        CMD_SHUTDOWN: shutdown,
        CMD_WIFI: toggle_wifi,
        CMD_NOTIFICATIONS: toggle_notifications,
        CMD_AIRPLANE: toggle_airplane_mode,
        CMD_BLUETOOTH: toggle_bluetooth,
        CMD_SOUND: toggle_mute,
        CMD_ENERGY_SAVER_ON: enable_energy_saver_mode,
        CMD_ENERGY_SAVER_OFF: disable_energy_saver_mode,
        CMD_RECORD_ON: start_recording,
        CMD_RECORD_OFF: stop_recording,
        CMD_LAUNCH_APP: app_manager.launch_app,
        CMD_CLOSE_APP: app_manager.close_app,
        CMD_UNINSTALL_APP: app_manager.uninstall_app,
        CMD_CREATE_FILE: desktop_manager.create_file,
        CMD_CREATE_FOLDER: desktop_manager.create_folder,
        CMD_DELETE: desktop_manager.delete,
        CMD_RENAME: desktop_manager.rename,
        CMD_RUN_SCRIPT: run_script,
        CMD_OPEN_SITE: open_in_browser,
    }


COMMAND_INFO = {
    CMD_EMPTY_RECYCLE_BIN: CommandInfo(
        wrapper=CmdEmptyRecycleBin, kwargs_model=CommandEmptyArgs
    ),
    CMD_SCREENSHOT: CommandInfo(wrapper=CmdScreenshot, kwargs_model=CommandEmptyArgs),
    CMD_SHUTDOWN: CommandInfo(wrapper=CmdShutdown, kwargs_model=CommandEmptyArgs),
    CMD_WIFI: CommandInfo(wrapper=CmdToggleWifi, kwargs_model=CommandEmptyArgs),
    CMD_NOTIFICATIONS: CommandInfo(
        wrapper=CmdToggleNotifications, kwargs_model=CommandEmptyArgs
    ),
    CMD_AIRPLANE: CommandInfo(
        wrapper=CmdToggleAirplaneMode, kwargs_model=CommandEmptyArgs
    ),
    CMD_BLUETOOTH: CommandInfo(
        wrapper=CmdToggleBluetooth, kwargs_model=CommandEmptyArgs
    ),
    CMD_SOUND: CommandInfo(wrapper=CmdToggleMute, kwargs_model=CommandEmptyArgs),
    CMD_ENERGY_SAVER_ON: CommandInfo(
        wrapper=CmdEnableEnergySaverMode, kwargs_model=CommandEmptyArgs
    ),
    CMD_ENERGY_SAVER_OFF: CommandInfo(
        wrapper=CmdDisableEnergySaverMode, kwargs_model=CommandEmptyArgs
    ),
    CMD_RECORD_ON: CommandInfo(
        wrapper=CmdStartRecording, kwargs_model=CommandEmptyArgs
    ),
    CMD_RECORD_OFF: CommandInfo(
        wrapper=CmdStopRecording, kwargs_model=CommandEmptyArgs
    ),
    CMD_LAUNCH_APP: CommandInfo(wrapper=CmdLaunchApp, kwargs_model=CommandApp),
    CMD_CLOSE_APP: CommandInfo(wrapper=CmdCloseApp, kwargs_model=CommandApp),
    CMD_UNINSTALL_APP: CommandInfo(wrapper=CmdUninstallApp, kwargs_model=CommandApp),
    CMD_CREATE_FILE: CommandInfo(wrapper=CmdCreateFile, kwargs_model=CommandCreateFile),
    CMD_CREATE_FOLDER: CommandInfo(
        wrapper=CmdCreateFolder, kwargs_model=CommandCreateFolder
    ),
    CMD_DELETE: CommandInfo(wrapper=CmdDelete, kwargs_model=CommandDelete),
    CMD_RENAME: CommandInfo(wrapper=CmdRename, kwargs_model=CommandRename),
    CMD_RUN_SCRIPT: CommandInfo(wrapper=CmdRunScript, kwargs_model=CommandRunScript),
    CMD_OPEN_SITE: CommandInfo(wrapper=CmdOpenBrowser, kwargs_model=CommandOpenBrowser),
    CMD_UNKNOWN: CommandInfo(wrapper=CmdUnknown, kwargs_model=CommandEmptyArgs),
}


_COMMAND_TO_WRAPPER: dict[str, type[StrictBaseModel]] = {
    cmd: info.wrapper for cmd, info in COMMAND_INFO.items()
}


_COMMAND_TO_KWARGS_MODEL: dict[str, type[StrictBaseModel]] = {
    cmd: info.kwargs_model for cmd, info in COMMAND_INFO.items()
}


def build_command(command_name: str, kwargs: Any | None = None) -> Command:
    """
    Build the final `Command` object from:
    - `command_name`
    - optional `kwargs`
    """

    wrapper_cls = _COMMAND_TO_WRAPPER.get(command_name, CmdUnknown)
    normalized_command_name = (
        command_name if command_name in _COMMAND_TO_WRAPPER else CMD_UNKNOWN
    )
    kwargs_model = get_kwargs_model_cls(normalized_command_name)

    if kwargs is None:
        kwargs_obj = kwargs_model()
    elif isinstance(kwargs, BaseModel):
        # Normalize to the expected kwargs model type.
        kwargs_obj = kwargs_model.model_validate(kwargs.model_dump())
    elif isinstance(kwargs, dict):
        kwargs_obj = kwargs_model.model_validate(kwargs)
    else:
        # Let pydantic raise a clear validation error if type is unsupported.
        kwargs_obj = kwargs_model.model_validate(kwargs)

    wrapper_obj = wrapper_cls(
        command_name=normalized_command_name,  # required by Literal discriminator
        kwargs=kwargs_obj,
    )
    return Command(command=wrapper_obj)


def build_command_from_text(text: str) -> Command | None:
    clean = text.strip().rstrip(string.punctuation + ".,!?;:").lower()
    if not clean:
        return None

    for cmd_name, cmd_info in COMMAND_INFO.items():
        cmd_name = cmd_name.lower()
        if cmd_name not in clean:
            continue

        # 1. Проверяем команды БЕЗ аргументов (точное совпадение или вхождение)
        if cmd_info.kwargs_model is CommandEmptyArgs:
            wrapper = cmd_info.wrapper(command_name=cmd_name, kwargs=CommandEmptyArgs())
            return Command(command=wrapper)

        # 2. Проверяем команды С аргументами
        # Извлекаем аргумент: всё, что после ключевого слова
        arg_text = clean.replace(cmd_name, "").strip()
        kwargs_model = get_kwargs_model_obj(cmd_name, arg_text)
        if kwargs_model is None:
            return build_command(CMD_UNKNOWN)

        return build_command(cmd_name, kwargs_model)

    kwargs_model = CommandApp(app_name=clean)
    return build_command(CMD_LAUNCH_APP, kwargs_model)


def get_kwargs_model_cls(cmd_name: str) -> StrictBaseModel:
    """Return the kwargs model class for a given command name."""
    return _COMMAND_TO_KWARGS_MODEL.get(cmd_name, CommandEmptyArgs)


def get_kwargs_model_obj(cmd_name: str, arg_text: str) -> StrictBaseModel | None:
    """Return the kwargs model object for a given command name."""
    if cmd_name == CMD_LAUNCH_APP:
        return CommandApp(app_name=arg_text if arg_text else "unknown")
    elif cmd_name == CMD_OPEN_SITE:
        return CommandOpenBrowser(website_name=arg_text if arg_text else "example.com")
    elif cmd_name == CMD_CREATE_FILE:
        return CommandCreateFile(filename=arg_text if arg_text else "untitled.txt")
    elif cmd_name == CMD_CREATE_FOLDER:
        return CommandCreateFolder(name=arg_text if arg_text else "new_folder")
    elif cmd_name in (CMD_DELETE, CMD_RENAME):
        return CommandDelete(name=arg_text if arg_text else "unknown")
    elif cmd_name == CMD_RUN_SCRIPT:
        return CommandRunScript(script_name=arg_text if arg_text else "script.py")
    else:
        return None
