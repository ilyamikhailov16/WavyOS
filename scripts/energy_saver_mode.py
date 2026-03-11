"""Скрипт для открытия системных настроек и установки энергосберегающего режима (смена герцовки + режим энергосбережения)"""

import subprocess
import ctypes
from ctypes import wintypes
import logging
import keyboard

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Константы для дисплея
user32 = ctypes.windll.user32

class DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", ctypes.c_wchar * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG),
        ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", ctypes.c_wchar * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags_or_Nup", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
    ]

DM_DISPLAYFREQUENCY = 0x00400000
CDS_UPDATEREGISTRY = 0x01
DISP_CHANGE_SUCCESSFUL = 0

def open_system_settings():
    """Просто открывает главное окно Параметры Windows"""
    try:
        subprocess.run(['start', 'ms-settings:'], shell=True, check=True)
        logger.info("[Параметры] Главное окно системных настроек открыто")
    except Exception as e:
        logger.error(f"[Параметры] Ошибка открытия: {e}")

def get_current_resolution_and_bpp():
    """Возвращает текущее разрешение и глубину цвета для сравнения"""
    devmode = DEVMODE()
    devmode.dmSize = ctypes.sizeof(DEVMODE)
    if user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode)):  # -1 = текущие
        return (
            devmode.dmPelsWidth,
            devmode.dmPelsHeight,
            devmode.dmBitsPerPel,
            devmode.dmDisplayFrequency  # текущая герцовка, для справки
        )
    logger.warning("Не удалось получить текущие параметры дисплея")
    return None, None, None, None

def set_refresh_rate(target_hz: int):
    """Устанавливает указанную герцовку, если поддерживается"""
    width, height, bpp, current_hz = get_current_resolution_and_bpp()
    if width is None:
        return False

    if current_hz == target_hz:
        logger.info(f"Уже стоит {target_hz} Гц — пропускаем")
        return True

    # Проверяем поддержку target_hz
    supported = False
    i = 0
    temp_mode = DEVMODE()
    temp_mode.dmSize = ctypes.sizeof(DEVMODE)
    while user32.EnumDisplaySettingsW(None, i, ctypes.byref(temp_mode)):
        if (temp_mode.dmPelsWidth == width and
                temp_mode.dmPelsHeight == height and
                temp_mode.dmBitsPerPel == bpp and
                temp_mode.dmDisplayFrequency == target_hz):
            supported = True
            break
        i += 1

    if not supported:
        logger.warning(f"{target_hz} Гц не поддерживается на текущем разрешении")
        return False

    devmode = DEVMODE()
    devmode.dmSize = ctypes.sizeof(DEVMODE)
    user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode))  # текущие

    devmode.dmDisplayFrequency = target_hz
    devmode.dmFields |= DM_DISPLAYFREQUENCY

    result = user32.ChangeDisplaySettingsW(ctypes.byref(devmode), CDS_UPDATEREGISTRY)
    if result == DISP_CHANGE_SUCCESSFUL:
        logger.info(f"Герцовка установлена на {target_hz} Гц")
        return True
    else:
        logger.error(f"Ошибка изменения герцовки на {target_hz} Гц, код: {result}")
        return False

def get_max_supported_refresh_rate():
    """Находит максимальную поддерживаемую герцовку для текущего разрешения/битности"""
    width, height, bpp, _ = get_current_resolution_and_bpp()
    if width is None:
        return 60  # fallback

    max_hz = 0
    i = 0
    temp_mode = DEVMODE()
    temp_mode.dmSize = ctypes.sizeof(DEVMODE)
    while user32.EnumDisplaySettingsW(None, i, ctypes.byref(temp_mode)):
        if (temp_mode.dmPelsWidth == width and
                temp_mode.dmPelsHeight == height and
                temp_mode.dmBitsPerPel == bpp):
            max_hz = max(max_hz, temp_mode.dmDisplayFrequency)
        i += 1

    if max_hz == 0:
        logger.warning("Не найдено ни одного подходящего режима — fallback на 60")
        return 60
    logger.info(f"Максимальная поддерживаемая герцовка: {max_hz} Гц")
    return max_hz

def enable_energy_saver_mode():
    """Включает 'Всегда использовать энергосбережение' + 60 Гц"""
    threshold = 100
    try:
        subprocess.run(
            ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", str(threshold)],
            check=True, capture_output=True, text=True, encoding='cp866'
        )
        subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], check=True, capture_output=True, text=True, encoding='cp866')
        logger.info("[Энергосбережение] 'Всегда использовать' включено (100%)")

        set_refresh_rate(60)  # всегда на 60 при включении режима

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[Энергосбережение] Ошибка: {e.stderr.strip() or 'нет вывода'}")
        logger.info("Запусти от админа, если нужно")
        return False
    except Exception as e:
        logger.error(f"[Энергосбережение] Общая ошибка: {e}")
        return False

def disable_energy_saver_mode():
    """Выключает 'Всегда использовать' + возвращает максимальную герцовку"""
    threshold = 0
    try:
        subprocess.run(
            ["powercfg", "/setdcvalueindex", "SCHEME_CURRENT", "SUB_ENERGYSAVER", "ESBATTTHRESHOLD", str(threshold)],
            check=True, capture_output=True, text=True, encoding='cp866'
        )
        subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], check=True, capture_output=True, text=True, encoding='cp866')
        logger.info("[Энергосбережение] 'Всегда использовать' выключено (0%)")

        max_hz = get_max_supported_refresh_rate()
        set_refresh_rate(max_hz)

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[Энергосбережение] Ошибка: {e.stderr.strip() or 'нет вывода'}")
        return False
    except Exception as e:
        logger.error(f"[Энергосбережение] Общая ошибка: {e}")
        return False

def hotkeys():
    logger.info("=== РЕЖИМ ГОРЯЧИХ КЛАВИШ ===")
    logger.info("  Ctrl+Alt+O  →  Параметры системы")
    logger.info("  Ctrl+Alt+E  →   вкл Энергосбережение")
    logger.info("  Ctrl+Alt+shift+E  →  выкл Энергосбережение")
    logger.info("  ESC  →  выход")
    logger.info("----------------------------")

    keyboard.add_hotkey("ctrl+alt+o", open_system_settings)
    keyboard.add_hotkey("ctrl+alt+e", enable_energy_saver_mode)
    keyboard.add_hotkey("ctrl+alt+shift+e", disable_energy_saver_mode)


    keyboard.wait("esc")
    logger.info("Выход...")


if __name__ == "__main__":
    hotkeys()