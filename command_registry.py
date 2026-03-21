from scripts.trash_tool import empty_recycle_bin
from scripts.screen_tool import take_screenshot
from scripts.turn_off import shutdown
from scripts.system_toggle_tool import (
    toggle_wifi,
    toggle_notifications,
    toggle_airplane_mode,
    toggle_bluetooth,
    toggle_mute
)
from scripts.energy_saver_mode import (
    enable_energy_saver_mode,
    disable_energy_saver_mode
)

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
}
