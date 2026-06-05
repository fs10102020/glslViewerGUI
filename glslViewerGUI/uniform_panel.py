import json
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QHBoxLayout,
    QScrollArea, QPushButton, QLabel, QFileDialog,
    QMessageBox,
)
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
        self._form_layout = QFormLayout(self._container)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        scroll.setWidget(self._container)
        outer_layout.addWidget(scroll)

        self._widgets: dict[str, QWidget] = {}

    def load_from_source(self, source: str) -> None:
        self.clear()
        uniforms = parse_uniforms(source)

        if not uniforms:
            label = QLabel("No user uniforms found in shader.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._form_layout.addRow(label)
            return

        for info in uniforms:
            name = info["name"]
            w = self._build_widget(info)
            if w is not None:
                self._widgets[name] = w
                self._form_layout.addRow(name + ":", w)

    def clear(self) -> None:
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

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
            if isinstance(w, QDoubleSpinBox):
                w.setValue(float(val))
            elif isinstance(w, QSpinBox):
                w.setValue(int(val))
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(val))
            elif hasattr(w, '_spinboxes'):
                if isinstance(val, (list, tuple)):
                    for i, sp in enumerate(w._spinboxes):
                        if i < len(val):
                            sp.setValue(float(val[i]))

    def all_values(self) -> dict[str, object]:
        return {name: self._read_widget(w) for name, w in self._widgets.items()}

    def _build_widget(self, info: dict):
        wtype = info["widget"]

        if wtype == "float":
            sp = QDoubleSpinBox()
            sp.setRange(info.get("min", -1e6), info.get("max", 1e6))
            sp.setSingleStep(info.get("step", 0.01))
            sp.setValue(info["value"])
            sp.setDecimals(6)
            sp.valueChanged.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return sp

        elif wtype == "int":
            sp = QSpinBox()
            sp.setRange(int(info.get("min", -1e6)), int(info.get("max", 1e6)))
            sp.setSingleStep(info.get("step", 1))
            sp.setValue(info["value"])
            sp.valueChanged.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return sp

        elif wtype == "bool":
            cb = QCheckBox()
            cb.setChecked(info["value"])
            cb.toggled.connect(lambda v, n=info["name"]: self.uniform_changed.emit(n, v))
            return cb

        elif wtype == "vec":
            return self._build_vec_widget(info)

        elif wtype == "mat":
            return self._build_mat_widget(info)

        return None

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

    def _read_widget(self, w):
        if isinstance(w, QDoubleSpinBox):
            return w.value()
        elif isinstance(w, QSpinBox):
            return w.value()
        elif isinstance(w, QCheckBox):
            return w.isChecked()
        else:
            vals = []
            for child in w.findChildren(QDoubleSpinBox):
                vals.append(child.value())
            if len(vals) == 1:
                return vals[0]
            return vals

    def _save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "", "JSON Presets (*.json)"
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
            self, "Load Preset", "", "JSON Presets (*.json)"
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
