# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import os
import re
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QDockWidget,
    QTabWidget, QScrollArea, QWidget, QLabel, QToolBar,
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
from file_classifier import classify_paths, build_session_from_plan
from session_config import (
    RenderSessionConfig, ShaderProgramSpec,
    ASSET_NAMED_TEXTURE, ASSET_STREAM_TEXTURE, ASSET_AUDIO, ASSET_MODEL,
    ASSET_CUBEMAP_SHOW, ASSET_CUBEMAP_ENV, ASSET_SEQUENCE_UNIFORM,
    ASSET_CAMERA_SEQUENCE,
)
from commands import (
    build_camera_sequence, build_audio_texture, build_load_model,
    build_stream_texture, build_texture, build_uniform,
)
from glsl_wrapper import write_glsl_wrapper
from sdf_project import SdfProject, SdfShaderComposer, load_sdf_project
from sdf_panel import SdfPanel

from assets_panel import AssetsPanel
from streams_panel import StreamsPanel
from scene_panel import ScenePanel
from pipeline_panel import PipelinePanel
from inspector_panel import InspectorPanel
from dependency_viewer_panel import DependencyViewerPanel
from runtime_controls_panel import RuntimeControlsPanel
from include_panel import IncludePanel
from defines_panel import DefinesPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlslViewerGUI \u2014 Shader Mission Control")
        self.resize(1400, 900)
        self.setMinimumSize(960, 640)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )

        self._session_config = RenderSessionConfig()
        self._bridge = RenderBridge(self)
        self._bridge._session_config = self._session_config
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

        self._sdf_project: SdfProject | None = None
        self._sdf_composer: SdfShaderComposer | None = None
        self._scene_revision: int = 0
        self._scene_editor: GLSLEditor | None = None
        self._scene_tab_index: int = -1

        self._build_menus()
        self._build_toolbar()
        self._build_central()
        self._build_docks()
        self._wire_extra_panels()

        self._bridge.start(DEFAULT_SHADER)

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

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
            act.triggered.connect(lambda checked=False, _c=cmd: self._bridge.send_command(_c))
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
            act.triggered.connect(lambda checked=False, _t=theme_name: self._apply_theme(_t.lower()))
            self._theme_menu.addAction(act)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main", self)
        tb.addAction("Open Fragment", self._open_shader)
        tb.addAction("Open Vertex", self._open_vertex_shader)
        tb.addAction("Open Geometry", self._open_geometry)
        tb.addAction("Reload", self._bridge.reload_current)
        self.addToolBar(tb)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        self._frag_editor = GLSLEditor(self)
        self._frag_editor.text_saved.connect(self._on_editor_saved)

        self._vert_editor = GLSLEditor(self)
        self._vert_editor.text_saved.connect(self._on_editor_saved)

        self._editor = self._frag_editor

        central = QTabWidget()
        central.addTab(self._frag_editor, "Fragment")
        central.addTab(self._vert_editor, "Vertex")
        self._central_tabs = central

        corner_label = QLabel(self._bridge.program.program_label)
        central.setCornerWidget(corner_label)
        self._program_label = corner_label

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # Docks
    # ------------------------------------------------------------------

    def _build_docks(self) -> None:
        self._build_right_dock()
        self._build_bottom_docks()

    def _build_right_dock(self) -> None:
        self._right_dock = QDockWidget("Controls", self)
        self._right_dock.setObjectName("RightDock")
        self._right_dock.setMinimumWidth(220)
        self._right_dock.setMaximumWidth(1000)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._right_dock)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        self._right_tabs = QTabWidget()
        right_scroll.setWidget(self._right_tabs)
        self._right_dock.setWidget(right_scroll)

        self._uniform_panel = UniformPanel(self)
        self._uniform_panel.uniform_changed.connect(self._on_uniform_changed)
        self._right_tabs.addTab(self._uniform_panel, "Uniforms")

        cam_scroll = QScrollArea()
        cam_scroll.setWidgetResizable(True)
        self._camera_panel = CameraPanel(self)
        self._camera_panel.camera_command.connect(self._bridge.send_command)
        cam_scroll.setWidget(self._camera_panel)
        self._right_tabs.addTab(cam_scroll, "Camera")

        self._runtime_panel = RuntimeControlsPanel(self)
        self._runtime_panel.command_requested.connect(self._bridge.send_command)
        self._right_tabs.addTab(self._runtime_panel, "Runtime")

        self._assets_panel = AssetsPanel(self)
        self._audio_panel = AssetsPanel(self)
        assets_tabs = QTabWidget()
        assets_tabs.addTab(self._assets_panel, "Image/Video")
        assets_tabs.addTab(self._audio_panel, "Audio")
        self._right_tabs.addTab(assets_tabs, "Assets")

        self._inspector_panel = InspectorPanel(self)
        self._dep_viewer_panel = DependencyViewerPanel(self)
        self._defines_panel = DefinesPanel(self)
        shader_tabs = QTabWidget()
        shader_tabs.addTab(self._inspector_panel, "Inspector")
        shader_tabs.addTab(self._dep_viewer_panel, "Dep Viewer")
        shader_tabs.addTab(self._defines_panel, "Defines")
        self._right_tabs.addTab(shader_tabs, "Shader")

        self._scene_panel = ScenePanel(self)
        self._streams_panel = StreamsPanel(self)
        self._include_panel = IncludePanel(self)
        self._pipeline_panel = PipelinePanel(self)
        sdf_scroll = QScrollArea()
        sdf_scroll.setWidgetResizable(True)
        self._sdf_panel = SdfPanel(self)
        self._sdf_panel.setEnabled(False)
        sdf_scroll.setWidget(self._sdf_panel)
        pipeline_tabs = QTabWidget()
        pipeline_tabs.addTab(self._scene_panel, "Scene")
        pipeline_tabs.addTab(self._streams_panel, "Streams")
        pipeline_tabs.addTab(self._include_panel, "Include")
        pipeline_tabs.addTab(self._pipeline_panel, "Pipeline")
        pipeline_tabs.addTab(sdf_scroll, "SDF")
        self._right_tabs.addTab(pipeline_tabs, "Pipeline")

    def _build_bottom_docks(self) -> None:
        self._console_panel = ConsolePanel(self)
        self._console_panel.set_command_handler(self._bridge.send_command)
        self._console_panel.set_query_handler(self._bridge.send_query)
        self._console_dock = QDockWidget("Console", self)
        self._console_dock.setObjectName("ConsoleDock")
        self._console_dock.setMaximumHeight(100000)
        self._console_dock.setWidget(self._console_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._console_dock)

        self._recording_panel = RecordingPanel(self)
        rec_scroll = QScrollArea()
        rec_scroll.setWidgetResizable(True)
        rec_scroll.setWidget(self._recording_panel)
        self._recording_dock = QDockWidget("Recording", self)
        self._recording_dock.setObjectName("RecordingDock")
        self._recording_dock.setMaximumHeight(100000)
        self._recording_dock.setWidget(rec_scroll)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._recording_dock)

        self._preset_panel = PresetPanel(self)
        self._preset_dock = QDockWidget("Presets", self)
        self._preset_dock.setObjectName("PresetDock")
        self._preset_dock.setMaximumHeight(100000)
        self._preset_dock.setWidget(self._preset_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._preset_dock)

        self.tabifyDockWidget(self._recording_dock, self._preset_dock)

        self._recording_panel.screenshot_requested.connect(self._on_screenshot_requested)
        self._recording_panel.sequence_requested.connect(self._on_sequence_requested)
        self._recording_panel.record_requested.connect(self._on_record_requested)
        self._recording_panel.frames_requested.connect(self._on_start_frames)
        self._bridge.recording_progress.connect(self._recording_panel.set_progress)

        self._preset_panel.preset_saved.connect(self._on_preset_saved)
        self._preset_panel.preset_loaded.connect(self._on_preset_loaded)

    # ------------------------------------------------------------------
    # Panel signal wiring
    # ------------------------------------------------------------------

    def _wire_extra_panels(self) -> None:
        self._scene_panel.command_requested.connect(self._bridge.send_command)
        self._streams_panel.command_requested.connect(self._bridge.send_command)
        self._pipeline_panel.command_requested.connect(self._bridge.send_command)
        self._pipeline_panel.define_requested.connect(self._on_define_from_panel)

        self._defines_panel.define_requested.connect(self._on_define)
        self._defines_panel.undefine_requested.connect(self._on_undefine)

        self._include_panel.include_added.connect(self._on_include_added)
        self._include_panel.include_removed.connect(self._on_include_removed)
        self._include_panel.restart_requested.connect(self._on_restart_requested)

        self._inspector_panel.query_requested.connect(self._bridge.send_query)
        self._dep_viewer_panel.query_requested.connect(self._bridge.send_query)

        self._assets_panel.asset_added.connect(self._on_asset_added)
        self._assets_panel.asset_refresh_requested.connect(self._bridge.send_command)

        self._sdf_panel.reset_requested.connect(self._on_sdf_reset)
        self._sdf_panel.pause_toggled.connect(
            lambda paused: self._bridge.set_uniform("u_paused", int(paused))
        )
        self._sdf_panel.config_changed.connect(self._on_sdf_config_changed)
        self._sdf_panel.integrator_changed.connect(self._on_sdf_integrator_changed)
        self._sdf_panel.debug_view_changed.connect(self._on_sdf_debug_view_changed)

    # ------------------------------------------------------------------
    # Open paths
    # ------------------------------------------------------------------

    def _open_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Fragment Shader", "",
            "Fragment Shaders (*.frag *.fs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._open_paths([path])

    def _open_vertex_shader(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Vertex Shader", "",
            "Vertex Shaders (*.vert *.vs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._open_paths([path], force_stage="vertex")

    def _open_geometry(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Geometry", "",
            "Geometry (*.ply *.obj *.stl *.glb *.gltf *.splat);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._open_paths([path])

    def _open_paths(self, paths: list[str], force_stage: str | None = None) -> None:
        plan = classify_paths(paths, force_stage=force_stage)

        if plan.sdf_project and not self._session_config.frag_path:
            self._enter_sdf_mode(plan.sdf_project)
            return

        if plan.geom_path is not None:
            self._session_config.geom_path = plan.geom_path
        elif plan.mesh_paths:
            self._session_config.geom_path = plan.mesh_paths[0]

        prior_asset_count = len(self._session_config.assets)
        build_session_from_plan(plan, self._session_config)
        new_assets = self._session_config.assets[prior_asset_count:]

        if plan.frag_path is not None:
            self._session_config.frag_path, self._session_config.source_frag_path = (
                self._wrap_glsl_path(plan.frag_path, "fragment")
            )
        if plan.vert_path is not None:
            self._session_config.vert_path, self._session_config.source_vert_path = (
                self._wrap_glsl_path(plan.vert_path, "vertex")
            )

        has_shader_change = plan.frag_path is not None or plan.vert_path is not None
        if has_shader_change or plan.mesh_paths:
            self._bridge.start_session(self._session_config)
            self._apply_runtime_assets(new_assets)
        else:
            self._apply_runtime_assets(new_assets)

        self._refresh_editors()
        self._update_program_label()

    def _wrap_glsl_path(self, path: str, stage: str) -> tuple[str, str]:
        if not path.lower().endswith(".glsl"):
            return path, path
        wrapped = write_glsl_wrapper(path, stage)
        return wrapped, path

    def _apply_runtime_assets(self, assets) -> None:
        for a in assets:
            if not self._bridge.is_running:
                break
            if a.kind == ASSET_CAMERA_SEQUENCE:
                self._bridge.send_command(build_camera_sequence(a.path))
            elif a.kind == ASSET_NAMED_TEXTURE:
                self._bridge.send_command(
                    build_texture(a.name, a.path, flip=a.options.get("flip", False))
                )
            elif a.kind == ASSET_STREAM_TEXTURE:
                self._bridge.send_command(
                    build_stream_texture(
                        a.name, a.path,
                        webcam=a.options.get("webcam", False),
                        flip=a.options.get("flip", False),
                    )
                )
            elif a.kind == ASSET_AUDIO:
                self._bridge.send_command(
                    build_audio_texture(a.name, a.options.get("device", "-1"))
                )
            elif a.kind == ASSET_MODEL:
                self._bridge.send_command(build_load_model(a.path))

    def _enter_sdf_mode(self, project_path: str) -> None:
        if self._sdf_project:
            self._leave_sdf_mode()
        self._sdf_project = load_sdf_project(project_path)
        self._sdf_composer = SdfShaderComposer(self._sdf_project)
        self._sdf_panel.load_config(self._sdf_project.config)
        self._sdf_panel.setEnabled(True)

        self._sdf_composer.generate()
        self._session_config.frag_path = str(self._sdf_project.generated_frag_path)
        self._session_config.source_frag_path = str(self._sdf_project.scene_path)
        self._session_config.vert_path = None
        self._session_config.cwd = str(self._sdf_project.project_dir)
        self._scene_revision = 0
        self._ensure_scene_tab()

        self._bridge.start_session(self._session_config)
        self._send_scene_revision_if_running()
        self._refresh_editors()
        self._update_program_label()

    def _leave_sdf_mode(self) -> None:
        self._sdf_project = None
        self._sdf_composer = None
        self._sdf_panel.setEnabled(False)
        self._session_config.frag_path = None
        self._session_config.source_frag_path = None
        self._session_config.cwd = ""
        self._remove_scene_tab()

    def _ensure_scene_tab(self) -> None:
        central = self._central_tabs
        if self._scene_tab_index >= 0 and self._scene_tab_index < central.count():
            return
        self._scene_editor = GLSLEditor(self)
        if self._sdf_project and self._sdf_project.scene_path:
            scene_path = str(self._sdf_project.scene_path)
            self._scene_editor.set_file_path(scene_path)
            try:
                with open(scene_path) as f:
                    self._scene_editor.set_source(f.read())
            except OSError:
                pass
            self._scene_editor.text_saved.connect(self._on_scene_saved)
        self._scene_tab_index = central.addTab(self._scene_editor, "Scene")

    def _remove_scene_tab(self) -> None:
        central = self._central_tabs
        if self._scene_tab_index < 0 or self._scene_tab_index >= central.count():
            return
        widget = central.widget(self._scene_tab_index)
        central.removeTab(self._scene_tab_index)
        if widget is not None:
            widget.deleteLater()
        self._scene_editor = None
        self._scene_tab_index = -1

    def _on_scene_saved(self, path: str) -> None:
        if not self._sdf_project:
            return
        try:
            with open(path) as f:
                self._sdf_project.scene_source = f.read()
        except OSError:
            return
        self._sdf_project.save_scene()
        if self._sdf_composer:
            self._sdf_composer.generate()
        self._bump_scene_revision(restart=False)

    def _on_sdf_config_changed(self) -> None:
        if not self._sdf_project:
            return
        self._sdf_project.config = self._sdf_panel.get_config()
        self._sdf_project.save_config()
        if self._sdf_composer:
            self._sdf_composer.generate()
        self._bump_scene_revision(restart=False)

    def _on_sdf_integrator_changed(self, value: str) -> None:
        if not self._sdf_project:
            return
        self._sdf_project.config.integrator = value
        self._sdf_project.save_config()
        if self._sdf_composer:
            self._sdf_composer.generate()
        if self._bridge.is_running:
            self._bridge.start_session(self._session_config)
            self._send_scene_revision_if_running()

    def _on_sdf_debug_view_changed(self, value: str) -> None:
        if not self._sdf_project:
            return
        if self._bridge.is_running:
            self._bridge.set_uniform("u_debugView", value)

    def _on_sdf_reset(self) -> None:
        if not self._bridge.is_running:
            return
        self._bridge.send_command("reset")
        self._send_scene_revision_if_running()

    def _bump_scene_revision(self, restart: bool = False) -> None:
        self._scene_revision += 1
        if not self._bridge.is_running:
            return
        if restart and self._session_config.frag_path:
            self._bridge.start_session(self._session_config)
        self._send_scene_revision_if_running()

    def _send_scene_revision_if_running(self) -> None:
        if self._bridge.is_running:
            self._bridge.send_command(build_uniform("u_sceneRevision", self._scene_revision))

    # ------------------------------------------------------------------
    # Define / Include handlers
    # ------------------------------------------------------------------

    def _on_define(self, name: str, value: str) -> None:
        self._session_config.defines[name] = value
        if self._bridge.is_running:
            from commands import build_define
            self._bridge.send_command(build_define(name, value))

    def _on_undefine(self, name: str) -> None:
        self._session_config.defines.pop(name, None)
        if self._bridge.is_running:
            from commands import build_undefine
            self._bridge.send_command(build_undefine(name))

    def _on_define_from_panel(self, name: str, value: str) -> None:
        self._on_define(name, value)

    def _on_include_added(self, folder: str) -> None:
        if folder not in self._session_config.include_dirs:
            self._session_config.include_dirs.append(folder)

    def _on_include_removed(self, folder: str) -> None:
        if folder in self._session_config.include_dirs:
            self._session_config.include_dirs.remove(folder)

    def _on_restart_requested(self) -> None:
        if self._bridge.is_running:
            self._bridge.start_session(self._session_config)

    def _on_asset_added(self, spec) -> None:
        self._session_config.assets.append(spec)
        if spec.kind in (ASSET_CUBEMAP_SHOW, ASSET_CUBEMAP_ENV):
            if self._bridge.is_running:
                self._bridge.start_session(self._session_config)
            return
        self._apply_runtime_assets([spec])

    # ------------------------------------------------------------------
    # Recording wrappers
    # ------------------------------------------------------------------

    def _on_screenshot_requested(self, path: str) -> None:
        if not self._bridge.is_running:
            self._recording_panel.reset_progress()
            return
        self._bridge.screenshot(path)

    def _on_sequence_requested(self, prefix: str, f: float, t: float, fps: float) -> None:
        if not self._bridge.is_running:
            self._recording_panel.reset_progress()
            return
        self._bridge.sequence(prefix, f, t, fps)
        self._recording_panel.set_busy(True)

    def _on_record_requested(self, path: str, f: float, t: float, fps: float) -> None:
        if not self._bridge.is_running:
            self._recording_panel.reset_progress()
            return
        self._bridge.record(path, f, t, fps)
        self._recording_panel.set_busy(True)

    def _on_start_frames(self, prefix: str, from_frame: int, to_frame: int, fps: float) -> None:
        if not self._bridge.is_running:
            self._recording_panel.reset_progress()
            return
        self._bridge.frames(prefix, from_frame, to_frame, fps)
        self._recording_panel.set_busy(True)

    # ------------------------------------------------------------------
    # Editor refresh
    # ------------------------------------------------------------------

    def _refresh_editors(self) -> None:
        frag = self._session_config.frag_path
        vert = self._session_config.vert_path
        source_frag = self._session_config.source_frag_path or frag
        source_vert = self._session_config.source_vert_path or vert
        if source_frag and os.path.exists(source_frag):
            self._frag_editor.set_file_path(source_frag)
            with open(source_frag) as f:
                self._frag_editor.set_source(f.read())
            self._refresh_uniforms_from_file(source_frag)
        if source_vert and os.path.exists(source_vert):
            self._vert_editor.set_file_path(source_vert)
            with open(source_vert) as f:
                self._vert_editor.set_source(f.read())

    def _update_program_label(self) -> None:
        label = self._bridge.program.program_label
        self._program_label.setText(label)

    # ------------------------------------------------------------------
    # Toggles
    # ------------------------------------------------------------------

    def _toggle_uniforms(self, visible: bool) -> None:
        self._uniform_panel.setVisible(visible)

    def _toggle_camera(self, visible: bool) -> None:
        self._camera_panel.setVisible(visible)

    def _toggle_console(self, visible: bool) -> None:
        self._console_dock.setVisible(visible)

    def _toggle_recording(self, visible: bool) -> None:
        self._recording_dock.setVisible(visible)

    def _toggle_presets(self, visible: bool) -> None:
        self._preset_dock.setVisible(visible)

    # ------------------------------------------------------------------
    # Bridge callbacks
    # ------------------------------------------------------------------

    def _on_process_started(self) -> None:
        self._refresh_editors()
        self._update_program_label()

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
                f"[Multiple errors ({len(self._error_buffer)}) received in last 2s]"
            )
        else:
            for _, msg in self._error_buffer:
                self._console_panel.append(msg)
                self._frag_editor.apply_errors(msg)

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
            "  \u2022 Your graphics drivers\n"
            "  \u2022 Whether glslViewer binary exists and is executable"
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
        found = {name for name in shadertoy_names if re.search(rf"\b{name}\b", source)}
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
        from PySide6.QtCore import QSettings
        try:
            from themes import apply_theme
            apply_theme(self, theme_name)
            QSettings("glslViewer", "GlslViewerGUI").setValue("theme", theme_name)
        except Exception as e:
            self._console_panel.append_line(f"Theme error: {e}")

    def closeEvent(self, event) -> None:
        self._bridge.stop()
        event.accept()
