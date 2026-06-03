import os
import re
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox,
)

from render_bridge import RenderBridge
from uniform_panel import UniformPanel
from console_panel import ConsolePanel
from camera_panel import CameraPanel
from recording_panel import RecordingPanel
from preset_manager import PresetPanel, save_preset
from shader_editor import GLSLEditor
from glslViewer_config import DEFAULT_SHADER
from shader_parser import parse_uniforms


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlslViewerGUI \u2014 Shader Mission Control")
        self.resize(900, 720)

        self._bridge = RenderBridge(self)
        self._bridge.process_started.connect(self._on_process_started)
        self._bridge.process_stopped.connect(self._on_process_stopped)
        self._bridge.stdout_received.connect(self._on_stdout)
        self._bridge.stderr_received.connect(self._on_stderr)
        self._bridge.process_crashed.connect(self._on_process_crashed)
        self._bridge.process_gave_up.connect(self._on_process_gave_up)

        self._error_buffer: list[tuple[float, str]] = []
        self._error_flush_timer = QTimer(self)
        self._error_flush_timer.setSingleShot(True)
        self._error_flush_timer.timeout.connect(self._flush_errors)

        self._build_menus()
        self._build_central()
        self._build_docks()

        self._bridge.start(DEFAULT_SHADER)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")

        open_frag = QAction("&Open Fragment Shader\u2026", self)
        open_frag.triggered.connect(self._open_shader)
        open_frag.setShortcut(QKeySequence("Ctrl+O"))
        file_menu.addAction(open_frag)

        open_vert = QAction("Open &Vertex Shader\u2026", self)
        open_vert.triggered.connect(self._open_vertex_shader)
        file_menu.addAction(open_vert)

        open_geom = QAction("Open &Geometry\u2026", self)
        open_geom.triggered.connect(self._open_geometry)
        file_menu.addAction(open_geom)

        file_menu.addSeparator()

        reload_act = QAction("&Reload", self)
        reload_act.triggered.connect(self._bridge.reload_current)
        reload_act.setShortcut(QKeySequence("F5"))
        file_menu.addAction(reload_act)

        file_menu.addSeparator()

        exit_act = QAction("E&xit", self)
        exit_act.triggered.connect(self.close)
        exit_act.setShortcut(QKeySequence("Ctrl+Q"))
        file_menu.addAction(exit_act)

        geom_menu = bar.addMenu("&Geometry")
        for label, cmd in [
            ("&Plane", "plane"),
            ("&Sphere", "sphere"),
            ("&Icosphere", "icosphere"),
            ("&Cylinder", "cylinder"),
        ]:
            act = QAction(label, self)
            act.triggered.connect(lambda _c=cmd: self._bridge.send_command(_c))
            geom_menu.addAction(act)

        view_menu = bar.addMenu("&View")
        self._show_uniforms_act = view_menu.addAction("&Uniforms")
        self._show_uniforms_act.setCheckable(True)
        self._show_uniforms_act.setChecked(True)
        self._show_uniforms_act.triggered.connect(self._toggle_uniforms)

        self._show_camera_act = view_menu.addAction("&Camera")
        self._show_camera_act.setCheckable(True)
        self._show_camera_act.setChecked(True)
        self._show_camera_act.triggered.connect(self._toggle_camera)

        self._show_console_act = view_menu.addAction("&Console")
        self._show_console_act.setCheckable(True)
        self._show_console_act.setChecked(True)
        self._show_console_act.triggered.connect(self._toggle_console)

        self._show_recording_act = view_menu.addAction("&Recording")
        self._show_recording_act.setCheckable(True)
        self._show_recording_act.setChecked(True)
        self._show_recording_act.triggered.connect(self._toggle_recording)

        self._show_presets_act = view_menu.addAction("&Presets")
        self._show_presets_act.setCheckable(True)
        self._show_presets_act.setChecked(True)
        self._show_presets_act.triggered.connect(self._toggle_presets)

        view_menu.addSeparator()
        self._theme_menu = view_menu.addMenu("&Theme")
        for theme_name in ["System", "Dark", "Light"]:
            act = QAction(theme_name, self)
            act.triggered.connect(lambda _t=theme_name: self._apply_theme(_t.lower()))
            self._theme_menu.addAction(act)

    def _build_central(self) -> None:
        self._editor = GLSLEditor(self)
        self._editor.text_saved.connect(self._on_editor_saved)
        self.setCentralWidget(self._editor)

    def _build_docks(self) -> None:
        self._uniform_panel = UniformPanel(self)
        self._uniform_panel.uniform_changed.connect(self._on_uniform_changed)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._uniform_panel)

        self._camera_panel = CameraPanel(self)
        self._camera_panel.camera_command.connect(self._bridge.send_command)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._camera_panel)

        self._console_panel = ConsolePanel(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._console_panel)

        self._recording_panel = RecordingPanel(self)
        self._recording_panel.screenshot_requested.connect(self._bridge.screenshot)
        self._recording_panel.sequence_requested.connect(
            lambda p, f, t, fps: self._bridge.sequence(p, f, t, fps)
        )
        self._recording_panel.record_requested.connect(
            lambda p, f, t, fps: self._bridge.record(p, f, t, fps)
        )
        self._bridge.recording_progress.connect(self._recording_panel.set_progress)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._recording_panel)

        self._preset_panel = PresetPanel(self)
        self._preset_panel.preset_saved.connect(self._on_preset_saved)
        self._preset_panel.preset_loaded.connect(self._on_preset_loaded)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._preset_panel)

    def _open_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Fragment Shader", "",
            "Fragment Shaders (*.frag *.fs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            try:
                self._bridge.load_shader(path, self._bridge.vert_path, self._bridge.geom_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_vertex_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Vertex Shader", "",
            "Vertex Shaders (*.vert *.vs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            try:
                frag = self._bridge.shader_path or DEFAULT_SHADER
                self._bridge.load_shader(frag, path, self._bridge.geom_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _open_geometry(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Geometry", "",
            "Geometry (*.ply *.obj *.stl *.glb *.gltf *.splat);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            try:
                frag = self._bridge.shader_path or DEFAULT_SHADER
                self._bridge.load_shader(frag, self._bridge.vert_path, path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _toggle_uniforms(self, visible: bool) -> None:
        self._uniform_panel.setVisible(visible)

    def _toggle_camera(self, visible: bool) -> None:
        self._camera_panel.setVisible(visible)

    def _toggle_console(self, visible: bool) -> None:
        self._console_panel.setVisible(visible)

    def _toggle_recording(self, visible: bool) -> None:
        self._recording_panel.setVisible(visible)

    def _toggle_presets(self, visible: bool) -> None:
        self._preset_panel.setVisible(visible)

    def _on_process_started(self) -> None:
        path = self._bridge.shader_path or DEFAULT_SHADER
        if os.path.exists(path):
            self._editor.set_file_path(path)
            self._editor.set_source(self._bridge.shader_source)
            self._refresh_uniforms_from_file(path)

    def _on_process_stopped(self) -> None:
        pass

    def _on_stdout(self, text: str) -> None:
        self._console_panel.append(text)

    def _on_stderr(self, text: str) -> None:
        now = time.time()
        self._error_buffer.append((now, text))
        if not self._error_flush_timer.isActive():
            self._error_flush_timer.start(2000)

    def _flush_errors(self) -> None:
        now = time.time()
        cutoff = now - 2.0
        self._error_buffer = [(t, msg) for t, msg in self._error_buffer if t >= cutoff]

        if len(self._error_buffer) > 5:
            self._console_panel.append_line(
                f"[Multiple errors ({len(self._error_buffer)}) received in last 2s — see console above]"
            )
        else:
            for _, msg in self._error_buffer:
                self._console_panel.append(msg)
                self._editor.apply_errors(msg)

        self._error_buffer.clear()

    def _on_process_crashed(self, exit_code: int, exit_status: int) -> None:
        self._console_panel.append_line(
            f"WARNING: glslViewer crashed (exit code {exit_code}, status {exit_status}). Restarting..."
        )

    def _on_process_gave_up(self) -> None:
        self._console_panel.append_line(
            "ERROR: glslViewer crashed repeatedly. Falling back to default shader."
        )
        QMessageBox.warning(
            self, "Renderer Crash",
            "glslViewer crashed multiple times in quick succession.\n\n"
            "Falling back to the default shader. If this persists, check:\n"
            "  • Your graphics drivers\n"
            "  • Whether glslViewer binary exists and is executable"
        )
        try:
            self._bridge.load_shader(DEFAULT_SHADER)
        except Exception as e:
            QMessageBox.critical(self, "Fatal Error", f"Could not load default shader: {e}")

    def _on_editor_saved(self, path: str) -> None:
        self._bridge.reload_current()
        self._refresh_uniforms_from_file(path)

    def _on_uniform_changed(self, name: str, value) -> None:
        self._bridge.set_uniform(name, value)

    def _refresh_uniforms_from_file(self, path: str) -> None:
        try:
            with open(path) as f:
                source = f.read()
            self._uniform_panel.load_from_source(source)
            self._check_shadertoy_uniforms(source)
        except Exception as e:
            self._console_panel.append_line(f"Error parsing uniforms: {e}")

    def _check_shadertoy_uniforms(self, source: str) -> None:
        shadertoy_names = {"iTime", "iResolution", "iMouse", "iFrame"}
        found = {name for name in shadertoy_names if re.search(rf"\\b{name}\\b", source)}
        if found:
            self._console_panel.append_line(
                f"WARNING: Shader uses Shadertoy uniforms ({', '.join(sorted(found))}). "
                "glslViewer auto-generates u_time, u_resolution, u_mouse, and u_frame. "
                "Rename these uniforms or they will remain at default values (black screen)."
            )

    def _on_preset_saved(self, name: str) -> None:
        data = {
            "shader_path": self._bridge.shader_path,
            "vert_path": self._bridge.vert_path,
            "geom_path": self._bridge.geom_path,
            "uniforms": self._uniform_panel.all_values(),
            "camera": self._camera_panel.get_state(),
        }
        try:
            save_preset(name, data)
            self._console_panel.append_line(f"Preset saved: {name}")
        except Exception as e:
            self._console_panel.append_line(f"Error saving preset: {e}")

    def _on_preset_loaded(self, name: str, data: dict) -> None:
        shader = data.get("shader_path")
        vert = data.get("vert_path")
        geom = data.get("geom_path")
        if shader and os.path.exists(shader):
            try:
                self._bridge.load_shader(shader, vert, geom)
            except Exception as e:
                self._console_panel.append_line(f"Error loading shader from preset: {e}")
        else:
            self._console_panel.append_line(
                f"Preset '{name}': shader not found, applying uniforms only."
            )

        uniforms = data.get("uniforms", {})
        if uniforms:
            self._uniform_panel.set_values(uniforms)
            for uname, uval in uniforms.items():
                self._bridge.set_uniform(uname, uval)

        camera = data.get("camera", {})
        if camera:
            self._camera_panel.set_state(camera)

        self._console_panel.append_line(f"Preset loaded: {name}")

    def _apply_theme(self, theme_name: str) -> None:
        from PyQt6.QtCore import QSettings
        try:
            from themes import apply_theme
            apply_theme(self, theme_name)
            QSettings("glslViewer", "GlslViewerGUI").setValue("theme", theme_name)
        except Exception as e:
            self._console_panel.append_line(f"Theme error: {e}")

    def closeEvent(self, event) -> None:
        self._bridge.stop()
        event.accept()
