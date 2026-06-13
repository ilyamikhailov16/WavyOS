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


def get_command_pool(
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
