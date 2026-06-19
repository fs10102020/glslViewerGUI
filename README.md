# GlslViewerGUI — Shader Mission Control

A PySide6 desktop GUI that wraps [glslViewer](https://github.com/patriciogonzalezvivo/glslViewer), providing a live shader editor, uniform controls, camera manipulation, recording tools, preset management, and a built-in SDF (signed distance field) renderer for ray-marched / path-traced scenes.

## Requirements

- Python 3.10+
- PySide6 (`uv pip install -r requirements.txt`)
- glslViewer binary built at `../glslViewer/build/glslViewer`

## Quick Start

```bash
cd glslViewerGUI
python3 main.py
```

To launch the bundled Apollonian SDF example from the **File → Open Apollonian Example** menu, then try the SDF panel (right dock → Pipeline tab → SDF) to switch between the `preview` and `pathtrace` integrators.

## Installation

```bash
make install        # installs to ~/.local/bin and ~/.local/share/applications
make uninstall      # removes installed files
```

## Features

- **Live GLSL Editor** — syntax highlighting, error line highlighting, auto-reload on save.
- **Smart File Loading** — `File → Open` accepts any glslViewer-loadable file: fragments, vertices, models, cubemaps, images, videos, CSVs, SDF project directories, URLs, `/dev/*` capture devices, and folders/wildcards treated as streaming image sequences. See [File Loading](#file-loading) below.
- **SDF Renderer** — turn-key signed-distance-field pipeline. Define a `float DE(vec3 p)` and the GUI composes a complete raymarcher (preview) or progressive path tracer (automatic two-pass `DOUBLE_BUFFER` accumulation) plus exposure, tone mapping, gamma, environment colors, shadow controls, and accumulation reset.
- **Uniform Panel** — auto-detects shader uniforms (float, int, bool, vec2/3/4, mat2/3/4); `// @ui slider min=0 max=1 step=0.01 default=0.5 group="…"` comments group and bound the widgets. Save/load presets.
- **Camera Panel** — distance, FOV, projection, position, look-at, nudge, exposure controls.
- **Recording Panel** — screenshots, PNG sequences, frame-index sequences, MP4/GIF video recording (via glslViewer's ffmpeg integration).
- **Raw Command Console** — type any glslViewer command directly; query mode routes responses back to the console (Ctrl+L to focus).
- **Preset Manager** — save and restore complete sessions (shader + uniforms + camera).
- **Theming** — Dark, Light, and System themes with persistent preference.
- **Error Recovery** — auto-restarts crashed renderer with fallback to default shader.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open (any supported file or directory) |
| Ctrl+Shift+N | New SDF project |
| Ctrl+Shift+O | Open SDF project directory |
| Ctrl+S | Save current editor buffer (inside the editor) |
| Ctrl+L | Focus raw command console |
| F5 | Reload shader |
| Ctrl+Q | Quit |

## File Loading

All "open this" actions route through a single classifier (`glslViewerGUI/file_classifier.py`). The classifier decides what each path is and assembles a `LoadPlan` that becomes the renderer's session.

What it recognises:

- `.frag` / `.fs` — fragment shader.
- `.vert` / `.vs` — vertex shader.
- `.glsl` — content-sniffed for `float DE(vec3 p)`, `gl_Position`, `gl_FragColor`/`fragColor`, `mainImage`, Shadertoy uniforms, or `#pragma stage`. A generic `.glsl` with `void main()` is used as a fragment shader by default, except **Open Vertex Shader...** forces vertex interpretation.
- Directories containing `project.json` with `"type": "sdf_project"` — SDF project.
- Other directories and wildcard paths — streaming image sequences.
- A selected `project.json` file itself is also accepted as an SDF project shortcut.
- `.ply`, `.obj`, `.stl`, `.glb`, `.gltf`, `.splat` — model / geometry assets.
- `.png`, `.jpg`, `.jpeg`, `.tga`, `.psd`, `.gif`, `.bmp`, `.hdr`, `.exr` — textures / cubemaps.
- `.mov`, `.mp4`, `.mkv`, `.mpg`, `.mpeg`, `.h264` — video streams.
- URLs and `/dev/*` paths — stream textures / capture devices.
- `.csv` — uniform or camera sequence (camera CSV if filename starts with `camera`).

A `.frag` is auto-paired with its `.vert` sibling and vice versa. Multi-file selection builds one combined session. Standalone `.glsl` files that only define `DE()` are imported as temporary SDF projects. Opening only assets or a model keeps the current fragment shader active and loads the assets at runtime.

## SDF Projects

Project layout:

```
my_project/
  project.json     {"type": "sdf_project", "config": {...}}
  scene.glsl       user code (required: DE(vec3); optional: baseColor, emissionAt, initScene)
```

Open with **File → Open SDF Project** or just open the project directory via **File → Open**; the classifier picks it up.

`scene.glsl` contract:

```glsl
// required
float DE(vec3 p);

// optional
vec3 baseColor(vec3 p, vec3 normal);
vec3 emissionAt(vec3 p, vec3 normal);
void initScene();
```

User uniforms can be annotated for the panel:

```glsl
// @ui slider min=0.5 max=3.0 step=0.01 default=1.4 group="Fractal"
uniform float u_inversionScale;

// @ui color default=0.55,0.35,0.2 group="Material"
uniform vec3 u_surfaceColor;

// @ui integer min=1 max=16 default=8 group="Fractal"
uniform int u_iterations;
```

The Apollonian example lives at `glslViewerGUI/examples/sdf_apollonian/` and is the easiest way to try SDF mode. Templates for the generated shader are under `glslViewerGUI/sdf_templates/`.

## Headless Testing

The full GUI can be smoke-tested without a display or a built glslViewer binary:

```bash
cd glslViewerGUI
QT_QPA_PLATFORM=offscreen uv run python smoke_test.py
```

The smoke test monkey-patches `RenderBridge.start` so no `glslViewer` is launched, and runs table-driven checks for the file classifier, SDF project validation, uniform parsing, command builders, session flags, query protocol, watcher batching, and the panel layout.

## File Layout

```
glslViewerGUI/
  main.py                       — Entry point
  main_window.py                — QMainWindow, docks, menus
  render_bridge.py              — QProcess wrapper around glslViewer
  file_classifier.py            — Single entry point for opening files
  sdf_project.py                — SDF project model + shader composer
  sdf_panel.py                  — SDF renderer control panel
  sdf_templates/                — GLSL templates for the generated shader
    common.glsl                 — math, RNG, environment lighting
    camera.glsl                 — ray generation from u_camera + matrices
    marcher.glsl                — robust sphere tracing, normal estimation, AO, soft shadows
    preview.glsl                — direct lighting preview integrator
    pathtrace.glsl              — progressive path tracer
    display.glsl                — exposure, tone mapping, gamma
    scene_defaults.glsl         — default DE / baseColor / emissionAt
    generated_main.frag.template— main() entry point
  examples/sdf_apollonian/      — bundled example SDF project
  shader_editor.py              — GLSL editor with syntax highlighting
  shader_parser.py              — GLSL uniform extraction + @ui metadata
  uniform_panel.py              — Auto-generated uniform widgets
  camera_panel.py               — Camera controls
  recording_panel.py            — Screenshot / sequence / video UI
  preset_manager.py             — Session preset browser
  pipeline_panel.py             — Pipeline overlays, advanced pass defines, scene toggles
  defines_panel.py              — Live define/undefine commands
  include_panel.py              — Add include directories at runtime
  dependency_viewer_panel.py    — List glslViewer's watched dependencies
  inspector_panel.py            — Runtime query commands
  scene_panel.py                — Quick scene toggles
  assets_panel.py               — Texture / asset queue
  streams_panel.py              — Video stream controls
  runtime_controls_panel.py     — fps / fullFps / vsync toggles
  console_panel.py              — Stdout/stderr log and raw command input
  error_parser.py               — Driver-agnostic shader compile error parser
  shader_diagnostics.py         — frag/vert pairing checks
  session_config.py             — RenderSessionConfig + ShaderProgramSpec
  session_dialog.py             — Window / renderer / paths editor
  themes.py                     — Dark / Light / System theme engine
  commands.py                   — CSV-command builders (uniform, define, …)
  default_shader.frag           — Default startup shader
  requirements.txt              — Python dependencies (PySide6 only)
  smoke_test.py                 — Headless CI test
  glslviewer-gui                — Shell launcher
  glslviewer-gui.desktop        — Linux desktop entry
```

Example shaders used as test inputs live in `exampleshaders/` at the repo root, **not** under `glslViewerGUI/`.
