import logging
import os
import pathlib
import sys

import keyboard
import send2trash
import win32com.shell.shell as shell

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings


logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TRASH_TOOL_SETTINGS = settings.trash_tool


def clear_folder(folder_path: str | os.PathLike) -> None:
    folder = pathlib.Path(folder_path)
    if not folder.is_dir():
        logger.error("[clear_folder] Not a directory or it does not exist: %s", folder)
        return

    items = list(folder.iterdir())
    if not items:
        logger.info("[clear_folder] Folder is already empty: %s", folder)
        return

    errors: list[tuple[pathlib.Path, Exception]] = []
    for item in items:
        try:
            send2trash.send2trash(str(item))
            logger.info("Trashed: %s", item.name)
        except Exception as exc:
            errors.append((item, exc))

    if errors:
        for item, exc in errors:
            logger.error("[clear_folder] Could not trash '%s': %s", item.name, exc)
        return

    logger.info("[clear_folder] Done. %s item(s) moved to Recycle Bin.", len(items))


def clear_downloads() -> None:
    downloads = pathlib.Path.home() / TRASH_TOOL_SETTINGS.paths.downloads_dir_name
    logger.info("[clear_downloads] Clearing: %s", downloads)
    clear_folder(downloads)


def empty_recycle_bin() -> None:
    flags = (
        TRASH_TOOL_SETTINGS.shell.no_confirmation
        | TRASH_TOOL_SETTINGS.shell.no_progress_ui
        | TRASH_TOOL_SETTINGS.shell.no_sound
    )

    try:
        shell.SHEmptyRecycleBin(None, None, flags)
        logger.info("[empty_recycle_bin] Recycle Bin emptied successfully.")
    except Exception as exc:
        hr = getattr(exc, "hresult", None)
        if hr in TRASH_TOOL_SETTINGS.shell.already_empty_hresult:
            logger.info("[empty_recycle_bin] Recycle Bin is already empty.")
        else:
            logger.error("[empty_recycle_bin] Failed: %s", exc)


def hotkeys() -> None:
    logger.info("Hotkey mode started.")
    keyboard.add_hotkey(TRASH_TOOL_SETTINGS.hotkeys.clear_downloads, clear_downloads)
    keyboard.add_hotkey(TRASH_TOOL_SETTINGS.hotkeys.empty_recycle_bin, empty_recycle_bin)
    keyboard.wait(TRASH_TOOL_SETTINGS.hotkeys.exit)
    logger.info("Exiting hotkey mode.")


if __name__ == "__main__":
    hotkeys()
