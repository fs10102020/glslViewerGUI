# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
"""SDF renderer control panel."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QGroupBox, QCheckBox, QLineEdit,
)

from sdf_project import SdfProjectConfig


class SdfPanel(QWidget):
    """Controls for SDF renderer integrator and parameters."""

    config_changed = Signal()  # any renderer parameter changed
    integrator_changed = Signal(str)
    debug_view_changed = Signal(str)
    reset_requested = Signal()
    pause_toggled = Signal(bool)
    scene_revision_needed = Signal()  # ask main window to bump u_sceneRevision

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SdfPanel")

        self._config = SdfProjectConfig()
        self._paused = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Integrator
        integrator_group = QGroupBox("Integrator")
        integrator_form = QFormLayout(integrator_group)

        self._integrator = QComboBox()
        self._integrator.addItems(["preview", "pathtrace"])
        self._integrator.currentTextChanged.connect(self._on_integrator_changed)
        integrator_form.addRow("Mode:", self._integrator)

        self._debug_view = QComboBox()
        self._debug_view.addItems(["beauty", "normal", "distance", "steps", "albedo", "emission"])
        self._debug_view.currentTextChanged.connect(self._on_debug_view_changed)
        integrator_form.addRow("Debug:", self._debug_view)

        layout.addWidget(integrator_group)

        # Status
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout(status_group)
        self._sample_label = QLabel("Samples: 0 / 256")
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setToolTip("Clear path-tracing accumulator")
        self._reset_btn.clicked.connect(self.reset_requested.emit)
        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setCheckable(True)
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        status_layout.addWidget(self._sample_label)
        status_layout.addWidget(self._reset_btn)
        status_layout.addWidget(self._pause_btn)
        layout.addWidget(status_group)

        # Raymarcher
        march_group = QGroupBox("Raymarcher")
        march_form = QFormLayout(march_group)

        self._max_steps = QSpinBox()
        self._max_steps.setRange(16, 512)
        self._max_steps.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Max steps:", self._max_steps)

        self._max_distance = QDoubleSpinBox()
        self._max_distance.setRange(1.0, 200.0)
        self._max_distance.setDecimals(2)
        self._max_distance.setSingleStep(1.0)
        self._max_distance.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Max distance:", self._max_distance)

        self._hit_epsilon = QDoubleSpinBox()
        self._hit_epsilon.setRange(0.00001, 0.01)
        self._hit_epsilon.setDecimals(5)
        self._hit_epsilon.setSingleStep(0.0001)
        self._hit_epsilon.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Hit epsilon:", self._hit_epsilon)

        self._step_scale = QDoubleSpinBox()
        self._step_scale.setRange(0.1, 1.5)
        self._step_scale.setDecimals(2)
        self._step_scale.setSingleStep(0.01)
        self._step_scale.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Step scale:", self._step_scale)

        self._normal_epsilon = QDoubleSpinBox()
        self._normal_epsilon.setRange(0.00001, 0.01)
        self._normal_epsilon.setDecimals(5)
        self._normal_epsilon.setSingleStep(0.0001)
        self._normal_epsilon.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Normal eps:", self._normal_epsilon)

        self._shadow_steps = QSpinBox()
        self._shadow_steps.setRange(0, 256)
        self._shadow_steps.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Shadow steps:", self._shadow_steps)

        self._shadow_epsilon = QDoubleSpinBox()
        self._shadow_epsilon.setRange(0.00001, 0.01)
        self._shadow_epsilon.setDecimals(5)
        self._shadow_epsilon.setSingleStep(0.0001)
        self._shadow_epsilon.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Shadow eps:", self._shadow_epsilon)

        self._camera_fov = QDoubleSpinBox()
        self._camera_fov.setRange(1.0, 179.0)
        self._camera_fov.setDecimals(1)
        self._camera_fov.setSingleStep(1.0)
        self._camera_fov.valueChanged.connect(self._on_config_changed)
        march_form.addRow("Camera FOV:", self._camera_fov)

        layout.addWidget(march_group)

        # Path tracer
        pt_group = QGroupBox("Path Tracer")
        pt_form = QFormLayout(pt_group)

        self._max_bounces = QSpinBox()
        self._max_bounces.setRange(1, 16)
        self._max_bounces.valueChanged.connect(self._on_config_changed)
        pt_form.addRow("Max bounces:", self._max_bounces)

        self._samples_per_frame = QSpinBox()
        self._samples_per_frame.setRange(1, 64)
        self._samples_per_frame.valueChanged.connect(self._on_config_changed)
        pt_form.addRow("Samples/frame:", self._samples_per_frame)

        self._target_samples = QSpinBox()
        self._target_samples.setRange(1, 65536)
        self._target_samples.setSingleStep(16)
        self._target_samples.valueChanged.connect(self._on_config_changed)
        pt_form.addRow("Target samples:", self._target_samples)

        self._rr_start_bounce = QSpinBox()
        self._rr_start_bounce.setRange(0, 16)
        self._rr_start_bounce.valueChanged.connect(self._on_config_changed)
        pt_form.addRow("RR start bounce:", self._rr_start_bounce)

        self._firefly_clamp = QDoubleSpinBox()
        self._firefly_clamp.setRange(0.0, 100.0)
        self._firefly_clamp.setDecimals(2)
        self._firefly_clamp.setSingleStep(1.0)
        self._firefly_clamp.valueChanged.connect(self._on_config_changed)
        pt_form.addRow("Firefly clamp:", self._firefly_clamp)

        layout.addWidget(pt_group)

        # Display
        display_group = QGroupBox("Display")
        display_form = QFormLayout(display_group)

        self._exposure = QDoubleSpinBox()
        self._exposure.setRange(0.001, 100.0)
        self._exposure.setDecimals(3)
        self._exposure.setSingleStep(0.1)
        self._exposure.valueChanged.connect(self._on_config_changed)
        display_form.addRow("Exposure:", self._exposure)

        self._tone_map = QComboBox()
        self._tone_map.addItems(["aces", "reinhard", "filmic", "none"])
        self._tone_map.currentTextChanged.connect(self._on_config_changed)
        display_form.addRow("Tone map:", self._tone_map)

        self._gamma = QDoubleSpinBox()
        self._gamma.setRange(1.0, 3.0)
        self._gamma.setDecimals(2)
        self._gamma.setSingleStep(0.05)
        self._gamma.valueChanged.connect(self._on_config_changed)
        display_form.addRow("Gamma:", self._gamma)

        layout.addWidget(display_group)

        # Environment
        env_group = QGroupBox("Environment")
        env_form = QFormLayout(env_group)

        self._sky_color = QLineEdit()
        self._sky_color.setPlaceholderText("r,g,b")
        self._sky_color.editingFinished.connect(self._on_config_changed)
        env_form.addRow("Sky color:", self._sky_color)

        self._horizon_color = QLineEdit()
        self._horizon_color.setPlaceholderText("r,g,b")
        self._horizon_color.editingFinished.connect(self._on_config_changed)
        env_form.addRow("Horizon color:", self._horizon_color)

        self._ground_color = QLineEdit()
        self._ground_color.setPlaceholderText("r,g,b")
        self._ground_color.editingFinished.connect(self._on_config_changed)
        env_form.addRow("Ground color:", self._ground_color)

        self._env_intensity = QDoubleSpinBox()
        self._env_intensity.setRange(0.0, 5.0)
        self._env_intensity.setDecimals(2)
        self._env_intensity.setSingleStep(0.01)
        self._env_intensity.valueChanged.connect(self._on_config_changed)
        env_form.addRow("Intensity:", self._env_intensity)

        self._sun_dir = QLineEdit()
        self._sun_dir.setPlaceholderText("x,y,z")
        self._sun_dir.editingFinished.connect(self._on_config_changed)
        env_form.addRow("Sun dir:", self._sun_dir)

        layout.addWidget(env_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Loading / syncing
    # ------------------------------------------------------------------

    def load_config(self, config: SdfProjectConfig) -> None:
        self._config = config
        self._block_signals(True)

        self._integrator.setCurrentText(config.integrator)
        self._debug_view.setCurrentText(config.debug_view)

        self._max_steps.setValue(config.max_steps)
        self._max_distance.setValue(config.max_distance)
        self._hit_epsilon.setValue(config.hit_epsilon)
        self._step_scale.setValue(config.step_scale)
        self._normal_epsilon.setValue(config.normal_epsilon)
        self._shadow_steps.setValue(config.shadow_steps)
        self._shadow_epsilon.setValue(config.shadow_epsilon)
        self._camera_fov.setValue(config.camera_fov)

        self._max_bounces.setValue(config.max_bounces)
        self._samples_per_frame.setValue(config.samples_per_frame)
        self._target_samples.setValue(config.target_samples)
        self._rr_start_bounce.setValue(config.rr_start_bounce)
        self._firefly_clamp.setValue(config.firefly_clamp)

        self._exposure.setValue(config.exposure)
        self._tone_map.setCurrentText(config.tone_map)
        self._gamma.setValue(config.gamma)

        self._sky_color.setText(",".join(str(v) for v in config.sky_color))
        self._horizon_color.setText(",".join(str(v) for v in config.horizon_color))
        self._ground_color.setText(",".join(str(v) for v in config.ground_color))
        self._env_intensity.setValue(config.env_intensity)
        self._sun_dir.setText(",".join(str(v) for v in config.sun_dir))

        self._update_enabled_states()
        self._block_signals(False)

    def get_config(self) -> SdfProjectConfig:
        cfg = self._config
        cfg.integrator = self._integrator.currentText()
        cfg.debug_view = self._debug_view.currentText()

        cfg.max_steps = self._max_steps.value()
        cfg.max_distance = self._max_distance.value()
        cfg.hit_epsilon = self._hit_epsilon.value()
        cfg.step_scale = self._step_scale.value()
        cfg.normal_epsilon = self._normal_epsilon.value()
        cfg.shadow_steps = self._shadow_steps.value()
        cfg.shadow_epsilon = self._shadow_epsilon.value()
        cfg.camera_fov = self._camera_fov.value()

        cfg.max_bounces = self._max_bounces.value()
        cfg.samples_per_frame = self._samples_per_frame.value()
        cfg.target_samples = self._target_samples.value()
        cfg.rr_start_bounce = self._rr_start_bounce.value()
        cfg.firefly_clamp = self._firefly_clamp.value()

        cfg.exposure = self._exposure.value()
        cfg.tone_map = self._tone_map.currentText()
        cfg.gamma = self._gamma.value()

        cfg.sky_color = self._parse_vec3(self._sky_color.text(), cfg.sky_color)
        cfg.horizon_color = self._parse_vec3(self._horizon_color.text(), cfg.horizon_color)
        cfg.ground_color = self._parse_vec3(self._ground_color.text(), cfg.ground_color)
        cfg.env_intensity = self._env_intensity.value()
        cfg.sun_dir = self._parse_vec3(self._sun_dir.text(), cfg.sun_dir)

        return cfg

    def set_sample_count(self, current: int) -> None:
        target = self._target_samples.value()
        self._sample_label.setText(f"Samples: {current} / {target}")

    def is_paused(self) -> bool:
        return self._paused

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_integrator_changed(self, value: str) -> None:
        self._update_enabled_states()
        self._config.integrator = value
        # Integrator changes restart the renderer, which bumps the revision.
        # Avoid double revision bumps by only emitting integrator_changed.
        self.integrator_changed.emit(value)

    def _on_debug_view_changed(self, value: str) -> None:
        self._config.debug_view = value
        self.debug_view_changed.emit(value)
        self.config_changed.emit()

    def _on_config_changed(self) -> None:
        self._config = self.get_config()
        self.config_changed.emit()

    def _on_pause_toggled(self, paused: bool) -> None:
        self._paused = paused
        self._pause_btn.setText("Resume" if paused else "Pause")
        self.pause_toggled.emit(paused)

    def _update_enabled_states(self) -> None:
        is_pt = self._integrator.currentText() == "pathtrace"
        self._max_bounces.setEnabled(is_pt)
        self._samples_per_frame.setEnabled(is_pt)
        self._target_samples.setEnabled(is_pt)
        self._firefly_clamp.setEnabled(is_pt)
        self._reset_btn.setEnabled(is_pt)
        self._pause_btn.setEnabled(is_pt)

    def _block_signals(self, block: bool) -> None:
        for w in [
            self._integrator, self._debug_view,
            self._max_steps, self._max_distance, self._hit_epsilon,
            self._step_scale, self._normal_epsilon,
            self._shadow_steps, self._shadow_epsilon, self._camera_fov,
            self._max_bounces, self._samples_per_frame, self._target_samples,
            self._rr_start_bounce, self._firefly_clamp,
            self._exposure, self._tone_map, self._gamma,
            self._sky_color, self._horizon_color, self._ground_color,
            self._env_intensity, self._sun_dir,
        ]:
            w.blockSignals(block)

    @staticmethod
    def _parse_vec3(text: str, fallback: list[float]) -> list[float]:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) == 3:
            try:
                return [float(p) for p in parts]
            except ValueError:
                pass
        return list(fallback)
