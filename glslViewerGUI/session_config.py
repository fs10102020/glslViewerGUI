# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import os
from dataclasses import dataclass, field

from commands import build_define

FRAG_EXTENSIONS = (".frag", ".fs", ".glsl")
VERT_EXTENSIONS = (".vert", ".vs")
GEOM_EXTENSIONS = ()
MESH_EXTENSIONS = (".ply", ".obj", ".stl", ".glb", ".gltf", ".splat")
TEXTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tga", ".psd", ".gif", ".bmp", ".hdr", ".exr")
VIDEO_EXTENSIONS = (".mov", ".mp4", ".mkv", ".mpg", ".mpeg", ".h264")


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _dir(path: str) -> str:
    return os.path.dirname(os.path.abspath(path))


def discover_vert_sibling(frag_path: str) -> str | None:
    base = _stem(frag_path)
    d = _dir(frag_path)
    for ext in VERT_EXTENSIONS:
        candidate = os.path.join(d, base + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def discover_frag_sibling(vert_path: str) -> str | None:
    base = _stem(vert_path)
    d = _dir(vert_path)
    for ext in FRAG_EXTENSIONS:
        candidate = os.path.join(d, base + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def discover_sibling(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in FRAG_EXTENSIONS:
        return discover_vert_sibling(path)
    if ext in VERT_EXTENSIONS:
        return discover_frag_sibling(path)
    return None


@dataclass
class AssetSpec:
    kind: str
    name: str = ""
    path: str = ""
    options: dict = field(default_factory=dict)


# Canonical asset kinds shared by the classifier, asset panel, and session config.
ASSET_NAMED_TEXTURE = "named_texture"
ASSET_STREAM_TEXTURE = "stream_texture"
ASSET_CUBEMAP_SHOW = "cubemap_show"
ASSET_CUBEMAP_ENV = "cubemap_env"
ASSET_AUDIO = "audio"
ASSET_MODEL = "model"
ASSET_SEQUENCE_UNIFORM = "sequence_uniform"
ASSET_CAMERA_SEQUENCE = "camera_sequence"
ASSET_AUTO_TEXTURE = "auto_texture"

# Kinds that can be passed directly on the glslViewer command line.
CLI_ASSET_KINDS = frozenset({
    ASSET_NAMED_TEXTURE,
    ASSET_CUBEMAP_SHOW,
    ASSET_CUBEMAP_ENV,
    ASSET_SEQUENCE_UNIFORM,
})


@dataclass
class ShaderProgramSpec:
    frag_path: str | None = None
    vert_path: str | None = None
    model_path: str | None = None
    source_stages: dict[str, str] = field(default_factory=dict)

    @property
    def program_label(self) -> str:
        parts = []
        if self.frag_path:
            parts.append(os.path.basename(self.frag_path))
        if self.vert_path:
            parts.append(os.path.basename(self.vert_path))
        if self.model_path:
            parts.append(os.path.basename(self.model_path))
        return " + ".join(parts) if parts else "(default)"

    @property
    def frag_source(self) -> str:
        return self.source_stages.get("frag", "")

    @property
    def vert_source(self) -> str:
        return self.source_stages.get("vert", "")

    def build_args(self) -> list[str]:
        args = []
        if self.frag_path and os.path.isfile(self.frag_path):
            args.append(self.frag_path)
        if self.vert_path and os.path.isfile(self.vert_path):
            args.append(self.vert_path)
        if self.model_path and os.path.isfile(self.model_path):
            args.append(self.model_path)
        return args

    def to_dict(self) -> dict:
        return {
            "frag_path": self.frag_path,
            "vert_path": self.vert_path,
            "model_path": self.model_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShaderProgramSpec":
        return cls(
            frag_path=data.get("frag_path"),
            vert_path=data.get("vert_path"),
            model_path=data.get("model_path"),
        )

    @classmethod
    def from_path(cls, path: str) -> "ShaderProgramSpec":
        ext = os.path.splitext(path)[1].lower()
        if ext in FRAG_EXTENSIONS:
            vert = discover_vert_sibling(path)
            return cls(frag_path=path, vert_path=vert)
        if ext in VERT_EXTENSIONS:
            frag = discover_frag_sibling(path)
            return cls(frag_path=frag, vert_path=path)
        if ext in MESH_EXTENSIONS:
            return cls(model_path=path)
        return cls()


@dataclass
class RenderSessionConfig:
    frag_path: str | None = None
    vert_path: str | None = None
    geom_path: str | None = None
    source_frag_path: str | None = None
    source_vert_path: str | None = None
    include_dirs: list[str] = field(default_factory=list)
    defines: dict[str, str] = field(default_factory=dict)
    assets: list[AssetSpec] = field(default_factory=list)
    full_fps: bool = True
    fps: int = 0
    noncurses: bool = True
    cwd: str = ""
    headless: bool = False
    fullscreen: bool = False
    screensaver: bool = False
    undecorated: bool = False
    nocursor: bool = False
    verbose: bool = False
    fxaa: bool = False
    msaa: bool = False
    vflip: bool = False
    window_x: int | None = None
    window_y: int | None = None
    window_width: int | None = None
    window_height: int | None = None
    window_size: int | None = None
    osc_port: int | None = None

    # Advanced / platform-specific glslViewer flags
    gl_major: int | None = None
    gl_minor: int | None = None
    life_coding: bool = False
    quilt: int | None = None
    quilt_tile: int | None = None
    lenticular_path: str = ""
    display_device: str = ""  # GBM display port, e.g. /dev/dri/card1
    mouse_device: str = ""  # non-GLFW mouse port
    video_device: str = ""  # --video <device>
    audio_device: str = ""  # --audio [device_id]
    cubemap_sh: bool = False  # -sh envmap mode (hidden SH, no visible skybox)

    def build_args(self) -> list[str]:
        args = ["--noncurses"]
        if self.headless:
            args.append("--headless")
        if self.fullscreen:
            args.append("--fullscreen")
        if self.screensaver:
            args.append("--screensaver")
        if self.undecorated:
            args.append("--undecorated")
        if self.nocursor:
            args.append("--nocursor")
        if self.verbose:
            args.append("--verbose")
        if self.fxaa:
            args.append("--fxaa")
        if self.msaa:
            args.append("--msaa")
        if self.vflip:
            args.append("--vFlip")
        if self.window_x is not None:
            args.extend(["-x", str(self.window_x)])
        if self.window_y is not None:
            args.extend(["-y", str(self.window_y)])
        if self.window_size is not None:
            args.extend(["--size", str(self.window_size)])
        else:
            if self.window_width is not None:
                args.extend(["--width", str(self.window_width)])
            if self.window_height is not None:
                args.extend(["--height", str(self.window_height)])
        if self.osc_port is not None:
            args.extend(["--port", str(self.osc_port)])
        if self.full_fps:
            args.append("--fullFps")
        elif self.fps > 0:
            args.extend(["-fps", str(self.fps)])

        if self.gl_major is not None:
            args.extend(["--major", str(self.gl_major)])
        if self.gl_minor is not None:
            args.extend(["--minor", str(self.gl_minor)])
        if self.life_coding:
            args.append("--life-coding")
        if self.quilt is not None:
            args.extend(["--quilt", str(self.quilt)])
        if self.quilt_tile is not None:
            args.extend(["--quilt_tile", str(self.quilt_tile)])
        if self.lenticular_path:
            args.extend(["--lenticular", self.lenticular_path])
        if self.display_device:
            args.extend(["--display", self.display_device])
        if self.mouse_device:
            args.extend(["--mouse", self.mouse_device])
        if self.video_device:
            args.extend(["--video", self.video_device])

        for d in self.include_dirs:
            args.extend(["-I", d])

        for key, val in self.defines.items():
            # SDF integrator defines are emitted by the SDF shader composer
            # itself (``#define SDF_INTEGRATOR_<MODE>`` at the top of the
            # generated frag). Putting them on the argv as well would
            # inject a duplicate into every model and the canvas shader.
            if key.startswith("SDF_INTEGRATOR_"):
                continue
            if val:
                args.extend(["-e", build_define(key, val)])
            else:
                args.append(f"-D{key}")

        for a in self.assets:
            if a.kind == "auto_texture":
                # glslViewer has no formal --auto-texture argv handler, but bare
                # paths are auto-named by the renderer's texture loader.
                args.append(a.path)
            elif a.kind == "named_texture":
                args.extend([f"-{a.name}", a.path])
            elif a.kind == "cubemap_show":
                args.extend(["-C", a.path])
            elif a.kind == "cubemap_env":
                if self.cubemap_sh:
                    args.extend(["-sh", a.path])
                else:
                    args.extend(["-c", a.path])
            elif a.kind == "sequence_uniform":
                args.extend([f"-{a.name}", a.path])

        if self.audio_device:
            args.extend(["--audio", self.audio_device])

        if self.frag_path:
            args.append(self.frag_path)
        if self.vert_path:
            args.append(self.vert_path)
        if self.geom_path:
            args.append(self.geom_path)

        return args

    def to_dict(self) -> dict:
        return {
            "frag_path": self.frag_path,
            "vert_path": self.vert_path,
            "geom_path": self.geom_path,
            "source_frag_path": self.source_frag_path,
            "source_vert_path": self.source_vert_path,
            "include_dirs": list(self.include_dirs),
            "defines": dict(self.defines),
            "assets": [
                {"kind": a.kind, "name": a.name, "path": a.path, "options": dict(a.options)}
                for a in self.assets
            ],
            "full_fps": self.full_fps,
            "fps": self.fps,
            "noncurses": self.noncurses,
            "cwd": self.cwd,
            "headless": self.headless,
            "fullscreen": self.fullscreen,
            "screensaver": self.screensaver,
            "undecorated": self.undecorated,
            "nocursor": self.nocursor,
            "verbose": self.verbose,
            "fxaa": self.fxaa,
            "msaa": self.msaa,
            "vflip": self.vflip,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_size": self.window_size,
            "osc_port": self.osc_port,
            "gl_major": self.gl_major,
            "gl_minor": self.gl_minor,
            "life_coding": self.life_coding,
            "quilt": self.quilt,
            "quilt_tile": self.quilt_tile,
            "lenticular_path": self.lenticular_path,
            "display_device": self.display_device,
            "mouse_device": self.mouse_device,
            "video_device": self.video_device,
            "audio_device": self.audio_device,
            "cubemap_sh": self.cubemap_sh,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenderSessionConfig":
        return cls(
            frag_path=data.get("frag_path"),
            vert_path=data.get("vert_path"),
            geom_path=data.get("geom_path"),
            source_frag_path=data.get("source_frag_path"),
            source_vert_path=data.get("source_vert_path"),
            include_dirs=data.get("include_dirs", []),
            defines=data.get("defines", {}),
            assets=[AssetSpec(**a) for a in data.get("assets", [])],
            full_fps=data.get("full_fps", True),
            fps=data.get("fps", 0),
            noncurses=data.get("noncurses", True),
            cwd=data.get("cwd", ""),
            headless=data.get("headless", False),
            fullscreen=data.get("fullscreen", False),
            screensaver=data.get("screensaver", False),
            undecorated=data.get("undecorated", False),
            nocursor=data.get("nocursor", False),
            verbose=data.get("verbose", False),
            fxaa=data.get("fxaa", False),
            msaa=data.get("msaa", False),
            vflip=data.get("vflip", False),
            window_x=data.get("window_x"),
            window_y=data.get("window_y"),
            window_width=data.get("window_width"),
            window_height=data.get("window_height"),
            window_size=data.get("window_size"),
            osc_port=data.get("osc_port"),
            gl_major=data.get("gl_major"),
            gl_minor=data.get("gl_minor"),
            life_coding=data.get("life_coding", False),
            quilt=data.get("quilt"),
            quilt_tile=data.get("quilt_tile"),
            lenticular_path=data.get("lenticular_path", ""),
            display_device=data.get("display_device", ""),
            mouse_device=data.get("mouse_device", ""),
            video_device=data.get("video_device", ""),
            audio_device=data.get("audio_device", ""),
            cubemap_sh=data.get("cubemap_sh", False),
        )

    def to_program(self) -> ShaderProgramSpec:
        return ShaderProgramSpec(
            frag_path=self.frag_path,
            vert_path=self.vert_path,
            model_path=self.geom_path,
        )
