from .commands_keys import *
from .commands_schema import *
from .commands_registry import (
    _COMMAND_TO_WRAPPER,
    _COMMAND_TO_KWARGS_MODEL,
    COMMAND_INFO,
)
from .commands_detector import _best_command_match, _extract_args_after_command

import logging
logger = logging.Logger("commands_builder")


def build_command(command_name: str, kwargs: Any | None = None) -> Command:
    """
    Build the final `Command` object from:
    - `command_name`
    - optional `kwargs`
    """

    wrapper_cls = _COMMAND_TO_WRAPPER.get(command_name, CmdUnknown)
    normalized_command_name = (
        command_name if command_name in _COMMAND_TO_WRAPPER else CMD_UNKNOWN
    )
    kwargs_model = get_kwargs_model_cls(normalized_command_name)

    if kwargs is None:
        kwargs_obj = kwargs_model()
    elif isinstance(kwargs, BaseModel):
        # Normalize to the expected kwargs model type.
        kwargs_obj = kwargs_model.model_validate(kwargs.model_dump())
    elif isinstance(kwargs, dict):
        kwargs_obj = kwargs_model.model_validate(kwargs)
    else:
        # Let pydantic raise a clear validation error if type is unsupported.
        kwargs_obj = kwargs_model.model_validate(kwargs)

    wrapper_obj = wrapper_cls(
        command_name=normalized_command_name,  # required by Literal discriminator
        kwargs=kwargs_obj,
    )
    return Command(command=wrapper_obj)


def build_command_from_text(text: str) -> Command | None:
    if not text or not text.strip():
        return None

    cmd_name, consumed_tokens = _best_command_match(text, threshold=80)

    print(f"After RapidFuzz: cmd_name={cmd_name}, consumed_tokens={consumed_tokens}")

    # No command detected: treat as app launch name
    if cmd_name is None:
        clean = text.strip().rstrip(".,!?;:")
        kwargs_model = CommandApp(app_name=clean if clean else "unknown")
        return build_command(CMD_LAUNCH_APP, kwargs_model)

    cmd_info = COMMAND_INFO[cmd_name]

    # Commands without args
    if cmd_info.kwargs_model is CommandEmptyArgs:
        wrapper = cmd_info.wrapper(command_name=cmd_name, kwargs=CommandEmptyArgs())
        return Command(command=wrapper)

    # Commands with args
    arg_text = _extract_args_after_command(text, consumed_tokens)
    kwargs_model = get_kwargs_model_obj(cmd_name, arg_text)

    if kwargs_model is None:
        return build_command(CMD_UNKNOWN)

    return build_command(cmd_name, kwargs_model)


def get_kwargs_model_cls(cmd_name: str) -> StrictBaseModel:
    """Return the kwargs model class for a given command name."""
    return _COMMAND_TO_KWARGS_MODEL.get(cmd_name, CommandEmptyArgs)


def get_kwargs_model_obj(cmd_name: str, arg_text: str) -> StrictBaseModel | None:
    """Return the kwargs model object for a given command name."""
    if cmd_name == CMD_LAUNCH_APP:
        return CommandApp(app_name=arg_text if arg_text else "unknown")
    elif cmd_name == CMD_OPEN_SITE:
        return CommandOpenBrowser(website_name=arg_text if arg_text else "example.com")
    elif cmd_name == CMD_CREATE_FILE:
        return CommandCreateFile(filename=arg_text if arg_text else "untitled.txt")
    elif cmd_name == CMD_CREATE_FOLDER:
        return CommandCreateFolder(name=arg_text if arg_text else "new_folder")
    elif cmd_name in (CMD_DELETE, CMD_RENAME):
        return CommandDelete(name=arg_text if arg_text else "unknown")
    elif cmd_name == CMD_RUN_SCRIPT:
        return CommandRunScript(script_name=arg_text if arg_text else "script.py")
    else:
        return None
