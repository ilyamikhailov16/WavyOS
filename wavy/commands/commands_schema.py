from __future__ import annotations
from typing import Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field
from .commands_keys import *


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandEmptyArgs(StrictBaseModel):
    pass


class CommandApp(StrictBaseModel):
    app_name: str = Field(
        description=(
            "App/alias: lowercase, no spaces; multi-word joined with '_' "
            "(consistent language + separator style)"
        )
    )


class CommandCreateFile(StrictBaseModel):
    filename: str = Field(
        description=(
            "File name: lowercase RU, '_' only, no spaces, with extension "
            "(.py/.json/.txt inferred if missing)"
        )
    )
    folder: str | None = Field(
        default=None,
        description="Desktop subfolder: lowercase RU, '_' only, no spaces",
    )
    content: str = Field(default="", description="Text content of the file")


class CommandCreateFolder(StrictBaseModel):
    name: str = Field(
        description="Folder name: lowercase RU, '_' only, no spaces"
    )


class CommandDelete(StrictBaseModel):
    name: str = Field(
        description=(
            "Target name (file/folder): lowercase RU, '_' only, no spaces; "
            "for files include extension (.py/.json/.txt inferred if needed)"
        )
    )
    folder: str | None = Field(
        default=None,
        description="Subfolder: lowercase RU, '_' only, no spaces",
    )


class CommandRename(StrictBaseModel):
    old_name: str = Field(
        description=(
            "Old name: lowercase RU, '_' only, no spaces; if file, include extension"
        )
    )
    new_name: str = Field(
        description=(
            "New name: lowercase RU, '_' only, no spaces; if file, include extension "
            "(keep old extension unless explicitly changed)"
        )
    )
    folder: str | None = Field(
        default=None,
        description="Subfolder: lowercase RU, '_' only, no spaces",
    )


class CommandRunScript(StrictBaseModel):
    script_name: str = Field(
        description="Script file: lowercase, '_' only, no spaces, '.py' exactly once"
    )


class CommandOpenBrowser(StrictBaseModel):
    website_name: str = Field(
        description=(
            "Domain: English-only, one token, lowercase, with TLD; no protocol/path"
        )
    )
    query: str | None = Field(
        default=None, description="Text to search or enter into the target field"
    )


class _CmdNoArgs(StrictBaseModel):
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class _CmdAppArgs(StrictBaseModel):
    kwargs: CommandApp


class _CmdCreateFileArgs(StrictBaseModel):
    kwargs: CommandCreateFile


class _CmdCreateFolderArgs(StrictBaseModel):
    kwargs: CommandCreateFolder


class _CmdDeleteArgs(StrictBaseModel):
    kwargs: CommandDelete


class _CmdRenameArgs(StrictBaseModel):
    kwargs: CommandRename


class _CmdRunScriptArgs(StrictBaseModel):
    kwargs: CommandRunScript


class _CmdOpenBrowserArgs(StrictBaseModel):
    kwargs: CommandOpenBrowser


class CmdEmptyRecycleBin(_CmdNoArgs):
    command_name: Literal[CMD_EMPTY_RECYCLE_BIN]


class CmdScreenshot(_CmdNoArgs):
    command_name: Literal[CMD_SCREENSHOT]


class CmdShutdown(_CmdNoArgs):
    command_name: Literal[CMD_SHUTDOWN]


class CmdToggleWifi(_CmdNoArgs):
    command_name: Literal[CMD_WIFI]


class CmdToggleNotifications(_CmdNoArgs):
    command_name: Literal[CMD_NOTIFICATIONS]


class CmdToggleAirplaneMode(_CmdNoArgs):
    command_name: Literal[CMD_AIRPLANE]


class CmdToggleBluetooth(_CmdNoArgs):
    command_name: Literal[CMD_BLUETOOTH]


class CmdToggleMute(_CmdNoArgs):
    command_name: Literal[CMD_SOUND]


class CmdEnableEnergySaverMode(_CmdNoArgs):
    command_name: Literal[CMD_ENERGY_SAVER_ON]


class CmdDisableEnergySaverMode(_CmdNoArgs):
    command_name: Literal[CMD_ENERGY_SAVER_OFF]


class CmdStartRecording(_CmdNoArgs):
    command_name: Literal[CMD_RECORD_ON]


class CmdStopRecording(_CmdNoArgs):
    command_name: Literal[CMD_RECORD_OFF]


class CmdLaunchApp(_CmdAppArgs):
    command_name: Literal[CMD_LAUNCH_APP]


class CmdCloseApp(_CmdAppArgs):
    command_name: Literal[CMD_CLOSE_APP]


class CmdUninstallApp(_CmdAppArgs):
    command_name: Literal[CMD_UNINSTALL_APP]


class CmdCreateFile(_CmdCreateFileArgs):
    command_name: Literal[CMD_CREATE_FILE]


class CmdCreateFolder(_CmdCreateFolderArgs):
    command_name: Literal[CMD_CREATE_FOLDER]


class CmdDelete(_CmdDeleteArgs):
    command_name: Literal[CMD_DELETE]


class CmdRename(_CmdRenameArgs):
    command_name: Literal[CMD_RENAME]


class CmdRunScript(_CmdRunScriptArgs):
    command_name: Literal[CMD_RUN_SCRIPT]


class CmdOpenBrowser(_CmdOpenBrowserArgs):
    command_name: Literal[CMD_OPEN_SITE]


class CmdUnknown(_CmdNoArgs):
    command_name: Literal["#"]


AnyCommand = Union[
    CmdEmptyRecycleBin,
    CmdScreenshot,
    CmdShutdown,
    CmdToggleWifi,
    CmdToggleNotifications,
    CmdToggleAirplaneMode,
    CmdToggleBluetooth,
    CmdToggleMute,
    CmdEnableEnergySaverMode,
    CmdDisableEnergySaverMode,
    CmdStartRecording,
    CmdStopRecording,
    CmdLaunchApp,
    CmdCloseApp,
    CmdUninstallApp,
    CmdCreateFile,
    CmdCreateFolder,
    CmdDelete,
    CmdRename,
    CmdRunScript,
    CmdOpenBrowser,
    CmdUnknown,
]


class Command(StrictBaseModel):
    command: AnyCommand


class CommandNameOnly(StrictBaseModel):
    command_name: Literal[
        CMD_EMPTY_RECYCLE_BIN,
        CMD_SCREENSHOT,
        CMD_SHUTDOWN,
        CMD_WIFI,
        CMD_NOTIFICATIONS,
        CMD_AIRPLANE,
        CMD_BLUETOOTH,
        CMD_SOUND,
        CMD_ENERGY_SAVER_ON,
        CMD_ENERGY_SAVER_OFF,
        CMD_RECORD_ON,
        CMD_RECORD_OFF,
        CMD_LAUNCH_APP,
        CMD_CLOSE_APP,
        CMD_UNINSTALL_APP,
        CMD_CREATE_FILE,
        CMD_CREATE_FOLDER,
        CMD_DELETE,
        CMD_RENAME,
        CMD_RUN_SCRIPT,
        CMD_OPEN_SITE,
        "#",
    ]


_COMMAND_TO_WRAPPER: dict[str, type[StrictBaseModel]] = {
    CMD_EMPTY_RECYCLE_BIN: CmdEmptyRecycleBin,
    CMD_SCREENSHOT: CmdScreenshot,
    CMD_SHUTDOWN: CmdShutdown,
    CMD_WIFI: CmdToggleWifi,
    CMD_NOTIFICATIONS: CmdToggleNotifications,
    CMD_AIRPLANE: CmdToggleAirplaneMode,
    CMD_BLUETOOTH: CmdToggleBluetooth,
    CMD_SOUND: CmdToggleMute,
    CMD_ENERGY_SAVER_ON: CmdEnableEnergySaverMode,
    CMD_ENERGY_SAVER_OFF: CmdDisableEnergySaverMode,
    CMD_RECORD_ON: CmdStartRecording,
    CMD_RECORD_OFF: CmdStopRecording,
    CMD_LAUNCH_APP: CmdLaunchApp,
    CMD_CLOSE_APP: CmdCloseApp,
    CMD_UNINSTALL_APP: CmdUninstallApp,
    CMD_CREATE_FILE: CmdCreateFile,
    CMD_CREATE_FOLDER: CmdCreateFolder,
    CMD_DELETE: CmdDelete,
    CMD_RENAME: CmdRename,
    CMD_RUN_SCRIPT: CmdRunScript,
    CMD_OPEN_SITE: CmdOpenBrowser,
    "#": CmdUnknown,
}


_COMMAND_TO_KWARGS_MODEL: dict[str, type[StrictBaseModel]] = {
    CMD_EMPTY_RECYCLE_BIN: CommandEmptyArgs,
    CMD_SCREENSHOT: CommandEmptyArgs,
    CMD_SHUTDOWN: CommandEmptyArgs,
    CMD_WIFI: CommandEmptyArgs,
    CMD_NOTIFICATIONS: CommandEmptyArgs,
    CMD_AIRPLANE: CommandEmptyArgs,
    CMD_BLUETOOTH: CommandEmptyArgs,
    CMD_SOUND: CommandEmptyArgs,
    CMD_ENERGY_SAVER_ON: CommandEmptyArgs,
    CMD_ENERGY_SAVER_OFF: CommandEmptyArgs,
    CMD_RECORD_ON: CommandEmptyArgs,
    CMD_RECORD_OFF: CommandEmptyArgs,
    CMD_LAUNCH_APP: CommandApp,
    CMD_CLOSE_APP: CommandApp,
    CMD_UNINSTALL_APP: CommandApp,
    CMD_CREATE_FILE: CommandCreateFile,
    CMD_CREATE_FOLDER: CommandCreateFolder,
    CMD_DELETE: CommandDelete,
    CMD_RENAME: CommandRename,
    CMD_RUN_SCRIPT: CommandRunScript,
    CMD_OPEN_SITE: CommandOpenBrowser,
    "#": CommandEmptyArgs,
}


def get_command_kwargs_model(command_name: str) -> type[StrictBaseModel]:
    """Return the kwargs model class for a given command name."""

    return _COMMAND_TO_KWARGS_MODEL.get(command_name, CommandEmptyArgs)


def build_command(command_name: str, kwargs: Any | None = None) -> Command:
    """
    Build the final `Command` object from:
    - `command_name`
    - optional `kwargs` 
    """

    wrapper_cls = _COMMAND_TO_WRAPPER.get(command_name, CmdUnknown)
    # Keep unknown always as '#'
    normalized_command_name = command_name if command_name in _COMMAND_TO_WRAPPER else "#"
    kwargs_model = get_command_kwargs_model(normalized_command_name)

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
