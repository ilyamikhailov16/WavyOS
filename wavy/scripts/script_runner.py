import os
import re
import inspect
from pathlib import Path
import subprocess
import sys
import threading as th
from dataclasses import dataclass, field

from app_logging import get_logger
from config import settings

SCRIPT_RUNNER_SETTINGS = settings.script_runner
logger = get_logger(__name__)


@dataclass
class ScriptDescriptor:
    script_name: str
    script_type: str
    script_path: Path
    timeout: float
    is_async: bool
    strict: bool
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)


def _validate_input(descriptor: ScriptDescriptor) -> bool:
    if not descriptor.script_path.is_file():
        logger.error(f"[run_script] Script not found: {descriptor.script_path}")
        return False

    if descriptor.script_type not in (".py", ".bat"):
        logger.error(
            f"[run_script] Only .py and .bat scripts are supported. Got: '{descriptor.script_path.name}'"
        )
        return False

    for a in descriptor.args:
        a_str = str(a)
        if re.search(r"[^ _a-zA-Z0-9.-]", a_str):
            if descriptor.strict:
                logger.error(
                    f"Argument '{a_str}' contains invalid characters."
                    f"Only alphanumeric characters, periods, hyphens, underscores, and spaces are allowed."
                )
                return False

    return True


def _build_command(descriptor: ScriptDescriptor) -> list[str]:
    cmd = []
    if descriptor.script_type == ".py":
        # Build the command: python <script> [args] [--key=value ...]
        cmd = [sys.executable, str(descriptor.script_path)]
        cmd += [str(a) for a in descriptor.args]
        cmd += [f"--{k}={v}" for k, v in descriptor.kwargs.items()]
    elif descriptor.script_type == ".bat":
        # Build the command: "<script_path>" [args]
        cmd = [str(descriptor.script_path)]
        cmd += [str(a) for a in descriptor.args]
    return cmd


def _execute_command(cmd: list[str], descriptor: ScriptDescriptor) -> None:
    def _run_worker():
        try:
            run_kwargs = {"check": True}
            run_parameters = inspect.signature(subprocess.run).parameters
            if "timeout" in run_parameters:
                run_kwargs["timeout"] = descriptor.timeout
            result = subprocess.run(cmd, **run_kwargs)
            logger.info(f"[run_script] Script exited with code {result.returncode}.")
        except subprocess.CalledProcessError as exc:
            logger.error(f"[run_script] Script failed with code {exc.returncode}.")
        except subprocess.TimeoutExpired:
            logger.error(f"[run_script] The process took too long and was terminated.")
        except Exception as exc:
            logger.error(f"[run_script] Unexpected error: {exc}")

    if descriptor.is_async:
        thread = th.Thread(target=_run_worker, daemon=True)
        thread.start()
    else:
        _run_worker()


def run_script(
    script_name: str,
    *args,
    script_path: str | os.PathLike = SCRIPT_RUNNER_SETTINGS.default_script_path,
    timeout: float = SCRIPT_RUNNER_SETTINGS.timeout,
    is_async: bool = SCRIPT_RUNNER_SETTINGS.is_async,
    strict: bool = SCRIPT_RUNNER_SETTINGS.strict,
    **kwargs,
) -> None:
    """
    Locate and execute a .py or .bat script.

    Parameters
    ----------
    script_name : str
        File name including the file extension, e.g. "my_script.py".
    script_path : str | PathLike
        Directory that contains the script. Defaults to script_runner's directory.
    timeout : float
        The time after which the script process terminates.
    is_async : bool
        Allows you to choose between lock and non-locking modes.
    strict : bool
        If strict=True, then raises exception,
        when arguments for .bat contain shell metacharacters.
        Otherwise such arguments are ignored.
    *args
        Positional arguments forwarded to the script via command line.
        Arguments for .bat must not contain shell metacharacters,
        guard behavior depends on the "strict" parameter.
    **kwargs
        Keyword arguments forwarded as --key=value flags.
        Ignored for .bat scripts
    """
    if args and isinstance(args[0], (str, os.PathLike)):
        candidate_script_path = Path(args[0])
        if (candidate_script_path / script_name).is_file():
            script_path = candidate_script_path
            args = args[1:]

    full_path = Path(script_path) / script_name
    descriptor = ScriptDescriptor(
        script_name,
        full_path.suffix,
        full_path,
        timeout,
        is_async,
        strict,
        args=args,
        kwargs=kwargs,
    )

    if not _validate_input(descriptor):
        return

    cmd = _build_command(descriptor)

    logger.info(f"[run_script] Running: {' '.join(cmd)}")

    _execute_command(cmd, descriptor)
