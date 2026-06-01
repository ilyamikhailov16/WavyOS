from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app_logging import get_logger
from config import settings

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------------


class ItemType(str, Enum):
    FILE = "file"
    FOLDER = "folder"


class OperationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OperationResult:
    """Unified response returned by each method."""

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
# Resolving desktop path
# ---------------------------------------------------------------------------


def _resolve_desktop() -> Path:
    """
    Resolve the desktop path using the Windows registry.
    Fallback — ~/Desktop if the registry is unavailable.
    """
    cfg = settings.desktop_manager
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            cfg.registry_key,
        )
        path, _ = winreg.QueryValueEx(key, cfg.registry_value)
        return Path(path)
    except Exception:
        return Path.home() / cfg.fallback_folder


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DesktopManager:
    """
    Manage files and folders on the user's desktop.

    Each public method returns an :class:`OperationResult`.
    """

    def __init__(self, desktop_path: Path | str | None = None) -> None:
        """
        Args:
            desktop_path: Explicit path to the desktop (for tests or custom environments).
                          If None — it is resolved automatically.
        """
        self.desktop: Path = Path(desktop_path) if desktop_path else _resolve_desktop()
        logger.info("DesktopManager initialized. Desktop path: %s", self.desktop)

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    def _safe_path(self, name: str, subfolder: str | None = None) -> Path:
        """Builds an absolute path that does not escape the desktop directory."""
        base = (self.desktop / subfolder) if subfolder else self.desktop
        target = (base / name).resolve()

        # Protection against path-traversal attacks
        if not str(target).startswith(str(self.desktop.resolve())):
            raise ValueError(f"Path '{target}' is outside the desktop directory.")

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
    # Public API
    # ------------------------------------------------------------------

    def create_folder(self, name: str) -> OperationResult:
        """
        Create a folder on the desktop.

        Args:
            name: Folder name (nested paths are allowed).

        Returns:
            OperationResult with data["path"] field.
        """
        try:
            path = self._safe_path(name)
            path.mkdir(parents=True, exist_ok=True)
            return self._ok(f"Folder '{name}' created.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Error creating folder '{name}': {exc}")

    def create_file(
        self,
        filename: str,
        content: str = "",
        folder: str | None = None,
        overwrite: bool = False,
    ) -> OperationResult:
        """
        Create a text file on the desktop or in the specified folder.

        Args:
            filename: File name with extension (e.g., "x.txt").
            content:  Text content of the file.
            folder:   Subfolder on the desktop (optional).
            overwrite: Overwrite the file if it already exists.

        Returns:
            OperationResult with data["path"] field.
        """
        try:
            path = self._safe_path(filename, subfolder=folder)
            if path.exists() and not overwrite:
                return self._err(
                    f"File '{filename}' already exists. Pass overwrite=True to overwrite.",
                    path=str(path),
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=settings.desktop_manager.file_encoding)
            return self._ok(f"File '{filename}' created.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Error creating file '{filename}': {exc}")

    def create_json_file(
        self,
        filename: str,
        data: dict[str, Any],
        folder: str | None = None,
        overwrite: bool = False,
    ) -> OperationResult:
        """
        Create a JSON file.

        Args:
            filename: File name (e.g., "config.json").
            data:     Dictionary to serialize.
            folder:   Subfolder on the desktop (optional).
            overwrite: Overwrite the file if it already exists.
        """
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.create_file(filename, content, folder=folder, overwrite=overwrite)

    def read_file(self, filename: str, folder: str | None = None) -> OperationResult:
        """
        Read the contents of a text file.

        Returns:
            OperationResult with data["content"] field.
        """
        try:
            path = self._safe_path(filename, subfolder=folder)
            if not path.is_file():
                return self._err(f"File '{filename}' not found.", path=str(path))
            content = path.read_text(encoding=settings.desktop_manager.file_encoding)
            return self._ok(
                f"File '{filename}' read.", content=content, path=str(path)
            )
        except (ValueError, OSError) as exc:
            return self._err(f"Error reading file '{filename}': {exc}")

    def delete(self, name: str, folder: str | None = None) -> OperationResult:
        """
        Delete a file or folder (folders are removed recursively).

        Args:
            name:   File or folder name.
            folder: Subfolder where the item is located (optional).
        """
        try:
            path = self._safe_path(name, subfolder=folder)
            if not path.exists():
                return self._err(f"'{name}' does not exist.", path=str(path))
            if path.is_dir():
                shutil.rmtree(path)
                return self._ok(f"Folder '{name}' deleted.", path=str(path))
            path.unlink()
            return self._ok(f"File '{name}' deleted.", path=str(path))
        except (ValueError, OSError) as exc:
            return self._err(f"Error deleting '{name}': {exc}")

    def rename(
        self, old_name: str, new_name: str, folder: str | None = None
    ) -> OperationResult:
        """
        Rename a file or folder.

        Args:
            old_name: Current name.
            new_name: New name.
            folder:   Subfolder (optional).
        """
        try:
            src = self._safe_path(old_name, subfolder=folder)
            dst = self._safe_path(new_name, subfolder=folder)
            if not src.exists():
                return self._err(f"'{old_name}' does not exist.")
            if dst.exists():
                return self._err(f"'{new_name}' already exists.")
            src.rename(dst)
            return self._ok(f"'{old_name}' renamed to '{new_name}'.", path=str(dst))
        except (ValueError, OSError) as exc:
            return self._err(f"Rename error: {exc}")

    def list_items(self, folder: str | None = None) -> OperationResult:
        """
        Get a list of files and folders.

        Args:
            folder: Subfolder to inspect; if None — desktop root.

        Returns:
            OperationResult with data["items"] — list of dictionaries
            {"name": str, "type": "file"|"folder", "size_bytes": int}.
        """
        try:
            base = self._safe_path(folder) if folder else self.desktop
            if not base.is_dir():
                return self._err(f"Folder '{folder}' not found.")

            items = []
            for entry in sorted(base.iterdir()):
                if entry.name.startswith("."):
                    continue  # hide system/hidden files
                items.append(
                    {
                        "name": entry.name,
                        "type": ItemType.FOLDER if entry.is_dir() else ItemType.FILE,
                        "size_bytes": entry.stat().st_size if entry.is_file() else None,
                    }
                )
            return self._ok(
                f"Items found: {len(items)}.",
                items=items,
                path=str(base),
            )
        except (ValueError, OSError) as exc:
            return self._err(f"Error reading contents: {exc}")

    def get_info(self) -> OperationResult:
        """
        Return information about the current manager configuration.
        """
        import sys

        return self._ok(
            "Information retrieved.",
            desktop_path=str(self.desktop),
            desktop_exists=self.desktop.exists(),
            python_version=sys.version,
        )


# ---------------------------------------------------------------------------
# Quick testing
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
