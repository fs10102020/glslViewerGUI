import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QHBoxLayout,
    QScrollArea, QPushButton, QLabel, QFileDialog,
    QMessageBox, QColorDialog, QGroupBox,
)
from PySide6.QtGui import QColor

from shader_parser import parse_uniforms


class UniformPanel(QWidget):
    uniform_changed = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UniformPanel")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(4, 4, 4, 4)
        outer_layout.setSpacing(4)

        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Preset")
        self._save_btn.clicked.connect(self._save_preset)
        self._load_btn = QPushButton("Load Preset")
        self._load_btn.clicked.connect(self._load_preset)
        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._load_btn)
        outer_layout.addLayout(btn_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setSpacing(6)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._container)
        outer_layout.addWidget(scroll)

        self._widgets: dict[str, QWidget] = {}
        self._groups: dict[str, QGroupBox] = {}

    def load_from_source(self, source: str) -> None:
        self.clear()
        uniforms = parse_uniforms(source)

        if not uniforms:
            label = QLabel("No user uniforms found in shader.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._container_layout.addWidget(label)
            return

        # Sort into groups preserving declaration order.
        grouped: dict[str, list[dict]] = {}
        for info in uniforms:
            group = info.get("group", "Uniforms")
            grouped.setdefault(group, []).append(info)

        for group_name, items in grouped.items():
            group_box = QGroupBox(group_name)
            form = QFormLayout(group_box)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form.setContentsMargins(4, 8, 4, 4)
            form.setSpacing(4)

            for info in items:
                name = info["name"]
                w = self._build_widget(info)
                if w is not None:
                    self._widgets[name] = w
                    form.addRow(name + ":", w)

            self._container_layout.addWidget(group_box)
            self._groups[group_name] = group_box

        self._container_layout.addStretch()

    def clear(self) -> None:
        while self._container_layout.count():
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()
        self._groups.clear()

    def get_value(self, name: str):
        w = self._widgets.get(name)
        if w is None:
            return None
        return self._read_widget(w)

    def set_values(self, values: dict[str, object]) -> None:
        for name, val in values.items():
            w = self._widgets.get(name)
            if w is None:
                continue
            self._write_widget(w, val)

    def all_values(self) -> dict[str, object]:
        return {name: self._read_widget(w) for name, w in self._widgets.items()}

    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_widget(self, info: dict):
        wtype = info["widget"]

        if wtype == "float":
            sp = QDoubleSpinBox()
            sp.setRange(info.get("min", -1e6), info.get("max", 1e6))
            sp.setSingleStep(info.get("step", 0.01))
            sp.setValue(float(info["value"]))
            sp.setDecimals(6)
            sp.valueChanged.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return sp

        elif wtype == "int":
            sp = QSpinBox()
            sp.setRange(int(info.get("min", -1e6)), int(info.get("max", 1e6)))
            sp.setSingleStep(int(info.get("step", 1)))
            sp.setValue(int(info["value"]))
            sp.valueChanged.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return sp

        elif wtype == "bool":
            cb = QCheckBox()
            cb.setChecked(bool(info["value"]))
            cb.toggled.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return cb

        elif wtype == "color":
            return self._build_color_widget(info)

        elif wtype == "vec":
            return self._build_vec_widget(info)

        elif wtype == "mat":
            return self._build_mat_widget(info)

        return None

    def _build_color_widget(self, info: dict):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        preview = QPushButton()
        preview.setFixedSize(24, 24)
        preview.setFlat(True)

        value = info["value"]
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            color = QColor.fromRgbF(float(value[0]), float(value[1]), float(value[2]))
        else:
            color = QColor.fromRgbF(1.0, 1.0, 1.0)
        preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")

        label = QLabel(color.name())
        label.setStyleSheet("font-family: monospace;")

        layout.addWidget(preview)
        layout.addWidget(label)
        layout.addStretch()

        container._value = [color.redF(), color.greenF(), color.blueF()]
        container._preview = preview
        container._label = label
        container._size = len(value) if isinstance(value, (list, tuple)) else 3

        def pick_color():
            current = QColor.fromRgbF(*container._value[:3])
            chosen = QColorDialog.getColor(current, self, "Choose color")
            if chosen.isValid():
                container._value[:3] = [chosen.redF(), chosen.greenF(), chosen.blueF()]
                preview.setStyleSheet(f"background-color: {chosen.name()}; border: 1px solid #888;")
                label.setText(chosen.name())
                self.uniform_changed.emit(info["name"], list(container._value))

        preview.clicked.connect(pick_color)
        return container

    def _build_vec_widget(self, info: dict):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        spinboxes = []
        for i in range(info["size"]):
            sp = QDoubleSpinBox()
            sp.setRange(info.get("min", -1e6), info.get("max", 1e6))
            sp.setSingleStep(info.get("step", 0.01))
            sp.setDecimals(6)
            sp.setValue(info["value"][i] if isinstance(info["value"], (list, tuple)) else 0.0)
            spinboxes.append(sp)
            layout.addSpacing(2)
            layout.addWidget(sp)

        container._spinboxes = spinboxes

        def on_any_change():
            vals = [sp.value() for sp in spinboxes]
            self.uniform_changed.emit(info["name"], vals)

        for sp in spinboxes:
            sp.valueChanged.connect(on_any_change)

        return container

    def _build_mat_widget(self, info: dict):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        rows = info["rows"]
        cols = info["cols"]
        spinboxes = []

        for r in range(rows):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            for c in range(cols):
                sp = QDoubleSpinBox()
                sp.setRange(info.get("min", -1e6), info.get("max", 1e6))
                sp.setSingleStep(info.get("step", 0.01))
                sp.setDecimals(6)
                idx = r * cols + c
                sp.setValue(info["value"][idx] if isinstance(info["value"], (list, tuple)) and idx < len(info["value"]) else 0.0)
                spinboxes.append(sp)
                row_layout.addWidget(sp)
            layout.addWidget(row_widget)

        container._spinboxes = spinboxes

        def on_any_change():
            vals = [sp.value() for sp in spinboxes]
            self.uniform_changed.emit(info["name"], vals)

        for sp in spinboxes:
            sp.valueChanged.connect(on_any_change)

        return container

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------

    def _read_widget(self, w):
        if isinstance(w, QDoubleSpinBox):
            return w.value()
        elif isinstance(w, QSpinBox):
            return w.value()
        elif isinstance(w, QCheckBox):
            return w.isChecked()
        elif hasattr(w, '_preview'):
            # Color widget
            return list(w._value)
        else:
            vals = []
            for child in w.findChildren(QDoubleSpinBox):
                vals.append(child.value())
            if len(vals) == 1:
                return vals[0]
            return vals

    def _write_widget(self, w, val):
        if isinstance(w, QDoubleSpinBox):
            w.setValue(float(val))
        elif isinstance(w, QSpinBox):
            w.setValue(int(val))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(val))
        elif hasattr(w, '_preview'):
            # Color widget
            if isinstance(val, (list, tuple)) and len(val) >= 3:
                w._value[:3] = [float(val[0]), float(val[1]), float(val[2])]
                color = QColor.fromRgbF(*w._value[:3])
                w._preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
                w._label.setText(color.name())
        elif hasattr(w, '_spinboxes'):
            if isinstance(val, (list, tuple)):
                for i, sp in enumerate(w._spinboxes):
                    if i < len(val):
                        sp.setValue(float(val[i]))

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "", "JSON Presets (*.json)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        data = self.all_values()
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", "", "JSON Presets (*.json)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.set_values(data)
            for name, val in data.items():
                self.uniform_changed.emit(name, val)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
