import os
import time
from PyQt6.QtCore import QProcess, QFileSystemWatcher, pyqtSignal, QObject, QTimer

from glslViewer_config import GLSLVIEWER_BIN
from shader_parser import build_uniform_command


class RenderBridge(QObject):
    stdout_received = pyqtSignal(str)
    stderr_received = pyqtSignal(str)
    process_started = pyqtSignal()
    process_stopped = pyqtSignal()
    process_crashed = pyqtSignal(int, int)  # exit_code, exit_status
    process_exited_normally = pyqtSignal()
    process_gave_up = pyqtSignal()
    recording_progress = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: QProcess | None = None
        self._watch: QFileSystemWatcher | None = None
        self._shader_path: str | None = None
        self._vert_path: str | None = None
        self._geom_path: str | None = None
        self._shader_source: str = ""

        self._crash_count = 0
        self._last_crash_time = 0.0
        self._restart_timer: QTimer | None = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() == QProcess.ProcessState.Running

    @property
    def shader_path(self) -> str | None:
        return self._shader_path

    @property
    def vert_path(self) -> str | None:
        return self._vert_path

    @property
    def geom_path(self) -> str | None:
        return self._geom_path

    def start(self, shader_path: str | None = None, vert_path: str | None = None, geom_path: str | None = None) -> None:
        if self.is_running:
            self.stop()

        self._shader_path = shader_path
        self._vert_path = vert_path
        self._geom_path = geom_path
        if shader_path and os.path.exists(shader_path):
            with open(shader_path) as f:
                self._shader_source = f.read()

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)

        args = ["--noncurses", "--fullFps"]
        if shader_path and os.path.exists(shader_path):
            args.append(shader_path)
        if vert_path and os.path.exists(vert_path):
            args.append(vert_path)
        if geom_path and os.path.exists(geom_path):
            args.append(geom_path)

        self._proc.start(GLSLVIEWER_BIN, args)

        if not self._proc.waitForStarted(5000):
            raise RuntimeError(f"Failed to start glslViewer: {self._proc.errorString()}")

        self._setup_watcher()
        self.process_started.emit()

    def stop(self) -> None:
        self._cancel_restart()
        self._stop_watcher()

        if self._proc:
            if self._proc.state() == QProcess.ProcessState.Running:
                try:
                    self._proc.finished.disconnect(self._on_finished)
                except TypeError:
                    pass
                self._proc.write(b"exit\n")
                if not self._proc.waitForFinished(3000):
                    self._proc.kill()
                    self._proc.waitForFinished(1000)
            self._proc = None

        self.process_stopped.emit()

    def send_command(self, command: str) -> None:
        if self.is_running:
            full = command if command.endswith("\n") else command + "\n"
            self._proc.write(full.encode("utf-8"))

    def set_uniform(self, name: str, value) -> None:
        cmd = build_uniform_command(name, value)
        self.send_command(cmd)

    def set_uniform_raw(self, name: str, *values: float) -> None:
        parts = ",".join(str(v) for v in values)
        self.send_command(f"uniform,{name},{parts}")

    def load_shader(self, path: str, vert_path: str | None = None, geom_path: str | None = None) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Shader file not found: {path}")
        self._crash_count = 0
        self.start(path, vert_path, geom_path)

    def reload_current(self) -> None:
        if self._shader_path and os.path.exists(self._shader_path):
            self.send_command("reload")

    def screenshot(self, path: str) -> None:
        self.send_command(f"screenshot,{path}")

    def sequence(self, prefix: str, from_sec: float, to_sec: float, fps: float = 24.0) -> None:
        self.send_command(f"sequence,{prefix},{from_sec},{to_sec},{fps}")

    def record(self, path: str, from_sec: float, to_sec: float, fps: float = 24.0) -> None:
        self.send_command(f"record,{path},{from_sec},{to_sec},{fps}")

    @property
    def shader_source(self) -> str:
        return self._shader_source

    def _on_stdout(self) -> None:
        raw = self._proc.readAllStandardOutput()
        data = bytes(raw).decode("utf-8", errors="replace")
        if data:
            self._parse_recording_progress(data)
            self.stdout_received.emit(data)

    def _on_stderr(self) -> None:
        raw = self._proc.readAllStandardError()
        data = bytes(raw).decode("utf-8", errors="replace")
        if data:
            self.stderr_received.emit(data)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._stop_watcher()

        is_crash = exit_status == QProcess.ExitStatus.CrashExit or exit_code != 0
        now = time.time()

        if is_crash:
            self._crash_count += 1
            self._last_crash_time = now
            self.process_crashed.emit(exit_code, exit_status.value)

            if self._crash_count < 3:
                delay_ms = 500 * self._crash_count
                self._restart_timer = QTimer(self)
                self._restart_timer.setSingleShot(True)
                self._restart_timer.timeout.connect(
                    lambda: self.start(self._shader_path, self._vert_path, self._geom_path)
                )
                self._restart_timer.start(delay_ms)
            else:
                self._crash_count = 0
                self.process_gave_up.emit()
        else:
            if now - self._last_crash_time > 10.0:
                self._crash_count = 0
            self.process_exited_normally.emit()

        self.process_stopped.emit()

    def _cancel_restart(self) -> None:
        if self._restart_timer:
            self._restart_timer.stop()
            try:
                self._restart_timer.timeout.disconnect()
            except TypeError:
                pass
            self._restart_timer.deleteLater()
            self._restart_timer = None

    def _setup_watcher(self) -> None:
        self._watch = QFileSystemWatcher(self)
        if self._shader_path and os.path.exists(self._shader_path):
            self._watch.addPath(self._shader_path)
        self._watch.fileChanged.connect(self._on_file_changed)

    def _stop_watcher(self) -> None:
        if self._watch:
            try:
                self._watch.fileChanged.disconnect(self._on_file_changed)
            except TypeError:
                pass
            for p in self._watch.files():
                self._watch.removePath(p)
            self._watch.deleteLater()
            self._watch = None

    def _on_file_changed(self, path: str) -> None:
        time.sleep(0.05)
        self.reload_current()
        with open(path) as f:
            self._shader_source = f.read()

    def _parse_recording_progress(self, text: str) -> None:
        import re
        for line in text.splitlines():
            m = re.search(r"([#\.]+)\s+(\d+)%", line)
            if m:
                try:
                    pct = float(m.group(2)) / 100.0
                    self.recording_progress.emit(pct)
                except ValueError:
                    pass
