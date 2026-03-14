"""Windows energy saver and display refresh-rate helpers."""

import ctypes
import logging
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

import keyboard

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings


logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ENERGY_SAVER_SETTINGS = settings.energy_saver
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


def open_system_settings() -> None:
    try:
        subprocess.run(["start", ENERGY_SAVER_SETTINGS.settings_uri], shell=True, check=True)
        logger.info("Windows Settings opened.")
    except Exception as exc:
        logger.error("Could not open Windows Settings: %s", exc)


def get_current_resolution_and_bpp() -> tuple[int | None, int | None, int | None, int | None]:
    devmode = DEVMODE()
    devmode.dmSize = ctypes.sizeof(DEVMODE)
    if user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode)):
        return (
            devmode.dmPelsWidth,
            devmode.dmPelsHeight,
            devmode.dmBitsPerPel,
            devmode.dmDisplayFrequency,
        )
    logger.warning("Could not read current display settings.")
    return None, None, None, None


def set_refresh_rate(target_hz: int) -> bool:
    width, height, bpp, current_hz = get_current_resolution_and_bpp()
    if width is None:
        return False

    if current_hz == target_hz:
        logger.info("Refresh rate is already set to %s Hz.", target_hz)
        return True

    supported = False
    index = 0
    temp_mode = DEVMODE()
    temp_mode.dmSize = ctypes.sizeof(DEVMODE)
    while user32.EnumDisplaySettingsW(None, index, ctypes.byref(temp_mode)):
        if (
            temp_mode.dmPelsWidth == width
            and temp_mode.dmPelsHeight == height
            and temp_mode.dmBitsPerPel == bpp
            and temp_mode.dmDisplayFrequency == target_hz
        ):
            supported = True
            break
        index += 1

    if not supported:
        logger.warning("%s Hz is not supported for the current display mode.", target_hz)
        return False

    devmode = DEVMODE()
    devmode.dmSize = ctypes.sizeof(DEVMODE)
    user32.EnumDisplaySettingsW(None, -1, ctypes.byref(devmode))
    devmode.dmDisplayFrequency = target_hz
    devmode.dmFields |= DM_DISPLAYFREQUENCY

    result = user32.ChangeDisplaySettingsW(ctypes.byref(devmode), CDS_UPDATEREGISTRY)
    if result == DISP_CHANGE_SUCCESSFUL:
        logger.info("Refresh rate changed to %s Hz.", target_hz)
        return True

    logger.error("Could not change refresh rate to %s Hz. Code: %s", target_hz, result)
    return False


def get_max_supported_refresh_rate() -> int:
    width, height, bpp, _ = get_current_resolution_and_bpp()
    if width is None:
        return 60

    max_hz = 0
    index = 0
    temp_mode = DEVMODE()
    temp_mode.dmSize = ctypes.sizeof(DEVMODE)
    while user32.EnumDisplaySettingsW(None, index, ctypes.byref(temp_mode)):
        if (
            temp_mode.dmPelsWidth == width
            and temp_mode.dmPelsHeight == height
            and temp_mode.dmBitsPerPel == bpp
        ):
            max_hz = max(max_hz, temp_mode.dmDisplayFrequency)
        index += 1

    if max_hz == 0:
        logger.warning("Could not determine the maximum supported refresh rate. Falling back to 60 Hz.")
        return 60
    logger.info("Maximum supported refresh rate: %s Hz.", max_hz)
    return max_hz


def enable_energy_saver_mode() -> bool:
    threshold = ENERGY_SAVER_SETTINGS.power.enabled_threshold
    try:
        subprocess.run(
            [
                "powercfg",
                "/setdcvalueindex",
                "SCHEME_CURRENT",
                "SUB_ENERGYSAVER",
                "ESBATTTHRESHOLD",
                str(threshold),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="cp866",
        )
        subprocess.run(
            ["powercfg", "/setactive", "SCHEME_CURRENT"],
            check=True,
            capture_output=True,
            text=True,
            encoding="cp866",
        )
        logger.info("Energy saver mode enabled.")
        set_refresh_rate(ENERGY_SAVER_SETTINGS.power.enabled_refresh_rate_hz)
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("Energy saver mode could not be enabled: %s", exc.stderr.strip() or "no output")
        return False
    except Exception as exc:
        logger.error("Unexpected error while enabling energy saver mode: %s", exc)
        return False


def disable_energy_saver_mode() -> bool:
    threshold = ENERGY_SAVER_SETTINGS.power.disabled_threshold
    try:
        subprocess.run(
            [
                "powercfg",
                "/setdcvalueindex",
                "SCHEME_CURRENT",
                "SUB_ENERGYSAVER",
                "ESBATTTHRESHOLD",
                str(threshold),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="cp866",
        )
        subprocess.run(
            ["powercfg", "/setactive", "SCHEME_CURRENT"],
            check=True,
            capture_output=True,
            text=True,
            encoding="cp866",
        )
        logger.info("Energy saver mode disabled.")
        set_refresh_rate(get_max_supported_refresh_rate())
        return True
    except subprocess.CalledProcessError as exc:
        logger.error("Energy saver mode could not be disabled: %s", exc.stderr.strip() or "no output")
        return False
    except Exception as exc:
        logger.error("Unexpected error while disabling energy saver mode: %s", exc)
        return False


def hotkeys() -> None:
    logger.info("Hotkey mode started.")
    keyboard.add_hotkey(ENERGY_SAVER_SETTINGS.hotkeys.open_settings, open_system_settings)
    keyboard.add_hotkey(ENERGY_SAVER_SETTINGS.hotkeys.enable, enable_energy_saver_mode)
    keyboard.add_hotkey(ENERGY_SAVER_SETTINGS.hotkeys.disable, disable_energy_saver_mode)
    keyboard.wait(ENERGY_SAVER_SETTINGS.hotkeys.exit)
    logger.info("Exiting hotkey mode.")


if __name__ == "__main__":
    hotkeys()
