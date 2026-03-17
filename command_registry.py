from scripts.trash_tool import empty_recycle_bin
from scripts.screen_tool import take_screenshot

COMMAND_POOL = {
    "Очистить корзину": empty_recycle_bin,
    "Скриншот": take_screenshot
}
