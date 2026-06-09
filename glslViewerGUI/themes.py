from dataclasses import dataclass

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QStyleFactory


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
QWidget {
    background-color: #1f2124;
    color: #d7d7d7;
    selection-background-color: #0f6f83;
    selection-color: #ffffff;
}
QMainWindow, QDialog {
    background-color: #181a1d;
}
QMenuBar, QToolBar {
    background-color: #23262a;
    border-bottom: 1px solid #3b3f45;
    spacing: 4px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 9px;
}
QMenuBar::item:selected, QMenu::item:selected {
    background-color: #3a2f1d;
    color: #ffb84d;
}
QMenu {
    background-color: #25282d;
    border: 1px solid #4a4f56;
}
QMenu::item {
    padding: 5px 24px 5px 18px;
}
QToolBar::separator {
    background: #3b3f45;
    width: 1px;
    margin: 4px;
}
QDockWidget::title {
    background-color: #25282d;
    border: 1px solid #3b3f45;
    padding: 4px 6px;
    color: #d7d7d7;
}
QMainWindow::separator {
    background: #4b5058;
    width: 5px;
    height: 5px;
}
QMainWindow::separator:hover {
    background: #ffb84d;
}
QTabWidget::pane {
    border: 1px solid #3b3f45;
    background-color: #202327;
}
QTabBar::tab {
    background-color: #2a2d32;
    color: #c8c8c8;
    border: 1px solid #3b3f45;
    border-bottom-color: #2a2d32;
    padding: 5px 10px;
}
QTabBar::tab:selected {
    background-color: #332819;
    color: #ffb84d;
    border-top: 2px solid #ffb84d;
}
QTabBar::tab:hover:!selected {
    background-color: #303844;
    color: #76d7e8;
}
QPushButton {
    background-color: #31353b;
    border: 1px solid #525862;
    border-radius: 3px;
    padding: 4px 8px;
}
QPushButton:hover {
    border-color: #76d7e8;
    color: #76d7e8;
}
QPushButton:pressed {
    background-color: #3a2f1d;
    border-color: #ffb84d;
    color: #ffb84d;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {
    background-color: #17191c;
    color: #d7d7d7;
    border: 1px solid #3f454d;
    border-radius: 3px;
    padding: 3px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QListWidget:focus {
    border-color: #76d7e8;
}
QGroupBox {
    border: 1px solid #3b3f45;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #ffb84d;
}
QHeaderView::section {
    background-color: #2a2d32;
    border: 1px solid #3b3f45;
    padding: 4px;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #202327;
    border: 1px solid #30343a;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #4b5058;
    border-radius: 3px;
}
QScrollBar::handle:hover {
    background: #76d7e8;
}
QProgressBar {
    background-color: #17191c;
    border: 1px solid #3f454d;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #0f6f83;
}
QCheckBox::indicator:checked {
    background-color: #ffb84d;
    border: 1px solid #ffcf7a;
}
QPlainTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}
"""

_QSS_LIGHT = """
QWidget {
    background-color: #f4f4f4;
    color: #1f2328;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}
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


_ORIGINAL_STYLE_NAME: str | None = None
_ORIGINAL_PALETTE: QPalette | None = None


def apply_theme(widget, theme_name: str) -> None:
    theme = get_theme(theme_name)
    app = QApplication.instance()
    if app is not None:
        global _ORIGINAL_STYLE_NAME, _ORIGINAL_PALETTE
        if _ORIGINAL_STYLE_NAME is None:
            _ORIGINAL_STYLE_NAME = app.style().objectName()
            _ORIGINAL_PALETTE = app.palette()
        if theme.name == "system":
            style = QStyleFactory.create(_ORIGINAL_STYLE_NAME)
            if style is not None:
                app.setStyle(style)
            if _ORIGINAL_PALETTE is not None:
                app.setPalette(_ORIGINAL_PALETTE)
        else:
            style = QStyleFactory.create("Fusion")
            if style is not None:
                app.setStyle(style)
            app.setPalette(theme.palette)
        app.setStyleSheet(theme.qss)
    else:
        widget.setStyleSheet(theme.qss)
    _notify_editor(widget, theme)


def _notify_editor(widget, theme: Theme) -> None:
    from shader_editor import GLSLEditor
    for editor in widget.findChildren(GLSLEditor):
        editor.set_theme(theme)
