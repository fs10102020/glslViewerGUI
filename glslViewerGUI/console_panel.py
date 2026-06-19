# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QCheckBox,
)


_PROMPT_RE = re.compile(r"^// >\s*", re.MULTILINE)


class ConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConsolePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setFont(QFont("monospace", 9))
        self._output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._output)

        input_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type command or query...")
        self._input.returnPressed.connect(self._on_submit)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, 1)

        self._query_mode = QCheckBox("Query")
        input_layout.addWidget(self._query_mode)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._output.clear)
        input_layout.addWidget(self._clear_btn)

        layout.addLayout(input_layout)

        self._history: list[str] = []
        self._history_idx = -1
        self._draft: str = ""

        self._command_requested = None
        self._query_requested = None

    def set_command_handler(self, handler) -> None:
        self._command_requested = handler

    def set_query_handler(self, handler) -> None:
        self._query_requested = handler

    def append(self, text: str) -> None:
        scrollbar = self._output.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 4

        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def append_line(self, text: str) -> None:
        self.append(text + "\n")

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._history.append(text)
        self._history_idx = -1
        self._draft = ""
        self._input.clear()
        if self._query_mode.isChecked() and self._query_requested:
            self._query_requested(text, self._show_query_response)
        elif self._command_requested:
            self._command_requested(text)

    def _show_query_response(self, text: str) -> None:
        cleaned = _PROMPT_RE.sub("", text.strip())
        self.append_line(cleaned)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self._input.hasFocus():
                self._navigate_history(event.key() == Qt.Key.Key_Up)
                return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                self._navigate_history(event.key() == Qt.Key.Key_Up)
                return True
        return super().eventFilter(obj, event)

    def _navigate_history(self, up: bool) -> None:
        if not self._history:
            return
        if self._history_idx == -1:
            self._draft = self._input.text()
        if up:
            if self._history_idx < len(self._history) - 1:
                self._history_idx += 1
        else:
            if self._history_idx >= 0:
                self._history_idx -= 1

        if self._history_idx >= 0:
            pos = len(self._history) - 1 - self._history_idx
            self._input.setText(self._history[pos])
        else:
            self._input.setText(self._draft)
