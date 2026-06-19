# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QGroupBox,
)


class DependencyViewerPanel(QWidget):
    query_requested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DependencyViewerPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Dependency"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(True)
        layout.addWidget(self._tree)

        btn_group = QGroupBox("Refresh")
        btn_layout = QHBoxLayout(btn_group)
        for label, cmd in [
            ("All", "dependencies"),
            ("Fragment", "dependencies,frag"),
            ("Vertex", "dependencies,vert"),
        ]:
            btn = QPushButton(label)
            btn.setMaximumWidth(90)
            btn.clicked.connect(lambda checked=False, _c=cmd: self._refresh(_c))
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        layout.addWidget(btn_group)

    def _refresh(self, cmd: str) -> None:
        if cmd == "dependencies":
            self._tree.clear()
            self.query_requested.emit("dependencies,frag", self._on_frag_result)
            self.query_requested.emit("dependencies,vert", self._on_vert_result)
        else:
            self._tree.clear()
            self.query_requested.emit(cmd, self._on_single_result(cmd))

    def _on_single_result(self, cmd: str):
        label = "Fragment" if "frag" in cmd else "Vertex"
        def cb(text):
            root = QTreeWidgetItem(self._tree, [label])
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("//") and not line.startswith("#"):
                    QTreeWidgetItem(root, [line])
            root.setExpanded(True)
        return cb

    def _on_frag_result(self, text: str) -> None:
        root = QTreeWidgetItem(self._tree, ["Fragment"])
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("//") and not line.startswith("#"):
                QTreeWidgetItem(root, [line])
        root.setExpanded(True)

    def _on_vert_result(self, text: str) -> None:
        root = QTreeWidgetItem(self._tree, ["Vertex"])
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("//") and not line.startswith("#"):
                QTreeWidgetItem(root, [line])
        root.setExpanded(True)
