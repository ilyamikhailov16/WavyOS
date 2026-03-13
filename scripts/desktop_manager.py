"""
desktop_manager.py
==================
Модуль управления файловой системой рабочего стола.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Настройка логгера
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Вспомогательные типы
# ---------------------------------------------------------------------------


class ItemType(str, Enum):
    FILE = "file"
    FOLDER = "folder"


class OperationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OperationResult:
    """Унифицированный ответ каждого метода."""

    status: OperationStatus
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Определение пути к рабочему столу
# ---------------------------------------------------------------------------


def _resolve_desktop() -> Path:
    """
    Определение пути к рабочему столу через реестр Windows.
    Fallback — ~/Desktop, если реестр недоступен.
    """
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        )
        path, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(path)
    except Exception:
        return Path.home() / "Desktop"  # fallback


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------


class DesktopManager:
    """
    Управление файлами и папками на рабочем столе пользователя.

    Каждый публичный метод возвращает :class:`OperationResult`.
    """

    def __init__(self, desktop_path: Path | str | None = None) -> None:
        """
        Args:
            desktop_path: Явный путь к рабочему столу (для тестов или кастомных сред).
                          Если None — определяется автоматически.
        """
        self.desktop: Path = Path(desktop_path) if desktop_path else _resolve_desktop()
        logger.info("DesktopManager инициализирован. Рабочий стол: %s", self.desktop)

    # ------------------------------------------------------------------
    # Приватные утилиты
    # ------------------------------------------------------------------

    def _safe_path(self, name: str, subfolder: str | None = None) -> Path:
        """Строит абсолютный путь, не выходящий за пределы рабочего стола."""
        base = (self.desktop / subfolder) if subfolder else self.desktop
        target = (base / name).resolve()

        # Защита от path-traversal атак
        if not str(target).startswith(str(self.desktop.resolve())):
            raise ValueError(f"Путь '{target}' выходит за пределы рабочего стола.")

        return target

    def _ok(self, message: str, **data: Any) -> OperationResult:
        logger.info(message)
        return OperationResult(
            status=OperationStatus.SUCCESS, message=message, data=dict(data)
        )

    def _err(self, message: str, **data: Any) -> OperationResult:
        logger.error(message)
        return OperationResult(
            status=OperationStatus.ERROR, message=message, data=dict(data)
        )

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def create_folder(self, name: str) -> OperationResult:
        """
        Создать папку на рабочем столе.

        Args:
            name: Имя папки (разрешен вложенный путь).

        Returns:
            OperationResult с полем data["path"].
        """
        try:
            path = self._safe_path(name)
            path.mkdir(parents=True, exist_ok=True)
            return self._ok(f"Папка '{name}' создана.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка при создании папки '{name}': {exc}")

    def create_file(
        self,
        filename: str,
        content: str = "",
        folder: str | None = None,
        overwrite: bool = False,
    ) -> OperationResult:
        """
        Создать текстовый файл на рабочем столе или в указанной папке.

        Args:
            filename: Имя файла с расширением (напр. "x.txt").
            content:  Текстовое содержимое файла.
            folder:   Подпапка на рабочем столе (необязательно).
            overwrite: Перезаписать файл, если он уже существует.

        Returns:
            OperationResult с полем data["path"].
        """
        try:
            path = self._safe_path(filename, subfolder=folder)
            if path.exists() and not overwrite:
                return self._err(
                    f"Файл '{filename}' уже существует. Передайте overwrite=True для перезаписи.",
                    path=str(path),
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return self._ok(f"Файл '{filename}' создан.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка при создании файла '{filename}': {exc}")

    def create_json_file(
        self,
        filename: str,
        data: dict[str, Any],
        folder: str | None = None,
        overwrite: bool = False,
    ) -> OperationResult:
        """
        Создать JSON-файл.

        Args:
            filename: Имя файла (напр. "config.json").
            data:     Словарь для сериализации.
            folder:   Подпапка на рабочем столе (необязательно).
            overwrite: Перезаписать файл, если он уже существует.
        """
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.create_file(filename, content, folder=folder, overwrite=overwrite)

    def read_file(self, filename: str, folder: str | None = None) -> OperationResult:
        """
        Прочитать содержимое текстового файла.

        Returns:
            OperationResult с полем data["content"].
        """
        try:
            path = self._safe_path(filename, subfolder=folder)
            if not path.is_file():
                return self._err(f"Файл '{filename}' не найден.", path=str(path))
            content = path.read_text(encoding="utf-8")
            return self._ok(
                f"Файл '{filename}' прочитан.", content=content, path=str(path)
            )
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка чтения файла '{filename}': {exc}")

    def delete(self, name: str, folder: str | None = None) -> OperationResult:
        """
        Удалить файл или папку (папка удаляется рекурсивно).

        Args:
            name:   Имя файла или папки.
            folder: Подпапка, в которой находится объект (необязательно).
        """
        try:
            path = self._safe_path(name, subfolder=folder)
            if not path.exists():
                return self._err(f"'{name}' не существует.", path=str(path))
            if path.is_dir():
                shutil.rmtree(path)
                return self._ok(f"Папка '{name}' удалена.", path=str(path))
            path.unlink()
            return self._ok(f"Файл '{name}' удалён.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка при удалении '{name}': {exc}")

    def rename(
        self, old_name: str, new_name: str, folder: str | None = None
    ) -> OperationResult:
        """
        Переименовать файл или папку.

        Args:
            old_name: Текущее имя.
            new_name: Новое имя.
            folder:   Подпапка (необязательно).
        """
        try:
            src = self._safe_path(old_name, subfolder=folder)
            dst = self._safe_path(new_name, subfolder=folder)
            if not src.exists():
                return self._err(f"'{old_name}' не существует.")
            if dst.exists():
                return self._err(f"'{new_name}' уже существует.")
            src.rename(dst)
            return self._ok(f"'{old_name}' переименован в '{new_name}'.", path=str(dst))
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка переименования: {exc}")

    def list_items(self, folder: str | None = None) -> OperationResult:
        """
        Получить список файлов и папок.

        Args:
            folder: Подпапка для просмотра; если None — корень рабочего стола.

        Returns:
            OperationResult с полем data["items"] — список словарей
            {"name": str, "type": "file"|"folder", "size_bytes": int}.
        """
        try:
            base = self._safe_path(folder) if folder else self.desktop
            if not base.is_dir():
                return self._err(f"Папка '{folder}' не найдена.")

            items = []
            for entry in sorted(base.iterdir()):
                if entry.name.startswith("."):
                    continue  # скрываем служебные файлы
                items.append(
                    {
                        "name": entry.name,
                        "type": ItemType.FOLDER if entry.is_dir() else ItemType.FILE,
                        "size_bytes": entry.stat().st_size if entry.is_file() else None,
                    }
                )
            return self._ok(
                f"Найдено элементов: {len(items)}.",
                items=items,
                path=str(base),
            )
        except (ValueError, OSError) as exc:
            return self._err(f"Ошибка при чтении содержимого: {exc}")

    def get_info(self) -> OperationResult:
        """
        Вернуть информацию о текущей конфигурации менеджера.
        """
        import sys

        return self._ok(
            "Информация получена.",
            desktop_path=str(self.desktop),
            desktop_exists=self.desktop.exists(),
            python_version=sys.version,
        )


# ---------------------------------------------------------------------------
# Быстрое тестирование
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     dm = DesktopManager()

#     dm.get_info().to_json()

#     dm.create_folder("ИИ_Ассистент/Проекты").to_json()

#     dm.create_file(
#         "задачи.txt",
#         content="1. Изучить Python\n2. Написать ассистента",
#         folder="ИИ_Ассистент",
#     ).to_json()

#     dm.create_json_file(
#         "config.json",
#         data={"version": "1.0", "assistant": "AI", "debug": False},
#         folder="ИИ_Ассистент",
#     ).to_json()

#     dm.list_items("ИИ_Ассистент").to_json()
