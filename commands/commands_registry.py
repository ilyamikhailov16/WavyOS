from .commands_keys import *
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

app_manager = AppManager()
desktop_manager = DesktopManager()

COMMAND_POOL = {
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
