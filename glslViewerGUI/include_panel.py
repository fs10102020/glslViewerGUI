from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QFileDialog, QGroupBox,
)


class IncludePanel(QWidget):
    include_added = Signal(str)
    include_removed = Signal(str)
    restart_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("IncludePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._list = QListWidget()
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        add_btn = QPushButton("Add Folder")
        add_btn.setMaximumWidth(100)
        add_btn.clicked.connect(self._on_add)
        rm_btn = QPushButton("Remove")
        rm_btn.setMaximumWidth(90)
        rm_btn.clicked.connect(self._on_remove)
        restart_btn = QPushButton("Restart Renderer")
        restart_btn.setMinimumHeight(28)
        restart_btn.clicked.connect(self.restart_requested.emit)

        btns.addWidget(add_btn)
        btns.addWidget(rm_btn)
        btns.addWidget(restart_btn)
        btns.addStretch()
        layout.addLayout(btns)

    def _on_add(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Add Include Folder",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if d and d not in self.dirs():
            self._list.addItem(d)
            self.include_added.emit(d)

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        path = item.text()
        self.include_removed.emit(path)
        self._list.takeItem(self._list.row(item))

    def dirs(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_dirs(self, dirs: list[str]) -> None:
        self._list.clear()
        for d in dirs:
            self._list.addItem(d)
