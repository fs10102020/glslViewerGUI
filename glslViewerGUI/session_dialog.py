# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QPushButton,
    QDialogButtonBox, QLabel, QGroupBox, QListWidget, QMessageBox,
    QFileDialog,
)

from session_config import RenderSessionConfig


class SessionDialog(QDialog):
    def __init__(self, config: RenderSessionConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Session Settings")
        self.resize(560, 560)
        self._config = config

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_window_tab()
        self._build_renderer_tab()
        self._build_paths_tab()
        self._build_advanced_tab()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    # ------------------------------------------------------------------
    def _build_window_tab(self) -> None:
        tab = QWidget()
        form = QFormLayout(tab)

        self._win_width = QSpinBox()
        self._win_width.setRange(0, 4096)
        self._win_width.setValue(self._config.window_width or 0)
        self._win_width.setSpecialValueText("Default")
        form.addRow("Width:", self._win_width)

        self._win_height = QSpinBox()
        self._win_height.setRange(0, 4096)
        self._win_height.setValue(self._config.window_height or 0)
        self._win_height.setSpecialValueText("Default")
        form.addRow("Height:", self._win_height)

        self._win_size = QSpinBox()
        self._win_size.setRange(0, 4096)
        self._win_size.setValue(self._config.window_size or 0)
        self._win_size.setSpecialValueText("Default")
        form.addRow("Square Size:", self._win_size)

        self._fullscreen = QCheckBox("Fullscreen")
        self._fullscreen.setChecked(self._config.fullscreen)
        form.addRow(self._fullscreen)

        self._screensaver = QCheckBox("Screensaver mode")
        self._screensaver.setChecked(self._config.screensaver)
        form.addRow(self._screensaver)

        self._undecorated = QCheckBox("Undecorated window")
        self._undecorated.setChecked(self._config.undecorated)
        form.addRow(self._undecorated)

        self._nocursor = QCheckBox("Hide cursor")
        self._nocursor.setChecked(self._config.nocursor)
        form.addRow(self._nocursor)

        self._headless = QCheckBox("Headless")
        self._headless.setChecked(self._config.headless)
        form.addRow(self._headless)

        self._tabs.addTab(tab, "Window")

    # ------------------------------------------------------------------
    def _build_renderer_tab(self) -> None:
        tab = QWidget()
        form = QFormLayout(tab)

        self._msaa = QCheckBox("Enable MSAA (4x)")
        self._msaa.setChecked(self._config.msaa)
        form.addRow(self._msaa)

        self._fxaa = QCheckBox("Enable FXAA")
        self._fxaa.setChecked(self._config.fxaa)
        form.addRow(self._fxaa)

        self._full_fps = QCheckBox("Full FPS (uncapped)")
        self._full_fps.setChecked(self._config.full_fps)
        form.addRow(self._full_fps)

        self._fps = QSpinBox()
        self._fps.setRange(0, 240)
        self._fps.setValue(self._config.fps)
        self._fps.setSpecialValueText("Default")
        form.addRow("Target FPS:", self._fps)

        self._verbose = QCheckBox("Verbose output")
        self._verbose.setChecked(self._config.verbose)
        form.addRow(self._verbose)

        self._vflip = QCheckBox("Use backend --vFlip (disable default vertical flip)")
        self._vflip.setChecked(self._config.vflip)
        form.addRow(self._vflip)

        self._osc_port = QSpinBox()
        self._osc_port.setRange(0, 65535)
        self._osc_port.setValue(self._config.osc_port or 0)
        self._osc_port.setSpecialValueText("None")
        form.addRow("OSC Port:", self._osc_port)

        self._life_coding = QCheckBox("Life-coding mode (always-on-top billboard)")
        self._life_coding.setChecked(self._config.life_coding)
        form.addRow(self._life_coding)

        self._tabs.addTab(tab, "Renderer")

    # ------------------------------------------------------------------
    def _build_paths_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Include paths
        inc_group = QGroupBox("Include Paths")
        inc_layout = QVBoxLayout(inc_group)
        self._inc_list = QListWidget()
        for d in self._config.include_dirs:
            self._inc_list.addItem(d)
        inc_layout.addWidget(self._inc_list)
        inc_btns = QHBoxLayout()
        inc_add = QPushButton("Add")
        inc_add.clicked.connect(self._on_add_include)
        inc_rm = QPushButton("Remove")
        inc_rm.clicked.connect(self._on_remove_include)
        inc_btns.addWidget(inc_add)
        inc_btns.addWidget(inc_rm)
        inc_btns.addStretch()
        inc_layout.addLayout(inc_btns)
        layout.addWidget(inc_group)

        # Defines
        def_group = QGroupBox("Startup Defines")
        def_layout = QVBoxLayout(def_group)
        self._def_list = QListWidget()
        for k, v in self._config.defines.items():
            self._def_list.addItem(f"{k}={v}" if v else k)
        def_layout.addWidget(self._def_list)
        def_btns = QHBoxLayout()
        def_add = QPushButton("Add")
        def_add.clicked.connect(self._on_add_define)
        def_rm = QPushButton("Remove")
        def_rm.clicked.connect(self._on_remove_define)
        def_btns.addWidget(def_add)
        def_btns.addWidget(def_rm)
        def_btns.addStretch()
        def_layout.addLayout(def_btns)
        layout.addWidget(def_group)

        layout.addStretch()
        self._tabs.addTab(tab, "Paths")

    # ------------------------------------------------------------------
    def _build_advanced_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self._gl_major = QSpinBox()
        self._gl_major.setRange(0, 9)
        self._gl_major.setValue(self._config.gl_major or 0)
        self._gl_major.setSpecialValueText("Default")
        form.addRow("GL Major:", self._gl_major)

        self._gl_minor = QSpinBox()
        self._gl_minor.setRange(0, 9)
        self._gl_minor.setValue(self._config.gl_minor or 0)
        self._gl_minor.setSpecialValueText("Default")
        form.addRow("GL Minor:", self._gl_minor)

        self._quilt = QSpinBox()
        self._quilt.setRange(-1, 15)
        self._quilt.setValue(self._config.quilt if self._config.quilt is not None else -1)
        self._quilt.setSpecialValueText("None")
        form.addRow("HoloPlay Quilt:", self._quilt)

        self._quilt_tile = QSpinBox()
        self._quilt_tile.setRange(-1, 1024)
        self._quilt_tile.setValue(self._config.quilt_tile if self._config.quilt_tile is not None else -1)
        self._quilt_tile.setSpecialValueText("None")
        form.addRow("HoloPlay Quilt Tile:", self._quilt_tile)

        self._lenticular_path = QLineEdit(self._config.lenticular_path)
        form.addRow("Lenticular JSON:", self._lenticular_path)

        self._display_device = QLineEdit(self._config.display_device)
        self._display_device.setPlaceholderText("/dev/dri/card1")
        form.addRow("GBM Display Device:", self._display_device)

        self._mouse_device = QLineEdit(self._config.mouse_device)
        self._mouse_device.setPlaceholderText("/dev/input/mice")
        form.addRow("Mouse Device:", self._mouse_device)

        self._video_device = QLineEdit(self._config.video_device)
        self._video_device.setPlaceholderText("0")
        form.addRow("Startup Video Device:", self._video_device)

        self._audio_device = QLineEdit(self._config.audio_device)
        self._audio_device.setPlaceholderText("-1")
        form.addRow("Startup Audio Device:", self._audio_device)

        self._cubemap_sh = QCheckBox("Use -sh spherical harmonics for environment (hidden)")
        self._cubemap_sh.setChecked(self._config.cubemap_sh)
        form.addRow(self._cubemap_sh)

        layout.addLayout(form)
        layout.addStretch()
        self._tabs.addTab(tab, "Advanced")

    # ------------------------------------------------------------------
    def _on_add_include(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Add Include Folder",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if d:
            self._inc_list.addItem(d)

    def _on_remove_include(self) -> None:
        item = self._inc_list.currentItem()
        if item:
            self._inc_list.takeItem(self._inc_list.row(item))

    def _on_add_define(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Add Define", "NAME=VALUE or NAME:")
        if ok and text.strip():
            self._def_list.addItem(text.strip())

    def _on_remove_define(self) -> None:
        item = self._def_list.currentItem()
        if item:
            self._def_list.takeItem(self._def_list.row(item))

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        self._config.window_width = self._win_width.value() or None
        self._config.window_height = self._win_height.value() or None
        self._config.window_size = self._win_size.value() or None
        self._config.fullscreen = self._fullscreen.isChecked()
        self._config.screensaver = self._screensaver.isChecked()
        self._config.undecorated = self._undecorated.isChecked()
        self._config.nocursor = self._nocursor.isChecked()
        self._config.headless = self._headless.isChecked()
        self._config.msaa = self._msaa.isChecked()
        self._config.fxaa = self._fxaa.isChecked()
        self._config.full_fps = self._full_fps.isChecked()
        self._config.fps = self._fps.value()
        self._config.verbose = self._verbose.isChecked()
        self._config.vflip = self._vflip.isChecked()
        self._config.osc_port = self._osc_port.value() or None
        self._config.life_coding = self._life_coding.isChecked()

        self._config.gl_major = self._gl_major.value() or None
        self._config.gl_minor = self._gl_minor.value() or None
        quilt = self._quilt.value()
        self._config.quilt = quilt if quilt >= 0 else None
        quilt_tile = self._quilt_tile.value()
        self._config.quilt_tile = quilt_tile if quilt_tile >= 0 else None
        self._config.lenticular_path = self._lenticular_path.text().strip()
        self._config.display_device = self._display_device.text().strip()
        self._config.mouse_device = self._mouse_device.text().strip()
        self._config.video_device = self._video_device.text().strip()
        self._config.audio_device = self._audio_device.text().strip()
        self._config.cubemap_sh = self._cubemap_sh.isChecked()

        self._config.include_dirs = [
            self._inc_list.item(i).text()
            for i in range(self._inc_list.count())
        ]

        defines: dict[str, str] = {}
        for i in range(self._def_list.count()):
            text = self._def_list.item(i).text()
            if "=" in text:
                k, v = text.split("=", 1)
                defines[k] = v
            else:
                defines[text] = ""
        self._config.defines = defines

        self.accept()

    # ------------------------------------------------------------------
    def config(self) -> RenderSessionConfig:
        return self._config
