# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
GLSLVIEWER_SRC = os.path.abspath(os.path.join(PROJECT_DIR, "..", "glslViewer"))
GLSLVIEWER_BIN = os.path.join(GLSLVIEWER_SRC, "build", "glslViewer")
DEFAULT_SHADER = os.path.join(PROJECT_DIR, "default_shader.frag")
PYGLSLVIEWER_SO = os.path.join(GLSLVIEWER_SRC, "build")
WINDOW_TITLE = "GlslViewerGUI — Shader Mission Control"
RENDER_FPS = 60

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "glslviewer-gui")
PRESETS_DIR = os.path.join(CONFIG_DIR, "presets")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(PRESETS_DIR, exist_ok=True)
