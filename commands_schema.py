from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, ConfigDict


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
    data: str = Field(default="", description="Text content of the file")


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
    command_name: Literal["Очистить корзину"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdScreenshot(StrictBaseModel):
    command_name: Literal["Скриншот"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdShutdown(StrictBaseModel):
    command_name: Literal["Выключить компьютер"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleWifi(StrictBaseModel):
    command_name: Literal["Переключить интернет"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleNotifications(StrictBaseModel):
    command_name: Literal["Переключить уведомления"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleAirplaneMode(StrictBaseModel):
    command_name: Literal["Переключить режим полёта"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleBluetooth(StrictBaseModel):
    command_name: Literal["Переключить блютуз"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdToggleMute(StrictBaseModel):
    command_name: Literal["Переключить звук"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdEnableEnergySaverMode(StrictBaseModel):
    command_name: Literal["Включить режим энергосбережения"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdDisableEnergySaverMode(StrictBaseModel):
    command_name: Literal["Выключить режим энергосбережения"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdStartRecording(StrictBaseModel):
    command_name: Literal["Включить запись экрана"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdStopRecording(StrictBaseModel):
    command_name: Literal["Выключить запись экрана"]
    kwargs: CommandEmptyArgs = Field(default_factory=CommandEmptyArgs)


class CmdLaunchApp(StrictBaseModel):
    command_name: Literal["Открыть приложение"]
    kwargs: CommandApp


class CmdCloseApp(StrictBaseModel):
    command_name: Literal["Закрыть приложение"]
    kwargs: CommandApp


class CmdUninstallApp(StrictBaseModel):
    command_name: Literal["Удалить приложение"]
    kwargs: CommandApp


class CmdCreateFile(StrictBaseModel):
    command_name: Literal["Создать файл"]
    kwargs: CommandCreateFile


class CmdCreateFolder(StrictBaseModel):
    command_name: Literal["Создать папку"]
    kwargs: CommandCreateFolder


class CmdDelete(StrictBaseModel):
    command_name: Literal["Удалить"]
    kwargs: CommandDelete


class CmdRename(StrictBaseModel):
    command_name: Literal["Переименовать"]
    kwargs: CommandRename


class CmdRunScript(StrictBaseModel):
    command_name: Literal["Запустить скрипт"]
    kwargs: CommandRunScript


class CmdOpenBrowser(StrictBaseModel):
    command_name: Literal["Открыть сайт"]
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
