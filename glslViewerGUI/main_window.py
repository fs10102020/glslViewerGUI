import hashlib
import os
import re
import shutil
import time
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
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
from commands import (
    build_audio_texture,
    build_camera_sequence,
    build_cubemap_load,
    build_define,
    build_environment,
    build_include_path,
    build_load_model,
    build_stream_texture,
    build_texture,
    build_undefine,
)
from console_panel import ConsolePanel
from defines_panel import DefinesPanel
from dependency_viewer_panel import DependencyViewerPanel
from file_classifier import (
    classify_paths,
    LoadPlan,
    build_session_from_plan,
)
from glslViewer_config import DEFAULT_SHADER, CONFIG_DIR, GLSLVIEWER_BIN
from glsl_wrapper import write_glsl_wrapper
from include_panel import IncludePanel
from inspector_panel import InspectorPanel
from pipeline_panel import PipelinePanel
from preset_manager import PresetPanel, save_preset
from recording_panel import RecordingPanel
from render_bridge import RenderBridge
from runtime_controls_panel import RuntimeControlsPanel
from scene_panel import ScenePanel
from session_config import (
    AssetSpec,
    RenderSessionConfig,
    ShaderProgramSpec,
    CLI_ASSET_KINDS,
    ASSET_NAMED_TEXTURE,
    ASSET_STREAM_TEXTURE,
    ASSET_CUBEMAP_SHOW,
    ASSET_CUBEMAP_ENV,
    ASSET_AUDIO,
    ASSET_MODEL,
    ASSET_SEQUENCE_UNIFORM,
    ASSET_CAMERA_SEQUENCE,
)
from session_dialog import SessionDialog
from shader_diagnostics import diagnose_shader_pair, diagnose_single_frag
from shader_editor import GLSLEditor
from shader_parser import parse_uniforms
from sdf_panel import SdfPanel
from sdf_project import (
    SdfProject,
    SdfProjectConfig,
    SdfShaderComposer,
    _strip_leading_version,
    is_sdf_project,
    load_sdf_project,
    copy_example_project,
    TEMPLATES_DIR,
)
from streams_panel import StreamsPanel
from themes import apply_theme
from uniform_panel import UniformPanel


def _confirm_overwrite(parent, dest: str) -> bool:
    """Ask the user before clobbering an existing directory."""
    reply = QMessageBox.question(
        parent,
        "Overwrite existing folder?",
        f"The destination already exists:\n{dest}\n\nOverwrite it?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GlslViewerGUI - Shader Mission Control")
        self.setMinimumSize(960, 640)
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        self._session_config = RenderSessionConfig(frag_path=DEFAULT_SHADER)
        self._error_buffer: list[tuple[float, str]] = []
        self._error_flush_timer = QTimer(self)
        self._error_flush_timer.setSingleShot(True)
        self._error_flush_timer.timeout.connect(self._flush_errors)

        # SDF project state
        self._sdf_project: SdfProject | None = None
        self._scene_revision: int = 1
        self._accumulation_paused: bool = False

        self._bridge = RenderBridge(self)
        self._bridge.process_started.connect(self._on_process_started)
        self._bridge.process_stopped.connect(self._on_process_stopped)
        self._bridge.stdout_received.connect(self._on_stdout)
        self._bridge.stderr_received.connect(self._on_stderr)
        self._bridge.process_crashed.connect(self._on_process_crashed)
        self._bridge.process_gave_up.connect(self._on_process_gave_up)
        self._bridge.file_changed.connect(self._on_bridge_file_changed)

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
        if Path(GLSLVIEWER_BIN).exists():
            try:
                self._bridge.start(DEFAULT_SHADER)
            except RuntimeError as e:
                QMessageBox.warning(self, "Renderer unavailable", str(e))
        else:
            QMessageBox.warning(
                self,
                "glslViewer not found",
                f"Expected renderer binary at:\n{GLSLVIEWER_BIN}\n\n"
                "Build it with `make -C glslViewer` from the repository root.",
            )

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

        open_geom = QAction("Open Model/&Geometry...", self)
        open_geom.triggered.connect(self._open_geometry)
        file_menu.addAction(open_geom)
        file_menu.addSeparator()

        new_sdf = QAction("New SDF &Project...", self)
        new_sdf.triggered.connect(self._new_sdf_project)
        new_sdf.setShortcut(QKeySequence("Ctrl+Shift+N"))
        file_menu.addAction(new_sdf)

        open_sdf = QAction("Open SDF Pro&ject...", self)
        open_sdf.triggered.connect(self._open_sdf_project)
        open_sdf.setShortcut(QKeySequence("Ctrl+Shift+O"))
        file_menu.addAction(open_sdf)

        open_example = QAction("Open Apollonian E&xample", self)
        open_example.triggered.connect(self._open_apollonian_example)
        file_menu.addAction(open_example)

        export_sdf = QAction("&Export Generated SDF Shader...", self)
        export_sdf.triggered.connect(self._export_generated_shader)
        file_menu.addAction(export_sdf)
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
        self._scene_editor = GLSLEditor(self)
        self._scene_editor.text_saved.connect(self._on_scene_editor_saved)
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
        self._defines_panel.undefine_requested.connect(self._on_undefine_requested)

        self._include_panel = IncludePanel(self)
        self._include_panel.include_added.connect(self._on_include_added)
        self._include_panel.restart_requested.connect(self._restart_renderer)

        self._dependency_panel = DependencyViewerPanel(self)
        self._dependency_panel.query_requested.connect(self._bridge.send_query)

        self._pipeline_panel = PipelinePanel(self)
        self._pipeline_panel.command_requested.connect(self._safe_send)
        self._pipeline_panel.define_requested.connect(self._on_define_requested)

        self._scene_panel = ScenePanel(self)
        self._scene_panel.command_requested.connect(self._safe_send)

        self._inspector_panel = InspectorPanel(self)
        self._inspector_panel.query_requested.connect(self._bridge.send_query)

        self._sdf_panel = SdfPanel(self)
        self._sdf_panel.config_changed.connect(self._on_sdf_config_changed)
        self._sdf_panel.integrator_changed.connect(self._on_sdf_integrator_changed)
        self._sdf_panel.debug_view_changed.connect(self._on_sdf_debug_view_changed)
        self._sdf_panel.reset_requested.connect(self._on_sdf_reset_requested)
        self._sdf_panel.pause_toggled.connect(self._on_sdf_pause_toggled)
        self._sdf_panel.setEnabled(False)

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
        pipeline_tabs.addTab(self._scroll_panel(self._sdf_panel), "SDF")
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
        self._bridge.recording_progress.connect(self._on_recording_progress)
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
            if not self._bridge.is_running:
                if hasattr(self, "_console_panel"):
                    self._console_panel.append_line(f"! renderer stopped, skipped: {command}")
                return
            self._bridge.send_command(command)
            if hasattr(self, "_console_panel"):
                self._console_panel.append_line(f"> {command}")
            # Camera motion invalidates path-traced accumulation.
            if self._sdf_project and command.startswith(("camera", "camera_")):
                self._bump_scene_revision()

    def _open_shader(self) -> None:
        """Smart open for any shader, scene, project, or asset."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open", "",
            "Shaders and Assets (*.frag *.fs *.vert *.vs *.glsl "
            "*.obj *.ply *.stl *.glb *.gltf *.splat "
            "*.png *.jpg *.jpeg *.tga *.psd *.gif *.bmp *.hdr *.exr "
            "*.mov *.mp4 *.mkv *.mpg *.mpeg *.h264 *.csv "
            "project.json);;"
            "All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if paths:
            self._open_paths(paths)

    def _open_vertex_shader(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Vertex Shader", "",
            "Vertex Shaders (*.vert *.vs *.glsl);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if paths:
            self._open_paths(paths)

    def _open_geometry(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Geometry", "",
            "Model / Geometry (*.ply *.obj *.stl *.glb *.gltf *.splat);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if paths:
            self._open_paths(paths)

    def _open_paths(self, paths: Iterable[str]) -> None:
        """Route arbitrary user-selected paths through the classifier."""
        path_list = [str(p) for p in paths if p]
        if not path_list:
            return

        plan = classify_paths(path_list)

        for w in plan.warnings:
            self._console_panel.append_line(f"WARNING: {w}")

        if plan.shadertoy_candidates:
            names = ", ".join(p.name for p in plan.shadertoy_candidates)
            self._console_panel.append_line(
                f"INFO: detected Shadertoy-style file(s) ({names}); "
                "glslViewer uses u_time/u_resolution/u_mouse/u_frame."
            )

        if plan.sdf_project is not None:
            try:
                project = load_sdf_project(plan.sdf_project)
                self._load_sdf_project(project)
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return

        if plan.sdf_scene is not None and plan.frag_path is None:
            frag_text = plan.sdf_scene.read_text(encoding="utf-8", errors="replace")
            try:
                # Create a temporary SDF project so we can use the full composer.
                digest = hashlib.sha1(str(plan.sdf_scene.resolve()).encode("utf-8")).hexdigest()[:10]
                tmp_dir = Path(CONFIG_DIR) / "imported_sdf" / digest
                tmp_dir.mkdir(parents=True, exist_ok=True)
                project = SdfProject.create_new(
                    tmp_dir,
                    scene_source=_strip_leading_version(frag_text),
                )
                project.config.scene = "scene.glsl"
                project.save()
                self._load_sdf_project(project)
                self._console_panel.append_line(
                    f"Imported SDF scene {plan.sdf_scene.name} as a temporary SDF project."
                )
                return
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                return

        if not plan.has_anything:
            if plan.unknown:
                QMessageBox.warning(
                    self,
                    "Nothing to load",
                    "No usable shaders, scenes, or assets were recognized:\n"
                    + "\n".join(str(p) for p in plan.unknown),
                )
            return

        # Build a session config from the plan, then apply it.
        old_frag = self._session_config.frag_path or DEFAULT_SHADER
        session = RenderSessionConfig.from_dict(self._session_config.to_dict())
        session.assets = list(self._session_config.assets)  # preserve queued assets
        build_session_from_plan(plan, base_session=session)
        self._prepare_session_shader_paths(session)
        # If the user only opened assets/models, keep the current shader.
        if session.frag_path is None:
            session.frag_path = old_frag
        self._session_config = session

        if self._sdf_project:
            self._close_sdf_project()

        try:
            self._bridge.apply_session_config(self._session_config)
            self._apply_runtime_assets(self._session_config)
            self._sync_extra_watch_files()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _load_program(self, program: ShaderProgramSpec) -> None:
        if self._sdf_project:
            self._close_sdf_project()
        if not program.frag_path:
            program.frag_path = DEFAULT_SHADER
        try:
            session = RenderSessionConfig(frag_path=program.frag_path, vert_path=program.vert_path, geom_path=program.model_path)
            self._prepare_session_shader_paths(session)
            self._session_config = session
            self._bridge.apply_session_config(session)
            self._sync_extra_watch_files()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _restart_renderer(self) -> None:
        if self._sdf_project:
            self._regenerate_sdf_shader()
        else:
            self._prepare_session_shader_paths(self._session_config)
            self._bridge.apply_session_config(self._session_config)
            self._sync_extra_watch_files()

    def _open_session_settings(self) -> None:
        dialog = SessionDialog(RenderSessionConfig.from_dict(self._session_config.to_dict()), self)
        if dialog.exec():
            self._session_config = dialog.config()
            if self._sdf_project:
                self._regenerate_sdf_shader()
            else:
                self._prepare_session_shader_paths(self._session_config)
                self._bridge.apply_session_config(self._session_config)
                self._apply_runtime_assets(self._session_config)
                self._sync_extra_watch_files()

    def _on_process_started(self) -> None:
        program = self._bridge.program
        self._program_label.setText(program.program_label)

        if self._sdf_project:
            self._load_editor_file(self._frag_editor, str(self._sdf_project.generated_frag_path))
            self._load_editor_file(self._scene_editor, str(self._sdf_project.scene_path))
            self._refresh_uniforms_from_source(self._sdf_project.scene_source)
            self._send_sdf_renderer_uniforms()
            self._bump_scene_revision()
        else:
            frag_source = self._session_config.source_frag_path or program.frag_path
            vert_source = self._session_config.source_vert_path or program.vert_path
            self._load_editor_file(self._frag_editor, frag_source)
            self._load_editor_file(self._vert_editor, vert_source)
            if frag_source:
                self._refresh_uniforms_from_file(frag_source)
            self._sync_extra_watch_files()
            if hasattr(self._pipeline_panel, "set_scene_enabled"):
                self._pipeline_panel.set_scene_enabled(bool(program.vert_path or program.model_path))
        self._run_shader_diagnostics()

    def _load_editor_file(self, editor: GLSLEditor, path: str | None) -> None:
        editor.set_file_path(path)
        if path and os.path.exists(path):
            with open(path) as f:
                editor.set_source(f.read())
        else:
            editor.set_source("")

    def _on_process_stopped(self) -> None:
        if hasattr(self, "_recording_panel"):
            self._recording_panel.reset_progress()

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

    def _on_bridge_file_changed(self, path: str) -> None:
        if not self._sdf_project:
            source_frag = self._session_config.source_frag_path or self._session_config.frag_path
            source_vert = self._session_config.source_vert_path or self._session_config.vert_path
            if any(path == asset.path for asset in self._session_config.assets):
                self._console_panel.append_line(f"Asset changed on disk, restarting renderer: {path}")
                self._prepare_session_shader_paths(self._session_config)
                self._bridge.apply_session_config(self._session_config)
                self._apply_runtime_assets(self._session_config)
                self._sync_extra_watch_files()
                return
            if path in {source_frag, source_vert}:
                self._prepare_session_shader_paths(self._session_config)
                if path == source_frag:
                    self._load_editor_file(self._frag_editor, source_frag)
                    self._refresh_uniforms_from_file(source_frag)
                elif path == source_vert:
                    self._load_editor_file(self._vert_editor, source_vert)
                self._run_shader_diagnostics()
            self._bridge.reload_current()
            return

        scene_path = str(self._sdf_project.scene_path)
        if path == scene_path:
            try:
                with open(scene_path, "r", encoding="utf-8") as f:
                    new_source = f.read()
            except OSError as e:
                self._console_panel.append_line(f"Error reading scene file: {e}")
                return
            # Ignore change events caused by our own editor save; those are
            # already handled by _on_scene_editor_saved.
            if new_source == self._scene_editor.source():
                return
            self._scene_editor.set_source(new_source)
            self._sdf_project.scene_source = new_source
            self._sdf_project.save_scene()
            self._uniform_panel.load_from_source(new_source)
            self._bump_scene_revision()
            self._regenerate_sdf_shader()
            self._console_panel.append_line(f"Scene file changed on disk: {path}")
            return

        try:
            is_template = Path(path).resolve().is_relative_to(TEMPLATES_DIR.resolve())
        except ValueError:
            is_template = False
        if is_template:
            self._console_panel.append_line(f"SDF template changed on disk: {path}")
            self._regenerate_sdf_shader()
            return

    def _on_editor_saved(self, path: str) -> None:
        if self._sdf_project:
            # In SDF mode the fragment tab shows the generated shader;
            # user edits there are transient. Scene edits drive regeneration.
            self._bridge.reload_current()
            self._run_shader_diagnostics()
            return
        self._bridge.reload_current()
        self._refresh_uniforms_from_file(path)
        self._run_shader_diagnostics()

    def _on_uniform_changed(self, name: str, value) -> None:
        self._bridge.set_uniform(name, value)
        if self._sdf_project:
            self._bump_scene_revision()

    def _refresh_uniforms_from_file(self, path: str) -> None:
        try:
            with open(path) as f:
                source = f.read()
            self._refresh_uniforms_from_source(source)
        except Exception as e:
            self._console_panel.append_line(f"Error parsing uniforms: {e}")

    def _refresh_uniforms_from_source(self, source: str) -> None:
        self._uniform_panel.load_from_source(source)
        self._check_shadertoy_uniforms(source)

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
        try:
            cmd = build_define(name, value)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid define", str(e))
            return
        self._session_config.defines[name] = value
        self._safe_send(cmd)
        if self._sdf_project:
            self._bump_scene_revision()

    def _on_undefine_requested(self, name: str) -> None:
        try:
            cmd = build_undefine(name)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid define", str(e))
            return
        self._session_config.defines.pop(name, None)
        self._safe_send(cmd)

    def _on_include_added(self, path: str) -> None:
        if path not in self._session_config.include_dirs:
            self._session_config.include_dirs.append(path)
        self._safe_send(build_include_path(path))

    def _on_asset_added(self, asset: AssetSpec) -> None:
        asset.name = self._unique_asset_name(asset.kind, asset.name, asset.path)
        self._session_config.assets.append(asset)
        if asset.kind in CLI_ASSET_KINDS:
            try:
                self._bridge.apply_session_config(self._session_config)
                self._apply_runtime_assets(self._session_config)
                self._sync_extra_watch_files()
            except ValueError as e:
                self._session_config.assets.remove(asset)
                QMessageBox.warning(self, "Invalid asset", str(e))
                return
            self._console_panel.append_line(f"Asset loaded via restart: {asset.kind} {asset.name} {asset.path}")
            return
        try:
            self._send_asset_command(asset)
        except ValueError as e:
            self._session_config.assets.remove(asset)
            QMessageBox.warning(self, "Invalid asset", str(e))
            return
        self._sync_extra_watch_files()
        self._console_panel.append_line(
            f"Asset loaded: {asset.kind} {asset.name} {asset.path}"
        )

    def _send_asset_command(self, asset: AssetSpec) -> None:
        """Send the runtime glslViewer command for a single asset.

        Also accepts a few legacy kind names ("image", "video", etc.) so older
        presets and sessions keep working after the asset vocabulary was
        normalized.
        """
        kind = asset.kind
        name = asset.name or ""
        path = asset.path
        opts = asset.options or {}

        if kind in (ASSET_NAMED_TEXTURE, "image"):
            cmd = build_texture(name or "u_tex0", path, flip=opts.get("flip", False))
        elif kind in (ASSET_STREAM_TEXTURE, "video"):
            cmd = build_stream_texture(
                name or "u_texStream0",
                path,
                webcam=opts.get("webcam", False),
                flip=opts.get("flip", False),
            )
        elif kind in (ASSET_CUBEMAP_SHOW, "skybox"):
            cmd = build_cubemap_load(name or "u_cube", path, show=True)
        elif kind in (ASSET_CUBEMAP_ENV, "environment"):
            cmd = build_environment(path)
        elif kind == ASSET_AUDIO:
            cmd = build_audio_texture(name or "u_audio0", opts.get("device", "-1"))
        elif kind == ASSET_MODEL:
            cmd = build_load_model(path)
        elif kind in (ASSET_SEQUENCE_UNIFORM, "sequence"):
            self._console_panel.append_line(
                "Sequence uniform assets are applied on renderer restart because glslViewer's "
                "runtime sequence_uniform command collides with sequence."
            )
            return
        elif kind == ASSET_CAMERA_SEQUENCE:
            cmd = build_camera_sequence(path)
        else:
            return
        self._safe_send(cmd)

    def _apply_runtime_assets(self, config: RenderSessionConfig) -> None:
        """Send runtime commands for assets not loaded via the CLI.

        Assets whose kind is handled by RenderSessionConfig.build_args() are
        already present as startup arguments, so we only dispatch runtime
        commands for the remaining kinds here.
        """
        for asset in config.assets:
            if asset.kind not in CLI_ASSET_KINDS:
                self._send_asset_command(asset)

    def _on_preset_saved(self, name: str) -> None:
        data = {
            "shader_path": self._bridge.shader_path,
            "vert_path": self._bridge.vert_path,
            "geom_path": self._bridge.geom_path,
            "uniforms": self._uniform_panel.all_values(),
            "camera": self._camera_panel.get_state(),
            "session": self._session_config.to_dict(),
        }
        if self._sdf_project:
            data["sdf_project_dir"] = str(self._sdf_project.project_dir)
            data["sdf_config"] = self._sdf_project.config.to_dict()
            data["sdf_scene_revision"] = self._scene_revision
        try:
            save_preset(name, data)
            self._console_panel.append_line(f"Preset saved: {name}")
        except Exception as e:
            self._console_panel.append_line(f"Error saving preset: {e}")

    def _on_preset_loaded(self, name: str, data: dict) -> None:
        session = data.get("session")
        if session:
            self._session_config = RenderSessionConfig.from_dict(session)
            self._prepare_session_shader_paths(self._session_config)

        sdf_dir = data.get("sdf_project_dir")
        if sdf_dir and is_sdf_project(sdf_dir):
            try:
                project = load_sdf_project(sdf_dir)
                if "sdf_config" in data:
                    project.config = SdfProjectConfig.from_dict(data["sdf_config"])
                self._load_sdf_project(project)
                self._scene_revision = data.get("sdf_scene_revision", 1)
            except Exception as e:
                self._console_panel.append_line(f"Error loading SDF preset: {e}")
        else:
            if self._session_config.frag_path:
                self._bridge.apply_session_config(self._session_config)
                self._apply_runtime_assets(self._session_config)
                self._sync_extra_watch_files()

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

    # ------------------------------------------------------------------
    # SDF project integration
    # ------------------------------------------------------------------

    def _new_sdf_project(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Create New SDF Project", "",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not path:
            return
        if (Path(path) / "project.json").exists() or (Path(path) / "scene.glsl").exists():
            if not _confirm_overwrite(self, path):
                return
        try:
            project = SdfProject.create_new(path)
            self._load_sdf_project(project)
            self._console_panel.append_line(f"Created SDF project: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_sdf_project(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Open SDF Project", "",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not path:
            return
        if not is_sdf_project(path):
            QMessageBox.warning(self, "Not an SDF project", "Selected directory does not contain a project.json.")
            return
        try:
            project = load_sdf_project(path)
            self._load_sdf_project(project)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_apollonian_example(self) -> None:
        try:
            dst = Path(CONFIG_DIR) / "sdf_apollonian_example"
            if dst.exists():
                if not _confirm_overwrite(self, str(dst)):
                    return
            project = copy_example_project(dst, overwrite=True)
            self._load_sdf_project(project)
            self._console_panel.append_line(f"Opened example project: {dst}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _export_generated_shader(self) -> None:
        if not self._sdf_project:
            QMessageBox.information(self, "Export", "No SDF project is currently open.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Generated Shader", "generated.frag",
            "Fragment Shaders (*.frag);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            try:
                composer = SdfShaderComposer(self._sdf_project)
                composer.generate(path)
                self._console_panel.append_line(f"Exported generated shader: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _load_sdf_project(self, project: SdfProject) -> None:
        if self._sdf_project is not None:
            self._close_sdf_project()

        self._sdf_project = project
        self._scene_revision = 1
        self._accumulation_paused = False

        # Update UI panel with project config.
        self._sdf_panel.load_config(project.config)
        self._sdf_panel.setEnabled(True)

        # Show scene editor, hide vertex editor.
        self._editor_tabs.addTab(self._scene_editor, "Scene")
        self._scene_editor.set_file_path(str(project.scene_path))
        self._scene_editor.set_source(project.scene_source)
        self._vert_editor.setVisible(False)

        # Load uniforms from scene.glsl (not the generated shader).
        self._uniform_panel.load_from_source(project.scene_source)

        # Generate and run.
        self._regenerate_sdf_shader()

    def _close_sdf_project(self) -> None:
        self._sdf_project = None
        self._scene_revision = 1
        self._accumulation_paused = False
        self._sdf_panel.setEnabled(False)
        idx = self._editor_tabs.indexOf(self._scene_editor)
        if idx >= 0:
            self._editor_tabs.removeTab(idx)
        self._vert_editor.setVisible(True)
        self._editor_tabs.setTabText(0, "Fragment")
        self._bridge.set_watch_files([])

    def _regenerate_sdf_shader(self) -> None:
        if not self._sdf_project:
            return

        project = self._sdf_project
        cfg = self._sdf_panel.get_config()
        project.config = cfg
        project.save_config()

        composer = SdfShaderComposer(project)
        generated_path = composer.generate()

        # Build session args for SDF mode.
        session = RenderSessionConfig.from_dict(self._session_config.to_dict())
        session.frag_path = str(generated_path)
        session.vert_path = None
        session.geom_path = None
        session.include_dirs = list(set(session.include_dirs + [str(TEMPLATES_DIR)]))
        session.defines = dict(session.defines)
        session.defines["SDF_INTEGRATOR_" + cfg.integrator.upper()] = ""
        # glslViewer automatically defines DOUBLE_BUFFER_0/1 when it creates
        # the per-pass shaders; defining them globally breaks the display pass.
        session.cwd = str(project.project_dir)

        # Watch scene source and templates so external edits trigger regeneration.
        watch_files = [str(project.scene_path)]
        for f in TEMPLATES_DIR.glob("*.glsl"):
            watch_files.append(str(f))
        for f in TEMPLATES_DIR.glob("*.template"):
            watch_files.append(str(f))
        self._bridge.set_watch_files(watch_files)

        self._session_config = session
        self._bridge.apply_session_config(session)
        self._apply_runtime_assets(session)

        # Set initial renderer uniforms.
        self._send_sdf_renderer_uniforms()

        # Load generated shader into fragment editor for inspection.
        self._load_editor_file(self._frag_editor, str(generated_path))
        self._editor_tabs.setTabText(0, "Generated")
        self._program_label.setText(f"SDF: {project.project_dir.name}")

    def _on_scene_editor_saved(self, path: str) -> None:
        if not self._sdf_project:
            return
        self._sdf_project.scene_source = self._scene_editor.source()
        self._sdf_project.save_scene()
        self._uniform_panel.load_from_source(self._sdf_project.scene_source)
        self._bump_scene_revision()
        self._regenerate_sdf_shader()

    def _on_sdf_config_changed(self) -> None:
        if not self._sdf_project:
            return
        # Update project config and persist it.
        self._sdf_project.config = self._sdf_panel.get_config()
        self._sdf_project.save_config()

        # Send renderer uniforms at runtime.
        self._send_sdf_renderer_uniforms()
        self._bump_scene_revision()

    def _on_sdf_integrator_changed(self, integrator: str) -> None:
        if not self._sdf_project:
            return
        # Buffer setup changes, so restart renderer.
        self._regenerate_sdf_shader()
        self._bump_scene_revision()

    def _on_sdf_debug_view_changed(self, view: str) -> None:
        if not self._sdf_project:
            return
        debug_map = {"beauty": 0, "normal": 1, "distance": 2, "steps": 3, "albedo": 4, "emission": 5}
        value = debug_map.get(view, 0)
        self._bridge.set_uniform("u_debugView", value)
        self._bump_scene_revision()

    def _on_sdf_reset_requested(self) -> None:
        self._bump_scene_revision()

    def _on_sdf_pause_toggled(self, paused: bool) -> None:
        self._accumulation_paused = paused
        # We don't have a direct pause command; reduce samples per frame to 0
        # effectively by setting u_samplesPerFrame to 0 when paused.
        self._bridge.set_uniform("u_samplesPerFrame", 0 if paused else self._sdf_panel.get_config().samples_per_frame)

    def _bump_scene_revision(self) -> None:
        self._scene_revision += 1
        self._bridge.set_uniform("u_sceneRevision", self._scene_revision)
        self._console_panel.append_line(f"SDF scene revision: {self._scene_revision}")

    def _send_sdf_renderer_uniforms(self) -> None:
        cfg = self._sdf_panel.get_config()
        self._bridge.set_uniform("u_maxSteps", cfg.max_steps)
        self._bridge.set_uniform("u_maxDistance", cfg.max_distance)
        self._bridge.set_uniform("u_hitEpsilon", cfg.hit_epsilon)
        self._bridge.set_uniform("u_stepScale", cfg.step_scale)
        self._bridge.set_uniform("u_normalEpsilon", cfg.normal_epsilon)
        self._bridge.set_uniform("u_shadowSteps", cfg.shadow_steps)
        self._bridge.set_uniform("u_shadowEpsilon", cfg.shadow_epsilon)

        self._bridge.set_uniform("u_maxBounces", cfg.max_bounces)
        self._bridge.set_uniform("u_samplesPerFrame", 0 if self._accumulation_paused else cfg.samples_per_frame)
        self._bridge.set_uniform("u_targetSamples", cfg.target_samples)
        self._bridge.set_uniform("u_rrStartBounce", cfg.rr_start_bounce)
        self._bridge.set_uniform("u_fireflyClamp", cfg.firefly_clamp)

        self._bridge.set_uniform("u_exposure", cfg.exposure)
        tone_map_map = {"none": 0, "aces": 1, "reinhard": 2, "filmic": 3}
        self._bridge.set_uniform("u_toneMap", tone_map_map.get(cfg.tone_map, 1))
        self._bridge.set_uniform("u_gamma", cfg.gamma)

        self._bridge.set_uniform("u_skyColor", cfg.sky_color)
        self._bridge.set_uniform("u_horizonColor", cfg.horizon_color)
        self._bridge.set_uniform("u_groundColor", cfg.ground_color)
        self._bridge.set_uniform("u_envIntensity", cfg.env_intensity)
        self._bridge.set_uniform("u_sunDir", cfg.sun_dir)

        debug_map = {"beauty": 0, "normal": 1, "distance": 2, "steps": 3, "albedo": 4, "emission": 5}
        self._bridge.set_uniform("u_debugView", debug_map.get(cfg.debug_view, 0))

    def _prepare_session_shader_paths(self, session: RenderSessionConfig) -> None:
        if session.source_frag_path:
            session.frag_path = write_glsl_wrapper(session.source_frag_path, "fragment")
            self._console_panel.append_line(f"Updated GLSL fragment wrapper: {session.frag_path}")
        elif session.frag_path and Path(session.frag_path).suffix.lower() == ".glsl":
            session.source_frag_path = session.frag_path
            session.frag_path = write_glsl_wrapper(session.source_frag_path, "fragment")
            self._console_panel.append_line(f"Wrapped GLSL fragment for backend: {session.frag_path}")
        elif session.frag_path and Path(session.frag_path).suffix.lower() in {".frag", ".fs"}:
            session.source_frag_path = None

        if session.source_vert_path:
            session.vert_path = write_glsl_wrapper(session.source_vert_path, "vertex")
            self._console_panel.append_line(f"Updated GLSL vertex wrapper: {session.vert_path}")
        elif session.vert_path and Path(session.vert_path).suffix.lower() == ".glsl":
            session.source_vert_path = session.vert_path
            session.vert_path = write_glsl_wrapper(session.source_vert_path, "vertex")
            self._console_panel.append_line(f"Wrapped GLSL vertex for backend: {session.vert_path}")
        elif session.vert_path and Path(session.vert_path).suffix.lower() in {".vert", ".vs"}:
            session.source_vert_path = None

    def _sync_extra_watch_files(self) -> None:
        if self._sdf_project:
            return
        paths = []
        for p in (self._session_config.source_frag_path, self._session_config.source_vert_path):
            if p:
                paths.append(p)
        for asset in self._session_config.assets:
            if asset.path and os.path.exists(asset.path):
                paths.append(asset.path)
        self._bridge.set_watch_files(paths)

    def _unique_asset_name(self, kind: str, name: str, path: str) -> str:
        if kind in {ASSET_CUBEMAP_ENV, ASSET_MODEL, ASSET_CAMERA_SEQUENCE}:
            return name
        base = name.strip() if name else ""
        if not base:
            if kind == ASSET_STREAM_TEXTURE:
                base = "u_texStream0"
            elif kind == ASSET_AUDIO:
                base = "u_audio0"
            elif kind == ASSET_SEQUENCE_UNIFORM:
                base = Path(path).stem if path else "u_values0"
            else:
                base = "u_tex0"
        base = re.sub(r"\W+", "_", base).strip("_") or "u_asset0"
        if not re.match(r"^[A-Za-z_]", base):
            base = f"u_{base}"
        used = {a.name for a in self._session_config.assets if a.name}
        if base not in used:
            return base
        stem = re.sub(r"\d+$", "", base) or base
        index = 1
        while f"{stem}{index}" in used:
            index += 1
        return f"{stem}{index}"

    def _on_recording_progress(self, pct: float) -> None:
        if pct >= 1.0:
            QTimer.singleShot(500, self._recording_panel.reset_progress)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self._open_paths(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._bridge.stop()
        event.accept()
