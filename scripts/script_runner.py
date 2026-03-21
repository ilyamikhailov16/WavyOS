import os
import pathlib
import subprocess
import sys

from app_logging import get_logger
from config import settings

SCRIPT_RUNNER_SETTINGS = settings.script_runner
logger = get_logger(__name__)


def run_script(
    script_name: str,
    script_path: str | os.PathLike = SCRIPT_RUNNER_SETTINGS.default_script_path,
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
        Directory that contains the script. Defaults to script_runner's directory.
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
