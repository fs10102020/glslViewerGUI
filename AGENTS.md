# AGENTS.md

Compact guide for OpenCode sessions working in this repo.

## Layout

- `glslViewer/` — C++ OpenGL renderer (vendored locally; not built by default).
- `glslViewerGUI/` — Python/PySide6 desktop wrapper (the project you usually edit).
- `exampleshaders/` — sample `.frag`/`.vert` files for testing the GUI (at the repo root, **not** under `glslViewerGUI/`).
- `/glslViewer/` is `.gitignore`d — users check it out and build it themselves.

## Commands

Run from repo root unless noted.

- Build C++ renderer: `make -C glslViewer` (add `nox11` for headless, `wasm` with `$EMSDK`).
- Stale CMake cache: `rm -rf glslViewer/build && mkdir glslViewer/build && cd glslViewer/build && cmake .. && make -j$(nproc)`.
- Install GUI deps: `cd glslViewerGUI && uv pip install -r requirements.txt` (only `PySide6>=6.4.0`).
- Run GUI: `cd glslViewerGUI && uv run python main.py` (or `python3 main.py`).
- GUI smoke test: `cd glslViewerGUI && QT_QPA_PLATFORM=offscreen uv run python smoke_test.py` (monkey-patches `RenderBridge.start` so no binary is launched).
- Targeted import check: `cd glslViewerGUI && uv run python -c "import main_window, render_bridge, file_classifier, sdf_project, sdf_panel"`.
- Install/uninstall to `~/.local`: `cd glslViewerGUI && make install` / `make uninstall`.

There is no linter, type checker, or test framework configured. The smoke test plus the classifier unit tests inside it are the only automated checks.

## GUI architecture (`glslViewerGUI/`)

- Entry point: `main.py` → `MainWindow` → starts `RenderBridge` (a `QProcess` wrapping `glslViewer/build/glslViewer`).
- Binary path resolution: `glslViewer_config.GLSLVIEWER_BIN`.
- **File loading is centralized** in `file_classifier.classify_paths()` returning a `LoadPlan`. All menu actions (Open Shader, Open Vertex, Open Geometry, drag/drop) route through `MainWindow._open_paths()`. **Add new load behaviors here**, not in dedicated `_open_*` methods.
- Asset-only or model-only opens keep the current fragment shader and apply the assets at runtime; `MainWindow._apply_runtime_assets()` dispatches non-CLI asset kinds (`stream_texture`, `model`, `sequence_uniform`, `camera_sequence`).
- Layout: `QMainWindow` with a `QTabWidget` central editor (Fragment/Vertex + a third Scene tab in SDF mode), a 6-tab right dock, and a bottom dock split into Console + Recording + Presets.
- Panels are `QWidget` subclasses; `main_window.py` wraps them in `QScrollArea` to prevent width pressure.
- Theme via `themes.apply_theme()`; default `"dark"`, forces Fusion style for `dark`/`light`.
- Generated SDF shaders are cached at `~/.config/glslviewer-gui/generated/<name>_<sha1>_generated.frag` (path includes hash to avoid collisions across projects with the same name).

## PySide6 rules

- Never import PyQt or `PyQt6`; use `PySide6.*` and `Signal` only. The `smoke_test.py` startup hook fails the run if any `PyQt*` module is loaded.
- `requirements.txt` must stay `PySide6>=6.4.0`.
- `triggered`/`toggled` signals pass a `checked` bool — always capture loop variables: `lambda checked=False, _cmd=cmd: self._safe_send(_cmd)`.
- Use `QFileDialog.Option.DontUseNativeDialog` for every dialog.
- Capture loop variables in `lambda`s for signals.

## SDF renderer

- Projects live in a directory with `project.json` (`{"type": "sdf_project", "config": {...}}`) and a `scene.glsl` that defines `float DE(vec3 p)`. Optional hooks: `baseColor()`, `emissionAt()`, `initScene()`.
- `is_sdf_project()` strictly validates `type` and that the referenced scene file exists — false positives are a real risk if you relax this.
- Templates are under `glslViewerGUI/sdf_templates/`. The composer (`sdf_project.SdfShaderComposer`) inlines them and prepends `#version 330 core` plus forward declarations of the scene hooks. The composer's scene hook detection (`_detect_scene_hooks`) uses regex to skip emitting `scene_defaults.glsl` bodies that the scene already defines.
- Integrators: `preview` (one-bounce raymarch) and `pathtrace` (progressive accumulation). Pathtrace uses **two** double-buffer passes: `DOUBLE_BUFFER_0` for accumulated radiance and `DOUBLE_BUFFER_1` for `(sample_count, 0, 0, revision_token)`. The GUI only defines `SDF_INTEGRATOR_PATHTRACE`; glslViewer creates the passes and injects `DOUBLE_BUFFER_0` / `DOUBLE_BUFFER_1` itself. Do not pass them as global `-D` defines.
- Reset conditions (all bump `u_sceneRevision`): scene source saved, uniform changed, integrator switched, debug view changed, SDF panel param changed, camera command, manual reset button.
- Uniform metadata comments: `// @ui slider min=0.1 max=4.0 default=1.4 group="Fractal"`. Both preceding and trailing comments on the uniform line are accepted. Widget aliases (`shader_parser.WIDGET_ALIASES`): `slider|float|number|range → float`, `integer|int → int`, `color|colour → color`. **Do not** store `slider`/`integer` as the widget id — the panel's `_build_widget()` only knows the canonical names.
- `commands.build_uniform(name, value)` produces correct `name,value` syntax for `glslViewer`'s uniform fallthrough (`commands.py`). Do not use `shader_parser.build_uniform_command()` — it emits the legacy `uniform,` prefix and breaks the fallthrough.

## glslViewer backend pitfalls (verified against `glslViewer/src/main.cpp` and `core/uniforms.cpp`)

- Renderer stdin **must** include `--noncurses`; ncurses steals stdout and the GUI's response parsing silently breaks.
- Command dispatch in `commandsRun()` uses prefix matching (`vera::beginsWith`), not exact match. `buffers,list` resolves to `buffer`; `textures,list` to `textures`. Some state-mutating commands return `false` and **fall through to uniform parsing**: `fullFps,on|off`, `vsync,on|off`, `cursor,on|off`, `track,*`, plain `camera`, `max_mem_in_queue`. Beware the silent fallthrough.
- File-type classification in `core/tools/files.h`: `FRAG_SHADER`, `VERT_SHADER`, `IMAGE`, `GEOMETRY`, `CUBEMAP`, `GLSL_DEPENDENCY`, `IMAGE_BUMPMAP`. The `dependency` and `bumpmap` types are not handled in `onFileChange()` reloads.
- Sequence/record commands (`sequence`, `record`, `secs`, `frames`) block the command thread — stdin is not processed while they run.
- CLI `--vFlip` actually sets `vFlip = false` (the name is misleading — keep it that way to match glslViewer's expectation).
- `stream_texture`'s fourth arg is either `webcam` or `flip`, never both.
- Noncurses stdout lines are wrapped in `// > ` markers; the `ConsolePanel` strips them.
- Reload only works for files already in glslViewer's watched list; the watcher polls every ~500ms.
- **Keep the C++ typo** `bKeepRunnig` (main.cpp:58) and the internal spelling `enviroment` in C++ comments/keys — both are intentional upstream quirks.

## File classifier (`file_classifier.py`)

- Extension-first fast path. For `.glsl` only, content-sniffs for:
  - `#pragma stage fragment` → fragment shader
  - `float DE(vec3 p)` + no `void main()` → `sdf_scene` candidate
  - `gl_Position` or `#pragma stage vertex` → vertex shader
  - `gl_FragColor` / `fragColor` → fragment shader
  - `void mainImage(...)` or Shadertoy uniforms (`iTime`/`iResolution`/...) → `shadertoy_like`
  - `void main()` alone → `generic_glsl` (used as fragment shader with a warning)
- Directories and individual `project.json` files are validated with `is_sdf_project()`; SDF scene promotion only happens when the parent directory is a valid SDF project.
- `classify_paths()` also auto-pairs a `.frag` with a `.vert` sibling and vice versa.
- `build_session_from_plan(plan, base_session)` turns a `LoadPlan` into `RenderSessionConfig` updates using canonical asset kinds (`named_texture`, `stream_texture`, `cubemap_env`, `model`, `sequence_uniform`, `camera_sequence`, etc.).
- Standalone `.glsl` files that only define `DE()` are wrapped with a stub `main()` and loaded as fragment shaders (see `MainWindow._open_paths`).

## Common gotchas

- `render_bridge.py` requires `import time` — it uses `time.time()` in `_on_finished()` and the debounced reload timer.
- `RenderBridge` watches a default set (current fragment/vertex/geom paths) plus an extra/custom set set via `set_watch_files()`. In SDF mode the extra set contains `scene.glsl` and the template files; `MainWindow._on_bridge_file_changed()` decides whether to reload or regenerate.
- `CONFIG_DIR` in `glslViewer_config.py` is a `str`; use `Path(CONFIG_DIR)` before joining with paths.
- `SdfProjectConfig` is a dataclass with a few `list[float]` fields (`sky_color`, `horizon_color`, `ground_color`, `sun_dir`). `from_dict()` filters unknown keys so old projects stay forward-compatible.
- The fragment editor's "Generated" tab in SDF mode shows the transient generated shader; user edits there are temporary — scene edits come from the Scene tab and drive regeneration.
- The smoke test patches `RenderBridge.start` before `MainWindow()` is constructed. Do not move the patch below the window construction or it will spawn the binary in CI.
- `RENDER_FPS` in `glslViewer_config.py` is unused (the session dialog manages FPS) but is kept as the documented default.
