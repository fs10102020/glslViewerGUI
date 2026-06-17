"""Headless smoke test for glslViewerGUI architecture."""
import sys
import os
import tempfile
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
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
from session_config import (
    AssetSpec,
    RenderSessionConfig,
    ShaderProgramSpec,
    discover_vert_sibling,
    discover_frag_sibling,
    ASSET_NAMED_TEXTURE,
    ASSET_STREAM_TEXTURE,
    ASSET_SEQUENCE_UNIFORM,
)
from glsl_wrapper import write_glsl_wrapper
from shader_diagnostics import diagnose_shader_pair
from sdf_panel import SdfPanel
from sdf_project import SdfProject, SdfProjectConfig, SdfShaderComposer, is_sdf_project
from shader_parser import parse_uniforms
from file_classifier import classify_paths, AssetKind, build_session_from_plan

# Quick class hierarchy check
assert issubclass(UniformPanel, QWidget), f"UniformPanel not QWidget: {UniformPanel.__bases__}"
assert issubclass(CameraPanel, QWidget), f"CameraPanel not QWidget: {CameraPanel.__bases__}"

# Prevent actual binary launch during smoke test. Keep this patched for the
# whole run so later _open_paths() tests don't spawn glslViewer.
original_start = RenderBridge.start
def fake_start(self, shader_path=None, vert_path=None, geom_path=None):
    from session_config import ShaderProgramSpec
    self._shader_path = shader_path
    self._vert_path = vert_path
    self._geom_path = geom_path
    self._program = ShaderProgramSpec(frag_path=shader_path, vert_path=vert_path, model_path=geom_path)
    self._session_config.frag_path = shader_path
    self._session_config.vert_path = vert_path
    self._session_config.geom_path = geom_path
    self.process_started.emit()
RenderBridge.start = fake_start

win = MainWindow()

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
assert pipeline_widget.count() == 4, f"Expected 4 pipeline sub-tabs, got {pipeline_widget.count()}"

# SDF panel should exist and be disabled by default
assert hasattr(win, "_sdf_panel"), "MainWindow should have _sdf_panel"
assert isinstance(win._sdf_panel, SdfPanel), f"_sdf_panel should be SdfPanel, got {type(win._sdf_panel)}"
assert not win._sdf_panel.isEnabled(), "SDF panel should be disabled until an SDF project is open"

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

# Verify GUI launch args enforce noncurses and avoid backend-broken valued -D syntax.
cfg = RenderSessionConfig(
    frag_path="shader.frag",
    defines={"FOO": "1", "BAR": ""},
    noncurses=False,
    assets=[AssetSpec(kind=ASSET_SEQUENCE_UNIFORM, name="u_curve", path="curve.csv")],
)
args = cfg.build_args()
assert "--noncurses" in args, "GUI sessions must always force --noncurses"
assert "-DFOO=1" not in args, "Valued defines must not use glslViewer's broken -DKEY=VALUE path"
assert "define,FOO,1" in args, "Valued defines should be emitted as startup commands"
assert "-u_curve" in args and "curve.csv" in args, "Sequence uniforms should load through CLI -name path"

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    source = tmp_path / "plain.glsl"
    source.write_text("void main() { gl_FragColor = vec4(1.0); }")
    wrapped = write_glsl_wrapper(str(source), "fragment")
    assert wrapped.endswith(".frag"), f"Fragment .glsl wrapper should end in .frag: {wrapped}"
    assert Path(wrapped).read_text() == source.read_text(), "Wrapper should preserve source text"

# Verify diagnostics
frag_src = "#version 330 core\nin vec2 vUV;\nout vec4 fragColor;\nvoid main() { fragColor = vec4(1.0); }"
vert_src = "#version 330 core\nin vec2 a_position;\nout vec2 vUV;\nvoid main() { vUV = a_position; gl_Position = vec4(a_position, 0.0, 1.0); }"
issues = diagnose_shader_pair(frag_src, vert_src)
assert isinstance(issues, list), "Diagnostics should return a list"

# Verify RenderBridge uses ShaderProgramSpec
assert hasattr(win._bridge, "program"), "Bridge should have .program property"
assert isinstance(win._bridge.program, ShaderProgramSpec), "Bridge.program should be ShaderProgramSpec"

# Verify SDF project creation / composer
with tempfile.TemporaryDirectory() as tmp:
    proj_dir = os.path.join(tmp, "test_sdf")
    proj = SdfProject.create_new(proj_dir)
    assert is_sdf_project(proj_dir), "Created directory should be recognized as SDF project"
    assert proj.is_valid, "Loaded project should be valid"
    assert "float DE(vec3 p)" in proj.scene_source, "Default scene should define DE"

    composer = SdfShaderComposer(proj)
    generated = composer.compose()
    assert "void main()" in generated, "Generated shader should contain main()"
    assert "DE(" in generated, "Generated shader should reference DE()"
    assert "u_maxSteps" in generated, "Generated shader should declare renderer uniforms"

    generated_path = composer.generate()
    assert os.path.exists(generated_path), "Generated shader file should be written"

# Verify uniform metadata parsing
meta_source = """
// @ui slider min=0.5 max=3.0 step=0.01 default=1.4 group="Fractal"
uniform float u_inversionScale;
// @ui color default=1.0,0.5,0.2 group="Material"
uniform vec3 u_surfaceColor;
// @ui integer min=1 max=16 step=1 default=8 group="Fractal"
uniform int u_iterations;
uniform float u_inline; // @ui slider min=0.0 max=2.0 step=0.1 default=1.0 group="Inline"
"""
uniforms = parse_uniforms(meta_source)
assert len(uniforms) == 4, f"Expected 4 parsed uniforms, got {len(uniforms)}"
inv = next(u for u in uniforms if u["name"] == "u_inversionScale")
assert inv["widget"] == "float", f"slider alias should normalize to float, got {inv['widget']!r}"
assert inv["group"] == "Fractal"
assert inv["value"] == 1.4
col = next(u for u in uniforms if u["name"] == "u_surfaceColor")
assert col["widget"] == "color"
assert col["value"] == [1.0, 0.5, 0.2]
itr = next(u for u in uniforms if u["name"] == "u_iterations")
assert itr["widget"] == "int", f"integer alias should normalize to int, got {itr['widget']!r}"
assert itr["value"] == 8
inline = next(u for u in uniforms if u["name"] == "u_inline")
assert inline["widget"] == "float", "trailing @ui comments should be parsed"
assert inline["value"] == 1.0

# Verify UniformPanel actually creates widgets for normalized metadata.
win._uniform_panel.load_from_source(meta_source)
from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
spinbox_names = [name for name, w in win._uniform_panel._widgets.items()
                 if isinstance(w, QDoubleSpinBox)]
assert "u_inversionScale" in spinbox_names, "slider/float metadata should produce a QDoubleSpinBox"
assert "u_inline" in spinbox_names, "trailing @ui metadata should produce a QDoubleSpinBox"
int_names = [name for name, w in win._uniform_panel._widgets.items()
             if isinstance(w, QSpinBox)]
assert "u_iterations" in int_names, "integer metadata should produce a QSpinBox"

# File classifier table-driven tests.
from file_classifier import classify_paths, AssetKind

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = __import__("pathlib").Path(tmp)

    frag = tmp_path / "x.frag"
    frag.write_text("void main() { gl_FragColor = vec4(1.0); }")
    vert = tmp_path / "x.vert"
    vert.write_text("void main() { gl_Position = vec4(0.0); }")

    sdf_dir = tmp_path / "my_sdf"
    sdf_dir.mkdir()
    (sdf_dir / "project.json").write_text(
        '{"type": "sdf_project", "config": {"scene": "scene.glsl"}}'
    )
    (sdf_dir / "scene.glsl").write_text("float DE(vec3 p) { return length(p); }")

    sdf_only = tmp_path / "scene.glsl"
    sdf_only.write_text("float DE(vec3 p) { return length(p); }")

    toy = tmp_path / "toy.glsl"
    toy.write_text("uniform float iTime; void mainImage(out vec4 c) { c = vec4(iTime); }")

    vert_only = tmp_path / "vert_only.glsl"
    vert_only.write_text("void main() { gl_Position = vec4(0.0); }")

    model = tmp_path / "thing.obj"
    model.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    tex = tmp_path / "thing.png"
    tex.write_bytes(b"\x89PNG\r\n\x1a\n")
    vid = tmp_path / "thing.mp4"
    vid.write_bytes(b"\x00\x00\x00\x18ftyp")
    csv_u = tmp_path / "u_curve.csv"
    csv_u.write_text("a,b\n0,0\n1,1\n")
    csv_cam = tmp_path / "camera_path.csv"
    csv_cam.write_text("t,x,y,z\n0,0,0,0\n1,1,1,1\n")

    plan = classify_paths([
        str(frag), str(vert),
        str(sdf_dir), str(sdf_only), str(toy), str(vert_only),
        str(model), str(tex), str(vid), str(csv_u), str(csv_cam),
    ])
    assert plan.frag_path == frag
    assert plan.vert_path == vert
    assert plan.sdf_project == sdf_dir
    assert plan.sdf_scene == sdf_only
    assert any(p == toy for p in plan.shadertoy_candidates)
    assert any(p == model for p in plan.mesh_paths)
    assert any(p == tex for p in plan.texture_paths)
    assert any(p == vid for p in plan.video_paths)
    assert csv_cam in plan.csv_paths
    assert csv_u in plan.csv_paths

    # Validator: directories with project.json of wrong type are not SDF projects.
    bad_dir = tmp_path / "bad_sdf"
    bad_dir.mkdir()
    (bad_dir / "project.json").write_text('{"type": "other_project"}')
    assert not is_sdf_project(bad_dir)

    # Validator: project without scene file is invalid.
    no_scene_dir = tmp_path / "no_scene"
    no_scene_dir.mkdir()
    (no_scene_dir / "project.json").write_text(
        '{"type": "sdf_project", "config": {"scene": "missing.glsl"}}'
    )
    assert not is_sdf_project(no_scene_dir)

    # Hash collision avoidance: two projects with same directory name in
    # different parents produce distinct generated paths.
    proj_a_dir = tmp_path / "scene"
    proj_a_dir.mkdir()
    (proj_a_dir / "project.json").write_text(
        '{"type": "sdf_project", "config": {"scene": "scene.glsl"}}'
    )
    (proj_a_dir / "scene.glsl").write_text("float DE(vec3 p) { return 1.0; }")
    proj_b_dir = tmp_path / "subdir" / "scene"
    proj_b_dir.mkdir(parents=True)
    (proj_b_dir / "project.json").write_text(
        '{"type": "sdf_project", "config": {"scene": "scene.glsl"}}'
    )
    (proj_b_dir / "scene.glsl").write_text("float DE(vec3 p) { return 1.0; }")
    pa = SdfProject(project_dir=proj_a_dir).load()
    pb = SdfProject(project_dir=proj_b_dir).load()
    assert pa.generated_frag_path != pb.generated_frag_path, (
        "Projects in different parents with the same name should not share cache path"
    )

# Verify stream_texture command never passes both webcam and flip.
from commands import build_stream_texture
assert build_stream_texture("u_cam", "/dev/video0", webcam=True, flip=True) == "stream_texture,u_cam,/dev/video0,webcam"
assert build_stream_texture("u_vid", "movie.mp4", webcam=False, flip=True) == "stream_texture,u_vid,movie.mp4,flip"

# Verify project.json file paths are recognized as SDF projects.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = __import__("pathlib").Path(tmp)
    sdf_dir = tmp_path / "from_json"
    sdf_dir.mkdir()
    (sdf_dir / "project.json").write_text(
        '{"type": "sdf_project", "config": {"scene": "scene.glsl"}}'
    )
    (sdf_dir / "scene.glsl").write_text("float DE(vec3 p) { return length(p); }")
    json_file = sdf_dir / "project.json"
    plan = classify_paths([str(json_file)])
    assert plan.sdf_project == json_file, "Selecting project.json should open its SDF project"

# Verify .glsl stage hints and generic fragment fallback.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = __import__("pathlib").Path(tmp)
    pragma_frag = tmp_path / "pragma.frag.glsl"
    pragma_frag.write_text('#pragma stage fragment\nvoid main() { gl_FragColor = vec4(1.0); }')
    plan = classify_paths([str(pragma_frag)])
    assert plan.frag_path == pragma_frag, "#pragma stage fragment should classify as fragment shader"

    generic = tmp_path / "generic.glsl"
    generic.write_text('out vec4 color;\nvoid main() { color = vec4(1.0); }')
    plan = classify_paths([str(generic)])
    assert plan.frag_path == generic, "Generic .glsl with main() should be used as fragment shader"

# Verify malformed and out-of-order @ui comments do not crash the parser.
malformed_source = """
uniform float u_bad; // @ui
// @ui default=2.0 group="Reordered" slider
uniform float u_reordered;
"""
malformed_uniforms = parse_uniforms(malformed_source)
assert len(malformed_uniforms) == 2, f"Expected 2 uniforms, got {len(malformed_uniforms)}"
bad = next(u for u in malformed_uniforms if u["name"] == "u_bad")
assert bad["widget"] == "float"  # falls back to type-based widget
reordered = next(u for u in malformed_uniforms if u["name"] == "u_reordered")
assert reordered["widget"] == "float", f"widget should be slider alias -> float, got {reordered['widget']!r}"
assert reordered["group"] == "Reordered"
assert reordered["value"] == 2.0

# Verify composer strips duplicate scene #version directives and ignores hooks in comments.
with tempfile.TemporaryDirectory() as tmp:
    proj_dir = os.path.join(tmp, "version_test")
    proj = SdfProject.create_new(proj_dir)
    proj.scene_source = """#version 300 es
// vec3 baseColor(vec3 p, vec3 normal) { return vec3(0.0); }
float DE(vec3 p) { return length(p) - 1.0; }
"""
    composer = SdfShaderComposer(proj)
    generated = composer.compose()
    version_lines = [l for l in generated.splitlines() if l.strip().startswith("#version")]
    assert len(version_lines) == 1, f"Generated shader must contain exactly one #version line, got {len(version_lines)}"
    assert "#define HAS_BASECOLOR" not in generated, "Commented-out baseColor should not trigger HAS_BASECOLOR"

# Verify preview generated shader has no double-buffer blocks, pathtrace does.
with tempfile.TemporaryDirectory() as tmp:
    proj_dir = os.path.join(tmp, "integrator_test")
    proj = SdfProject.create_new(proj_dir)
    proj.config.integrator = "preview"
    preview_src = SdfShaderComposer(proj).compose()
    assert "#ifdef DOUBLE_BUFFER_0" not in preview_src, "Preview shader should not request double buffers"
    assert "#ifdef DOUBLE_BUFFER_1" not in preview_src, "Preview shader should not request double buffers"

    proj.config.integrator = "pathtrace"
    pt_src = SdfShaderComposer(proj).compose()
    assert "#ifdef DOUBLE_BUFFER_0" in pt_src, "Pathtrace shader must request double buffer 0"
    assert "#ifdef DOUBLE_BUFFER_1" in pt_src, "Pathtrace shader must request double buffer 1"

# Verify _open_paths preserves the current shader when only assets/models are opened.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = __import__("pathlib").Path(tmp)
    active_frag = tmp_path / "active.frag"
    active_frag.write_text("void main() { gl_FragColor = vec4(1.0); }")
    win._session_config.frag_path = str(active_frag)

    model = tmp_path / "cube.obj"
    model.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    tex = tmp_path / "tex.png"
    tex.write_bytes(b"\x89PNG\r\n\x1a\n")
    csv = tmp_path / "u_curve.csv"
    csv.write_text("a,b\n0,0\n1,1\n")
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"\x00\x00\x00\x18ftyp")

    sent_commands: list[str] = []
    original_send = win._bridge.send_command
    win._bridge.send_command = lambda cmd: sent_commands.append(cmd)
    try:
        win._open_paths([str(model), str(tex), str(csv), str(vid)])
    finally:
        win._bridge.send_command = original_send

    assert win._session_config.geom_path == str(model), "Model-only open should set geom_path"
    assert win._session_config.frag_path == str(active_frag), "Asset-only open should keep active fragment shader"
    asset_kinds = {a.kind for a in win._session_config.assets}
    assert ASSET_NAMED_TEXTURE in asset_kinds, "Texture should be queued as named_texture"
    assert ASSET_STREAM_TEXTURE in asset_kinds, "Video should be queued as stream_texture"
    assert ASSET_SEQUENCE_UNIFORM in asset_kinds, "CSV should be queued as sequence_uniform"
    assert not any("sequence_uniform" in c for c in sent_commands), "Runtime sequence_uniform command is intentionally avoided"

# Verify standalone SDF .glsl import does not overwrite the active fragment file.
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = __import__("pathlib").Path(tmp)
    active_frag = tmp_path / "keepme.frag"
    active_frag.write_text("// original fragment shader\nvoid main() { gl_FragColor = vec4(1.0); }")
    win._session_config.frag_path = str(active_frag)

    sdf_only = tmp_path / "standalone.glsl"
    sdf_only.write_text("float DE(vec3 p) { return length(p) - 1.0; }")

    win._open_paths([str(sdf_only)])
    assert active_frag.read_text().startswith("// original fragment shader"), (
        "Importing a standalone SDF scene must not overwrite the active fragment shader"
    )

RenderBridge.start = original_start

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
