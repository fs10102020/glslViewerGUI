from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QHBoxLayout, QLabel, QGroupBox, QLineEdit,
)
from commands import (
    build_camera_distance,
    build_camera_default,
    build_camera_exposure,
    build_camera_fov,
    build_camera_look_at,
    build_camera_move,
    build_camera_name,
    build_camera_position,
    build_camera_type,
)


class CameraPanel(QWidget):
    camera_command = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CameraPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Distance
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0.01, 1e6)
        self._distance.setSingleStep(0.1)
        self._distance.setDecimals(3)
        self._distance.setValue(2.0)
        self._distance.valueChanged.connect(
            lambda v: self.camera_command.emit(build_camera_distance(v))
        )

        # FOV
        self._fov = QSpinBox()
        self._fov.setRange(1, 179)
        self._fov.setValue(45)
        self._fov.valueChanged.connect(
            lambda v: self.camera_command.emit(build_camera_fov(v))
        )

        # Projection type
        self._proj = QComboBox()
        self._proj.addItems(["perspective", "ortho"])
        self._proj.currentTextChanged.connect(
            lambda t: self.camera_command.emit(build_camera_type(t))
        )

        self._cam_name = QLineEdit()
        self._cam_name.setPlaceholderText("default")
        self._cam_name.returnPressed.connect(self._set_camera_name)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Distance:", self._distance)
        form.addRow("FOV:", self._fov)
        form.addRow("Projection:", self._proj)
        form.addRow("Name:", self._cam_name)
        layout.addLayout(form)

        # Position
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

        # Look At
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

        # Move buttons
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
                    build_camera_move(_dx, _dy, _dz)
                )
            )
            move_grid.addWidget(btn)
        layout.addWidget(move_group)

        exposure_group = QGroupBox("Exposure")
        exposure_layout = QHBoxLayout(exposure_group)
        self._exp_aper = self._make_spinbox()
        self._exp_aper.setValue(5.6)
        self._exp_shutter = self._make_spinbox()
        self._exp_shutter.setValue(125.0)
        self._exp_iso = self._make_spinbox()
        self._exp_iso.setValue(100.0)
        exposure_layout.addWidget(QLabel("Aperture"))
        exposure_layout.addWidget(self._exp_aper)
        exposure_layout.addWidget(QLabel("Shutter"))
        exposure_layout.addWidget(self._exp_shutter)
        exposure_layout.addWidget(QLabel("ISO"))
        exposure_layout.addWidget(self._exp_iso)
        btn_exp = QPushButton("Set")
        btn_exp.clicked.connect(self._set_exposure)
        exposure_layout.addWidget(btn_exp)
        layout.addWidget(exposure_group)

        layout.addStretch()

    def _make_spinbox(self):
        sp = QDoubleSpinBox()
        sp.setRange(-1e6, 1e6)
        sp.setSingleStep(0.1)
        sp.setDecimals(3)
        return sp

    def _set_position(self) -> None:
        x = self._pos_x.value()
        y = self._pos_y.value()
        z = self._pos_z.value()
        self.camera_command.emit(build_camera_position(x, y, z))

    def _set_look_at(self) -> None:
        x = self._look_x.value()
        y = self._look_y.value()
        z = self._look_z.value()
        self.camera_command.emit(build_camera_look_at(x, y, z))

    def _set_exposure(self) -> None:
        self.camera_command.emit(
            build_camera_exposure(self._exp_aper.value(), self._exp_shutter.value(), self._exp_iso.value())
        )

    def _set_camera_name(self) -> None:
        name = self._cam_name.text().strip()
        self.camera_command.emit(build_camera_name(name) if name else build_camera_default())

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
