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
    "Очистить корзину": empty_recycle_bin,
    "Скриншот": take_screenshot,
    "Выключить компьютер": shutdown,
    "Переключить интернет": toggle_wifi,
    "Переключить уведомления": toggle_notifications,
    "Переключить режим полёта": toggle_airplane_mode,
    "Переключить блютуз": toggle_bluetooth,
    "Переключить звук": toggle_mute,
    "Включить режим энергосбережения": enable_energy_saver_mode,
    "Выключить режим энергосбережения": disable_energy_saver_mode,
    "Включить запись экрана": start_recording,
    "Выключить запись экрана": stop_recording,
    "Открыть приложение": app_manager.launch_app,
    "Закрыть приложение": app_manager.close_app,
    "Удалить приложение": app_manager.uninstall_app,
    "Создать файл": desktop_manager.create_file,
    "Создать папку": desktop_manager.create_folder,
    "Удалить": desktop_manager.delete,
    "Переименовать": desktop_manager.rename,
    "Запустить скрипт": run_script,
    "Открыть сайт": open_in_browser,
}
