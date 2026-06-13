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
    command_name: Literal[CMD_UNKNOWN]


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
        CMD_UNKNOWN,
    ]


class CommandInfo(StrictBaseModel):
    wrapper: type[StrictBaseModel]
    kwargs_model: type[StrictBaseModel]
