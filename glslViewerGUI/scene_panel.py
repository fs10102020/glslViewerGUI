# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QDoubleSpinBox,
    QComboBox, QGridLayout,
)
from commands import (
    build_light_position, build_light_color, build_light_falloff,
    build_light_intensity, build_sun_elevation, build_sun_azimuth,
    build_sky_turbidity, build_models_clear, build_generate_sdf,
)
from glslViewer_config import GLSLVIEWER_BIN


class ScenePanel(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScenePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        light_group = QGroupBox("Lighting")
        light_form = QVBoxLayout(light_group)

        pos_row = QGridLayout()
        self._lx = self._make_spinbox()
        self._ly = self._make_spinbox()
        self._lz = self._make_spinbox()
        pos_row.addWidget(QLabel("X"), 0, 0)
        pos_row.addWidget(self._lx, 0, 1)
        pos_row.addWidget(QLabel("Y"), 1, 0)
        pos_row.addWidget(self._ly, 1, 1)
        pos_row.addWidget(QLabel("Z"), 2, 0)
        pos_row.addWidget(self._lz, 2, 1)
        pos_btn = QPushButton("Set")
        pos_btn.setMaximumWidth(60)
        pos_btn.clicked.connect(self._on_light_pos)
        pos_row.addWidget(pos_btn, 2, 2)
        light_form.addLayout(pos_row)

        color_row = QGridLayout()
        self._lr = self._make_spinbox(1.0)
        self._lg = self._make_spinbox(1.0)
        self._lb = self._make_spinbox(1.0)
        color_row.addWidget(QLabel("R"), 0, 0)
        color_row.addWidget(self._lr, 0, 1)
        color_row.addWidget(QLabel("G"), 1, 0)
        color_row.addWidget(self._lg, 1, 1)
        color_row.addWidget(QLabel("B"), 2, 0)
        color_row.addWidget(self._lb, 2, 1)
        col_btn = QPushButton("Set")
        col_btn.setMaximumWidth(60)
        col_btn.clicked.connect(self._on_light_color)
        color_row.addWidget(col_btn, 2, 2)
        light_form.addLayout(color_row)

        falloff_row = QHBoxLayout()
        falloff_row.addWidget(QLabel("Falloff:"))
        self._falloff = QDoubleSpinBox()
        self._falloff.setRange(0.0, 1e6)
        self._falloff.setDecimals(3)
        self._falloff.setValue(1.0)
        falloff_row.addWidget(self._falloff)
        ff_btn = QPushButton("Set")
        ff_btn.setMaximumWidth(60)
        ff_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_light_falloff(self._falloff.value())))
        falloff_row.addWidget(ff_btn)
        light_form.addLayout(falloff_row)

        intensity_row = QHBoxLayout()
        intensity_row.addWidget(QLabel("Intensity:"))
        self._intensity = QDoubleSpinBox()
        self._intensity.setRange(0.0, 1e6)
        self._intensity.setDecimals(3)
        self._intensity.setValue(1.0)
        intensity_row.addWidget(self._intensity)
        int_btn = QPushButton("Set")
        int_btn.setMaximumWidth(60)
        int_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_light_intensity(self._intensity.value())))
        intensity_row.addWidget(int_btn)
        light_form.addLayout(intensity_row)

        layout.addWidget(light_group)

        sky_group = QGroupBox("Sky / Environment")
        sky_form = QVBoxLayout(sky_group)

        sun_r1 = QHBoxLayout()
        sun_r1.addWidget(QLabel("Elevation:"))
        self._sun_el = QDoubleSpinBox()
        self._sun_el.setRange(-90.0, 90.0)
        self._sun_el.setDecimals(2)
        self._sun_el.setValue(45.0)
        sun_r1.addWidget(self._sun_el)
        el_btn = QPushButton("Set")
        el_btn.setMaximumWidth(60)
        el_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_sun_elevation(self._sun_el.value())))
        sun_r1.addWidget(el_btn)
        sky_form.addLayout(sun_r1)

        sun_r2 = QHBoxLayout()
        sun_r2.addWidget(QLabel("Azimuth:"))
        self._sun_az = QDoubleSpinBox()
        self._sun_az.setRange(0.0, 360.0)
        self._sun_az.setDecimals(2)
        self._sun_az.setValue(180.0)
        sun_r2.addWidget(self._sun_az)
        az_btn = QPushButton("Set")
        az_btn.setMaximumWidth(60)
        az_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_sun_azimuth(self._sun_az.value())))
        sun_r2.addWidget(az_btn)
        sky_form.addLayout(sun_r2)

        turb_r = QHBoxLayout()
        turb_r.addWidget(QLabel("Turbidity:"))
        self._turb = QDoubleSpinBox()
        self._turb.setRange(1.0, 32.0)
        self._turb.setDecimals(2)
        self._turb.setValue(3.0)
        turb_r.addWidget(self._turb)
        turb_btn = QPushButton("Set")
        turb_btn.setMaximumWidth(60)
        turb_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_sky_turbidity(self._turb.value())))
        turb_r.addWidget(turb_btn)
        sky_form.addLayout(turb_r)

        layout.addWidget(sky_group)

        model_group = QGroupBox("Models / SDF")
        model_row = QHBoxLayout(model_group)
        for label, cmd in [
            ("List Models", "models"),
            ("Clear Models", "models,clear"),
            ("Generate SDF", "generate_sdf,0.01"),
        ]:
            btn = QPushButton(label)
            btn.setMaximumWidth(110)
            btn.clicked.connect(lambda checked=False, _c=cmd: self.command_requested.emit(_c))
            model_row.addWidget(btn)
        model_row.addStretch()
        layout.addWidget(model_group)

        layout.addStretch()

    def _make_spinbox(self, default: float = 0.0):
        sp = QDoubleSpinBox()
        sp.setRange(-1e6, 1e6)
        sp.setSingleStep(0.1)
        sp.setDecimals(3)
        sp.setValue(default)
        return sp

    def _on_light_pos(self) -> None:
        self.command_requested.emit(build_light_position(
            self._lx.value(), self._ly.value(), self._lz.value()
        ))

    def _on_light_color(self) -> None:
        self.command_requested.emit(build_light_color(
            self._lr.value(), self._lg.value(), self._lb.value()
        ))
