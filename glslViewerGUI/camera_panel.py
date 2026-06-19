# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QLabel, QGroupBox, QLineEdit,
)


class CameraPanel(QWidget):
    camera_command = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CameraPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        dist_row = QHBoxLayout()
        dist_row.addWidget(QLabel("Distance:"))
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0.01, 1e6)
        self._distance.setSingleStep(0.1)
        self._distance.setDecimals(3)
        self._distance.setValue(2.0)
        self._distance.valueChanged.connect(
            lambda v: self.camera_command.emit(f"camera_distance,{v}")
        )
        dist_row.addWidget(self._distance)
        layout.addLayout(dist_row)

        fov_row = QHBoxLayout()
        fov_row.addWidget(QLabel("FOV:"))
        self._fov = QSpinBox()
        self._fov.setRange(1, 179)
        self._fov.setValue(45)
        self._fov.valueChanged.connect(
            lambda v: self.camera_command.emit(f"camera_fov,{v}")
        )
        fov_row.addWidget(self._fov)
        layout.addLayout(fov_row)

        proj_row = QHBoxLayout()
        proj_row.addWidget(QLabel("Projection:"))
        self._proj = QComboBox()
        self._proj.addItems(["perspective", "ortho"])
        self._proj.currentTextChanged.connect(
            lambda t: self.camera_command.emit(f"camera_type,{t}")
        )
        proj_row.addWidget(self._proj)
        layout.addLayout(proj_row)

        cam_name_row = QHBoxLayout()
        cam_name_row.addWidget(QLabel("Camera:"))
        self._cam_name = QLineEdit()
        self._cam_name.setPlaceholderText("camera name")
        self._cam_name.editingFinished.connect(self._on_cam_name)
        cam_name_row.addWidget(self._cam_name)
        layout.addLayout(cam_name_row)

        exposure_group = QGroupBox("Exposure")
        exp_layout = QHBoxLayout(exposure_group)
        exp_layout.addWidget(QLabel("Aperture:"))
        self._exp_aper = QDoubleSpinBox()
        self._exp_aper.setRange(0.0, 100.0)
        self._exp_aper.setDecimals(2)
        self._exp_aper.setSingleStep(0.1)
        self._exp_aper.setValue(2.8)
        exp_layout.addWidget(self._exp_aper)
        exp_layout.addWidget(QLabel("Shutter:"))
        self._exp_shutter = QDoubleSpinBox()
        self._exp_shutter.setRange(0.0, 1.0)
        self._exp_shutter.setDecimals(4)
        self._exp_shutter.setSingleStep(0.01)
        self._exp_shutter.setValue(0.01)
        exp_layout.addWidget(self._exp_shutter)
        exp_layout.addWidget(QLabel("ISO:"))
        self._exp_iso = QDoubleSpinBox()
        self._exp_iso.setRange(1.0, 25600.0)
        self._exp_iso.setDecimals(0)
        self._exp_iso.setSingleStep(100.0)
        self._exp_iso.setValue(100.0)
        exp_layout.addWidget(self._exp_iso)
        exp_set = QPushButton("Set")
        exp_set.setMaximumWidth(50)
        exp_set.clicked.connect(self._set_exposure)
        exp_layout.addWidget(exp_set)
        layout.addWidget(exposure_group)

        pos_group = QGroupBox("Position")
        pos_layout = QHBoxLayout(pos_group)
        self._pos_x = self._make_spinbox()
        self._pos_y = self._make_spinbox()
        self._pos_z = self._make_spinbox()
        pos_layout.addWidget(QLabel("X"))
        pos_layout.addWidget(self._pos_x)
        pos_layout.addWidget(QLabel("Y"))
        pos_layout.addWidget(self._pos_y)
        pos_layout.addWidget(QLabel("Z"))
        pos_layout.addWidget(self._pos_z)
        btn_pos = QPushButton("Set")
        btn_pos.clicked.connect(self._set_position)
        pos_layout.addWidget(btn_pos)
        layout.addWidget(pos_group)

        look_group = QGroupBox("Look At")
        look_layout = QHBoxLayout(look_group)
        self._look_x = self._make_spinbox()
        self._look_y = self._make_spinbox()
        self._look_z = self._make_spinbox()
        look_layout.addWidget(QLabel("X"))
        look_layout.addWidget(self._look_x)
        look_layout.addWidget(QLabel("Y"))
        look_layout.addWidget(self._look_y)
        look_layout.addWidget(QLabel("Z"))
        look_layout.addWidget(self._look_z)
        btn_look = QPushButton("Set")
        btn_look.clicked.connect(self._set_look_at)
        look_layout.addWidget(btn_look)
        layout.addWidget(look_group)

        move_group = QGroupBox("Nudge")
        move_grid = QHBoxLayout(move_group)
        for label, dx, dy, dz in [
            ("\u2190", -0.1, 0.0, 0.0),
            ("\u2192", 0.1, 0.0, 0.0),
            ("\u2191", 0.0, 0.0, 0.1),
            ("\u2193", 0.0, 0.0, -0.1),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(
                lambda checked=False, _dx=dx, _dy=dy, _dz=dz: self.camera_command.emit(
                    f"camera_move,{_dx},{_dy},{_dz}"
                )
            )
            move_grid.addWidget(btn)
        layout.addWidget(move_group)

        layout.addStretch()

    def _make_spinbox(self):
        sp = QDoubleSpinBox()
        sp.setRange(-1e6, 1e6)
        sp.setSingleStep(0.1)
        sp.setDecimals(3)
        return sp

    def _on_cam_name(self) -> None:
        name = self._cam_name.text().strip()
        if name:
            self.camera_command.emit(f"camera,{name}")

    def _set_exposure(self) -> None:
        aper = self._exp_aper.value()
        shutter = self._exp_shutter.value()
        iso = self._exp_iso.value()
        self.camera_command.emit(f"camera_exposure,{aper},{shutter},{iso}")

    def _set_position(self) -> None:
        x = self._pos_x.value()
        y = self._pos_y.value()
        z = self._pos_z.value()
        self.camera_command.emit(f"camera_position,{x},{y},{z}")

    def _set_look_at(self) -> None:
        x = self._look_x.value()
        y = self._look_y.value()
        z = self._look_z.value()
        self.camera_command.emit(f"camera_look_at,{x},{y},{z}")

    def get_state(self) -> dict:
        return {
            "distance": self._distance.value(),
            "fov": self._fov.value(),
            "projection": self._proj.currentText(),
            "position": [self._pos_x.value(), self._pos_y.value(), self._pos_z.value()],
            "look_at": [self._look_x.value(), self._look_y.value(), self._look_z.value()],
        }

    def set_state(self, state: dict) -> None:
        if "distance" in state:
            self._distance.setValue(state["distance"])
        if "fov" in state:
            self._fov.setValue(state["fov"])
        if "projection" in state:
            self._proj.setCurrentText(state["projection"])
        if "position" in state:
            x, y, z = state["position"]
            self._pos_x.setValue(x)
            self._pos_y.setValue(y)
            self._pos_z.setValue(z)
            self._set_position()
        if "look_at" in state:
            x, y, z = state["look_at"]
            self._look_x.setValue(x)
            self._look_y.setValue(y)
            self._look_z.setValue(z)
            self._set_look_at()
