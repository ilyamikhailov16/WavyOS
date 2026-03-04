import os
import pathlib
import logging

import keyboard
import send2trash
import win32com.shell.shell as shell

SHERB_NOCONFIRMATION = 0x00000001  # no confirmation dialog
SHERB_NOPROGRESSUI = 0x00000002  # no progress window
SHERB_NOSOUND = 0x00000004  # no completion sound

ALREADY_EMPTY_HRESULTS = (
    -2147024809,  # 0x80070057 – standard "already empty"
    -2147418113,  # 0x8000FFFF – "Catastrophic failure" = also already empty
)

logging.basicConfig(
    level=logging.DEBUG,  # This enables DEBUG and above
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def clear_folder(folder_path: str | os.PathLike) -> None:
    folder = pathlib.Path(folder_path)

    if not folder.is_dir():
        logger.error(f"[clear_folder] Not a directory or does not exist: {folder}")
        return

    items = list(folder.iterdir())
    if not items:
        logger.info(f"[clear_folder] Folder is already empty: {folder}")
        return

    errors = []
    for item in items:
        try:
            send2trash.send2trash(str(item))
            logger.info(f"Trashed: {item.name}")
        except Exception as exc:
            errors.append((item, exc))

    if errors:
        for item, exc in errors:
            logger.error(f"[clear_folder] Could not trash '{item.name}': {exc}")
    else:
        logger.info(f"[clear_folder] Done – {len(items)} item(s) moved to Recycle Bin.")


def clear_downloads() -> None:
    downloads = pathlib.Path.home() / "Downloads"
    logger.info(f"[clear_downloads] Clearing: {downloads}")
    clear_folder(downloads)


def empty_recycle_bin() -> None:
    flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND

    try:
        # SHEmptyRecycleBin(hwnd, pszRootPath, dwFlags)
        # hwnd = None  ->  no parent window (dialogs appear as top-level windows on taskbar)
        # pszRootPath = None  ->  empties all drives
        shell.SHEmptyRecycleBin(None, None, flags)
        logger.info("[empty_recycle_bin] Recycle Bin emptied successfully.")
    except Exception as exc:
        hr = getattr(exc, "hresult", None)
        if hr in ALREADY_EMPTY_HRESULTS:
            logger.info("[empty_recycle_bin] Recycle Bin is already empty.")
        else:
            logger.error(f"[empty_recycle_bin] Failed: {exc}")


def hotkeys() -> None:
    logger.info("=== РЕЖИМ ГОРЯЧИХ КЛАВИШ ===")
    logger.info("  Ctrl+Shift+D  ->  очистка папки загрузок")
    logger.info("  Ctrl+Shift+R  ->  очистка корзины")
    logger.info("  ESC  ->  выход")
    logger.info("----------------------------")

    keyboard.add_hotkey("ctrl+shift+d", clear_downloads)
    keyboard.add_hotkey("ctrl+shift+r", empty_recycle_bin)

    keyboard.wait("esc")

    logger.info("Выход...")


if __name__ == "__main__":
    hotkeys()
