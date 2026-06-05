from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QTextEdit, QLabel, QGroupBox,
)


QUERY_COMMANDS = [
    ("Uniforms", "uniforms"),
    ("Uniforms All", "uniforms,all"),
    ("Uniforms Active", "uniforms,active"),
    ("Uniforms Defined", "uniforms,defined"),
    ("Uniforms Textures", "uniforms,textures"),
    ("Uniforms Buffers", "uniforms,buffers"),
    ("Uniforms Cubemaps", "uniforms,cubemaps"),
    ("Uniforms Cameras", "uniforms,cameras"),
    ("Uniforms Lights", "uniforms,lights"),
    ("Defines", "defines"),
    ("Dependencies", "dependencies"),
    ("Deps (Frag)", "dependencies,frag"),
    ("Deps (Vert)", "dependencies,vert"),
    ("Files", "files"),
    ("Frag Source", "frag"),
    ("Vert Source", "vert"),
    ("Version", "version"),
    ("GLSL Version", "glsl_version"),
    ("Textures List", "textures,list"),
    ("Buffers List", "buffers,list"),
    ("Cubemaps", "cubemaps"),
    ("Streams", "streams"),
    ("Lights", "lights"),
    ("Models", "models"),
]

METRIC_QUERIES = [
    ("FPS", "fps"),
    ("Delta", "delta"),
    ("Time", "time"),
    ("Date", "date"),
    ("Window W", "window_width"),
    ("Window H", "window_height"),
    ("Screen", "screen_size"),
    ("Viewport", "viewport"),
    ("Mouse", "mouse"),
    ("Pixel Density", "pixel_density"),
]


class InspectorPanel(QWidget):
    query_requested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InspectorPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._result = QTextEdit()
        self._result.setReadOnly(True)
        self._result.setMaximumHeight(150)
        layout.addWidget(self._result)

        state_group = QGroupBox("State Queries")
        state_grid = QGridLayout(state_group)
        state_grid.setHorizontalSpacing(6)
        state_grid.setVerticalSpacing(6)
        for i, (label, cmd) in enumerate(QUERY_COMMANDS):
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, _c=cmd: self.query_requested.emit(_c, self._show_result))
            state_grid.addWidget(btn, i // 3, i % 3)
        layout.addWidget(state_group)

        metric_group = QGroupBox("Runtime Metrics")
        metric_grid = QGridLayout(metric_group)
        metric_grid.setHorizontalSpacing(8)
        metric_grid.setVerticalSpacing(8)
        self._metric_labels: dict[str, QLabel] = {}
        for i, (label, cmd) in enumerate(METRIC_QUERIES):
            container = QVBoxLayout()
            name_lbl = QLabel(label)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl = QLabel("--")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setProperty("telemetry", True)
            container.addWidget(name_lbl)
            container.addWidget(val_lbl)
            metric_grid.addLayout(container, i // 3, i % 3)
            self._metric_labels[cmd] = val_lbl
        layout.addWidget(metric_group)

        refresh_btn = QPushButton("Refresh Metrics")
        refresh_btn.setMaximumWidth(140)
        refresh_btn.clicked.connect(self._refresh_metrics)
        layout.addWidget(refresh_btn)

        layout.addStretch()

    def _show_result(self, text: str) -> None:
        self._result.setPlainText(text)

    def _refresh_metrics(self) -> None:
        for cmd in METRIC_QUERIES:
            c = cmd[1]
            label = self._metric_labels[c]

            def make_cb(lbl, cmd_str):
                def cb(text):
                    lbl.setText(text.strip()[:60])
                return cb

            self.query_requested.emit(c, make_cb(label, c))

    def set_metric(self, name: str, value: str) -> None:
        if name in self._metric_labels:
            self._metric_labels[name].setText(value.strip()[:60])
