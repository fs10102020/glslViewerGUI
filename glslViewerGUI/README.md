# GlslViewerGUI — Shader Mission Control

A PySide6 desktop GUI that wraps [glslViewer](https://github.com/patriciogonzalezvivo/glslViewer), providing a live shader editor, uniform controls, camera manipulation, recording tools, preset management, and a built-in SDF (signed distance field) renderer for ray-marched / path-traced scenes.

![Screenshot](Screenshot.jpg)

## Requirements

- Python 3.10+
- PySide6 (`uv pip install -r requirements.txt`)
- glslViewer binary built at `../glslViewer/build/glslViewer`

## Quick Start

```bash
cd glslViewerGUI
python3 main.py
```

To launch the bundled Apollonian SDF example, use **File → Open Apollonian Example**, then try the SDF panel in the right dock under **Pipeline → SDF** to switch between the `preview` and `pathtrace` integrators.

## Installation

```bash
make install        # installs to ~/.local/bin and ~/.local/share/applications
make uninstall      # removes installed files
```

## Features

- **Live GLSL Editor** — syntax highlighting, error line highlighting, auto-reload on save.
- **Smart File Loading** — `File → Open` accepts fragments, vertices, models, cubemaps, images, videos, CSVs, SDF project directories, URLs, `/dev/*` capture devices, and folders/wildcards treated as streaming image sequences.
- **SDF Renderer** — turn-key signed-distance-field pipeline. Define a `float DE(vec3 p)` and the GUI composes a complete raymarcher or progressive path tracer with accumulation controls.
- **Uniform Panel** — auto-detects shader uniforms and supports `// @ui ...` metadata for grouped, bounded widgets.
- **Camera Panel** — distance, FOV, projection, position, look-at, nudge, and exposure controls.
- **Recording Panel** — screenshots, PNG sequences, frame-index sequences, and MP4/GIF video recording via glslViewer's ffmpeg integration.
- **Raw Command Console** — type glslViewer commands directly, with routed query responses and command history.
- **Preset Manager** — save and restore complete sessions.
- **Theming** — Dark, Light, and System themes with persistent preference.
- **Error Recovery** — auto-restarts crashed renderer while preserving session state.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open any supported file or directory |
| Ctrl+Shift+N | New SDF project |
| Ctrl+Shift+O | Open SDF project directory |
| Ctrl+S | Save current editor buffer |
| Ctrl+L | Focus raw command console |
| F5 | Reload shader |
| Ctrl+Q | Quit |

## File Loading

All open/drop/menu flows route through `file_classifier.py`, which classifies paths and builds the renderer session.

- `.frag` / `.fs` — fragment shader.
- `.vert` / `.vs` — vertex shader.
- `.glsl` — content-sniffed for SDF, vertex, fragment, Shadertoy, or `#pragma stage`; generic files default to fragment unless **Open Vertex Shader...** forces vertex interpretation.
- Directories containing `project.json` with `"type": "sdf_project"` — SDF project.
- Other directories and wildcard paths — streaming image sequences.
- `.ply`, `.obj`, `.stl`, `.glb`, `.gltf`, `.splat` — model / geometry assets.
- `.png`, `.jpg`, `.jpeg`, `.tga`, `.psd`, `.gif`, `.bmp`, `.hdr`, `.exr` — textures / cubemaps.
- `.mov`, `.mp4`, `.mkv`, `.mpg`, `.mpeg`, `.h264` — video streams.
- URLs and `/dev/*` paths — stream textures / capture devices.
- `.csv` — uniform or camera sequence.

A `.frag` is auto-paired with its `.vert` sibling and vice versa. Opening only assets or a model keeps the current fragment shader active and loads the assets incrementally at runtime.

## SDF Projects

Project layout:

```text
my_project/
  project.json     {"type": "sdf_project", "config": {...}}
  scene.glsl       user code; required: DE(vec3); optional: baseColor, emissionAt, initScene
```

Open with **File → Open SDF Project** or open the project directory through **File → Open**. The bundled example lives at `examples/sdf_apollonian/`.

User uniforms can be annotated for the panel:

```glsl
// @ui slider min=0.5 max=3.0 step=0.01 default=1.4 group="Fractal"
uniform float u_inversionScale;

// @ui color default=0.55,0.35,0.2 group="Material"
uniform vec3 u_surfaceColor;
```

## Headless Testing

The full GUI can be smoke-tested without a display or a built glslViewer binary:

```bash
QT_QPA_PLATFORM=offscreen uv run python smoke_test.py
```

The smoke test monkey-patches process launch and covers file classification, SDF composition, uniform parsing, command builders, session flags, query protocol, watcher batching, recording reset, GLSL wrapping, SDF mode enter/leave, scene revision tracking, incremental asset application, and layout.

## File Layout

```text
glslViewerGUI/
  main.py                       — Entry point
  main_window.py                — QMainWindow, docks, menus
  render_bridge.py              — QProcess wrapper around glslViewer
  file_classifier.py            — Single entry point for opening files
  sdf_project.py                — SDF project model + shader composer
  sdf_panel.py                  — SDF renderer control panel
  sdf_templates/                — GLSL templates for generated shaders
  examples/sdf_apollonian/      — Bundled example SDF project
  shader_editor.py              — GLSL editor with syntax highlighting
  shader_parser.py              — GLSL uniform extraction + @ui metadata
  uniform_panel.py              — Auto-generated uniform widgets
  camera_panel.py               — Camera controls
  recording_panel.py            — Screenshot / sequence / video UI
  preset_manager.py             — Session preset browser
  pipeline_panel.py             — Pipeline overlays, advanced pass defines, scene toggles
  assets_panel.py               — Texture / asset queue
  runtime_controls_panel.py     — fps / fullFps / vsync toggles
  console_panel.py              — Stdout/stderr log and raw command input
  session_config.py             — RenderSessionConfig + ShaderProgramSpec
  commands.py                   — CSV-command builders
  requirements.txt              — Python dependencies (PySide6 only)
  smoke_test.py                 — Headless smoke test
```

Example shaders used as test inputs live in `../exampleshaders/` at the repo root, not under `glslViewerGUI/`.
