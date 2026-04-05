from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field
from .commands_keys import *


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandEmptyArgs(StrictBaseModel):
    pass


class CommandApp(StrictBaseModel):
    app_name: str = Field(description="Name of the application or alias")


class CommandCreateFile(StrictBaseModel):
    filename: str = Field(description="File name with extension")
    folder: str | None = Field(
        default=None, description="Subfolder name on the desktop"
    )
    content: str = Field(default="", description="Text content of the file")


class CommandCreateFolder(StrictBaseModel):
    name: str = Field(description="Folder name")


class CommandDelete(StrictBaseModel):
    name: str = Field(description="File or folder name")
    folder: str | None = Field(
        default=None, description="Subfolder where the item is located"
    )


class CommandRename(StrictBaseModel):
    old_name: str = Field(description="Current name of the file or folder")
    new_name: str = Field(description="New name")
    folder: str | None = Field(default=None, description="Subfolder name")


class CommandRunScript(StrictBaseModel):
    script_name: str = Field(description="File name including the .py extension")


class CommandOpenBrowser(StrictBaseModel):
    website_name: str = Field(description="Domain name or preset engine name")
    query: str | None = Field(
        default=None, description="Text to search or enter into the target field"
    )


class CmdEmptyRecycleBin(StrictBaseModel):
    command_name: Literal[CMD_EMPTY_RECYCLE_BIN]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdScreenshot(StrictBaseModel):
    command_name: Literal[CMD_SCREENSHOT]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdShutdown(StrictBaseModel):
    command_name: Literal[CMD_SHUTDOWN]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleWifi(StrictBaseModel):
    command_name: Literal[CMD_WIFI]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleNotifications(StrictBaseModel):
    command_name: Literal[CMD_NOTIFICATIONS]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleAirplaneMode(StrictBaseModel):
    command_name: Literal[CMD_AIRPLANE]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleBluetooth(StrictBaseModel):
    command_name: Literal[CMD_BLUETOOTH]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleMute(StrictBaseModel):
    command_name: Literal[CMD_SOUND]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdEnableEnergySaverMode(StrictBaseModel):
    command_name: Literal[CMD_ENERGY_SAVER_ON]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdDisableEnergySaverMode(StrictBaseModel):
    command_name: Literal[CMD_ENERGY_SAVER_OFF]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdStartRecording(StrictBaseModel):
    command_name: Literal[CMD_RECORD_ON]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdStopRecording(StrictBaseModel):
    command_name: Literal[CMD_RECORD_OFF]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdLaunchApp(StrictBaseModel):
    command_name: Literal[CMD_LAUNCH_APP]
    kwargs: CommandApp


class CmdCloseApp(StrictBaseModel):
    command_name: Literal[CMD_CLOSE_APP]
    kwargs: CommandApp


class CmdUninstallApp(StrictBaseModel):
    command_name: Literal[CMD_UNINSTALL_APP]
    kwargs: CommandApp


class CmdCreateFile(StrictBaseModel):
    command_name: Literal[CMD_CREATE_FILE]
    kwargs: CommandCreateFile


class CmdCreateFolder(StrictBaseModel):
    command_name: Literal[CMD_CREATE_FOLDER]
    kwargs: CommandCreateFolder


class CmdDelete(StrictBaseModel):
    command_name: Literal[CMD_DELETE]
    kwargs: CommandDelete


class CmdRename(StrictBaseModel):
    command_name: Literal[CMD_RENAME]
    kwargs: CommandRename


class CmdRunScript(StrictBaseModel):
    command_name: Literal[CMD_RUN_SCRIPT]
    kwargs: CommandRunScript


class CmdOpenBrowser(StrictBaseModel):
    command_name: Literal[CMD_OPEN_SITE]
    kwargs: CommandOpenBrowser


class CmdUnknown(StrictBaseModel):
    command_name: Literal["#"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


AnyCommand = Annotated[
    Union[
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
    ],
    Field(discriminator="command_name"),
]


class Command(StrictBaseModel):
    command: AnyCommand
