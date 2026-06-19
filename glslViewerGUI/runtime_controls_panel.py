# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
from PySide6.QtCore import Qt, Signal, QSignalBlocker
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
        self._display_checkboxes: dict[str, QCheckBox] = {}
        for label, on_cmd, off_cmd, default in [
            ("Debug", build_debug(True), build_debug(False), False),
            ("Error Screen", build_error_screen(True), build_error_screen(False), False),
            ("Cursor", build_cursor(True), build_cursor(False), True),
            ("VSync", build_vsync(True), build_vsync(False), True),
            ("Full FPS", build_full_fps(True), build_full_fps(False), False),
        ]:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.toggled.connect(lambda v, _on=on_cmd, _off=off_cmd: self.command_requested.emit(_on if v else _off))
            self._display_checkboxes[label] = cb
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

    def set_display_state(self, label: str, value: bool | None) -> None:
        """Update a display checkbox without emitting commands (None = indeterminate).

        All signals on the checkbox are blocked while the state is being
        applied so the user (or this setter) cannot trigger a feedback loop
        where applying a backend state changes the checkbox, the change
        emits ``toggled``, the slot sends a command, and the backend
        re-emits the same state.
        """
        cb = self._display_checkboxes.get(label)
        if cb is None:
            return
        blocker = QSignalBlocker(cb)
        try:
            if value is None:
                cb.setTristate(True)
                cb.setCheckState(Qt.CheckState.PartiallyChecked)
            else:
                cb.setTristate(False)
                cb.setChecked(value)
        finally:
            del blocker
