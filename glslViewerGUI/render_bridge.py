# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import os
import re as _re
import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QProcess, QFileSystemWatcher, Signal, QObject, QTimer

from glslViewer_config import GLSLVIEWER_BIN
from commands import build_uniform
from session_config import RenderSessionConfig, ShaderProgramSpec


@dataclass
class _PendingCommand:
    command: str
    callback: Optional[Callable[[str], None]] = None


class RenderBridge(QObject):
    stdout_received = Signal(str)
    stderr_received = Signal(str)
    process_started = Signal()
    process_stopped = Signal()
    process_crashed = Signal(int, int)
    process_exited_normally = Signal()
    process_gave_up = Signal()
    recording_progress = Signal(float)
    state_query_response = Signal(str, str)

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

        self._pending: list[_PendingCommand] = []
        self._startup_prompt_seen = False
        self._prompt_buffer = ""
        self._pending_changed_paths: set[str] = set()
        self._watcher_debounce: QTimer | None = None
        self._query_timeout: QTimer | None = None
        self._session_backed: bool = False

        self._session_config = RenderSessionConfig()
        self._program = ShaderProgramSpec()

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
    def pending_command_count(self) -> int:
        return len(self._pending)

    @property
    def session_backed(self) -> bool:
        return self._session_backed

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------

    def start(self, shader_path: str | None = None, vert_path: str | None = None, geom_path: str | None = None) -> None:
        if self.is_running:
            self.stop()

        self._shader_path = shader_path
        self._vert_path = vert_path
        self._geom_path = geom_path
        if shader_path and os.path.exists(shader_path):
            with open(shader_path) as f:
                self._shader_source = f.read()

        self._program = ShaderProgramSpec(frag_path=shader_path, vert_path=vert_path, model_path=geom_path)
        self._session_config.frag_path = shader_path
        self._session_config.vert_path = vert_path
        self._session_config.geom_path = geom_path

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

        self._pending.clear()
        self._startup_prompt_seen = False
        self._prompt_buffer = ""
        self._setup_watcher()
        self.process_started.emit()

    def start_session(self, config: RenderSessionConfig) -> None:
        if self.is_running:
            self.stop()

        self._session_config = config
        self._session_backed = True
        self._shader_path = config.frag_path
        self._vert_path = config.vert_path
        self._geom_path = config.geom_path

        if config.frag_path and os.path.exists(config.frag_path):
            with open(config.frag_path) as f:
                self._shader_source = f.read()

        self._program = ShaderProgramSpec(
            frag_path=config.frag_path,
            vert_path=config.vert_path,
            model_path=config.geom_path,
        )

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self._proc.readyReadStandardOutput.connect(self._on_stdout)
        self._proc.readyReadStandardError.connect(self._on_stderr)
        self._proc.finished.connect(self._on_finished)

        args = config.build_args()
        cwd = config.cwd or None
        if cwd and os.path.isdir(cwd):
            self._proc.setWorkingDirectory(cwd)
        self._proc.start(GLSLVIEWER_BIN, args)

        if not self._proc.waitForStarted(5000):
            self._session_backed = False
            raise RuntimeError(f"Failed to start glslViewer: {self._proc.errorString()}")

        self._pending.clear()
        self._startup_prompt_seen = False
        self._prompt_buffer = ""
        self._setup_watcher()
        self.process_started.emit()

    def stop(self) -> None:
        self._cancel_restart()
        self._stop_watcher()
        self._stop_query_timeout()

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

        self._pending.clear()
        self._session_backed = False
        self.process_stopped.emit()

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def send_command(self, command: str) -> None:
        if self.is_running:
            full = command if command.endswith("\n") else command + "\n"
            self._pending.append(_PendingCommand(command=command.strip()))
            self._proc.write(full.encode("utf-8"))

    def send_query(self, command: str, callback: Callable[[str], None]) -> None:
        if self.is_running:
            full = command if command.endswith("\n") else command + "\n"
            self._pending.append(_PendingCommand(command=command.strip(), callback=callback))
            self._proc.write(full.encode("utf-8"))
            self._start_query_timeout()

    def set_uniform(self, name: str, value) -> None:
        cmd = build_uniform(name, value)
        self.send_command(cmd)

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

    def frames(self, prefix: str, from_frame: int, to_frame: int, fps: float = 24.0) -> None:
        self.send_command(f"frames,{prefix},{from_frame},{to_frame},{fps}")

    @property
    def shader_source(self) -> str:
        return self._shader_source

    # ------------------------------------------------------------------
    # I/O handling
    # ------------------------------------------------------------------

    def _on_stdout(self) -> None:
        raw = self._proc.readAllStandardOutput()
        data = bytes(raw).decode("utf-8", errors="replace")
        if data:
            self._parse_recording_progress(data)
            self._route_prompt_output(data)
            self.stdout_received.emit(data)

    def _on_stderr(self) -> None:
        raw = self._proc.readAllStandardError()
        data = bytes(raw).decode("utf-8", errors="replace")
        if data:
            self.stderr_received.emit(data)

    def _route_prompt_output(self, chunk: str = "") -> None:
        if chunk:
            self._prompt_buffer += chunk
        while "// > " in self._prompt_buffer:
            idx = self._prompt_buffer.find("// > ")
            batch = self._prompt_buffer[:idx]
            self._prompt_buffer = self._prompt_buffer[idx + len("// > "):]

            if not self._startup_prompt_seen:
                self._startup_prompt_seen = True
                continue

            if self._pending:
                cmd = self._pending.pop(0)
                text = batch.strip()
                if cmd.callback:
                    cmd.callback(text)

        if not self._has_pending_queries():
            self._stop_query_timeout()

    def _flush_stale_prompts(self) -> None:
        while self._pending:
            cmd = self._pending.pop(0)
            if cmd.callback:
                cmd.callback("")
        self._stop_query_timeout()

    def _has_pending_queries(self) -> bool:
        return any(cmd.callback is not None for cmd in self._pending)

    def _start_query_timeout(self) -> None:
        if self._query_timeout is None:
            self._query_timeout = QTimer(self)
            self._query_timeout.setSingleShot(True)
            self._query_timeout.setInterval(5000)
            self._query_timeout.timeout.connect(self._flush_stale_prompts)
        self._query_timeout.start()

    def _stop_query_timeout(self) -> None:
        if self._query_timeout is not None and self._query_timeout.isActive():
            self._query_timeout.stop()

    # ------------------------------------------------------------------
    # Process lifecycle
    # ------------------------------------------------------------------

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._stop_watcher()
        self._stop_query_timeout()
        self._flush_stale_prompts()

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
                if self._session_backed:
                    self._restart_timer.timeout.connect(
                        lambda: self.start_session(self._session_config)
                    )
                else:
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

        self._session_backed = False
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

    # ------------------------------------------------------------------
    # File watcher with debounce
    # ------------------------------------------------------------------

    def _setup_watcher(self) -> None:
        self._watch = QFileSystemWatcher(self)
        if self._shader_path and os.path.exists(self._shader_path):
            self._watch.addPath(self._shader_path)
        if self._vert_path and os.path.exists(self._vert_path):
            self._watch.addPath(self._vert_path)
        if self._geom_path and os.path.exists(self._geom_path):
            self._watch.addPath(self._geom_path)
        self._watch.fileChanged.connect(self._on_file_changed)

        self._pending_changed_paths.clear()
        self._watcher_debounce = QTimer(self)
        self._watcher_debounce.setSingleShot(True)
        self._watcher_debounce.setInterval(150)
        self._watcher_debounce.timeout.connect(self._flush_changed_paths)

    def _stop_watcher(self) -> None:
        if self._watcher_debounce:
            self._watcher_debounce.stop()
            self._watcher_debounce.deleteLater()
            self._watcher_debounce = None
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
        self._pending_changed_paths.add(path)
        if self._watcher_debounce:
            self._watcher_debounce.start()

    def _flush_changed_paths(self) -> None:
        paths = sorted(self._pending_changed_paths)
        self._pending_changed_paths.clear()
        for p in paths:
            if self.is_running:
                self.send_command(f"reload,{p}")
                try:
                    with open(p) as f:
                        self._shader_source = f.read()
                except OSError:
                    pass

    def _parse_recording_progress(self, text: str) -> None:
        for line in text.splitlines():
            m = _re.search(r"([#\.]+)\s+(\d+)%", line)
            if m:
                try:
                    pct = float(m.group(2)) / 100.0
                    self.recording_progress.emit(pct)
                except ValueError:
                    pass
