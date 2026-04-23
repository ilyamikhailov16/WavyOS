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

from .aliases import transliterate

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class OperationStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OperationResult:
    """Unified response for every method — convenient for LLM parsing."""

    status: OperationStatus
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "message": self.message, "data": self.data}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Removes spaces, dashes, underscores for fuzzy matching.
    "counter-strike 2" → "counterstrike2", "counter strike" → "counterstrike"
    """
    return _re.sub(r"[\s\-_.]", "", text.lower())


def _word_match(key: str, name: str) -> bool:
    """True if key appears as a separate word (or prefix of a word) in name."""
    return bool(_re.search(r"\b" + _re.escape(key), name))


class AppManager:
    """
    Application management: launch, close, uninstall, process listing.

    On initialization, reads the registry once and builds two caches:
      _exe_cache:       display_name.lower() → absolute path to .exe
      _uninstall_cache: display_name.lower() → UninstallString

    All subsequent requests work via dictionary O(1) without registry access.
    Each public method returns :class:`OperationResult`.
    """

    def __init__(self) -> None:
        self._exe_cache: dict[str, str] = {}
        self._uninstall_cache: dict[str, str] = {}
        self._exe_norm: dict[str, str] = {}
        self._uninstall_norm: dict[str, str] = {}
        self._build_registry_cache()

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _ok(self, message: str, **data: Any) -> OperationResult:
        logger.info(message)
        return OperationResult(OperationStatus.SUCCESS, message, data)

    def _err(self, message: str, **data: Any) -> OperationResult:
        logger.error(message)
        return OperationResult(OperationStatus.ERROR, message, data)

    def _run(self, cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
        """
        Executes a command, returns (returncode, stdout, stderr).
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
                    f"Timeout ({timeout}s): {' '.join(cmd)}",
                )
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"

    @staticmethod
    def _to_exe_name(resolved: str) -> str:
        """Returns .exe name without path — for tasklist lookup."""
        name = Path(resolved).name
        return name if name.lower().endswith(".exe") else f"{name}.exe"

    def _is_process_running(self, exe_name: str) -> bool:
        """Checks process presence via tasklist /FI."""
        code, out, _ = self._run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV", "/NH"]
        )
        return code == 0 and exe_name.lower() in out.lower()

    # ------------------------------------------------------------------
    # Registry cache
    # ------------------------------------------------------------------

    def _build_registry_cache(self) -> None:
        """
        Reads Windows registry once, fills _exe_cache and _uninstall_cache.
        Called on initialization and after uninstall_app().
        """
        try:
            import winreg
        except ImportError:
            logger.warning("winreg not available — registry cache not built.")
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
            """Root folder, then one level deeper (Squirrel: app-X.Y.Z/)."""
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

                    # Path to .exe → _exe_cache
                    if name_key in self._exe_cache:
                        continue

                    exe_found: str | None = None

                    # DisplayIcon — most reliable source of path
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

                    # InstallLocation — fallback with subfolder search
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
            "Registry cache: %d apps for launch, %d for uninstall.",
            exe_count,
            uninstall_count,
        )

    def refresh_registry_cache(self) -> OperationResult:
        """
        Refresh registry cache. Call after installing/uninstalling apps.
        Available to AI agent as a separate tool.
        """
        self._exe_cache.clear()
        self._uninstall_cache.clear()
        self._exe_norm.clear()
        self._uninstall_norm.clear()
        self._build_registry_cache()
        return self._ok(
            f"Registry cache refreshed: {len(self._exe_cache)} apps.",
            exe_count=len(self._exe_cache),
            uninstall_count=len(self._uninstall_cache),
        )

    def _lookup_exe(self, app_name: str) -> str | None:
        """
        Search for .exe path in cache.
        Order: exact → normalized → transliteration → word-boundary → substring.
        """
        key = app_name.lower()

        # 1. Exact
        if key in self._exe_cache:
            return self._exe_cache[key]

        # 2. Normalized (removes dashes/spaces)
        norm = _normalize(key)
        for n_key, exe in self._exe_norm.items():
            if norm == n_key or norm in n_key:
                logger.info("Found in cache (normalized): '%s' → %s", n_key, exe)
                return exe

        # 3. Transliteration → try as normalized
        translit = _normalize(transliterate(key))
        if translit != norm:
            for n_key, exe in self._exe_norm.items():
                if translit == n_key or translit in n_key:
                    logger.info(
                        "Found in cache (translit '%s'): '%s' → %s",
                        translit,
                        n_key,
                        exe,
                    )
                    return exe

        # 4. Word-boundary → choose closest by length
        candidates = [(n, e) for n, e in self._exe_cache.items() if _word_match(key, n)]
        if not candidates:
            candidates = [(n, e) for n, e in self._exe_cache.items() if key in n]
        if candidates:
            best_name, best_exe = min(
                candidates, key=lambda t: abs(len(t[0]) - len(key))
            )
            logger.info("Found in cache (word): '%s' → %s", best_name, best_exe)
            return best_exe

        return None

    def _lookup_uninstall_str(self, app_name: str) -> str | None:
        """Search for UninstallString. Same priority as _lookup_exe."""
        key = app_name.lower()

        if key in self._uninstall_cache:
            return self._uninstall_cache[key]

        norm = _normalize(key)
        for n_key, us in self._uninstall_norm.items():
            if norm == n_key or norm in n_key:
                logger.info("Found UninstallString (normalized): '%s'", n_key)
                return us

        translit = _normalize(transliterate(key))
        if translit != norm:
            for n_key, us in self._uninstall_norm.items():
                if translit == n_key or translit in n_key:
                    logger.info(
                        "Found UninstallString (translit '%s'): '%s'", translit, n_key
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
            logger.info("Found UninstallString (word): '%s'", best_name)
            return best_us

        return None

    def _resolve_app_name(self, app_name: str) -> str:
        """
        Resolves name/alias into executable path or URI.

        Priority:
          1. protocol_aliases — URI protocols (ms-settings:, epic://, …)
          2. special_launch   — special launch logic (Roblox, steam://)
          3. app_aliases      — system utilities (notepad, calc, …)
          4. name_aliases     — localized alias → DisplayName → registry cache
          5. Registry cache   — normalized + translit + word-boundary
          6. known_paths      — known paths outside registry
          7. Fallback         — return as-is
        """
        key = app_name.lower()
        am = settings.app_manager

        if uri := am.protocol_aliases.get(key):
            return uri

        if special := am.special_launch.get(key):
            exe_template, _args = special
            if exe_template.startswith("steam://"):
                return exe_template
            expanded = os.path.expandvars(exe_template)
            if Path(expanded).exists():
                return expanded

        if alias := am.app_aliases.get(key):
            return alias

        registry_name = am.name_aliases.get(key, app_name)
        if exe := self._lookup_exe(registry_name):
            return exe

        for path_str in settings.app_manager.known_paths.get(key, []):
            expanded = os.path.expandvars(path_str)
            if Path(expanded).exists():
                logger.info("Found via known path: %s", expanded)
                return expanded

        return app_name

    # ------------------------------------------------------------------
    # Uninstall: internal logic
    # ------------------------------------------------------------------

    def _uninstall_via_winget(self, app_name: str) -> OperationResult:
        """Uninstall via winget (Win 10+)."""
        logger.info("Attempting to uninstall '%s' via winget...", app_name)
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

        # Timeout → launcher opened confirmation dialog
        if "таймаут" in err.lower():
            return self._err(
                f"Uninstalling '{app_name}' requires confirmation in a launcher. "
                "Confirm in the opened window.",
                method="winget",
                reason="launcher_confirmation_required",
            )

        if code != 0:
            return self._err(
                f"winget failed to uninstall '{app_name}': {err or out}",
                method="winget",
                returncode=code,
            )

        # Check: still in registry → uninstall not finished
        uninstall_str = self._lookup_uninstall_str(app_name)
        if uninstall_str is not None:
            if "steam://" in uninstall_str.lower():
                logger.info("Steam app — delegating to registry handler.")
                return self._uninstall_via_registry(app_name, uninstall_str)
            return self._err(
                f"'{app_name}' still present in registry — uninstall not completed. "
                "Launcher confirmation may be required.",
                method="winget",
                reason="launcher_confirmation_required",
            )

        return self._ok(
            f"'{app_name}' successfully uninstalled.", method="winget", output=out
        )

    def _uninstall_via_registry(
        self, app_name: str, uninstall_str: str | None = None
    ) -> OperationResult:
        """
        Fallback: uninstall via UninstallString from registry.

        Args:
            uninstall_str: Passed from _uninstall_via_winget to avoid re-lookup.
        """
        logger.info("Attempting to uninstall '%s' via registry...", app_name)

        uninstall_str = uninstall_str or self._lookup_uninstall_str(app_name)
        if not uninstall_str:
            return self._err(
                f"'{app_name}' not found. It may not be installed.",
                method="registry",
            )

        # Steam: URI handled by Windows protocol handler
        if "steam://" in uninstall_str.lower():
            steam_uri = next(
                (p for p in uninstall_str.split() if p.startswith("steam://")), None
            )
            if not steam_uri:
                return self._err(
                    f"Failed to extract steam:// URI from: {uninstall_str}",
                    method="registry",
                )
            try:
                os.startfile(steam_uri)
                return self._ok(
                    f"Uninstall request for '{app_name}' sent to Steam. "
                    "Confirm in the opened window.",
                    method="registry",
                    reason="launcher_confirmation_required",
                    steam_uri=steam_uri,
                )
            except OSError as exc:
                return self._err(f"Failed to open Steam: {exc}", method="registry")

        # Parse command — shlex handles quoted paths
        try:
            cmd = [c.strip('"') for c in shlex.split(uninstall_str, posix=False)]
        except ValueError:
            cmd = uninstall_str.split()

        exe_path = Path(cmd[0])
        if not exe_path.exists():
            return self._err(
                f"File '{exe_path}' not found — registry entry is stale. "
                "Remove it via Apps → Installed Apps.",
                method="registry",
                reason="ghost_registry_entry",
                uninstall_path=str(exe_path),
            )

        # Silent uninstall flags by installer type
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
            return self._ok(
                f"'{app_name}' uninstalled via registry.", method="registry"
            )
        return self._err(
            f"Error uninstalling '{app_name}': {err or out}",
            method="registry",
            returncode=code,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def launch_app(self, app_name: str) -> OperationResult:
        """
        Launch an application by name, alias, or full path.

        Supports:
          - Localized aliases ("дискорд", "блокнот")
          - URI protocols ("ms-settings:", "com.epicgames.launcher://")
          - Console apps (cmd, powershell) with visible window

        Args:
            app_name: Name, alias, or path (e.g. "discord", "notepad", "settings").

        Returns:
            OperationResult with fields data["resolved"] and data["pid"].
        """
        resolved = self._resolve_app_name(app_name)

        # URI protocol (ms-settings:, com.epicgames.launcher://, …) — only via startfile
        if "://" in resolved or resolved.endswith(":"):
            try:
                os.startfile(resolved)
                return self._ok(
                    f"'{app_name}' launched via system handler.",
                    app=app_name,
                    resolved=resolved,
                )
            except OSError as exc:
                return self._err(
                    f"Failed to open '{app_name}' via URI: {exc}",
                    app=app_name,
                    resolved=resolved,
                )

        exe_name = self._to_exe_name(resolved)

        # Console apps require CREATE_NEW_CONSOLE, otherwise window is hidden
        is_console = exe_name.lower() in settings.app_manager.console_apps
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
            )  # GUI process needs time to initialize

            # Some launchers spawn a child process and exit immediately
            # so proc.poll() == 0 but the app is actually running.
            # Consider success if: process is alive (poll=None) OR exited cleanly (poll=0).
            poll = proc.poll()
            if poll is not None and poll != 0:
                return self._err(
                    f"'{app_name}' exited with error (code {poll}).",
                    app=app_name,
                    resolved=resolved,
                    returncode=poll,
                )

            # For non-launchers additionally check tasklist
            if poll is None and not self._is_process_running(exe_name):
                return self._err(
                    f"'{app_name}' not found in process list after launch.",
                    app=app_name,
                    resolved=resolved,
                )

            return self._ok(
                f"Application '{app_name}' launched.",
                app=app_name,
                resolved=resolved,
                pid=proc.pid,
            )

        except FileNotFoundError:
            return self._err(
                f"File '{resolved}' not found. Check application name.",
                app=app_name,
                resolved=resolved,
            )
        except PermissionError:
            # WinError 5 — requires UAC elevation
            return self._launch_elevated(app_name, resolved)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 5:
                return self._launch_elevated(app_name, resolved)
            return self._err(f"Failed to launch '{app_name}': {exc}")

    def _launch_elevated(self, app_name: str, resolved: str) -> OperationResult:
        """
        Launch with UAC elevation via ShellExecuteW (runas).
        Used as fallback on WinError 5 (Access denied).
        """
        import ctypes

        logger.info("Requesting UAC elevation for '%s'...", app_name)
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                resolved,
                None,
                None,
                1,  # SW_SHOWNORMAL
            )
            if ret > 32:  # ShellExecute returns > 32 on success
                return self._ok(
                    f"'{app_name}' launched with elevated privileges.",
                    app=app_name,
                    resolved=resolved,
                    elevated=True,
                )
            return self._err(
                f"Failed to launch '{app_name}' with elevation (code {ret}).",
                app=app_name,
                resolved=resolved,
            )
        except Exception as exc:
            return self._err(f"UAC launch error for '{app_name}': {exc}")

    def close_app(self, app_name: str) -> OperationResult:
        """
        Terminate a process by name or alias (without .exe extension).

        Args:
            app_name: Process name (e.g. "notepad", "discord").
        """
        resolved = self._resolve_app_name(app_name)

        code, out, err = self._run(["taskkill", "/IM", f"{resolved}", "/F"])
        if code == 0:
            return self._ok(f"Process '{resolved}' terminated.", output=out)
        return self._err(
            f"Failed to terminate '{resolved}': {err or out}", returncode=code
        )

    def uninstall_app(self, app_name: str) -> OperationResult:
        """
        Uninstall an installed application.

        Strategy:
          1. winget uninstall  — silent uninstall without UI
          2. registry (fallback) — UninstallString for legacy and Steam apps

        Args:
            app_name: Application name (e.g. "Telegram").

        Returns:
            OperationResult with data["method"] — method used.
        """
        result = self._uninstall_via_winget(app_name)
        if result.status == OperationStatus.SUCCESS:
            self.refresh_registry_cache()
            return result

        logger.warning("winget failed, trying registry...")
        result = self._uninstall_via_registry(app_name)
        if result.status == OperationStatus.SUCCESS:
            self.refresh_registry_cache()
        return result

    def list_running_apps(self) -> OperationResult:
        """
        List of running processes.

        Returns:
            OperationResult with data["processes"] — sorted list of names.
        """
        code, out, err = self._run(["tasklist", "/FO", "CSV", "/NH"])
        if code != 0:
            return self._err(f"Failed to get process list: {err}")
        processes = sorted(
            {line.split(",")[0].strip('"') for line in out.splitlines() if line.strip()}
        )
        return self._ok(f"Running processes: {len(processes)}.", processes=processes)

    def is_app_running(self, app_name: str) -> OperationResult:
        """
        Check if an application is running.

        Accepts alias, localized name, or .exe name.

        Args:
            app_name: Alias or process name (e.g. "discord").

        Returns:
            OperationResult with data["running"] — bool.
        """
        resolved = self._resolve_app_name(app_name)
        exe_name = self._to_exe_name(resolved)
        running = self._is_process_running(exe_name)
        return self._ok(
            f"'{app_name}' {'is running' if running else 'is not running'}.",
            running=running,
            app=app_name,
            resolved=exe_name,
        )


# ---------------------------------------------------------------------------
# Quick testing
# ---------------------------------------------------------------------------

# am = AppManager()

# print(am.launch_app("блокнот").to_json())
# print(am.launch_app("riot client").to_json())
# print(am.is_app_running("discord").to_json())

# print(am.close_app("блокнот").to_json())
# print(am.uninstall_app("VLC media player").to_json())
