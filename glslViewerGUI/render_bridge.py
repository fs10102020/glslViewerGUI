import os
import time
from collections import deque
from typing import Callable
from PySide6.QtCore import QProcess, QFileSystemWatcher, Signal, QObject, QTimer

from glslViewer_config import GLSLVIEWER_BIN
from commands import build_record, build_screenshot, build_sequence, build_uniform
from session_config import RenderSessionConfig, ShaderProgramSpec


class RenderBridge(QObject):
    stdout_received = Signal(str)
    stderr_received = Signal(str)
    process_started = Signal()
    process_stopped = Signal()
    process_crashed = Signal(int, int)  # exit_code, exit_status
    process_exited_normally = Signal()
    process_gave_up = Signal()
    recording_progress = Signal(float)
    file_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: QProcess | None = None
        self._watch: QFileSystemWatcher | None = None
        self._default_watch_files: list[str] = []
        self._extra_watch_files: list[str] = []
        self._pending_changed_path: str | None = None
        self._shader_path: str | None = None
        self._vert_path: str | None = None
        self._geom_path: str | None = None
        self._shader_source: str = ""
        self._program = ShaderProgramSpec()
        self._session_config = RenderSessionConfig()

        self._crash_count = 0
        self._last_crash_time = 0.0
        self._restart_timer: QTimer | None = None
        self._deferred_reload_timer: QTimer | None = None
        self._pending_queries: deque[Callable[[str], None]] = deque()
        self._query_buffer = ""

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

    @property
    def program(self) -> ShaderProgramSpec:
        return self._program

    @property
    def session_config(self) -> RenderSessionConfig:
        return self._session_config

    def start(self, shader_path: str | None = None, vert_path: str | None = None, geom_path: str | None = None) -> None:
        if self.is_running:
            self.stop()

        self._shader_path = shader_path
        self._vert_path = vert_path
        self._geom_path = geom_path
        self._program = ShaderProgramSpec(frag_path=shader_path, vert_path=vert_path, model_path=geom_path)
        self._session_config.frag_path = shader_path
        self._session_config.vert_path = vert_path
        self._session_config.geom_path = geom_path
        if shader_path and os.path.exists(shader_path):
            with open(shader_path) as f:
                self._shader_source = f.read()

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)

        if self._session_config.cwd:
            self._proc.setWorkingDirectory(self._session_config.cwd)

        args = self._session_config.build_args()
        if "--noncurses" not in args:
            args.insert(0, "--noncurses")

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

    def send_query(self, command: str, callback: Callable[[str], None]) -> None:
        if not self.is_running:
            callback("")
            return
        if not self._pending_queries:
            self._query_buffer = ""
        self._pending_queries.append(callback)
        self.send_command(command)

    def set_uniform(self, name: str, value) -> None:
        cmd = build_uniform(name, value)
        self.send_command(cmd)

    def set_uniform_raw(self, name: str, *values: float) -> None:
        parts = ",".join(str(v) for v in values)
        self.send_command(f"{name},{parts}")

    def apply_session_config(self, config: RenderSessionConfig) -> None:
        self._session_config = config
        self.start(config.frag_path, config.vert_path, config.geom_path)

    def load_shader(self, path: str, vert_path: str | None = None, geom_path: str | None = None) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Shader file not found: {path}")
        self._crash_count = 0
        self.start(path, vert_path, geom_path)

    def reload_current(self) -> None:
        if self._shader_path and os.path.exists(self._shader_path):
            self.send_command("reload")

    def set_watch_files(self, paths: list[str]) -> None:
        """Replace the extra/custom file watcher set with the given paths.

        The default watch set (current fragment, vertex, and geometry/model
        files) is always watched automatically when they exist.
        """
        self._extra_watch_files = [p for p in paths if os.path.exists(p)]
        self._setup_watcher()

    def screenshot(self, path: str) -> None:
        self.send_command(build_screenshot(path))

    def sequence(self, prefix: str, from_sec: float, to_sec: float, fps: float = 24.0) -> None:
        self.send_command(build_sequence(prefix, from_sec, to_sec, fps))

    def record(self, path: str, from_sec: float, to_sec: float, fps: float = 24.0) -> None:
        self.send_command(build_record(path, from_sec, to_sec, fps))

    @property
    def shader_source(self) -> str:
        return self._shader_source

    def _on_stdout(self) -> None:
        raw = self._proc.readAllStandardOutput()
        data = bytes(raw).decode("utf-8", errors="replace")
        if data:
            self._parse_recording_progress(data)
            self._route_query_output(data)
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
            if now - self._last_crash_time > 30.0:
                self._crash_count = 0
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
        self._stop_watcher()
        self._watch = QFileSystemWatcher(self)

        # Default watch set: currently loaded shader files.
        self._default_watch_files = []
        for p in (self._shader_path, self._vert_path, self._geom_path):
            if p and os.path.exists(p):
                self._default_watch_files.append(p)

        for p in set(self._default_watch_files + self._extra_watch_files):
            self._watch.addPath(p)
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
        # Defer notification slightly to batch rapid successive changes.
        self._pending_changed_path = path
        if self._deferred_reload_timer is None:
            self._deferred_reload_timer = QTimer(self)
            self._deferred_reload_timer.setSingleShot(True)
            self._deferred_reload_timer.timeout.connect(self._do_deferred_reload)
        self._deferred_reload_timer.stop()
        self._deferred_reload_timer.start(150)

    def _do_deferred_reload(self) -> None:
        path = self._pending_changed_path
        self._pending_changed_path = None
        if path:
            if self._watch and os.path.exists(path) and path not in self._watch.files():
                self._watch.addPath(path)
            self.file_changed.emit(path)
        if self._shader_path and os.path.exists(self._shader_path):
            with open(self._shader_path) as f:
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

    def _route_query_output(self, text: str) -> None:
        if not self._pending_queries:
            return
        self._query_buffer += text
        while self._pending_queries and self._query_buffer.count("// > ") >= 2:
            before, _, rest = self._query_buffer.partition("// > ")
            response, _, remainder = rest.partition("// > ")
            self._query_buffer = remainder
            callback = self._pending_queries.popleft()
            callback(self._clean_query_response(response))

    def _clean_query_response(self, text: str) -> str:
        cleaned = []
        for line in text.replace("\r", "\n").splitlines():
            stripped = line.strip()
            if not stripped or stripped == "// >":
                continue
            if stripped.startswith("// >"):
                stripped = stripped[4:].strip()
            cleaned.append(stripped)
        return "\n".join(cleaned).strip()
