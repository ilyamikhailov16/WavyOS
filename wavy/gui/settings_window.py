"""
Settings window for the application.
Reads/writes config.json and validates the structure via Pydantic before saving.
"""

import json
import shutil
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QTabWidget,
    QFileDialog,
    QComboBox,
)
from PySide6.QtCore import Signal, Qt
import logging

from config.settings import Settings

logger = logging.getLogger(__name__)


class SettingsWindow(QWidget):
    """Main settings interface with logically separated tabs."""

    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.config_path = config_path
        self.setWindowTitle("Application Settings")
        self.resize(580, 520)
        self._init_ui()
        self._load_from_file()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # === TAB 1: Script Runner ===
        sr_tab = QWidget()
        sr_layout = QVBoxLayout(sr_tab)
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
        sr_layout.addStretch()
        self.tabs.addTab(sr_tab, "📜 Script Runner")

        # === TAB 2: App Manager ===
        am_tab = QWidget()
        am_layout = QVBoxLayout(am_tab)
        am_group = QGroupBox("App Manager Tuning")
        am_grp_layout = QVBoxLayout()

        self.winget_timeout_edit = QLineEdit()
        self.uninstall_timeout_edit = QLineEdit()
        self.launch_wait_edit = QLineEdit()
        self.subprocess_encoding_edit = QLineEdit()

        am_grp_layout.addWidget(QLabel("Winget Timeout (seconds):"))
        am_grp_layout.addWidget(self.winget_timeout_edit)
        am_grp_layout.addWidget(QLabel("Uninstall Timeout (seconds):"))
        am_grp_layout.addWidget(self.uninstall_timeout_edit)
        am_grp_layout.addWidget(QLabel("Launch Wait Delay (seconds):"))
        am_grp_layout.addWidget(self.launch_wait_edit)
        am_grp_layout.addWidget(QLabel("Subprocess Encoding:"))
        am_grp_layout.addWidget(self.subprocess_encoding_edit)

        am_group.setLayout(am_grp_layout)
        am_layout.addWidget(am_group)
        am_layout.addStretch()
        self.tabs.addTab(am_tab, "📦 App Manager")

        # === TAB 3: Browser ===
        br_tab = QWidget()
        br_layout = QVBoxLayout(br_tab)
        br_group = QGroupBox("Browser Selection")
        br_grp_layout = QVBoxLayout()

        self.browser_choice_combo = QComboBox()
        self.browser_choice_combo.addItems(
            ["default", "yandex", "opera", "chrome", "edge", "custom"]
        )

        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setEnabled(False)
        self.custom_path_browse = QPushButton("📁")
        self.custom_path_browse.setFixedWidth(40)
        self.custom_path_browse.setEnabled(False)

        br_path_layout = QHBoxLayout()
        br_path_layout.addWidget(QLabel("Custom Path:"))
        br_path_layout.addWidget(self.custom_path_edit)
        br_path_layout.addWidget(self.custom_path_browse)

        self.custom_engine_combo = QComboBox()
        self.custom_engine_combo.addItems(["chromium", "firefox"])
        self.custom_engine_combo.setEnabled(False)

        br_engine_layout = QHBoxLayout()
        br_engine_layout.addWidget(QLabel("Engine (for custom):"))
        br_engine_layout.addWidget(self.custom_engine_combo)

        self.custom_preset_combo = QComboBox()
        self.custom_preset_combo.addItems(
            ["", "google", "bing", "yandex", "duckduckgo"]
        )
        self.custom_preset_combo.setEnabled(False)

        br_preset_layout = QHBoxLayout()
        br_preset_layout.addWidget(QLabel("Search Preset (for custom):"))
        br_preset_layout.addWidget(self.custom_preset_combo)

        br_grp_layout.addWidget(QLabel("Default Browser:"))
        br_grp_layout.addWidget(self.browser_choice_combo)
        br_grp_layout.addLayout(br_path_layout)
        br_grp_layout.addLayout(br_engine_layout)
        br_grp_layout.addLayout(br_preset_layout)
        br_group.setLayout(br_grp_layout)
        br_layout.addWidget(br_group)
        br_layout.addStretch()
        self.tabs.addTab(br_tab, "🌐 Browser")

        # === TAB 4: AI & STT ===
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)

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
        ai_layout.addWidget(api_group)

        stt_group = QGroupBox("Speech-to-Text (STT)")
        stt_grp_layout = QVBoxLayout()
        self.stt_language_edit = QLineEdit()
        stt_grp_layout.addWidget(QLabel("Language (ru/en):"))
        stt_grp_layout.addWidget(self.stt_language_edit)
        stt_group.setLayout(stt_grp_layout)
        ai_layout.addWidget(stt_group)
        ai_layout.addStretch()
        self.tabs.addTab(ai_tab, "🤖 AI / STT")

        # === TAB 5: EnergySaver & Screen ===
        sys_tab = QWidget()
        sys_layout = QVBoxLayout(sys_tab)

        es_group = QGroupBox("Energy Saver")
        es_grp_layout = QVBoxLayout()
        self.energy_hz_edit = QLineEdit()
        es_grp_layout.addWidget(QLabel("Target Refresh Rate (Hz) when enabled:"))
        es_grp_layout.addWidget(self.energy_hz_edit)
        es_group.setLayout(es_grp_layout)
        sys_layout.addWidget(es_group)

        st_group = QGroupBox("Screen Tool")
        st_grp_layout = QVBoxLayout()
        self.fps_recording_edit = QLineEdit()
        st_grp_layout.addWidget(QLabel("Recording FPS:"))
        st_grp_layout.addWidget(self.fps_recording_edit)
        st_group.setLayout(st_grp_layout)
        sys_layout.addWidget(st_group)
        sys_layout.addStretch()
        self.tabs.addTab(sys_tab, "⚙️ EnergySaver / Screen")

        # === Action Buttons ===
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("🔄 Reset to Default")
        self.reset_btn.clicked.connect(self._on_reset_config)

        self.save_btn = QPushButton("💾 Save")
        self.cancel_btn = QPushButton("❌ Cancel")
        self.save_btn.clicked.connect(self._save_config)
        self.cancel_btn.clicked.connect(self.hide)

        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # Connect UI logic
        self.script_dir_btn.clicked.connect(self._on_browse_script_dir)
        self.custom_path_browse.clicked.connect(self._on_browse_custom_browser)
        self.browser_choice_combo.currentTextChanged.connect(
            self._on_browser_choice_changed
        )
        self._on_browser_choice_changed(self.browser_choice_combo.currentText())

    # ------------------------------------------------------------------
    # Validation Helpers
    # ------------------------------------------------------------------
    def _validate_path(self, text: str, field_name: str) -> Optional[str]:
        path = text.strip()
        if not path:
            QMessageBox.warning(self, "Input Error", f"{field_name} cannot be empty.")
            return None
        return path

    def _validate_integer(
        self, text: str, field_name: str, min_val: int, max_val: int
    ) -> Optional[int]:
        try:
            val = int(text.strip())
            if not (min_val <= val <= max_val):
                raise ValueError
            return val
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                f"{field_name} must be an integer between {min_val} and {max_val}.",
            )
            return None

    def _validate_float(
        self, text: str, field_name: str, min_val: float, max_val: float
    ) -> Optional[float]:
        try:
            val = float(text.strip())
            if not (min_val <= val <= max_val):
                raise ValueError
            return val
        except ValueError:
            QMessageBox.warning(
                self,
                "Input Error",
                f"{field_name} must be a number between {min_val} and {max_val}.",
            )
            return None

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------
    def _load_from_file(self):
        if not self.config_path.exists():
            QMessageBox.warning(
                self, "Error", f"Configuration file not found: {self.config_path}"
            )
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "config.json is corrupted.")
                return

        # Script Runner
        sr = data.get("script_runner", {})
        self.script_dir_edit.setText(
            str(sr.get("default_script_path") or sr.get("base_dir", "scripts"))
        )
        self.script_timeout_edit.setText(str(sr.get("timeout", 300)))
        self.script_async_cb.setChecked(sr.get("is_async", True))
        self.script_strict_cb.setChecked(sr.get("strict", False))

        # App Manager
        am = data.get("app_manager", {})
        self.winget_timeout_edit.setText(str(am.get("winget_timeout_s", 120)))
        self.uninstall_timeout_edit.setText(str(am.get("uninstall_timeout_s", 120)))
        self.launch_wait_edit.setText(str(am.get("launch_wait_s", 1.0)))
        self.subprocess_encoding_edit.setText(am.get("subprocess_encoding", "utf-8"))

        # Browser
        br = data.get("browser", {})
        self.browser_choice_combo.setCurrentText(br.get("default_choice", "default"))
        self.custom_path_edit.setText(br.get("custom_path", ""))
        self.custom_engine_combo.setCurrentText(br.get("custom_engine", "chromium"))
        self.custom_preset_combo.setCurrentText(br.get("custom_search_preset", ""))
        self._on_browser_choice_changed(self.browser_choice_combo.currentText())

        # AI & STT
        api = data.get("api", {})
        self.api_base_url_edit.setText(
            api.get("base_url", "https://openrouter.ai/api/v1")
        )
        self.api_model_edit.setText(api.get("model", "openrouter/free"))
        self.api_token_edit.setText(api.get("token", ""))
        self.api_use_llm_cb.setChecked(data.get("use_llm_for_stt", False))

        stt = data.get("stt", {})
        self.stt_language_edit.setText(stt.get("language", "ru"))

        # System & Screen
        es = data.get("energy_saver", {})
        self.energy_hz_edit.setText(
            str(es.get("enabled_lower_refresh_rate_hz_edit", 60))
        )

        st = data.get("screen_tool", {})
        self.fps_recording_edit.setText(
            str(st.get("fps") or st.get("fps_recording_edit", 20))
        )

    # ------------------------------------------------------------------
    # Data Saving
    # ------------------------------------------------------------------
    def _save_config(self):
        # Load current config to preserve untouched keys
        current = json.loads(self.config_path.read_text(encoding="utf-8"))

        # 1. Validate Inputs
        dir_path = self._validate_path(self.script_dir_edit.text(), "Scripts Directory")
        if dir_path is None:
            return

        timeout = self._validate_float(
            self.script_timeout_edit.text(), "Script Timeout", 1.0, 3600.0
        )
        if timeout is None:
            return

        winget_to = self._validate_integer(
            self.winget_timeout_edit.text(), "Winget Timeout", 10, 600
        )
        if winget_to is None:
            return

        uninstall_to = self._validate_integer(
            self.uninstall_timeout_edit.text(), "Uninstall Timeout", 10, 600
        )
        if uninstall_to is None:
            return

        launch_wait = self._validate_float(
            self.launch_wait_edit.text(), "Launch Wait", 0.1, 30.0
        )
        if launch_wait is None:
            return

        hz = self._validate_integer(self.energy_hz_edit.text(), "Refresh Rate", 30, 360)
        if hz is None:
            return

        fps = self._validate_float(
            self.fps_recording_edit.text(), "Recording FPS", 10.0, 60.0
        )
        if fps is None:
            return

        lang = self.stt_language_edit.text().strip()
        if not lang:
            QMessageBox.warning(self, "Input Error", "STT language cannot be empty.")
            return

        encoding = self.subprocess_encoding_edit.text().strip()
        if not encoding:
            QMessageBox.warning(
                self, "Input Error", "Subprocess encoding cannot be empty."
            )
            return

        # 2. Build Dict (Pydantic-compatible structure)
        current["script_runner"] = {
            "default_script_path": dir_path,
            "timeout": timeout,
            "is_async": self.script_async_cb.isChecked(),
            "strict": self.script_strict_cb.isChecked(),
        }

        current["app_manager"] = {
            **current.get("app_manager", {}),
            "winget_timeout_s": winget_to,
            "uninstall_timeout_s": uninstall_to,
            "launch_wait_s": launch_wait,
            "subprocess_encoding": encoding,
        }

        current["browser"] = {
            **current.get("browser", {}),
            "default_choice": self.browser_choice_combo.currentText(),
            "custom_path": (
                self.custom_path_edit.text().strip()
                if self.browser_choice_combo.currentText() == "custom"
                else ""
            ),
            "custom_engine": (
                self.custom_engine_combo.currentText()
                if self.browser_choice_combo.currentText() == "custom"
                else "chromium"
            ),
            "custom_search_preset": (
                self.custom_preset_combo.currentText()
                if self.browser_choice_combo.currentText() == "custom"
                else ""
            ),
        }

        current["api"] = {
            "base_url": self.api_base_url_edit.text().strip(),
            "model": self.api_model_edit.text().strip(),
            "token": self.api_token_edit.text().strip(),
        }
        current["use_llm_for_stt"] = self.api_use_llm_cb.isChecked()
        current.setdefault("stt", {})
        current["stt"]["language"] = lang

        current.setdefault("energy_saver", {})
        current["energy_saver"]["enabled_lower_refresh_rate_hz_edit"] = hz

        current.setdefault("screen_tool", {})
        current["screen_tool"]["fps"] = fps

        # 3. Pydantic Validation
        try:
            Settings.model_validate(current)
        except Exception as e:
            QMessageBox.critical(
                self, "Validation Error", f"Invalid configuration:\n{str(e)}"
            )
            return

        # 4. Write
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        QMessageBox.information(
            self,
            "Saved",
            "Settings saved successfully.\n"
            "Changes will take effect after restarting the application.",
        )
        self.hide()

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------
    def _on_reset_config(self):
        default_path = Path(__file__).parent / "default_config.json"
        if not default_path.exists():
            QMessageBox.critical(
                self, "Error", "default_config.json not found in settings folder."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Reset all settings to default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            shutil.copy2(default_path, self.config_path)
            QMessageBox.information(
                self, "Success", "Config reset. UI updated. Restart recommended."
            )
            self._load_from_file()

    def _on_browse_script_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Scripts Directory")
        if path:
            self.script_dir_edit.setText(path)

    def _on_browse_custom_browser(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Browser Executable",
            "",
            "Executable Files (*.exe);;All Files (*)",
        )
        if path:
            self.custom_path_edit.setText(path)

    def _on_browser_choice_changed(self, choice: str):
        is_custom = choice == "custom"
        self.custom_path_edit.setEnabled(is_custom)
        self.custom_path_browse.setEnabled(is_custom)
        self.custom_engine_combo.setEnabled(is_custom)
        self.custom_preset_combo.setEnabled(is_custom)
        if not is_custom:
            self.custom_path_edit.clear()

    def closeEvent(self, event):
        """Intercept window close (X button) → just hide, don't destroy or shutdown."""
        event.ignore()
        self.hide()
