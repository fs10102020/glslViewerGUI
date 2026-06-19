# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QTextEdit, QGroupBox, QComboBox,
    QSpinBox, QLineEdit, QLabel, QCheckBox,
)
from commands import (
    build_buffers, build_debug,
    build_define, build_floor, build_grid, build_axis, build_bboxes,
)


class PipelinePanel(QWidget):
    command_requested = Signal(str)
    define_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PipelinePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        buf_group = QGroupBox("Buffer / Texture Overlay")
        buf_grid = QGridLayout(buf_group)
        for i, (label, cmd_true, cmd_false) in enumerate([
            ("Buffers", build_buffers(True), build_buffers(False)),
        ]):
            cb = QCheckBox(label)
            cb.toggled.connect(lambda v, _t=cmd_true, _f=cmd_false: self.command_requested.emit(_t if v else _f))
            buf_grid.addWidget(cb, 0, i)
        tex_cb = QCheckBox("Textures")
        tex_cb.setEnabled(False)
        tex_cb.setToolTip("The backend does not provide a runtime textures,on/off toggle.")
        buf_grid.addWidget(tex_cb, 0, 1)
        debug_cb = QCheckBox("Debug")
        debug_cb.toggled.connect(lambda v: self.command_requested.emit(build_debug(v)))
        buf_grid.addWidget(debug_cb, 1, 0)
        layout.addWidget(buf_group)

        query_row = QHBoxLayout()
        for label, cmd in [
            ("Buffers List", "buffers,list"),
            ("Textures List", "textures,list"),
            ("Defines List", "defines"),
        ]:
            btn = QPushButton(label)
            btn.setMaximumWidth(100)
            btn.clicked.connect(lambda checked=False, _c=cmd: self.command_requested.emit(_c))
            query_row.addWidget(btn)
        query_row.addStretch()
        layout.addLayout(query_row)

        mp_group = QGroupBox("Multi-Pass Defines")
        mp_form = QGridLayout(mp_group)
        mp_form.addWidget(QLabel("Type:"), 0, 0)
        self._mp_type = QComboBox()
        self._mp_type.addItems(["BUFFER", "DOUBLE_BUFFER", "PYRAMID", "FLOOD"])
        self._mp_type.setToolTip("Buffer pass defines should normally come from #ifdef blocks in shader source.")
        mp_form.addWidget(self._mp_type, 0, 1, 1, 2)
        mp_form.addWidget(QLabel("Index:"), 1, 0)
        self._mp_idx = QSpinBox()
        self._mp_idx.setRange(0, 9)
        mp_form.addWidget(self._mp_idx, 1, 1)
        mp_form.addWidget(QLabel("Value:"), 2, 0)
        self._mp_val = QLineEdit()
        self._mp_val.setPlaceholderText("optional")
        mp_form.addWidget(self._mp_val, 2, 1)
        mp_add = QPushButton("Add global define")
        mp_add.setMaximumWidth(70)
        mp_add.setToolTip("Advanced: global pass defines can conflict with backend-managed pass shaders.")
        mp_add.clicked.connect(self._on_mp_define)
        mp_form.addWidget(mp_add, 2, 2)
        layout.addWidget(mp_group)

        scene_group = QGroupBox("Scene Toggles")
        self._scene_toggles = []
        scene_grid = QGridLayout(scene_group)
        for i, (label, cmd_true, cmd_false) in enumerate([
            ("Floor", build_floor(True), build_floor(False)),
            ("Grid", build_grid(True), build_grid(False)),
            ("Axis", build_axis(True), build_axis(False)),
            ("BBoxes", build_bboxes(True), build_bboxes(False)),
        ]):
            cb = QCheckBox(label)
            cb.toggled.connect(lambda v, _t=cmd_true, _f=cmd_false: self.command_requested.emit(_t if v else _f))
            self._scene_toggles.append(cb)
            scene_grid.addWidget(cb, i // 2, i % 2)
        layout.addWidget(scene_group)

        layout.addStretch()

    def _on_mp_define(self) -> None:
        name = f"{self._mp_type.currentText()}_{self._mp_idx.value()}"
        value = self._mp_val.text().strip()
        self.define_requested.emit(name, value)

    def set_scene_enabled(self, enabled: bool) -> None:
        for toggle in self._scene_toggles:
            toggle.setEnabled(enabled)
            toggle.setToolTip("" if enabled else "Scene controls require a vertex shader or model.")
