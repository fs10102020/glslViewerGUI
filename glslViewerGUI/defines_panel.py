from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QGroupBox, QLabel, QMessageBox,
)


class DefinesPanel(QWidget):
    define_requested = Signal(str, str)
    undefine_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DefinesPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        form = QHBoxLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("NAME")
        self._value = QLineEdit()
        self._value.setPlaceholderText("optional value")
        self._add_btn = QPushButton("Define")
        self._add_btn.setMaximumWidth(90)
        self._add_btn.clicked.connect(self._on_define)
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setMaximumWidth(90)
        self._remove_btn.clicked.connect(self._on_remove)

        form.addWidget(self._name)
        form.addWidget(self._value)
        form.addWidget(self._add_btn)
        form.addWidget(self._remove_btn)
        layout.addLayout(form)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_selected)
        layout.addWidget(self._list)

        quick_group = QGroupBox("Safe Quick Presets")
        quick_layout = QHBoxLayout(quick_group)
        for label, cmd_name, cmd_val in [
            ("AA", "AA", "2"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, _n=cmd_name, _v=cmd_val: self._on_quick(_n, _v))
            quick_layout.addWidget(btn)
        note = QLabel("Backend buffer defines are source-driven and not set globally.")
        note.setWordWrap(True)
        quick_layout.addWidget(note)
        layout.addWidget(quick_group)

        self._entries: dict[str, str] = {}

    def _on_define(self) -> None:
        name = self._name.text().strip()
        if not name:
            return
        value = self._value.text().strip()
        self._entries[name] = value
        if value:
            self.define_requested.emit(name, value)
            label = f"{name}={value}"
        else:
            self.define_requested.emit(name, "")
            label = name
        self._replace_or_add(label, name)

    def _on_quick(self, name: str, value: str) -> None:
        self._entries[name] = value
        if value:
            self.define_requested.emit(name, value)
            label = f"{name}={value}"
        else:
            self.define_requested.emit(name, "")
            label = name
        self._replace_or_add(label, name)

    def _replace_or_add(self, label: str, name: str) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            text = item.text()
            existing = text.split("=")[0] if "=" in text else text
            if existing == name:
                self._list.takeItem(i)
                break
        self._list.addItem(label)

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        text = item.text()
        name = text.split("=")[0] if "=" in text else text
        self.undefine_requested.emit(name)
        self._entries.pop(name, None)
        self._list.takeItem(self._list.row(item))

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        text = item.text()
        if "=" in text:
            name, value = text.split("=", 1)
            self._name.setText(name)
            self._value.setText(value)
        else:
            self._name.setText(text)
            self._value.clear()

    def set_defines(self, defines: dict[str, str]) -> None:
        self._list.clear()
        self._entries = dict(defines)
        for name, value in defines.items():
            label = f"{name}={value}" if value else name
            self._list.addItem(label)

    def clear(self) -> None:
        self._list.clear()
        self._entries.clear()
