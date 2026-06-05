from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QTextCursor, QTextBlockFormat, QKeyEvent,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel

from error_parser import parse_errors


GLSL_KEYWORDS = [
    "attribute", "const", "uniform", "varying", "break", "continue",
    "do", "for", "while", "if", "else", "in", "out", "inout", "float",
    "int", "void", "bool", "true", "false", "lowp", "mediump", "highp",
    "precision", "invariant", "discard", "return", "struct", "sampler2D",
    "samplerCube", "sampler3D", "sampler2DArray", "sampler2DShadow",
    "samplerCubeShadow", "isampler2D", "usampler2D", "layout", "flat",
]

GLSL_TYPES = [
    "vec2", "vec3", "vec4", "ivec2", "ivec3", "ivec4", "bvec2", "bvec3",
    "bvec4", "mat2", "mat3", "mat4", "mat2x2", "mat2x3", "mat2x4",
    "mat3x2", "mat3x3", "mat3x4", "mat4x2", "mat4x3", "mat4x4",
    "uint", "uvec2", "uvec3", "uvec4", "double", "dvec2", "dvec3",
    "dvec4", "dmatrix2x2", "dmatrix2x3", "dmatrix2x4", "dmatrix3x2",
    "dmatrix3x3", "dmatrix3x4", "dmatrix4x2", "dmatrix4x3", "dmatrix4x4",
]

GLSL_BUILTINS = [
    "radians", "degrees", "sin", "cos", "tan", "asin", "acos", "atan",
    "pow", "exp", "log", "exp2", "log2", "sqrt", "inversesqrt", "abs",
    "sign", "floor", "ceil", "fract", "mod", "min", "max", "clamp",
    "mix", "step", "smoothstep", "length", "distance", "dot", "cross",
    "normalize", "faceforward", "reflect", "refract", "matrixCompMult",
    "lessThan", "lessThanEqual", "greaterThan", "greaterThanEqual",
    "equal", "notEqual", "any", "all", "not", "texture2D", "textureCube",
    "texture", "textureLod", "textureProj", "texelFetch", "dFdx", "dFdy",
    "fwidth", "gl_Position", "gl_FragColor", "gl_FragCoord", "gl_FragDepth",
    "gl_PointCoord", "gl_VertexID", "gl_InstanceID", "gl_FrontFacing",
]


class GLSLHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._rules = []
        self._comment_fmt = QTextCharFormat()
        self._string_fmt = QTextCharFormat()
        self.set_theme({
            "keyword": "#cc7a00",
            "type": "#267cb5",
            "builtin": "#795da3",
            "comment": "#6a737d",
            "preprocessor": "#6a737d",
            "string": "#032f62",
        })

    def set_theme(self, colors: dict) -> None:
        self._rules = []

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor(colors.get("keyword", "#cc7a00")))
        keyword_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in GLSL_KEYWORDS:
            self._rules.append((rf"\b{kw}\b", keyword_fmt))

        type_fmt = QTextCharFormat()
        type_fmt.setForeground(QColor(colors.get("type", "#267cb5")))
        type_fmt.setFontWeight(QFont.Weight.Bold)
        for ty in GLSL_TYPES:
            self._rules.append((rf"\b{ty}\b", type_fmt))

        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor(colors.get("builtin", "#795da3")))
        for fn in GLSL_BUILTINS:
            self._rules.append((rf"\b{fn}\b", builtin_fmt))

        preproc_fmt = QTextCharFormat()
        preproc_fmt.setForeground(QColor(colors.get("preprocessor", "#6a737d")))
        self._rules.append((r"#\s*\w+", preproc_fmt))

        self._comment_fmt.setForeground(QColor(colors.get("comment", "#6a737d")))
        self._comment_fmt.setFontItalic(True)

        self._string_fmt.setForeground(QColor(colors.get("string", "#032f62")))
        self.rehighlight()

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            import re
            for m in re.finditer(pattern, text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

        # Single-line comments
        import re
        for m in re.finditer(r"//.*", text):
            self.setFormat(m.start(), m.end() - m.start(), self._comment_fmt)

        # Multi-line comments
        start = self.previousBlockState()
        if start < 0:
            start = 0

        i = 0
        in_comment = start == 1
        while True:
            if not in_comment:
                idx = text.find("/*", i)
                if idx == -1:
                    break
                end_idx = text.find("*/", idx + 2)
                if end_idx == -1:
                    self.setFormat(idx, len(text) - idx, self._comment_fmt)
                    self.setCurrentBlockState(1)
                    return
                else:
                    self.setFormat(idx, end_idx - idx + 2, self._comment_fmt)
                    i = end_idx + 2
            else:
                end_idx = text.find("*/", i)
                if end_idx == -1:
                    self.setFormat(0, len(text), self._comment_fmt)
                    self.setCurrentBlockState(1)
                    return
                else:
                    self.setFormat(0, end_idx + 2, self._comment_fmt)
                    i = end_idx + 2
                    in_comment = False
        self.setCurrentBlockState(0)


class GLSLEditor(QWidget):
    text_saved = Signal(str)
    errors_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._editor = QPlainTextEdit()
        self._editor.setFont(QFont("monospace", 10))
        self._highlighter = GLSLHighlighter(self._editor.document())

        self._live_checkbox = QCheckBox("Live reload")
        self._live_checkbox.setChecked(True)
        self._status = QLabel("Ready")

        top = QHBoxLayout()
        top.addWidget(self._live_checkbox)
        top.addStretch()
        top.addWidget(self._status)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._editor)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._on_debounce)
        self._editor.textChanged.connect(self._on_text_changed)

        self._file_path: str | None = None
        self._error_lines: set[int] = set()

    def set_file_path(self, path: str | None) -> None:
        self._file_path = path

    def set_source(self, source: str) -> None:
        self._editor.blockSignals(True)
        self._editor.setPlainText(source)
        self._editor.blockSignals(False)
        self._clear_error_highlight()

    def source(self) -> str:
        return self._editor.toPlainText()

    def save(self) -> None:
        if not self._file_path:
            return
        with open(self._file_path, "w") as f:
            f.write(self.source())
        self.text_saved.emit(self._file_path)
        self._status.setText("Saved")

    def apply_errors(self, error_text: str) -> None:
        errors = parse_errors(error_text)
        self._clear_error_highlight()
        self._error_lines = {e["line"] for e in errors}
        for line_num in self._error_lines:
            self._highlight_line(line_num, QColor("#ffcccc"))
        self.errors_changed.emit(errors)
        if errors:
            self._status.setText(f"{len(errors)} error(s)")
        else:
            self._status.setText("Ready")

    def clear_errors(self) -> None:
        self._clear_error_highlight()
        self._error_lines.clear()
        self.errors_changed.emit([])
        self._status.setText("Ready")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.save()
            return
        super().keyPressEvent(event)

    def _on_text_changed(self) -> None:
        if self._live_checkbox.isChecked():
            self._debounce.stop()
            self._debounce.start(600)

    def _on_debounce(self) -> None:
        self.save()

    def _highlight_line(self, line_number: int, color: QColor) -> None:
        block = self._editor.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        fmt = QTextCharFormat()
        fmt.setBackground(color)
        cursor.mergeCharFormat(fmt)

    def set_theme(self, theme) -> None:
        self._highlighter.set_theme({
            "keyword": theme.keyword,
            "type": theme.type_color,
            "builtin": theme.builtin,
            "comment": theme.comment,
            "preprocessor": theme.preprocessor,
            "string": theme.string,
        })
        if theme.editor_bg:
            self._editor.setStyleSheet(f"QPlainTextEdit {{ background-color: {theme.editor_bg}; color: {theme.editor_fg}; }}")
        else:
            self._editor.setStyleSheet("")

    def _clear_error_highlight(self) -> None:
        cursor = QTextCursor(self._editor.document())
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("transparent"))
        cursor.mergeCharFormat(fmt)
