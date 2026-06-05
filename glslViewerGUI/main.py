import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glslViewer", "build"))

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from themes import apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GlslViewerGUI")
    app.setOrganizationName("glslViewer")

    settings = QSettings("glslViewer", "GlslViewerGUI")
    saved_theme = settings.value("theme", "dark")
    if isinstance(saved_theme, str):
        apply_theme(app, saved_theme)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
