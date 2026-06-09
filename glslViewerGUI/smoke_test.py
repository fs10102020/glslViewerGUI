"""Headless smoke test for glslViewerGUI architecture."""
import sys
import os

os.chdir("/home/frontstreet/Desktop/OpenCode-TUI-Projects/glslViewer-GUI-Testing/glslViewerGUI")
sys.path.insert(0, os.getcwd())

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMainWindow, QScrollArea, QWidget, QTabWidget

app = QApplication(sys.argv)

forbidden_binding = "Py" + "Qt6"
for mod in sorted(sys.modules):
    if mod.startswith(forbidden_binding):
        print(f"FAIL: forbidden Qt binding module still loaded: {mod}")
        sys.exit(1)

# Verify all panel imports work
from main_window import MainWindow
from uniform_panel import UniformPanel
from camera_panel import CameraPanel
from recording_panel import RecordingPanel
from console_panel import ConsolePanel
from preset_manager import PresetPanel
from assets_panel import AssetsPanel
from streams_panel import StreamsPanel
from scene_panel import ScenePanel
from pipeline_panel import PipelinePanel
from inspector_panel import InspectorPanel
from dependency_viewer_panel import DependencyViewerPanel
from runtime_controls_panel import RuntimeControlsPanel
from include_panel import IncludePanel
from defines_panel import DefinesPanel
from session_dialog import SessionDialog
from render_bridge import RenderBridge
from commands import build_uniform, build_reload, build_camera_list
from session_config import ShaderProgramSpec, discover_vert_sibling, discover_frag_sibling
from shader_diagnostics import diagnose_shader_pair

# Quick class hierarchy check
assert issubclass(UniformPanel, QWidget), f"UniformPanel not QWidget: {UniformPanel.__bases__}"
assert issubclass(CameraPanel, QWidget), f"CameraPanel not QWidget: {CameraPanel.__bases__}"

# Prevent actual binary launch during smoke test
original_start = RenderBridge.start
RenderBridge.start = lambda self, *a, **k: self.process_started.emit()

try:
    win = MainWindow()
finally:
    RenderBridge.start = original_start

# Right dock checks
right_dock = win._right_dock
right_tabs = win._right_tabs
assert right_tabs.count() == 6, f"Expected 6 right tabs, got {right_tabs.count()}"

# Verify nested tabs exist
assets_widget = right_tabs.widget(3)
shader_widget = right_tabs.widget(4)
pipeline_widget = right_tabs.widget(5)

assert isinstance(assets_widget, QTabWidget), f"Assets tab should be QTabWidget, got {type(assets_widget)}"
assert assets_widget.count() == 2, f"Expected 2 asset sub-tabs, got {assets_widget.count()}"

assert isinstance(shader_widget, QTabWidget), f"Shader tab should be QTabWidget, got {type(shader_widget)}"
assert shader_widget.count() == 3, f"Expected 3 shader sub-tabs, got {shader_widget.count()}"

assert isinstance(pipeline_widget, QTabWidget), f"Pipeline tab should be QTabWidget, got {type(pipeline_widget)}"
assert pipeline_widget.count() == 3, f"Expected 3 pipeline sub-tabs, got {pipeline_widget.count()}"

# Central editor checks — should be a tabbed editor with Fragment + Vertex
central = win.centralWidget()
assert isinstance(central, QTabWidget), f"Central widget should be QTabWidget, got {type(central)}"
assert central.count() == 2, f"Expected 2 editor tabs (Fragment + Vertex), got {central.count()}"
assert central.tabText(0) == "Fragment", f"First tab should be 'Fragment', got '{central.tabText(0)}'"
assert central.tabText(1) == "Vertex", f"Second tab should be 'Vertex', got '{central.tabText(1)}'"

# Verify corner widget shows program label
corner = central.cornerWidget()
assert corner is not None, "Editor should have a corner widget showing program label"
assert hasattr(corner, "text"), "Corner widget should be a QLabel with text()"

# Bottom dock checks
assert isinstance(win._console_dock, type(right_dock)), "Console should be QDockWidget"
assert isinstance(win._recording_dock, type(right_dock)), "Recording should be QDockWidget"
assert isinstance(win._preset_dock, type(right_dock)), "Presets should be QDockWidget"

# Toolbar check
from PySide6.QtWidgets import QToolBar
toolbars = win.findChildren(QToolBar)
assert len(toolbars) >= 1, f"Expected at least 1 toolbar, got {len(toolbars)}"

# Verify uniform command uses correct syntax (no "uniform," prefix)
cmd = build_uniform("myVar", 0.5)
assert cmd == "myVar,0.5", f"Uniform command wrong: {cmd!r}"

# Verify camera panel has new controls
assert hasattr(win._camera_panel, "_cam_name"), "CameraPanel missing _cam_name"
assert hasattr(win._camera_panel, "_exp_aper"), "CameraPanel missing _exp_aper"

# Verify theme was applied (amber accent)
from PySide6.QtCore import QSettings
from themes import get_theme, apply_theme
settings = QSettings("glslViewer", "GlslViewerGUI")
theme = settings.value("theme", "dark")
assert theme in ("dark", "light", "system"), f"Unexpected theme: {theme}"

dark_qss = get_theme("dark").qss
for selector in ["QMenuBar", "QPushButton", "QDockWidget::title", "QTabBar::tab:selected", "QProgressBar::chunk"]:
    assert selector in dark_qss, f"Dark theme missing selector: {selector}"

apply_theme(win, "dark")
assert "#1e1e1e" in win._frag_editor._editor.styleSheet(), "Fragment editor did not receive dark theme"
assert "#1e1e1e" in win._vert_editor._editor.styleSheet(), "Vertex editor did not receive dark theme"

# Verify window size and constraints
assert win.width() >= 1400 and win.height() >= 900, f"Window too small: {win.width()}x{win.height()}"
assert win.minimumWidth() == 960 and win.minimumHeight() == 640, f"Wrong minimum size: {win.minimumWidth()}x{win.minimumHeight()}"

# Verify bottom docks have no restrictive max height
assert win._console_dock.maximumHeight() >= 1000, f"Console max height too restrictive: {win._console_dock.maximumHeight()}"
assert win._recording_dock.maximumHeight() >= 1000, f"Recording max height too restrictive: {win._recording_dock.maximumHeight()}"
assert win._preset_dock.maximumHeight() >= 1000, f"Presets max height too restrictive: {win._preset_dock.maximumHeight()}"

# Verify recording dock is wrapped in scroll area
rec_scroll = win._recording_dock.widget()
assert isinstance(rec_scroll, QScrollArea), f"Recording dock widget should be QScrollArea, got {type(rec_scroll)}"

# Verify dock layout is resizable and nested explicitly
assert win.dockOptions() & QMainWindow.DockOption.AllowNestedDocks, "Nested docks must be enabled for bottom split resizing"
assert win.tabifiedDockWidgets(win._recording_dock) == [win._preset_dock], "Presets should be tabified with Recording"

# Verify right dock has no restrictive maximum width
assert win._right_dock.maximumWidth() >= 1000, f"Right dock max width too restrictive: {win._right_dock.maximumWidth()}"
assert win._right_dock.minimumWidth() == 220, f"Right dock min width wrong: {win._right_dock.minimumWidth()}"
assert win._right_dock.minimumSizeHint().width() <= 260, f"Right dock min size hint too wide: {win._right_dock.minimumSizeHint().width()}"
assert isinstance(win._right_tabs.widget(1), QScrollArea), "Camera tab should be scroll-wrapped to avoid width pressure"

# Verify ShaderProgramSpec works
prog = ShaderProgramSpec(frag_path="/tmp/test.frag", vert_path="/tmp/test.vert")
assert prog.program_label == "test.frag + test.vert", f"Label wrong: {prog.program_label}"

prog2 = ShaderProgramSpec()
assert prog2.program_label == "(default)", f"Default label wrong: {prog2.program_label}"

# Verify sibling discovery
vert_sibling = discover_vert_sibling("/home/frontstreet/Desktop/OpenCode-TUI-Projects/glslViewer-GUI-Testing/exampleshaders/orbital_geometry.frag")
assert vert_sibling is not None, "Should discover orbital_geometry.vert as sibling"
assert vert_sibling.endswith("orbital_geometry.vert"), f"Wrong sibling: {vert_sibling}"

frag_sibling = discover_frag_sibling("/home/frontstreet/Desktop/OpenCode-TUI-Projects/glslViewer-GUI-Testing/exampleshaders/orbital_geometry.vert")
assert frag_sibling is not None, "Should discover orbital_geometry.frag as sibling"
assert frag_sibling.endswith("orbital_geometry.frag"), f"Wrong sibling: {frag_sibling}"

# Verify from_path factory
sp = ShaderProgramSpec.from_path("/home/frontstreet/Desktop/OpenCode-TUI-Projects/glslViewer-GUI-Testing/exampleshaders/orbital_geometry.frag")
assert sp.frag_path is not None, "from_path should set frag_path"
assert sp.vert_path is not None, "from_path should auto-discover vert sibling"
assert sp.vert_path.endswith("orbital_geometry.vert"), f"Auto-discovered vert wrong: {sp.vert_path}"

# Verify diagnostics
frag_src = "#version 330 core\nin vec2 vUV;\nout vec4 fragColor;\nvoid main() { fragColor = vec4(1.0); }"
vert_src = "#version 330 core\nin vec2 a_position;\nout vec2 vUV;\nvoid main() { vUV = a_position; gl_Position = vec4(a_position, 0.0, 1.0); }"
issues = diagnose_shader_pair(frag_src, vert_src)
assert isinstance(issues, list), "Diagnostics should return a list"

# Verify RenderBridge uses ShaderProgramSpec
assert hasattr(win._bridge, "program"), "Bridge should have .program property"
assert isinstance(win._bridge.program, ShaderProgramSpec), "Bridge.program should be ShaderProgramSpec"

print("ALL CHECKS PASSED")
print(f"  right_tabs={right_tabs.count()}")
print(f"  assets_subtabs={assets_widget.count()}")
print(f"  shader_subtabs={shader_widget.count()}")
print(f"  pipeline_subtabs={pipeline_widget.count()}")
print(f"  editor_tabs={central.count()}")
print(f"  bottom_docks=3")
print(f"  toolbar=1")
print(f"  window={win.width()}x{win.height()}")
print(f"  theme={theme}")
print(f"  program_label={corner.text()}")
print(f"  shader_program={win._bridge.program.program_label}")
