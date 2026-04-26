"""
Settings window for the application.
Reads/writes config.json and validates the structure via Pydantic before saving.
"""
import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QMessageBox, QGroupBox, QTabWidget, QFileDialog
)
from PySide6.QtCore import Signal
import logging

from config.settings import Settings

logger = logging.getLogger(__name__)


class SettingsWindow(QWidget):
    """Main settings interface with tabbed layout."""
    shutdown_requested = Signal()

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("Application Settings")
        self.resize(520, 480)
        self._init_ui()
        self._load_from_file()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _init_ui(self):
        """Builds the tabbed interface and connects widgets."""
        main_layout = QVBoxLayout(self)

        # Main tabs container
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # ==================== TAB 1: Script Runner ====================
        sr_tab = QWidget()
        sr_layout = QVBoxLayout(sr_tab)

        # Group 1: Script Execution
        sr_group = QGroupBox("Script Execution")
        sr_grp_layout = QVBoxLayout()
        self.script_dir_edit = QLineEdit()
        self.script_dir_btn = QPushButton("Browse...")
        self.script_dir_btn.setFixedWidth(80)
        dir_hbox = QHBoxLayout()
        dir_hbox.addWidget(self.script_dir_edit)
        dir_hbox.addWidget(self.script_dir_btn)

        self.script_timeout_edit = QLineEdit()
        self.script_async_cb = QCheckBox("Run scripts asynchronously")
        self.script_strict_cb = QCheckBox("Strict error checking")

        sr_grp_layout.addWidget(QLabel("Scripts Directory:"))
        sr_grp_layout.addLayout(dir_hbox)
        sr_grp_layout.addWidget(QLabel("Execution Timeout (seconds):"))
        sr_grp_layout.addWidget(self.script_timeout_edit)
        sr_grp_layout.addWidget(self.script_async_cb)
        sr_grp_layout.addWidget(self.script_strict_cb)
        sr_group.setLayout(sr_grp_layout)
        sr_layout.addWidget(sr_group)

        # Group 2: Energy Saver
        es_group = QGroupBox("Energy Saver")
        es_grp_layout = QVBoxLayout()
        self.energy_hz_edit = QLineEdit()
        es_grp_layout.addWidget(QLabel("Target Refresh Rate (Hz) when enabled:"))
        es_grp_layout.addWidget(self.energy_hz_edit)
        es_group.setLayout(es_grp_layout)
        sr_layout.addWidget(es_group)

        # Group 3: Screen Tool
        st_group = QGroupBox("Screen Tool")
        st_grp_layout = QVBoxLayout()
        self.fps_recording_edit = QLineEdit()
        st_grp_layout.addWidget(QLabel("Target fps recording"))
        st_grp_layout.addWidget(self.fps_recording_edit)
        st_group.setLayout(st_grp_layout)
        sr_layout.addWidget(st_group)

        self.tabs.addTab(sr_tab, "Script Runner")

        # ==================== TAB 2: App Manager ====================
        am_tab = QWidget()
        am_layout = QVBoxLayout(am_tab)

        # Group 1: API / LLM
        api_group = QGroupBox("API / LLM")
        api_grp_layout = QVBoxLayout()
        self.api_base_url_edit = QLineEdit()
        self.api_model_edit = QLineEdit()
        self.api_token_edit = QLineEdit()
        self.api_token_edit.setEchoMode(QLineEdit.Password)
        self.api_use_llm_cb = QCheckBox("Use LLM for speech processing")

        api_grp_layout.addWidget(QLabel("Base URL:"))
        api_grp_layout.addWidget(self.api_base_url_edit)
        api_grp_layout.addWidget(QLabel("Model:"))
        api_grp_layout.addWidget(self.api_model_edit)
        api_grp_layout.addWidget(QLabel("API Token:"))
        api_grp_layout.addWidget(self.api_token_edit)
        api_grp_layout.addWidget(self.api_use_llm_cb)
        api_group.setLayout(api_grp_layout)
        am_layout.addWidget(api_group)

        # Group 2: STT
        stt_group = QGroupBox("STT")
        stt_grp_layout = QVBoxLayout()
        self.stt_language_edit = QLineEdit()
        stt_grp_layout.addWidget(QLabel("Language (ru/en):"))
        stt_grp_layout.addWidget(self.stt_language_edit)
        stt_group.setLayout(stt_grp_layout)
        am_layout.addWidget(stt_group)

        self.tabs.addTab(am_tab, "App Manager")

        # ==================== Action Buttons ====================
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save & Restart")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self._save_and_restart)
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # Connect directory picker
        self.script_dir_btn.clicked.connect(self._on_browse_script_dir)

    # ------------------------------------------------------------------
    # Validation Helpers
    # ------------------------------------------------------------------
    def _validate_path(self, text: str, field_name: str) -> Optional[str]:
        """Validates non-empty path string."""
        path = text.strip()
        if not path:
            QMessageBox.warning(self, "Input Error", f"{field_name} cannot be empty.")
            return None
        return path

    def _validate_integer(self, text: str, field_name: str, min_val: int, max_val: int) -> Optional[int]:
        """Validates integer within a specific range."""
        try:
            val = int(text.strip())
            if not (min_val <= val <= max_val):
                raise ValueError
            return val
        except ValueError:
            QMessageBox.warning(self, "Input Error", f"{field_name} must be an integer between {min_val} and {max_val}.")
            return None

    def _validate_float(self, text: str, field_name: str, min_val: float, max_val: float) -> Optional[float]:
        """Validates float within a specific range."""
        try:
            val = float(text.strip())
            if not (min_val <= val <= max_val):
                raise ValueError
            return val
        except ValueError:
            QMessageBox.warning(self, "Input Error", f"{field_name} must be a number between {min_val} and {max_val}.")
            return None

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------
    def _load_from_file(self):
        """Reads config.json and populates UI widgets safely."""
        if not self.config_path.exists():
            QMessageBox.warning(self, "Error", f"Configuration file not found: {self.config_path}")
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "config.json is corrupted.")
                return

        # API / LLM
        api = data.get("api", {})
        self.api_base_url_edit.setText(api.get("base_url", ""))
        self.api_model_edit.setText(api.get("model", ""))
        self.api_token_edit.setText(api.get("token", ""))
        self.api_use_llm_cb.setChecked(data.get("use_llm_for_stt", False))

        # STT
        stt = data.get("stt", {})
        self.stt_language_edit.setText(stt.get("language", "ru"))

        # Script Runner
        sr = data.get("script_runner", {})
        # Fallback to 'base_dir' for backward compatibility with old configs
        self.script_dir_edit.setText(str(sr.get("default_script_path") or sr.get("base_dir", "scripts")))
        self.script_timeout_edit.setText(str(sr.get("timeout", 300)))
        self.script_async_cb.setChecked(sr.get("is_async", True))
        self.script_strict_cb.setChecked(sr.get("strict", False))

        # Energy Saver (matches nested Pydantic structure)
        es = data.get("energy_saver", {})
        power = es.get("power", {})
        self.energy_hz_edit.setText(str(power.get("enabled_lower_refresh_rate_hz", 60)))

        # Screen Tool
        st = data.get("screen_tool", {})
        self.fps_recording_edit.setText(str(st.get('fps_recording_edit',20)))


    # ------------------------------------------------------------------
    # Data Saving
    # ------------------------------------------------------------------
    def _save_and_restart(self):
        """Collects inputs, validates, writes to config.json, and triggers restart."""
        current = json.loads(self.config_path.read_text(encoding="utf-8"))

        # 1. Validate all inputs first
        dir_path = self._validate_path(self.script_dir_edit.text(), "Scripts Directory")
        if dir_path is None: return

        timeout = self._validate_float(self.script_timeout_edit.text(), "Execution Timeout", 1.0, 3600.0)
        if timeout is None: return

        hz = self._validate_integer(self.energy_hz_edit.text(), "Refresh Rate", 30, 360)
        if hz is None: return

        lang = self.stt_language_edit.text().strip()
        if not lang:
            QMessageBox.warning(self, "Input Error", "STT language cannot be empty.")
            return

        # 2. Collect clean values
        base_url = self.api_base_url_edit.text().strip()
        model = self.api_model_edit.text().strip()
        token = self.api_token_edit.text().strip()
        use_llm = self.api_use_llm_cb.isChecked()
        is_async = self.script_async_cb.isChecked()
        strict = self.script_strict_cb.isChecked()
        fps_recording = self.fps_recording_edit.text().strip()

        # 3. Merge into dict (preserves untouched keys)
        current["api"] = current.get("api", {})
        current["api"]["base_url"] = base_url
        current["api"]["model"] = model
        current["api"]["token"] = token
        current["use_llm_for_stt"] = use_llm

        current.setdefault("stt", {})
        current["stt"]["language"] = lang

        current.setdefault("script_runner", {})
        current["script_runner"]["default_script_path"] = dir_path  # Matches Pydantic field name
        current["script_runner"]["timeout"] = timeout
        current["script_runner"]["is_async"] = is_async
        current["script_runner"]["strict"] = strict

        current.setdefault("energy_saver", {})
        current["energy_saver"].setdefault("power", {})
        current["energy_saver"]["power"]["enabled_lower_refresh_rate_hz"] = hz

        current.setdefault("screen_tool", {})
        current["screen_tool"]["fps_recording_edit"] = fps_recording

        # 4. Structural validation
        try:
            Settings.model_validate(current)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Invalid configuration:\n{str(e)}")
            return

        # 5. Write to disk
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        QMessageBox.information(self, "Success", "Settings saved. The application will restart.")
        self.close()
        self.shutdown_requested.emit()

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------
    def _on_browse_script_dir(self):
        """Opens system dialog to select a folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Scripts Directory")
        if path:
            self.script_dir_edit.setText(path)
