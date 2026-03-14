import os
import pathlib
import textwrap
import subprocess
import sys
import keyboard

from bootstrap import settings
from app_logging import get_logger

logger = get_logger(__name__)


def run_script(
    script_name: str,
    script_path: str | os.PathLike = "C:/",
    *args,
    **kwargs,
) -> None:
    """
    Locate and execute a .py script.

    Parameters
    ----------
    script_name : str
        File name including the .py extension, e.g. "my_script.py".
    script_path : str | PathLike
        Directory that contains the script. Defaults to "C:/".
    *args
        Positional arguments forwarded to the script via command line.
    **kwargs
        Keyword arguments forwarded as --key=value flags.
    """
    if not script_name.endswith(".py"):
        logger.error(
            f"[run_script] Only .py scripts are supported. Got: '{script_name}'"
        )
        return

    full_path = pathlib.Path(script_path) / script_name

    if not full_path.is_file():
        logger.error(f"[run_script] Script not found: {full_path}")
        return

    # Build the command: python <script> [args] [--key=value ...]
    cmd = [sys.executable, str(full_path)]
    cmd += [str(a) for a in args]
    cmd += [f"--{k}={v}" for k, v in kwargs.items()]

    logger.info(f"[run_script] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
        logger.info(f"[run_script] Script exited with code {result.returncode}.")
    except subprocess.CalledProcessError as exc:
        logger.error(f"[run_script] Script failed with code {exc.returncode}.")
    except Exception as exc:
        logger.error(f"[run_script] Unexpected error: {exc}")


if __name__ == "__main__":
    SCRIPT_RUNNER_SETTINGS = settings.script_runner
    DUMMY_SCRIPT_NAME = SCRIPT_RUNNER_SETTINGS.dummy.script_name
    DUMMY_SCRIPT_CONTENT = '''\
    """
    play_sound.py – dummy script that plays a Windows system sound.
    """
    import winsound
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    def play() -> None:
        logger.info("[play_sound] Playing Windows Exclamation sound...")
        # MB_ICONEXCLAMATION plays the system "Exclamation" sound defined in
        # Windows sound settings (usually a cheerful ding).
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        logger.info("[play_sound] Done.")

    if __name__ == "__main__":
        play()
    '''

    def ensure_dummy_script() -> pathlib.Path:
        path = pathlib.Path(SCRIPT_RUNNER_SETTINGS.dummy.script_directory)
        target = path / DUMMY_SCRIPT_NAME
        if not target.exists():
            target.write_text(
                textwrap.dedent(DUMMY_SCRIPT_CONTENT),
                encoding="utf-8",
            )
            logger.info(f"[ensure_dummy_script] Created dummy script: {target}")
        else:
            logger.debug(f"[ensure_dummy_script] Dummy script already exists: {target}")
        return path

    def hotkeys() -> None:
        script_dir = ensure_dummy_script()

        def run_dummy() -> None:
            run_script(DUMMY_SCRIPT_NAME, script_path=script_dir)

        logger.info("=== SCRIPT RUNNER – HOTKEY MODE ===")
        logger.info(f"  {SCRIPT_RUNNER_SETTINGS.hotkeys.run_dummy}  ->  run {DUMMY_SCRIPT_NAME}")
        logger.info("  ESC           ->  quit")
        logger.info("-----------------------------------")

        keyboard.add_hotkey(SCRIPT_RUNNER_SETTINGS.hotkeys.run_dummy, run_dummy)
        keyboard.wait(SCRIPT_RUNNER_SETTINGS.hotkeys.exit)

        logger.info("Выход...")

    hotkeys()
