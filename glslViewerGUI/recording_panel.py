import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox,
    QFileDialog, QProgressBar, QGroupBox, QMessageBox,
)


class RecordingPanel(QWidget):
    screenshot_requested = Signal(str)
    sequence_requested = Signal(str, float, float, float)
    record_requested = Signal(str, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RecordingPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Screenshot
        ss_group = QGroupBox("Screenshot")
        ss_layout = QHBoxLayout(ss_group)
        self._ss_btn = QPushButton("Save Screenshot\u2026")
        self._ss_btn.clicked.connect(self._on_screenshot)
        ss_layout.addWidget(self._ss_btn)
        layout.addWidget(ss_group)

        # Sequence
        seq_group = QGroupBox("PNG Sequence")
        seq_layout = QVBoxLayout(seq_group)

        seq_dir = QHBoxLayout()
        seq_dir.addWidget(QLabel("Prefix:"))
        self._seq_prefix = QLabel("frame_")
        self._seq_prefix.setStyleSheet("font-weight: bold;")
        seq_dir.addWidget(self._seq_prefix)
        self._seq_dir_btn = QPushButton("Choose Directory\u2026")
        self._seq_dir_btn.clicked.connect(self._on_choose_seq_dir)
        seq_dir.addWidget(self._seq_dir_btn)
        seq_layout.addLayout(seq_dir)

        seq_times = QHBoxLayout()
        seq_times.addWidget(QLabel("From (s):"))
        self._seq_from = QDoubleSpinBox()
        self._seq_from.setRange(0.0, 1e6)
        self._seq_from.setDecimals(2)
        self._seq_from.setSingleStep(0.5)
        self._seq_from.setValue(0.0)
        seq_times.addWidget(self._seq_from)

        seq_times.addWidget(QLabel("To (s):"))
        self._seq_to = QDoubleSpinBox()
        self._seq_to.setRange(0.0, 1e6)
        self._seq_to.setDecimals(2)
        self._seq_to.setSingleStep(0.5)
        self._seq_to.setValue(5.0)
        seq_times.addWidget(self._seq_to)

        seq_times.addWidget(QLabel("FPS:"))
        self._seq_fps = QSpinBox()
        self._seq_fps.setRange(1, 240)
        self._seq_fps.setValue(24)
        seq_times.addWidget(self._seq_fps)
        seq_layout.addLayout(seq_times)

        self._seq_start = QPushButton("Start Sequence")
        self._seq_start.clicked.connect(self._on_start_sequence)
        seq_layout.addWidget(self._seq_start)
        layout.addWidget(seq_group)

        # Video
        vid_group = QGroupBox("Video (MP4 / GIF)")
        vid_layout = QVBoxLayout(vid_group)

        vid_file = QHBoxLayout()
        vid_file.addWidget(QLabel("Output:"))
        self._vid_path = QLabel("(none)")
        self._vid_path.setStyleSheet("font-weight: bold;")
        vid_file.addWidget(self._vid_path)
        self._vid_file_btn = QPushButton("Choose File\u2026")
        self._vid_file_btn.clicked.connect(self._on_choose_vid_file)
        vid_file.addWidget(self._vid_file_btn)
        vid_layout.addLayout(vid_file)

        vid_times = QHBoxLayout()
        vid_times.addWidget(QLabel("From (s):"))
        self._vid_from = QDoubleSpinBox()
        self._vid_from.setRange(0.0, 1e6)
        self._vid_from.setDecimals(2)
        self._vid_from.setSingleStep(0.5)
        self._vid_from.setValue(0.0)
        vid_times.addWidget(self._vid_from)

        vid_times.addWidget(QLabel("To (s):"))
        self._vid_to = QDoubleSpinBox()
        self._vid_to.setRange(0.0, 1e6)
        self._vid_to.setDecimals(2)
        self._vid_to.setSingleStep(0.5)
        self._vid_to.setValue(5.0)
        vid_times.addWidget(self._vid_to)

        vid_times.addWidget(QLabel("FPS:"))
        self._vid_fps = QSpinBox()
        self._vid_fps.setRange(1, 240)
        self._vid_fps.setValue(24)
        vid_times.addWidget(self._vid_fps)
        vid_layout.addLayout(vid_times)

        self._vid_start = QPushButton("Start Recording")
        self._vid_start.clicked.connect(self._on_start_video)
        vid_layout.addWidget(self._vid_start)
        layout.addWidget(vid_group)

        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        self._status = QLabel("Ready")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        layout.addStretch()
        self._seq_dir: str | None = None
        self._vid_file: str | None = None

    def set_progress(self, pct: float) -> None:
        self._progress.setValue(int(pct * 100))
        self._status.setText(f"Recording\u2026 {int(pct * 100)}%")

    def reset_progress(self) -> None:
        self._progress.setValue(0)
        self._status.setText("Ready")
        self._seq_start.setEnabled(True)
        self._vid_start.setEnabled(True)

    def set_busy(self, busy: bool) -> None:
        self._seq_start.setEnabled(not busy)
        self._vid_start.setEnabled(not busy)

    def _on_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "screenshot.png",
            "PNG Images (*.png);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self.screenshot_requested.emit(path)

    def _on_choose_seq_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Choose Sequence Directory", "",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if d:
            self._seq_dir = d
            self._seq_prefix.setText(os.path.join(d, "frame_"))

    def _on_start_sequence(self) -> None:
        if not self._seq_dir:
            QMessageBox.warning(self, "Sequence", "Please choose an output directory first.")
            return
        prefix = os.path.join(self._seq_dir, "frame_")
        self.set_busy(True)
        self.sequence_requested.emit(
            prefix,
            self._seq_from.value(),
            self._seq_to.value(),
            float(self._seq_fps.value()),
        )

    def _on_choose_vid_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", "output.mp4",
            "MP4 Video (*.mp4);;GIF Animation (*.gif);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if path:
            self._vid_file = path
            self._vid_path.setText(path)

    def _on_start_video(self) -> None:
        if not self._vid_file:
            QMessageBox.warning(self, "Video", "Please choose an output file first.")
            return
        self.set_busy(True)
        self.record_requested.emit(
            self._vid_file,
            self._vid_from.value(),
            self._vid_to.value(),
            float(self._vid_fps.value()),
        )
