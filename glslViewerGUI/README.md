# GlslViewerGUI — Shader Mission Control

A PyQt6 desktop GUI that wraps [glslViewer](https://github.com/patriciogonzalezvivo/glslViewer), providing a live shader editor, uniform controls, camera manipulation, recording tools, and preset management.

![Screenshot](../Working.png)

## Requirements

- Python 3.10+
- PyQt6 (`pip install PyQt6`)
- glslViewer binary built at `../glslViewer/build/glslViewer`

## Quick Start

```bash
cd glslViewerGUI
python3 main.py
```

## Installation

```bash
make install        # installs to ~/.local/bin and ~/.local/share/applications
make uninstall      # removes installed files
```

## Features

- **Live GLSL Editor** — syntax highlighting, error line highlighting, auto-reload on save
- **Uniform Panel** — auto-detects shader uniforms (float, int, bool, vec2/3/4, mat2/3/4), save/load presets
- **Camera Panel** — distance, FOV, projection, position, look-at, nudge controls
- **Recording Panel** — screenshots, PNG sequences, MP4/GIF video recording (via glslViewer's ffmpeg integration)
- **Preset Manager** — save and restore complete sessions (shader + uniforms + camera)
- **Theming** — Dark, Light, and System themes with persistent preference
- **Error Recovery** — auto-restarts crashed renderer with fallback to default shader

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open fragment shader |
| Ctrl+S | Save current shader |
| F5 | Reload shader |
| Ctrl+Q | Quit |

## File Layout

```
glslViewerGUI/
  main.py              — Entry point
  main_window.py       — QMainWindow, docks, menus
  render_bridge.py     — QProcess wrapper around glslViewer binary
  shader_editor.py     — GLSL editor with syntax highlighting
  uniform_panel.py     — Auto-generated uniform widgets
  camera_panel.py      — Camera controls
  recording_panel.py   — Screenshot / sequence / video UI
  preset_manager.py    — Session preset browser and storage
  console_panel.py     — Stdout/stderr log
  error_parser.py      — Driver-agnostic shader compile error parser
  shader_parser.py     — GLSL uniform extraction
  themes.py            — Dark / Light / System theme engine
  default_shader.frag  — Default startup shader
  requirements.txt     — Python dependencies
  glslviewer-gui       — Shell launcher
  glslviewer-gui.desktop — Linux desktop entry
```
