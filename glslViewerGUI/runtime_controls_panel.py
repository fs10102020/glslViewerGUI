from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QGroupBox, QComboBox, QCheckBox, QLabel,
)
from commands import (
    build_plot, build_debug, build_error_screen, build_cursor,
    build_vsync, build_full_fps, build_fps, build_reset,
    build_track_start, build_track_stop, build_cubemap_toggle,
    build_cubemap_sh, build_sky_toggle,
)


class RuntimeControlsPanel(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RuntimeControlsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        plot_group = QGroupBox("Plot Overlay")
        plot_row = QHBoxLayout(plot_group)
        self._plot = QComboBox()
        self._plot.addItems(["off", "luma", "red", "green", "blue", "rgb", "fps", "ms"])
        self._plot.currentTextChanged.connect(
            lambda v: self.command_requested.emit(build_plot(v))
        )
        plot_row.addWidget(QLabel("Mode:"))
        plot_row.addWidget(self._plot)
        layout.addWidget(plot_group)

        display_group = QGroupBox("Display Toggles")
        disp_grid = QHBoxLayout(display_group)
        for label, on_cmd, off_cmd in [
            ("Debug", build_debug(True), build_debug(False)),
            ("Error Screen", build_error_screen(True), build_error_screen(False)),
            ("Cursor", build_cursor(True), build_cursor(False)),
            ("VSync", build_vsync(True), build_vsync(False)),
            ("Full FPS", build_full_fps(True), build_full_fps(False)),
        ]:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.toggled.connect(lambda v, _on=on_cmd, _off=off_cmd: self.command_requested.emit(_on if v else _off))
            disp_grid.addWidget(cb)
        layout.addWidget(display_group)

        time_group = QGroupBox("Time / Tracking")
        time_row = QHBoxLayout(time_group)
        reset_btn = QPushButton("Reset Time")
        reset_btn.setMaximumWidth(100)
        reset_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_reset()))
        track_start_btn = QPushButton("Track Start")
        track_start_btn.setMaximumWidth(100)
        track_start_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_track_start()))
        track_stop_btn = QPushButton("Track Stop")
        track_stop_btn.setMaximumWidth(100)
        track_stop_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_track_stop()))
        time_row.addWidget(reset_btn)
        time_row.addWidget(track_start_btn)
        time_row.addWidget(track_stop_btn)
        time_row.addStretch()
        layout.addWidget(time_group)

        env_group = QGroupBox("Environment")
        env_row = QHBoxLayout(env_group)
        cubemap_btn = QPushButton("Toggle Cubemap")
        cubemap_btn.setMaximumWidth(120)
        cubemap_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_cubemap_toggle()))
        sh_btn = QPushButton("Print SH")
        sh_btn.setMaximumWidth(90)
        sh_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_cubemap_sh()))
        sky_btn = QPushButton("Toggle Sky")
        sky_btn.setMaximumWidth(100)
        sky_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_sky_toggle()))
        env_row.addWidget(cubemap_btn)
        env_row.addWidget(sh_btn)
        env_row.addWidget(sky_btn)
        env_row.addStretch()
        layout.addWidget(env_group)

        layout.addStretch()
