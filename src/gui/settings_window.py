# Окно настроек. Читает/пишет config.json, валидирует через Pydantic.

import json
import sys
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QCheckBox, QPushButton, QMessageBox, QGroupBox)
from PySide6.QtCore import Signal
import logging

# Импортируем модель только для валидации, не используем runtime settings
from config.settings import Settings

logger = logging.getLogger(__name__)

class SettingsWindow(QWidget):
    shutdown_requested = Signal()
    def __init__(self, config_path: Path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("Настройки приложения")
        self.resize(400, 350)

        self._init_ui()
        self._load_from_file()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        # --- LLM блок ---
        llm_group = QGroupBox("LLM / API")
        llm_layout = QVBoxLayout()

        self.base_url_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.use_llm_cb = QCheckBox("Использовать LLM для обработки речи")

        llm_layout.addWidget(QLabel("Base URL:"))
        llm_layout.addWidget(self.base_url_edit)
        llm_layout.addWidget(QLabel("Model:"))
        llm_layout.addWidget(self.model_edit)
        llm_layout.addWidget(QLabel("API Token:"))
        llm_layout.addWidget(self.token_edit)
        llm_layout.addWidget(self.use_llm_cb)
        llm_group.setLayout(llm_layout)
        main_layout.addWidget(llm_group)

        # --- STT блок ---
        stt_group = QGroupBox("STT (Распознавание)")
        stt_layout = QVBoxLayout()

        self.language_edit = QLineEdit()
        self.use_llm_cb.setChecked(True) # по умолчанию True, переопределим при загрузке

        stt_layout.addWidget(QLabel("Язык (ru/en):"))
        stt_layout.addWidget(self.language_edit)
        stt_group.setLayout(stt_layout)
        main_layout.addWidget(stt_group)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить и перезапустить")
        self.cancel_btn = QPushButton("Отмена")

        self.save_btn.clicked.connect(self._save_and_restart)
        self.cancel_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def _load_from_file(self):
        """Читает JSON и заполняет UI. Безопасно для frozen-моделей."""
        if not self.config_path.exists():
            QMessageBox.warning(self, "Ошибка", f"Файл настроек не найден: {self.config_path}")
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Ошибка", "config.json повреждён")
                return

        api = data.get("api", {})
        self.base_url_edit.setText(api.get("base_url", ""))
        self.model_edit.setText(api.get("model", ""))
        self.token_edit.setText(api.get("token", ""))
        self.use_llm_cb.setChecked(data.get("use_llm_for_stt", False))
        self.language_edit.setText(data.get("stt", {}).get("language", "ru"))

    def _save_and_restart(self):
        """Собирает данные, валидирует, пишет файл, закрывает приложение."""
        current = json.loads(self.config_path.read_text(encoding="utf-8"))

        # Обновляем только те поля, которые редактируем
        current["api"] = current.get("api", {})
        current["api"]["base_url"] = self.base_url_edit.text().strip()
        current["api"]["model"] = self.model_edit.text().strip()
        current["api"]["token"] = self.token_edit.text().strip()
        current["use_llm_for_stt"] = self.use_llm_cb.isChecked()

        current.setdefault("stt", {})
        current["stt"]["language"] = self.language_edit.text().strip()

        # Валидация через Pydantic
        try:
            Settings.model_validate(current)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка валидации", f"Некорректные данные:\n{str(e)}")
            return

        # Запись
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

        QMessageBox.information(self, "Успех", "Настройки сохранены. Перезапустите приложение для применения.")
        self.close()

        self.shutdown_requested.emit()