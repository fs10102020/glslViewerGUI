# AGENTS.md

Two projects share this repo. `glslViewer/` is the C++ OpenGL renderer; `glslViewerGUI/` is the Python/PySide6 desktop wrapper. Most third-party code lives under `glslViewer/deps/`; avoid editing vendored deps unless the task explicitly targets them.

## Commands
- Build renderer: `make -C glslViewer`
- Build renderer without X11: `make -C glslViewer nox11`
- Build WASM renderer: `make -C glslViewer wasm` (`$EMSDK` required)
- If CMake cache is stale: `rm -rf glslViewer/build && mkdir glslViewer/build && cd glslViewer/build && cmake .. && make -j$(nproc)`
- Install GUI deps: `cd glslViewerGUI && uv pip install -r requirements.txt`
- Run GUI: `cd glslViewerGUI && uv run python main.py`
- GUI smoke test: `cd glslViewerGUI && QT_QPA_PLATFORM=offscreen uv run python smoke_test.py`
- Focused GUI import check: `cd glslViewerGUI && uv run python -c "import main_window, render_bridge, shader_editor, uniform_panel, camera_panel, console_panel, recording_panel, preset_manager, themes; print('imports ok')"`

## PySide6 GUI Rules
- Never add PyQt, PyQt imports, PyQt signals, or PyQt/PySide compatibility fallbacks. Licensing is the reason; use `PySide6.*` and `Signal` only.
- `requirements.txt` must stay `PySide6>=6.4.0`.
- Panels are `QWidget` subclasses. `main_window.py` owns `QDockWidget` wrappers and embeds panels in central editor tabs, right control tabs, and bottom docks.
- Qt `triggered`/`toggled` signals pass a `checked` bool; capture loop variables with `lambda checked=False, _cmd=cmd: ...`.
- Use `QFileDialog.Option.DontUseNativeDialog` for consistent dialogs.
- Default theme is `dark`; `themes.py` applies QPalette + QSS.
- There is no linter/test framework config. Use the smoke test and import check above.

## GUI Wiring
- Runtime process lives in `render_bridge.py`; binary path is `glslViewer/build/glslViewer` via `glslViewerGUI/glslViewer_config.py`.
- `main_window.py` starts the renderer on construction; `smoke_test.py` monkeypatches `RenderBridge.start` to avoid launching the binary.
- `RenderSessionConfig.build_args()` is the source for startup flags (`--noncurses`, `--fullFps`, `-I`, `-D`, window options, queued assets).
- `ShaderProgramSpec` represents frag/vert/model state and sibling discovery; `RenderBridge.program` and the editor corner label depend on it.
- Presets live in `~/.config/glslviewer-gui/presets`.

## glslViewer Command Pitfalls
- GUI renderer stdin must include `--noncurses`; ncurses steals stdout.
- C++ command dispatch in `glslViewer/src/main.cpp::commandsRun()` uses prefix matching with `vera::beginsWith`. Examples: `buffers,list` hits `buffer`, `textures,list` hits `textures`, `materials` hits `material`.
- If no command resolves, C++ falls through to `sandbox.uniforms.parseLine(_cmd)`. Uniform stdin syntax is `myVar,0.5` or `myVec,0.1,0.2,0.3`; do not send `uniform,myVar,0.5`.
- `commands.build_uniform(name, value)` is the correct GUI builder. `shader_parser.build_uniform_command()` still emits the wrong `uniform,` prefix and must not be used for renderer stdin.
- CSV commands have no quoting/escaping. Paths, names, or values containing commas break parsing; `commands.py` validates common cases.
- Some commands mutate state but return `false`, so they also fall through to uniform parsing: `fullFps,on|off`, `vsync,on|off`, `cursor,on|off`, `track,*`, plain `camera`, `max_mem_in_queue`.

## Renderer Gotchas
- Keep the C++ typo `bKeepRunnig`; it is intentional existing code.
- The environment command uses internal spelling `enviroment` in C++ comments/keys; do not “fix” it casually.
- `stream_texture` accepts fourth arg `webcam` or `flip`, not both.
- CLI `--vFlip` sets `vFlip = false`; the name is misleading.
- Noncurses stdout prompts include `// > ` around output lines.
- Reload only works for files already in glslViewer's watched file list; the watcher polls about every 500ms.
- Sequence/record commands block the command thread; stdin commands are not processed while recording.
- Per-buffer enable has an upstream indexing bug: `uniforms.buffers[i]->enabled = (values[1] == "on")` uses the command index, not a separate buffer parameter.

## Shader/Asset Notes
- Shadertoy uniforms `iTime`, `iResolution`, `iMouse`, `iFrame` are not glslViewer's generated names; GUI warns because glslViewer uses `u_time`, `u_resolution`, `u_mouse`, `u_frame`.
- Include paths can be added at runtime with `include_path`; there is no remove command, so removals require restart/session changes.
- Live asset commands used by the GUI include `texture`, `stream_texture`, `audio_texture`, `cubemap_load`, `skybox`, `environment`, `sequence_uniform`, `camera_sequence`, and `load_model`.
- Supported geometry extensions in GUI session config: `.ply`, `.obj`, `.stl`, `.glb`, `.gltf`, `.splat`.
