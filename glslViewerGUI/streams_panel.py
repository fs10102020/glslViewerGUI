from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QDoubleSpinBox,
    QSpinBox, QLineEdit, QGridLayout,
)
from commands import (
    build_stream_play, build_stream_stop, build_stream_restart,
    build_stream_speed, build_stream_time, build_stream_pct,
    build_streams_play, build_streams_stop, build_streams_restart,
    build_streams_speed, build_streams_time, build_streams_pct,
    build_streams_frame, build_streams_prevs,
)


class StreamsPanel(QWidget):
    command_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StreamsPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        global_group = QGroupBox("All Streams")
        global_row = QHBoxLayout(global_group)
        for label, cmd in [
            ("Play", build_streams_play()),
            ("Stop", build_streams_stop()),
            ("Restart", build_streams_restart()),
            ("List", "streams"),
        ]:
            btn = QPushButton(label)
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked=False, _c=cmd: self.command_requested.emit(_c))
            global_row.addWidget(btn)
        global_row.addStretch()
        layout.addWidget(global_group)

        global_ctrl = QHBoxLayout()
        global_ctrl.addWidget(QLabel("Speed:"))
        self._gspeed = QDoubleSpinBox()
        self._gspeed.setRange(0.0, 100.0)
        self._gspeed.setValue(1.0)
        self._gspeed.setSingleStep(0.1)
        global_ctrl.addWidget(self._gspeed)
        gs_btn = QPushButton("Set")
        gs_btn.setMaximumWidth(60)
        gs_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_streams_speed(self._gspeed.value())))
        global_ctrl.addWidget(gs_btn)
        global_ctrl.addStretch()
        layout.addLayout(global_ctrl)

        gpct_row = QHBoxLayout()
        gpct_row.addWidget(QLabel("Pct:"))
        self._gpct = QDoubleSpinBox()
        self._gpct.setRange(0.0, 1.0)
        self._gpct.setDecimals(3)
        self._gpct.setSingleStep(0.01)
        gpct_row.addWidget(self._gpct)
        gpct_btn = QPushButton("Set Pct")
        gpct_btn.setMaximumWidth(70)
        gpct_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_streams_pct(self._gpct.value())))
        gpct_row.addWidget(gpct_btn)
        gpct_row.addStretch()
        layout.addLayout(gpct_row)

        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Frame:"))
        self._gframe = QSpinBox()
        self._gframe.setRange(0, 999999)
        self._gframe.setValue(0)
        frame_row.addWidget(self._gframe)
        gf_btn = QPushButton("Jump")
        gf_btn.setMaximumWidth(70)
        gf_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_streams_frame(self._gframe.value())))
        frame_row.addWidget(gf_btn)
        frame_row.addStretch()

        prevs_row = QHBoxLayout()
        prevs_row.addWidget(QLabel("Prevs:"))
        self._gprevs = QSpinBox()
        self._gprevs.setRange(0, 32)
        self._gprevs.setValue(0)
        prevs_row.addWidget(self._gprevs)
        gp_btn = QPushButton("Set")
        gp_btn.setMaximumWidth(60)
        gp_btn.clicked.connect(lambda checked=False: self.command_requested.emit(build_streams_prevs(self._gprevs.value())))
        prevs_row.addWidget(gp_btn)
        prevs_row.addStretch()
        layout.addLayout(frame_row)
        layout.addLayout(prevs_row)

        per_group = QGroupBox("Per Stream")
        per_form = QVBoxLayout(per_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self._sname = QLineEdit()
        self._sname.setPlaceholderText("u_tex0")
        name_row.addWidget(self._sname)
        per_form.addLayout(name_row)

        per_buttons = QHBoxLayout()
        for label, build_fn in [
            ("Play", build_stream_play),
            ("Stop", build_stream_stop),
            ("Restart", build_stream_restart),
        ]:
            btn = QPushButton(label)
            btn.setMaximumWidth(80)
            btn.clicked.connect(lambda checked=False, _b=build_fn: self._emit_stream(_b))
            per_buttons.addWidget(btn)
        per_buttons.addStretch()
        per_form.addLayout(per_buttons)

        per_ctrl = QGridLayout()
        per_ctrl.addWidget(QLabel("Speed:"), 0, 0)
        self._pspeed = QDoubleSpinBox()
        self._pspeed.setRange(0.0, 100.0)
        self._pspeed.setValue(1.0)
        self._pspeed.setSingleStep(0.1)
        per_ctrl.addWidget(self._pspeed, 0, 1)
        per_ctrl.addWidget(QLabel("Time:"), 1, 0)
        self._ptime = QDoubleSpinBox()
        self._ptime.setRange(0.0, 1e6)
        self._ptime.setValue(0.0)
        per_ctrl.addWidget(self._ptime, 1, 1)
        per_ctrl.addWidget(QLabel("Pct:"), 2, 0)
        self._ppct = QDoubleSpinBox()
        self._ppct.setRange(0.0, 1.0)
        self._ppct.setDecimals(3)
        self._ppct.setSingleStep(0.01)
        per_ctrl.addWidget(self._ppct, 2, 1)
        ps_btn = QPushButton("Set Speed")
        ps_btn.setMaximumWidth(90)
        ps_btn.clicked.connect(lambda checked=False: self._emit_stream(lambda n: build_stream_speed(n, self._pspeed.value())))
        pt_btn = QPushButton("Set Time")
        pt_btn.setMaximumWidth(80)
        pt_btn.clicked.connect(lambda checked=False: self._emit_stream(lambda n: build_stream_time(n, self._ptime.value())))
        ppct_btn = QPushButton("Set Pct")
        ppct_btn.setMaximumWidth(80)
        ppct_btn.clicked.connect(lambda checked=False: self._emit_stream(lambda n: build_stream_pct(n, self._ppct.value())))
        per_ctrl.addWidget(ps_btn, 0, 2)
        per_ctrl.addWidget(pt_btn, 1, 2)
        per_ctrl.addWidget(ppct_btn, 2, 2)
        per_form.addLayout(per_ctrl)

        layout.addWidget(per_group)

        layout.addStretch()

    def _emit_stream(self, builder) -> None:
        name = self._sname.text().strip()
        if not name:
            return
        self.command_requested.emit(builder(name))
