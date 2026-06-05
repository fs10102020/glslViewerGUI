from dataclasses import dataclass

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


@dataclass
class Theme:
    name: str
    editor_bg: str
    editor_fg: str
    keyword: str
    type_color: str
    builtin: str
    comment: str
    preprocessor: str
    string: str
    error_bg: str
    palette: QPalette
    qss: str


_QSS_DARK = """
QDockWidget::title {
    background-color: #2d2d2d;
    padding: 4px;
}
QMainWindow::separator {
    background: #3c3c3c;
    width: 2px;
    height: 2px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #2d2d2d;
}
QPlainTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}
"""

_QSS_LIGHT = """
QDockWidget::title {
    background-color: #e0e0e0;
    padding: 4px;
}
QMainWindow::separator {
    background: #c0c0c0;
    width: 2px;
    height: 2px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #f0f0f0;
}
QPlainTextEdit {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c0c0c0;
}
"""

_QSS_SYSTEM = """
QDockWidget::title {
    padding: 4px;
}
QMainWindow::separator {
    width: 2px;
    height: 2px;
}
"""


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#2d2d2d"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
    p.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#252526"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2d2d2d"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#d4d4d4"))
    p.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
    p.setColor(QPalette.ColorRole.Button, QColor("#3c3c3c"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#d4d4d4"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#264f78"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.Light, QColor("#3c3c3c"))
    p.setColor(QPalette.ColorRole.Midlight, QColor("#3c3c3c"))
    p.setColor(QPalette.ColorRole.Dark, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.Mid, QColor("#2d2d2d"))
    p.setColor(QPalette.ColorRole.Shadow, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Link, QColor("#3794ff"))
    p.setColor(QPalette.ColorRole.LinkVisited, QColor("#3794ff"))
    return p


def _light_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#f5f5f5"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#f5f5f5"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.Text, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.Button, QColor("#e0e0e0"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#0078d4"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.Light, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.Midlight, QColor("#e0e0e0"))
    p.setColor(QPalette.ColorRole.Dark, QColor("#c0c0c0"))
    p.setColor(QPalette.ColorRole.Mid, QColor("#e0e0e0"))
    p.setColor(QPalette.ColorRole.Shadow, QColor("#a0a0a0"))
    p.setColor(QPalette.ColorRole.Link, QColor("#0066cc"))
    p.setColor(QPalette.ColorRole.LinkVisited, QColor("#0066cc"))
    return p


_THEMES: dict[str, Theme] = {
    "dark": Theme(
        name="dark",
        editor_bg="#1e1e1e",
        editor_fg="#d4d4d4",
        keyword="#cc7a00",
        type_color="#267cb5",
        builtin="#795da3",
        comment="#6a737d",
        preprocessor="#6a737d",
        string="#032f62",
        error_bg="#ffcccc",
        palette=_dark_palette(),
        qss=_QSS_DARK,
    ),
    "light": Theme(
        name="light",
        editor_bg="#ffffff",
        editor_fg="#1e1e1e",
        keyword="#af00db",
        type_color="#267cb5",
        builtin="#795da3",
        comment="#008000",
        preprocessor="#808080",
        string="#a31515",
        error_bg="#ffcccc",
        palette=_light_palette(),
        qss=_QSS_LIGHT,
    ),
    "system": Theme(
        name="system",
        editor_bg="",
        editor_fg="",
        keyword="#cc7a00",
        type_color="#267cb5",
        builtin="#795da3",
        comment="#6a737d",
        preprocessor="#6a737d",
        string="#032f62",
        error_bg="#ffcccc",
        palette=QApplication.palette(),
        qss=_QSS_SYSTEM,
    ),
}


def get_theme(name: str) -> Theme:
    return _THEMES.get(name, _THEMES["dark"])


def apply_theme(widget, theme_name: str) -> None:
    theme = get_theme(theme_name)
    app = QApplication.instance()
    if app is not None:
        app.setPalette(theme.palette)
    widget.setStyleSheet(theme.qss)
    _notify_editor(widget, theme)


def _notify_editor(widget, theme: Theme) -> None:
    from shader_editor import GLSLEditor
    editor = widget.findChild(GLSLEditor)
    if editor is not None:
        editor.set_theme(theme)
