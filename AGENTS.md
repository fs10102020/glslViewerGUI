# AGENTS.md — OpenCode TUI Projects

This repo contains **two independent projects** sharing a directory:

- **`glslViewer/`** — C++ console-based OpenGL sandbox for 2D/3D GLSL shaders
- **`glslViewerGUI/`** — Python/PyQt6 GUI frontend that wraps the C++ binary

There is also a **Blender integration** (Python scripts inside `glslViewer/scripts/`).

---

## glslViewer (C++) — Core Engine

### Build

| Command | Purpose |
|---------|---------|
| `make -C glslViewer` | Default build (cmake + make) |
| `make -C glslViewer nox11` | Build without X11 (`-DNO_X11`) |
| `make -C glslViewer wasm` | Cross-compile to WASM via emscripten (`$EMSDK` must be set) |
| `make -C glslViewer install` | Install built binary |
| `cmake -DPYTHON_BINDINGS=ON ..` | Build with Python bindings (requires pybind11) |

Output goes to `glslViewer/build/` (or `build_nox11`, `build_wasm`). The binary is `glslViewer`.

### Dependencies

- **vera** — core GL framework (git submodule in `deps/vera`)
- **liblo** — OSC support (in `deps/liblo`, compiled automatically)
- **pybind11** — optional Python bindings (in `deps/pybind11`)
- **ncurses** — optional TUI mode (auto-detected)
- **ffmpeg** — optional video/audio texture support

### Architecture

```
src/main.cpp                 — Entry point, CLI args, file watcher thread, command loop
src/core/glslViewer.h/.cpp   — Central GlslViewer class ("sandbox"): render pipeline,
                                shader management, defines, events
src/core/sceneRender.h/.cpp  — 3D scene: geometry loading, PBR lighting, camera,
                                wireframe, shadow maps
src/core/uniforms.h/.cpp     — Uniform system: auto-generated (u_time, u_mouse…),
                                user-defined uniforms, textures, buffers, sequences
src/core/tools/command.h     — Command struct: trigger + exec function + formula + description
src/core/tools/console.h/.cpp— stdin/readline console loop, command dispatch
src/core/tools/files.h       — WatchFile struct, WatchFileList, file type enums
src/core/tools/record.h/.cpp — Screenshot and PNG sequence recording
src/core/tools/text.h/.cpp   — Text rendering with FreeType
src/core/tools/tracker.h/.cpp— Draw-time tracking (histogram data)
src/core/tools/job.h         — Thread-safe job queue
src/core/tools/lockFreeQueue.h — Lock-free single-producer-single-consumer queue
src/python/engine.h/.cpp     — Pybind11 Engine class (wraps GlslViewer)
src/python/headless.h/.cpp   — Headless renderer for Python
src/python/bindings.cpp      — Pybind11 module definition (PyGlslViewer)
```

### Control Flow

1. `main.cpp` parses CLI args → builds a `WatchFileList` + a `GlslViewer sandbox`
2. Enters render loop: `renderPrep()` → `render()` → `renderPost()` → `renderUI()` → `renderDone()`
3. `commandsInit()` registers ~50 CSV-like commands (e.g. `uniform,name,val`, `reload`, `define,...`)
4. Commands arrive via stdin (console), OSC, or file watcher (hot-reload)
5. Uniform system auto-detects built-in uniforms from shader source and feeds them each frame

### Key Globals (in `main.cpp`)

| Variable | Purpose |
|----------|---------|
| `sandbox` | The single `GlslViewer` instance (manages shaders, renders, uniforms) |
| `files` | `WatchFileList` — all loaded assets with paths and timestamps |
| `commands` | `CommandList` — all registered console/OSC commands |
| `textureCounter` | Sequential counter for auto-named textures (`u_tex0`, `u_tex1`…) |
| `bKeepRunnig` | Atomic bool — render loop runs while true |

### Naming Conventions

- **Member variables**: `m_` prefix (`m_frag_source`, `m_sceneRender`)
- **Booleans**: `b` prefix in globals (`bKeepRunnig`, `bScreensaverMode` — note: typo is intentional, don't "fix")
- **Functions**: `camelCase` for methods, `snake_case` for free functions
- **Types**: PascalCase (`GlslViewer`, `UniformData`, `WatchFile`)
- **Uniform naming**: `u_` prefix convention
- **Constants**: `UPPER_SNAKE_CASE` (via `#define`)
- **Headers**: `#pragma once` (not include guards)

### Render Pipeline Order

```
renderPrep()   — update uniforms, clear buffers
render()       — canvas shader → buffers → double-buffers → pyramids → floods → scene → post-processing → plot
renderPost()   — screenshot/recording
renderUI()     — crosshair, help overlay, debug overlays
renderDone()   — swap buffers, frame counter
```

### Gotchas

- **`bKeepRunnig`** is a global `std::atomic<bool>` — intentional misspelling, do not correct
- The project uses **C++14**, not C++17/20
- **WASM builds** require `$EMSDK` environment variable set to emscripten SDK path
- **DEBUG** define is always set in CMakeLists.txt — enables the `TRACK_BEGIN`/`TRACK_END` macros
- Commands use **CSV-like** format on stdin/OSC (e.g. `uniform,myVar,0.5`)
- The `vera` submodule is **forked** — it's maintained by the same author, not the upstream
- `sceneRender` holds PBR material state — adding new material properties requires updating the shader generation in `sceneRender.cpp`

---

## glslViewerGUI (Python/PyQt6) — Desktop GUI

### Run

```bash
cd glslViewerGUI && python main.py
```

Requires: `PyQt6` pip package. Assumes `glslViewer/build/glslViewer` binary exists.

### Architecture

```
main.py                  — Entry point: QApplication → MainWindow
main_window.py           — QMainWindow: File menu (Open/Reload/Exit), View menu (toggles),
                            central info label, dock widgets
render_bridge.py         — QObject: manages glslViewer QProcess, file watcher, stdin command
                            writer, stdout/stderr reader. Signals: stdout_received,
                            process_started, process_stopped
uniform_panel.py         — QDockWidget: auto-generates spinboxes/sliders from shader uniforms
shader_parser.py         — Regex GLSL parser: extracts uniform declarations, strips comments,
                            builds CSV command strings
console_panel.py         — QDockWidget: read-only monospace QTextEdit with "Clear" button
glslViewer_config.py     — Path constants (binary, shader, build dir)
default_shader.frag      — Default fragment shader (rainbow animation)
```

### Communication

- GUI launches `glslViewer --noncurses --fullFps [shader]` as a **QProcess**
- Commands sent to **stdin** as CSV: `uniform,name,val\n` or `reload,path\n` or `reload\n`
- `QFileSystemWatcher` triggers hot reload on shader file changes
- Uniforms are parsed from GLSL source (regex), then mapped to Qt widgets

### Gotchas

- `sys.path.insert(0, ...)` in `main.py` adds the **build** directory for PyGlslViewer — but the GUI actually uses the binary via QProcess, not pybind11
- `config.py` path `GLSLVIEWER_SRC` points to `../glslViewer` relative to the GUI dir
- Shader parser has a **built-in uniform filter** (`BUILTIN_UNIFORMS`) — these are skipped from the UI
- The `@uniform` annotation regex (`USER_ATTR_PATTERN`) is defined but **not wired** anywhere — range hints from annotations are not applied

---

## Blender Integration (Python scripts)

Location: `glslViewer/scripts/`

```
gv_render_engine.py   — Blender RenderEngine (bl_idname: "GLSLVIEWER_ENGINE")
gv_lib.py             — PyGlslViewer binding helpers
gv_operators.py       — Blender operators (reload, open in editor, etc.)
gv_preferences.py     — Blender addon preferences
gv_properties.py      — Blender property group definitions
gv_render_ui.py       — Blender UI panels
gv_translate.py       — Blender → glslViewer coordinate/light/camera translation
```

Uses the **pybind11** module (`PyGlslViewer`), not the standalone binary. Provides both viewport preview (`GVRenderEngine.view_update`/`view_draw`) and final render (`GVRenderEngine.render`).

---

## General Notes

- No test framework detected (no test files found)
- No linter/formatter config detected
- CI uses Travis (`.travis.yml`) — Linux only, Clang compiler
- The `docs/` folder contains a WASM demo site (JS/HTML/CSS)
- Supported geometry formats: PLY, OBJ, STL, GLB/GLTF, SPLAT
- Supported texture formats: PNG, JPG, TGA, PSD, GIF, BMP, HDR, MP4, MOV, MKV, RTSP
