import json
import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QInputDialog, QMessageBox,
)

from glslViewer_config import PRESETS_DIR


def _preset_path(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in " -_.").strip()
    return os.path.join(PRESETS_DIR, f"{safe}.json")


def list_presets() -> list[str]:
    if not os.path.isdir(PRESETS_DIR):
        return []
    names = []
    for f in sorted(os.listdir(PRESETS_DIR)):
        if f.endswith(".json"):
            names.append(f[:-5])
    return names


def load_preset(name: str) -> dict:
    path = _preset_path(name)
    with open(path) as f:
        return json.load(f)


def save_preset(name: str, data: dict) -> None:
    path = _preset_path(name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def delete_preset(name: str) -> None:
    path = _preset_path(name)
    if os.path.exists(path):
        os.remove(path)


class PresetPanel(QDockWidget):
    preset_loaded = pyqtSignal(str, dict)
    preset_saved = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Presets", parent)
        self.setObjectName("PresetPanel")
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_load)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        self._save_btn = QPushButton("Save Current")
        self._save_btn.clicked.connect(self._on_save)
        self._load_btn = QPushButton("Load")
        self._load_btn.clicked.connect(self._on_load)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        self._rename_btn = QPushButton("Rename")
        self._rename_btn.clicked.connect(self._on_rename)

        btns.addWidget(self._save_btn)
        btns.addWidget(self._load_btn)
        btns.addWidget(self._delete_btn)
        btns.addWidget(self._rename_btn)
        layout.addLayout(btns)

        self.setWidget(outer)
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        for name in list_presets():
            self._list.addItem(name)

    def _on_save(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        self.preset_saved.emit(name)
        self.refresh()

    def _on_load(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        name = item.text()
        try:
            data = load_preset(name)
            self.preset_loaded.emit(name, data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load preset: {e}")

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_preset(name)
            self.refresh()

    def _on_rename(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, "Rename Preset", "New name:", text=old_name
        )
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        try:
            data = load_preset(old_name)
            save_preset(new_name, data)
            delete_preset(old_name)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename preset: {e}")
