import os
import re
import time

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolBar,
)

from assets_panel import AssetsPanel
from camera_panel import CameraPanel
from commands import build_camera_sequence, build_include_path, build_load_model, build_sequence_uniform
from console_panel import ConsolePanel
from defines_panel import DefinesPanel
from dependency_viewer_panel import DependencyViewerPanel
from glslViewer_config import DEFAULT_SHADER
from include_panel import IncludePanel
from inspector_panel import InspectorPanel
from pipeline_panel import PipelinePanel
from preset_manager import PresetPanel, save_preset
from recording_panel import RecordingPanel
from render_bridge import RenderBridge
from runtime_controls_panel import RuntimeControlsPanel
from scene_panel import ScenePanel
from session_config import AssetSpec, RenderSessionConfig, ShaderProgramSpec
from session_dialog import SessionDialog
from shader_diagnostics import diagnose_shader_pair, diagnose_single_frag
from shader_editor import GLSLEditor
from shader_parser import parse_uniforms
from streams_panel import StreamsPanel
from themes import apply_theme
from uniform_panel import UniformPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlslViewerGUI - Shader Mission Control")
        self.setMinimumSize(960, 640)
        self.resize(1400, 900)

        self._session_config = RenderSessionConfig(frag_path=DEFAULT_SHADER)
        self._error_buffer: list[tuple[float, str]] = []
        self._error_flush_timer = QTimer(self)
        self._error_flush_timer.setSingleShot(True)
        self._error_flush_timer.timeout.connect(self._flush_errors)

        self._bridge = RenderBridge(self)
        self._bridge.process_started.connect(self._on_process_started)
        self._bridge.process_stopped.connect(self._on_process_stopped)
        self._bridge.stdout_received.connect(self._on_stdout)
        self._bridge.stderr_received.connect(self._on_stderr)
        self._bridge.process_crashed.connect(self._on_process_crashed)
        self._bridge.process_gave_up.connect(self._on_process_gave_up)

        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AllowNestedDocks
        )
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.BottomDockWidgetArea)

        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_docks()

        apply_theme(self, QSettings("glslViewer", "GlslViewerGUI").value("theme", "dark"))
        self._bridge.start(DEFAULT_SHADER)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        open_frag = QAction("&Open Fragment Shader...", self)
        open_frag.triggered.connect(self._open_shader)
        open_frag.setShortcut(QKeySequence("Ctrl+O"))
        file_menu.addAction(open_frag)

        open_vert = QAction("Open &Vertex Shader...", self)
        open_vert.triggered.connect(self._open_vertex_shader)
        file_menu.addAction(open_vert)

        open_geom = QAction("Open &Geometry...", self)
        open_geom.triggered.connect(self._open_geometry)
        file_menu.addAction(open_geom)
        file_menu.addSeparator()

        session_act = QAction("Session &Settings...", self)
        session_act.triggered.connect(self._open_session_settings)
        file_menu.addAction(session_act)

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
            act.triggered.connect(lambda checked=False, _cmd=cmd: self._safe_send(_cmd))
            geom_menu.addAction(act)

        view_menu = bar.addMenu("&View")
        for dock_name, attr in [
            ("Right Panels", "_right_dock"),
            ("Console", "_console_dock"),
            ("Recording", "_recording_dock"),
            ("Presets", "_preset_dock"),
        ]:
            act = QAction(dock_name, self)
            act.setCheckable(True)
            act.setChecked(True)
            act.triggered.connect(lambda visible, _attr=attr: getattr(self, _attr).setVisible(visible))
            view_menu.addAction(act)

        theme_menu = view_menu.addMenu("&Theme")
        for theme_name in ["Dark", "Light", "System"]:
            act = QAction(theme_name, self)
            act.triggered.connect(lambda checked=False, _t=theme_name.lower(): self._apply_theme(_t))
            theme_menu.addAction(act)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("MainToolBar")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        for label, handler in [
            ("Open", self._open_shader),
            ("Reload", self._bridge.reload_current),
            ("Session", self._open_session_settings),
            ("Restart", self._restart_renderer),
        ]:
            act = QAction(label, self)
            act.triggered.connect(handler)
            toolbar.addAction(act)

    def _build_central(self) -> None:
        self._editor_tabs = QTabWidget(self)
        self._frag_editor = GLSLEditor(self)
        self._vert_editor = GLSLEditor(self)
        self._frag_editor.text_saved.connect(self._on_editor_saved)
        self._vert_editor.text_saved.connect(self._on_editor_saved)
        self._editor_tabs.addTab(self._frag_editor, "Fragment")
        self._editor_tabs.addTab(self._vert_editor, "Vertex")
        self._program_label = QLabel("(default)")
        self._editor_tabs.setCornerWidget(self._program_label)
        self.setCentralWidget(self._editor_tabs)

    def _build_docks(self) -> None:
        self._uniform_panel = UniformPanel(self)
        self._uniform_panel.uniform_changed.connect(self._on_uniform_changed)

        self._camera_panel = CameraPanel(self)
        self._camera_panel.camera_command.connect(self._safe_send)

        self._runtime_panel = RuntimeControlsPanel(self)
        self._runtime_panel.command_requested.connect(self._safe_send)

        self._assets_panel = AssetsPanel(self)
        self._assets_panel.asset_added.connect(self._on_asset_added)
        self._assets_panel.asset_refresh_requested.connect(self._safe_send)

        self._streams_panel = StreamsPanel(self)
        self._streams_panel.command_requested.connect(self._safe_send)

        self._defines_panel = DefinesPanel(self)
        self._defines_panel.define_requested.connect(self._on_define_requested)
        self._defines_panel.undefine_requested.connect(lambda name: self._safe_send(f"undefine,{name}"))

        self._include_panel = IncludePanel(self)
        self._include_panel.include_added.connect(lambda path: self._safe_send(build_include_path(path)))
        self._include_panel.restart_requested.connect(self._restart_renderer)

        self._dependency_panel = DependencyViewerPanel(self)
        self._dependency_panel.query_requested.connect(lambda cmd, payload: self._safe_send(cmd))

        self._pipeline_panel = PipelinePanel(self)
        self._pipeline_panel.command_requested.connect(self._safe_send)
        self._pipeline_panel.define_requested.connect(self._on_define_requested)

        self._scene_panel = ScenePanel(self)
        self._scene_panel.command_requested.connect(self._safe_send)

        self._inspector_panel = InspectorPanel(self)
        self._inspector_panel.query_requested.connect(lambda cmd, payload: self._safe_send(cmd))

        self._right_tabs = QTabWidget(self)
        self._right_tabs.setMinimumWidth(0)
        self._right_tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self._right_tabs.addTab(self._scroll_panel(self._uniform_panel), "Uniforms")
        self._right_tabs.addTab(self._scroll_panel(self._camera_panel), "Camera")
        self._right_tabs.addTab(self._scroll_panel(self._runtime_panel), "Runtime")

        assets_tabs = QTabWidget(self)
        assets_tabs.setMinimumWidth(0)
        assets_tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        assets_tabs.addTab(self._scroll_panel(self._assets_panel), "Assets")
        assets_tabs.addTab(self._scroll_panel(self._streams_panel), "Streams")
        self._right_tabs.addTab(assets_tabs, "Assets")

        shader_tabs = QTabWidget(self)
        shader_tabs.setMinimumWidth(0)
        shader_tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        shader_tabs.addTab(self._scroll_panel(self._defines_panel), "Defines")
        shader_tabs.addTab(self._scroll_panel(self._include_panel), "Includes")
        shader_tabs.addTab(self._scroll_panel(self._dependency_panel), "Dependencies")
        self._right_tabs.addTab(shader_tabs, "Shader")

        pipeline_tabs = QTabWidget(self)
        pipeline_tabs.setMinimumWidth(0)
        pipeline_tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        pipeline_tabs.addTab(self._scroll_panel(self._pipeline_panel), "Pipeline")
        pipeline_tabs.addTab(self._scroll_panel(self._scene_panel), "Scene")
        pipeline_tabs.addTab(self._scroll_panel(self._inspector_panel), "Inspector")
        self._right_tabs.addTab(pipeline_tabs, "Pipeline")

        self._right_dock = QDockWidget("Controls", self)
        self._right_dock.setObjectName("RightDock")
        self._right_dock.setWidget(self._right_tabs)
        self._right_dock.setMinimumWidth(220)
        self._right_dock.setMaximumWidth(16777215)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._right_dock)

        self._console_panel = ConsolePanel(self)
        self._console_dock = QDockWidget("Console", self)
        self._console_dock.setObjectName("ConsoleDock")
        self._console_dock.setWidget(self._console_panel)
        self._console_dock.setMaximumHeight(16777215)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._console_dock)

        self._recording_panel = RecordingPanel(self)
        self._recording_panel.screenshot_requested.connect(self._bridge.screenshot)
        self._recording_panel.sequence_requested.connect(self._bridge.sequence)
        self._recording_panel.record_requested.connect(self._bridge.record)
        self._bridge.recording_progress.connect(self._recording_panel.set_progress)
        recording_scroll = QScrollArea(self)
        recording_scroll.setWidgetResizable(True)
        recording_scroll.setWidget(self._recording_panel)
        self._recording_dock = QDockWidget("Recording", self)
        self._recording_dock.setObjectName("RecordingDock")
        self._recording_dock.setWidget(recording_scroll)
        self._recording_dock.setMaximumHeight(16777215)
        self.splitDockWidget(self._console_dock, self._recording_dock, Qt.Orientation.Horizontal)

        self._preset_panel = PresetPanel(self)
        self._preset_panel.preset_saved.connect(self._on_preset_saved)
        self._preset_panel.preset_loaded.connect(self._on_preset_loaded)
        self._preset_dock = QDockWidget("Presets", self)
        self._preset_dock.setObjectName("PresetDock")
        self._preset_dock.setWidget(self._preset_panel)
        self._preset_dock.setMaximumHeight(16777215)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._preset_dock)
        self.tabifyDockWidget(self._recording_dock, self._preset_dock)
        self._recording_dock.raise_()
        self.resizeDocks([self._console_dock, self._recording_dock], [1, 2], Qt.Orientation.Horizontal)
        self.resizeDocks([self._console_dock, self._recording_dock], [160, 160], Qt.Orientation.Vertical)

    def _scroll_panel(self, panel):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(0)
        scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        scroll.setWidget(panel)
        panel.setMinimumWidth(0)
        panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        return scroll

    def _safe_send(self, command: str) -> None:
        if command:
            self._bridge.send_command(command)
            if hasattr(self, "_console_panel"):
                self._console_panel.append_line(f"> {command}")

    def _open_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Fragment Shader", "",
            "Fragment Shaders (*.frag *.fs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._load_program(ShaderProgramSpec.from_path(path))

    def _open_vertex_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Vertex Shader", "",
            "Vertex Shaders (*.vert *.vs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            program = ShaderProgramSpec.from_path(path)
            if not program.frag_path:
                program.frag_path = self._bridge.shader_path or DEFAULT_SHADER
            self._load_program(program)

    def _open_geometry(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Geometry", "",
            "Geometry (*.ply *.obj *.stl *.glb *.gltf *.splat);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._load_program(ShaderProgramSpec(
                frag_path=self._bridge.shader_path or DEFAULT_SHADER,
                vert_path=self._bridge.vert_path,
                model_path=path,
            ))

    def _load_program(self, program: ShaderProgramSpec) -> None:
        if not program.frag_path:
            program.frag_path = DEFAULT_SHADER
        try:
            self._bridge.load_shader(program.frag_path, program.vert_path, program.model_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _restart_renderer(self) -> None:
        self._bridge.start(self._bridge.shader_path or DEFAULT_SHADER, self._bridge.vert_path, self._bridge.geom_path)

    def _open_session_settings(self) -> None:
        dialog = SessionDialog(RenderSessionConfig.from_dict(self._session_config.to_dict()), self)
        if dialog.exec():
            self._session_config = dialog.config()
            self._bridge.apply_session_config(self._session_config)

    def _on_process_started(self) -> None:
        program = self._bridge.program
        self._program_label.setText(program.program_label)
        self._load_editor_file(self._frag_editor, program.frag_path)
        self._load_editor_file(self._vert_editor, program.vert_path)
        if program.frag_path:
            self._refresh_uniforms_from_file(program.frag_path)
        self._run_shader_diagnostics()

    def _load_editor_file(self, editor: GLSLEditor, path: str | None) -> None:
        editor.set_file_path(path)
        if path and os.path.exists(path):
            with open(path) as f:
                editor.set_source(f.read())
        else:
            editor.set_source("")

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
            self._console_panel.append_line(f"[Multiple errors ({len(self._error_buffer)}) received in last 2s]")
        else:
            for _, msg in self._error_buffer:
                self._console_panel.append(msg)
                self._frag_editor.apply_errors(msg)
                self._vert_editor.apply_errors(msg)
        self._error_buffer.clear()

    def _on_process_crashed(self, exit_code: int, exit_status: int) -> None:
        self._console_panel.append_line(
            f"WARNING: glslViewer crashed (exit code {exit_code}, status {exit_status}). Restarting..."
        )

    def _on_process_gave_up(self) -> None:
        self._console_panel.append_line("ERROR: glslViewer crashed repeatedly. Falling back to default shader.")
        QMessageBox.warning(self, "Renderer Crash", "glslViewer crashed repeatedly. Falling back to the default shader.")
        self._bridge.load_shader(DEFAULT_SHADER)

    def _on_editor_saved(self, path: str) -> None:
        self._bridge.reload_current()
        self._refresh_uniforms_from_file(path)
        self._run_shader_diagnostics()

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
        found = {name for name in shadertoy_names if re.search(rf"\b{name}\b", source)}
        if found:
            self._console_panel.append_line(
                f"WARNING: Shader uses Shadertoy uniforms ({', '.join(sorted(found))}). "
                "glslViewer auto-generates u_time, u_resolution, u_mouse, and u_frame."
            )

    def _run_shader_diagnostics(self) -> None:
        frag = self._frag_editor.source()
        vert = self._vert_editor.source()
        issues = diagnose_shader_pair(frag, vert) if vert else diagnose_single_frag(frag)
        for issue in issues:
            self._console_panel.append_line(f"DIAGNOSTIC: {issue}")

    def _on_define_requested(self, name: str, value: str) -> None:
        cmd = f"define,{name},{value}" if value else f"define,{name}"
        self._safe_send(cmd)

    def _on_asset_added(self, asset: AssetSpec) -> None:
        if asset.kind in {"sequence_uniform", "camera_sequence", "model"}:
            if asset.kind == "sequence_uniform":
                self._safe_send(build_sequence_uniform(asset.name, asset.path))
            elif asset.kind == "camera_sequence":
                self._safe_send(build_camera_sequence(asset.path))
            elif asset.kind == "model":
                self._safe_send(build_load_model(asset.path))
            return
        self._session_config.assets.append(asset)
        self._console_panel.append_line(f"Asset queued for next restart: {asset.kind} {asset.name} {asset.path}")

    def _on_preset_saved(self, name: str) -> None:
        data = {
            "shader_path": self._bridge.shader_path,
            "vert_path": self._bridge.vert_path,
            "geom_path": self._bridge.geom_path,
            "uniforms": self._uniform_panel.all_values(),
            "camera": self._camera_panel.get_state(),
            "session": self._session_config.to_dict(),
        }
        try:
            save_preset(name, data)
            self._console_panel.append_line(f"Preset saved: {name}")
        except Exception as e:
            self._console_panel.append_line(f"Error saving preset: {e}")

    def _on_preset_loaded(self, name: str, data: dict) -> None:
        session = data.get("session")
        if session:
            self._session_config = RenderSessionConfig.from_dict(session)
        shader = data.get("shader_path") or self._session_config.frag_path
        if shader and os.path.exists(shader):
            self._bridge.load_shader(shader, data.get("vert_path"), data.get("geom_path"))
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
        try:
            apply_theme(self, theme_name)
            QSettings("glslViewer", "GlslViewerGUI").setValue("theme", theme_name)
        except Exception as e:
            self._console_panel.append_line(f"Theme error: {e}")

    def closeEvent(self, event) -> None:
        self._bridge.stop()
        event.accept()
