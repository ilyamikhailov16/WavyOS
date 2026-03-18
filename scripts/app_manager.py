from __future__ import annotations

import json
import os
import re as _re
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app_logging import get_logger
from config import settings

from .aliases import (
    APP_ALIASES,
    APP_CONSOLE_APPS,
    APP_NAME_ALIASES,
    APP_PROTOCOL_ALIASES,
    transliterate,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Типы
# ---------------------------------------------------------------------------


class OperationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OperationResult:
    """Унифицированный ответ каждого метода — удобен для LLM-парсинга."""

    status: OperationStatus
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "message": self.message, "data": self.data}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Убирает пробелы, дефисы, подчёркивания для fuzzy-сравнения.
    "counter-strike 2" → "counterstrike2", "counter strike" → "counterstrike"
    """
    return _re.sub(r"[\s\-_.]", "", text.lower())


def _word_match(key: str, name: str) -> bool:
    """True если key встречается как отдельное слово (или начало слова) в name."""
    return bool(_re.search(r"\b" + _re.escape(key), name))


class AppManager:
    """
    Управление приложениями: запуск, закрытие, удаление, список процессов.

    При инициализации читает реестр один раз и строит два кеша:
      _exe_cache:       display_name.lower() → абсолютный путь к .exe
      _uninstall_cache: display_name.lower() → UninstallString

    Все последующие запросы работают через словарь O(1) без обращений к реестру.
    Каждый публичный метод возвращает :class:`OperationResult`.
    """

    def __init__(self) -> None:
        self._exe_cache: dict[str, str] = {}
        self._uninstall_cache: dict[str, str] = {}
        self._exe_norm: dict[str, str] = {}
        self._uninstall_norm: dict[str, str] = {}
        self._build_registry_cache()

    # ------------------------------------------------------------------
    # Внутренние утилиты
    # ------------------------------------------------------------------

    def _ok(self, message: str, **data: Any) -> OperationResult:
        logger.info(message)
        return OperationResult(OperationStatus.SUCCESS, message, data)

    def _err(self, message: str, **data: Any) -> OperationResult:
        logger.error(message)
        return OperationResult(OperationStatus.ERROR, message, data)

    def _run(self, cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
        """
        Запускает команду, возвращает (returncode, stdout, stderr).
        """
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=settings.app_manager.subprocess_encoding,
                errors="replace",
            )
            try:
                out, err = proc.communicate(timeout=timeout)
                return proc.returncode, out.strip(), err.strip()
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                return (
                    -1,
                    out.strip() if out else "",
                    f"Таймаут ({timeout}с): {' '.join(cmd)}",
                )
        except FileNotFoundError:
            return -1, "", f"Команда не найдена: {cmd[0]}"

    @staticmethod
    def _to_exe_name(resolved: str) -> str:
        """Возвращает имя .exe без пути — для поиска в tasklist."""
        name = Path(resolved).name
        return name if name.lower().endswith(".exe") else f"{name}.exe"

    def _is_process_running(self, exe_name: str) -> bool:
        """Проверяет наличие процесса через tasklist /FI."""
        code, out, _ = self._run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"]
        )
        return code == 0 and exe_name.lower() in out.lower()

    # ------------------------------------------------------------------
    # Кеш реестра
    # ------------------------------------------------------------------

    def _build_registry_cache(self) -> None:
        """
        Читает реестр Windows один раз, заполняет _exe_cache и _uninstall_cache.
        Вызывается при инициализации и после uninstall_app().
        """
        try:
            import winreg
        except ImportError:
            logger.warning("winreg недоступен — кеш реестра не построен.")
            return

        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
        }

        def _valid_exe(p: Path, app_lower: str) -> bool:
            return (
                p.suffix.lower() == ".exe"
                and p.exists()
                and not any(
                    s in p.stem.lower() for s in settings.app_manager.skip_exe_names
                )
                and app_lower in p.stem.lower()
            )

        def _find_exe_in_dir(directory: Path, app_lower: str) -> Path | None:
            """Корень папки, затем один уровень вглубь (Squirrel: app-X.Y.Z/)."""
            for exe in sorted(directory.glob("*.exe")):
                if _valid_exe(exe, app_lower):
                    return exe
            for sub in sorted(directory.iterdir()):
                if sub.is_dir():
                    for exe in sorted(sub.glob("*.exe")):
                        if _valid_exe(exe, app_lower):
                            return exe
            return None

        exe_count = uninstall_count = 0

        for reg_path, hive_name in settings.app_manager.registry_uninstall_paths:
            try:
                key = winreg.OpenKey(hive_map[hive_name], reg_path)
            except OSError:
                continue

            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey = winreg.OpenKey(key, winreg.EnumKey(key, i))
                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                    name_key = display_name.lower()
                    app_lower = name_key.replace(" ", "")

                    # UninstallString → _uninstall_cache
                    if name_key not in self._uninstall_cache:
                        try:
                            uninstall_str, _ = winreg.QueryValueEx(
                                subkey, "UninstallString"
                            )
                            self._uninstall_cache[name_key] = uninstall_str
                            self._uninstall_norm[_normalize(name_key)] = uninstall_str
                            uninstall_count += 1
                        except (OSError, FileNotFoundError):
                            pass

                    # Путь к .exe → _exe_cache
                    if name_key in self._exe_cache:
                        continue

                    exe_found: str | None = None

                    # DisplayIcon — самый надёжный источник пути
                    try:
                        icon, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                        candidate = Path(icon.split(",")[0].strip().strip('"'))
                        if (
                            candidate.suffix.lower() == ".exe"
                            and candidate.exists()
                            and not any(
                                s in candidate.stem.lower()
                                for s in settings.app_manager.skip_exe_names
                            )
                        ):
                            exe_found = str(candidate)
                    except (OSError, FileNotFoundError):
                        pass

                    # InstallLocation — fallback с поиском в подпапках
                    if not exe_found:
                        try:
                            install_dir, _ = winreg.QueryValueEx(
                                subkey, "InstallLocation"
                            )
                            install_path = Path(install_dir.strip().strip('"'))
                            if install_path.is_dir():
                                found = _find_exe_in_dir(install_path, app_lower)
                                if found:
                                    exe_found = str(found)
                        except (OSError, FileNotFoundError):
                            pass

                    if exe_found:
                        self._exe_cache[name_key] = exe_found
                        self._exe_norm[_normalize(name_key)] = exe_found
                        exe_count += 1

                except (OSError, FileNotFoundError):
                    continue

        logger.info(
            "Кеш реестра: %d приложений для запуска, %d для удаления.",
            exe_count,
            uninstall_count,
        )

    def refresh_registry_cache(self) -> OperationResult:
        """
        Обновить кеш реестра. Вызывать после установки/удаления приложений.
        Доступен ИИ-агенту как отдельный инструмент.
        """
        self._exe_cache.clear()
        self._uninstall_cache.clear()
        self._exe_norm.clear()
        self._uninstall_norm.clear()
        self._build_registry_cache()
        return self._ok(
            f"Кеш реестра обновлён: {len(self._exe_cache)} приложений.",
            exe_count=len(self._exe_cache),
            uninstall_count=len(self._uninstall_cache),
        )

    def _lookup_exe(self, app_name: str) -> str | None:
        """
        Поиск пути к .exe в кеше.
        Порядок: точное → нормализованное → транслит → word-boundary → подстрока.
        """
        key = app_name.lower()

        # 1. Точное
        if key in self._exe_cache:
            return self._exe_cache[key]

        # 2. Нормализованное (убирает дефисы/пробелы)
        norm = _normalize(key)
        for n_key, exe in self._exe_norm.items():
            if norm == n_key or norm in n_key:
                logger.info("Найден в кеше (норм.): '%s' → %s", n_key, exe)
                return exe

        # 3. Транслитерация → попробуем как norm
        translit = _normalize(transliterate(key))
        if translit != norm:
            for n_key, exe in self._exe_norm.items():
                if translit == n_key or translit in n_key:
                    logger.info(
                        "Найден в кеше (транслит '%s'): '%s' → %s", translit, n_key, exe
                    )
                    return exe

        # 4. Word-boundary → выбираем ближайшее по длине
        candidates = [(n, e) for n, e in self._exe_cache.items() if _word_match(key, n)]
        if not candidates:
            candidates = [(n, e) for n, e in self._exe_cache.items() if key in n]
        if candidates:
            best_name, best_exe = min(
                candidates, key=lambda t: abs(len(t[0]) - len(key))
            )
            logger.info("Найден в кеше (word): '%s' → %s", best_name, best_exe)
            return best_exe

        return None

    def _lookup_uninstall_str(self, app_name: str) -> str | None:
        """Поиск UninstallString. Те же приоритеты что и _lookup_exe."""
        key = app_name.lower()

        if key in self._uninstall_cache:
            return self._uninstall_cache[key]

        norm = _normalize(key)
        for n_key, us in self._uninstall_norm.items():
            if norm == n_key or norm in n_key:
                logger.info("Найден UninstallString (норм.): '%s'", n_key)
                return us

        translit = _normalize(transliterate(key))
        if translit != norm:
            for n_key, us in self._uninstall_norm.items():
                if translit == n_key or translit in n_key:
                    logger.info(
                        "Найден UninstallString (транслит '%s'): '%s'", translit, n_key
                    )
                    return us

        candidates = [
            (n, u) for n, u in self._uninstall_cache.items() if _word_match(key, n)
        ]
        if not candidates:
            candidates = [(n, u) for n, u in self._uninstall_cache.items() if key in n]
        if candidates:
            best_name, best_us = min(
                candidates, key=lambda t: abs(len(t[0]) - len(key))
            )
            logger.info("Найден UninstallString (word): '%s'", best_name)
            return best_us

        return None

    def _resolve_app_name(self, app_name: str) -> str:
        """
        Резолвит имя/алиас в путь к исполняемому файлу или URI.

        Приоритет:
          1. APP_PROTOCOL_ALIASES — URI-протоколы (ms-settings:, epic://, …)
          2. APP_SPECIAL_LAUNCH   — нестандартный запуск (Roblox, steam://)
          3. APP_ALIASES          — системные утилиты (notepad, calc, …)
          4. APP_NAME_ALIASES     — русский алиас → DisplayName → кеш реестра
          5. Кеш реестра          — нормализованный + транслит + word-boundary
          6. APP_KNOWN_PATHS      — известные пути вне реестра
          7. Fallback             — передаём как есть
        """
        key = app_name.lower()

        if uri := APP_PROTOCOL_ALIASES.get(key):
            return uri

        if special := settings.app_manager.special_launch.get(key):
            exe_template, _args = special
            if exe_template.startswith("steam://"):
                return exe_template
            expanded = os.path.expandvars(exe_template)
            if Path(expanded).exists():
                return expanded

        if alias := APP_ALIASES.get(key):
            return alias

        registry_name = APP_NAME_ALIASES.get(key, app_name)
        if exe := self._lookup_exe(registry_name):
            return exe

        for path_str in settings.app_manager.known_paths.get(key, []):
            expanded = os.path.expandvars(path_str)
            if Path(expanded).exists():
                logger.info("Найден по известному пути: %s", expanded)
                return expanded

        return app_name

    # ------------------------------------------------------------------
    # Удаление: внутренняя логика
    # ------------------------------------------------------------------

    def _uninstall_via_winget(self, app_name: str) -> OperationResult:
        """Удаление через winget (Win 10+)."""
        logger.info("Попытка удаления '%s' через winget...", app_name)
        code, out, err = self._run(
            [
                "winget",
                "uninstall",
                "--name",
                app_name,
                "--silent",
                "--accept-source-agreements",
            ],
            timeout=settings.app_manager.winget_timeout_s,
        )

        # Таймаут → лаунчер открыл диалог подтверждения
        if "таймаут" in err.lower():
            return self._err(
                f"Удаление '{app_name}' требует подтверждения в стороннем лаунчере. "
                "Подтвердите удаление в открывшемся окне.",
                method="winget",
                reason="launcher_confirmation_required",
            )

        if code != 0:
            return self._err(
                f"winget не смог удалить '{app_name}': {err or out}",
                method="winget",
                returncode=code,
            )

        # Проверяем: запись в кеше ещё есть → удаление не завершено.
        uninstall_str = self._lookup_uninstall_str(app_name)
        if uninstall_str is not None:
            if "steam://" in uninstall_str.lower():
                logger.info("Steam-игра — передаём в registry-обработчик.")
                return self._uninstall_via_registry(app_name, uninstall_str)
            return self._err(
                f"'{app_name}' ещё присутствует в реестре — удаление не завершено. "
                "Возможно, требуется подтверждение в стороннем лаунчере.",
                method="winget",
                reason="launcher_confirmation_required",
            )

        return self._ok(f"'{app_name}' успешно удалён.", method="winget", output=out)

    def _uninstall_via_registry(
        self, app_name: str, uninstall_str: str | None = None
    ) -> OperationResult:
        """
        Fallback: удаление через UninstallString из реестра.

        Args:
            uninstall_str: Передаётся из _uninstall_via_winget, чтобы не
                           обращаться к кешу повторно.
        """
        logger.info("Попытка удаления '%s' через реестр...", app_name)

        uninstall_str = uninstall_str or self._lookup_uninstall_str(app_name)
        if not uninstall_str:
            return self._err(
                f"'{app_name}' не найден. Возможно, приложение не установлено.",
                method="registry",
            )

        # Steam: URI открывается через обработчик протокола Windows
        if "steam://" in uninstall_str.lower():
            steam_uri = next(
                (p for p in uninstall_str.split() if p.startswith("steam://")), None
            )
            if not steam_uri:
                return self._err(
                    f"Не удалось извлечь steam:// URI из: {uninstall_str}",
                    method="registry",
                )
            try:
                os.startfile(steam_uri)
                return self._ok(
                    f"Запрос удаления '{app_name}' отправлен в Steam. "
                    "Подтвердите в открывшемся окне.",
                    method="registry",
                    reason="launcher_confirmation_required",
                    steam_uri=steam_uri,
                )
            except OSError as exc:
                return self._err(f"Не удалось открыть Steam: {exc}", method="registry")

        # Парсим строку — shlex корректно обрабатывает пути с пробелами в кавычках
        try:
            cmd = [c.strip('"') for c in shlex.split(uninstall_str, posix=False)]
        except ValueError:
            cmd = uninstall_str.split()

        exe_path = Path(cmd[0])
        if not exe_path.exists():
            return self._err(
                f"Файл '{exe_path}' не найден — запись в реестре устарела. "
                "Очистите её через Apps → Installed Apps.",
                method="registry",
                reason="ghost_registry_entry",
                uninstall_path=str(exe_path),
            )

        # Флаги тихого удаления по типу установщика
        exe_lower = str(exe_path).lower()
        args_lower = uninstall_str.lower()

        if "msiexec" in exe_lower:
            cmd += ["/quiet", "/norestart"]
        elif "maintenancetool" in exe_lower:  # Qt Installer Framework
            if "--confirm-command" not in args_lower:
                cmd += ["--confirm-command"]
        elif "uninst" in exe_lower and "inno" in args_lower:  # Inno Setup
            cmd += ["/VERYSILENT", "/SUPPRESSMSGBOXES"]
        elif "/s" not in args_lower and "--silent" not in args_lower:  # NSIS и прочие
            cmd += ["/S"]

        code, out, err = self._run(
            cmd, timeout=settings.app_manager.uninstall_timeout_s
        )
        if code == 0:
            return self._ok(f"'{app_name}' удалён через реестр.", method="registry")
        return self._err(
            f"Ошибка удаления '{app_name}': {err or out}",
            method="registry",
            returncode=code,
        )

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def launch_app(self, app_name: str) -> OperationResult:
        """
        Запустить приложение по имени, алиасу или полному пути.

        Поддерживает:
          - Русские алиасы ("дискорд", "блокнот")
          - URI-протоколы ("ms-settings:", "com.epicgames.launcher://")
          - Консольные приложения (cmd, powershell) с видимым окном

        Args:
            app_name: Имя, алиас или путь (напр. "discord", "блокнот", "settings").

        Returns:
            OperationResult с полями data["resolved"] и data["pid"].
        """
        resolved = self._resolve_app_name(app_name)

        # URI-протокол (ms-settings:, com.epicgames.launcher://, …) — только startfile
        if "://" in resolved or resolved.endswith(":"):
            try:
                os.startfile(resolved)
                return self._ok(
                    f"'{app_name}' запущен через системный обработчик.",
                    app=app_name,
                    resolved=resolved,
                )
            except OSError as exc:
                return self._err(
                    f"Не удалось открыть '{app_name}' через URI: {exc}",
                    app=app_name,
                    resolved=resolved,
                )

        exe_name = self._to_exe_name(resolved)

        # Консольные приложения требуют CREATE_NEW_CONSOLE, иначе окно скрыто
        is_console = exe_name.lower() in APP_CONSOLE_APPS
        creation_flags = subprocess.CREATE_NEW_CONSOLE if is_console else 0

        try:
            proc = subprocess.Popen(
                [resolved],
                shell=False,
                stdout=subprocess.DEVNULL if not is_console else None,
                stderr=subprocess.DEVNULL if not is_console else None,
                creationflags=creation_flags,
            )
            time.sleep(
                settings.app_manager.launch_wait_s
            )  # GUI-процессу нужно время на инициализацию

            # Некоторые лаунчеры запускают дочерний процесс
            # и сразу завершаются — для них proc.poll() == 0, но приложение живо.
            # Считаем успехом если: процесс жив (poll=None) ИЛИ завершился чисто (poll=0).
            poll = proc.poll()
            if poll is not None and poll != 0:
                return self._err(
                    f"'{app_name}' завершился с ошибкой (код {poll}).",
                    app=app_name,
                    resolved=resolved,
                    returncode=poll,
                )

            # Для не-лаунчеров дополнительно проверяем tasklist
            if poll is None and not self._is_process_running(exe_name):
                return self._err(
                    f"'{app_name}' не обнаружен в процессах после запуска.",
                    app=app_name,
                    resolved=resolved,
                )

            return self._ok(
                f"Приложение '{app_name}' запущено.",
                app=app_name,
                resolved=resolved,
                pid=proc.pid,
            )

        except FileNotFoundError:
            return self._err(
                f"Файл '{resolved}' не найден. Проверьте имя приложения.",
                app=app_name,
                resolved=resolved,
            )
        except PermissionError:
            # WinError 5 — требуется UAC-повышение
            return self._launch_elevated(app_name, resolved)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 5:
                return self._launch_elevated(app_name, resolved)
            return self._err(f"Не удалось запустить '{app_name}': {exc}")

    def _launch_elevated(self, app_name: str, resolved: str) -> OperationResult:
        """
        Запуск с UAC-повышением через ShellExecuteW (runas).
        Используется как fallback при WinError 5 (Access denied).
        """
        import ctypes

        logger.info("Запрос UAC-повышения для '%s'...", app_name)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                resolved,
                None,
                None,
                1,  # SW_SHOWNORMAL
            )
            if ret > 32:  # ShellExecute возвращает > 32 при успехе
                return self._ok(
                    f"'{app_name}' запущен с повышенными правами.",
                    app=app_name,
                    resolved=resolved,
                    elevated=True,
                )
            return self._err(
                f"Не удалось запустить '{app_name}' с повышением (код {ret}).",
                app=app_name,
                resolved=resolved,
            )
        except Exception as exc:
            return self._err(f"Ошибка UAC-запуска '{app_name}': {exc}")

    def close_app(self, app_name: str) -> OperationResult:
        """
        Завершить процесс по имени (без расширения .exe).

        Args:
            app_name: Имя процесса (напр. "notepad", "discord").
        """
        code, out, err = self._run(["taskkill", "/IM", f"{app_name}.exe", "/F"])
        if code == 0:
            return self._ok(f"Процесс '{app_name}' завершён.", output=out)
        return self._err(
            f"Не удалось завершить '{app_name}': {err or out}", returncode=code
        )

    def uninstall_app(self, app_name: str) -> OperationResult:
        """
        Удалить установленное приложение.

        Стратегия:
          1. winget uninstall  — тихое удаление без UI
          2. реестр (fallback) — UninstallString для legacy и Steam-игр

        Args:
            app_name: Название приложения (напр. "Telegram").

        Returns:
            OperationResult с полем data["method"] — использованный способ.
        """
        result = self._uninstall_via_winget(app_name)
        if result.status == OperationStatus.SUCCESS:
            self.refresh_registry_cache()
            return result

        logger.warning("winget не справился, пробуем реестр...")
        result = self._uninstall_via_registry(app_name)
        if result.status == OperationStatus.SUCCESS:
            self.refresh_registry_cache()
        return result

    def list_running_apps(self) -> OperationResult:
        """
        Список запущенных процессов.

        Returns:
            OperationResult с полем data["processes"] — отсортированный список имён.
        """
        code, out, err = self._run(["tasklist", "/FO", "CSV", "/NH"])
        if code != 0:
            return self._err(f"Не удалось получить список процессов: {err}")
        processes = sorted(
            {line.split(",")[0].strip('"') for line in out.splitlines() if line.strip()}
        )
        return self._ok(f"Запущено процессов: {len(processes)}.", processes=processes)

    def is_app_running(self, app_name: str) -> OperationResult:
        """
        Проверить, запущено ли приложение.

        Принимает алиас, русское название или имя .exe.

        Args:
            app_name: Алиас или имя процесса (напр. "discord", "дискорд").

        Returns:
            OperationResult с полем data["running"] — bool.
        """
        resolved = self._resolve_app_name(app_name)
        exe_name = self._to_exe_name(resolved)
        running = self._is_process_running(exe_name)
        return self._ok(
            f"'{app_name}' {'запущен' if running else 'не запущен'}.",
            running=running,
            app=app_name,
            resolved=exe_name,
        )


# ---------------------------------------------------------------------------
# Быстрое тестирование
# ---------------------------------------------------------------------------

# am = AppManager()

# print(am.launch_app("блокнот").to_json())
# print(am.launch_app("riot client").to_json())
# print(am.is_app_running("discord").to_json())

# print(am.close_app("notepad").to_json())
# print(am.uninstall_app("VLC media player").to_json())
