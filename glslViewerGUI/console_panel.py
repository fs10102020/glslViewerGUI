from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QPushButton


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

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._output.clear)
        layout.addWidget(self._clear_btn)

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
