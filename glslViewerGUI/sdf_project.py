"""SDF project model and shader composer.

An SDF project is a small directory containing:

    project.json    renderer settings (integrator, marcher, display, etc.)
    scene.glsl      user code providing DE(vec3 p) and optional material hooks

The GUI composes a complete fragment shader from renderer templates and the
user's scene code, then launches glslViewer with the generated shader.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "sdf_templates"
GENERATED_CACHE_DIR = Path.home() / ".config" / "glslviewer-gui" / "generated"


def _ensure_dirs() -> None:
    GENERATED_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _strip_leading_version(source: str) -> str:
    """Remove all scene-level #version directives so the composer can set its own.

    glslViewer (and the templates) expect the generated shader to start with
    a single #version line. Leaving an extra #version inside the user's scene
    source produces a compilation error, so every occurrence is stripped.
    """
    return re.sub(r"^\s*#version\s+.*$", "", source, flags=re.MULTILINE)


def _remove_double_buffer_blocks(source: str) -> str:
    """Strip the #ifdef DOUBLE_BUFFER_0/1 blocks from the generated main.

    glslViewer counts these #ifdef lines to decide how many double buffers
    to allocate. In preview mode we do not want any, so the blocks are
    removed entirely; in pathtrace mode they are preserved.
    """
    return re.sub(
        r"#ifdef\s+DOUBLE_BUFFER_\d+\b.*?#endif",
        "",
        source,
        flags=re.DOTALL,
    )


def _imported_sdf_cache_path(source_path: Path) -> Path:
    """Stable path for the temporary wrapper of an imported SDF-only .glsl file."""
    _ensure_dirs()
    import hashlib
    digest = hashlib.sha1(str(source_path.resolve()).encode("utf-8")).hexdigest()[:10]
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", source_path.stem).strip("_")
    if not safe_name:
        safe_name = "imported"
    return GENERATED_CACHE_DIR / f"{safe_name}_{digest}_imported.frag"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_SCENE_SOURCE = """// SDF scene contract
//
// Required:
//   float DE(vec3 p);
//
// Optional:
//   vec3 baseColor(vec3 p, vec3 normal);
//   vec3 emissionAt(vec3 p, vec3 normal);
//   void initScene();

uniform float u_inversionScale; // @ui slider min=0.5 max=3.0 step=0.01 default=1.4 group="Fractal"
uniform int   u_iterations;     // @ui integer min=1 max=16 step=1 default=8 group="Fractal"
uniform vec3  u_surfaceColor;   // @ui color default=0.55,0.35,0.2 group="Material"
uniform vec3  u_glowColor;      // @ui color default=1.0,0.45,0.05 group="Material"
uniform float u_glowIntensity;  // @ui slider min=0.0 max=10.0 step=0.01 default=2.0 group="Material"

float DE(vec3 p) {
    float scale = 3.0;
    int iter = max(u_iterations, 1);
    for (int i = 0; i < 16; ++i) {
        if (i >= iter) break;
        p = mod(p - 1.0, 2.0) - 1.0;
        float inv = u_inversionScale / max(dot(p, p), 1.0e-10);
        p *= inv;
        scale *= inv;
    }
    return length(p.yz) / scale;
}

vec3 baseColor(vec3 p, vec3 normal) {
    return u_surfaceColor;
}

vec3 emissionAt(vec3 p, vec3 normal) {
    // Stronger emission in tight cavities (small distance between folds)
    float glow = clamp(u_glowIntensity / (abs(DE(p + normal * 0.01)) * 20.0 + 0.1), 0.0, 8.0);
    return u_glowColor * glow;
}

void initScene() {
}
"""


# ---------------------------------------------------------------------------
# Project configuration
# ---------------------------------------------------------------------------

@dataclass
class SdfProjectConfig:
    """Renderer settings persisted in project.json."""

    # Core
    scene: str = "scene.glsl"
    integrator: str = "preview"  # preview, direct, pathtrace
    debug_view: str = "beauty"  # beauty, normal, distance, steps, albedo, emission

    # Marcher
    max_steps: int = 160
    max_distance: float = 80.0
    hit_epsilon: float = 0.0005
    step_scale: float = 0.8
    normal_epsilon: float = 0.001
    shadow_epsilon: float = 0.005
    shadow_steps: int = 48

    # Path tracer
    max_bounces: int = 4
    samples_per_frame: int = 1
    target_samples: int = 256
    rr_start_bounce: int = 3
    firefly_clamp: float = 10.0

    # Camera / scene
    camera_fov: float = 60.0
    exposure: float = 1.0
    tone_map: str = "aces"  # aces, reinhard, filmic, none
    gamma: float = 2.2

    # Environment
    sky_color: list[float] = field(default_factory=lambda: [0.05, 0.07, 0.12])
    horizon_color: list[float] = field(default_factory=lambda: [0.15, 0.13, 0.1])
    ground_color: list[float] = field(default_factory=lambda: [0.02, 0.02, 0.02])
    env_intensity: float = 1.0
    sun_dir: list[float] = field(default_factory=lambda: [0.4, 0.8, 0.3])

    # Display
    denoise_amount: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SdfProjectConfig":
        # Only accept known fields so saved projects stay forward-compatible.
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------

@dataclass
class SdfProject:
    """Loaded SDF project."""

    project_dir: Path
    config: SdfProjectConfig = field(default_factory=SdfProjectConfig)

    # Populated on load
    scene_path: Path | None = None
    scene_source: str = ""

    @property
    def is_valid(self) -> bool:
        return self.scene_path is not None and self.scene_path.exists()

    @property
    def project_json_path(self) -> Path:
        return self.project_dir / "project.json"

    @property
    def generated_frag_path(self) -> Path:
        """Stable generated shader path in user cache.

        Combines project directory name with a short hash of the absolute
        path to avoid collisions when two unrelated projects share a stem.
        """
        _ensure_dirs()
        import hashlib
        digest = hashlib.sha1(str(self.project_dir.resolve()).encode("utf-8")).hexdigest()[:10]
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", self.project_dir.name).strip("_")
        if not safe_name:
            safe_name = "project"
        return GENERATED_CACHE_DIR / f"{safe_name}_{digest}_generated.frag"

    @classmethod
    def create_new(cls, project_dir: Path | str, scene_source: str | None = None) -> "SdfProject":
        """Create a fresh project directory with project.json and scene.glsl."""
        project_dir = Path(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        config = SdfProjectConfig()
        project = cls(project_dir=project_dir, config=config)

        project.scene_path = project_dir / config.scene
        project.scene_source = scene_source if scene_source is not None else DEFAULT_SCENE_SOURCE
        project.save()
        return project

    def load(self) -> "SdfProject":
        """Load project.json and scene.glsl from disk."""
        if self.project_json_path.exists():
            with open(self.project_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Accept legacy/flat project.json files that may contain top-level
            # config keys without a "config" wrapper.
            if "config" in data:
                self.config = SdfProjectConfig.from_dict(data["config"])
            else:
                self.config = SdfProjectConfig.from_dict(data)

        self.scene_path = self.project_dir / self.config.scene
        if self.scene_path.exists():
            with open(self.scene_path, "r", encoding="utf-8") as f:
                self.scene_source = f.read()
        return self

    def save(self) -> None:
        """Persist project.json and scene.glsl."""
        self.save_config()
        self.save_scene()

    def save_config(self) -> None:
        """Persist project.json only."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        data = {"type": "sdf_project", "config": self.config.to_dict()}
        with open(self.project_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_scene(self) -> None:
        """Persist scene.glsl only."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        if self.scene_path is None:
            self.scene_path = self.project_dir / self.config.scene
        with open(self.scene_path, "w", encoding="utf-8") as f:
            f.write(self.scene_source)

    def write_scene_source(self, source: str) -> None:
        """Update in-memory scene source and write it to disk."""
        self.scene_source = source
        self.save_scene()

    def get_user_uniforms_source(self) -> str:
        """Return scene.glsl with non-uniform lines removed if desired.

        Currently the composer inserts the entire scene source; this helper
        exists for future per-stage extraction.
        """
        return self.scene_source


# ---------------------------------------------------------------------------
# Shader composer
# ---------------------------------------------------------------------------

class SdfShaderComposer:
    """Composes a complete fragment shader from templates + user scene."""

    def __init__(self, project: SdfProject):
        self.project = project

    def compose(self) -> str:
        """Generate the full fragment shader source."""
        project = self.project
        cfg = project.config

        parts: list[str] = []
        parts.append("#version 330 core")
        parts.append(self._load_template("common.glsl"))
        parts.append(self._load_template("camera.glsl"))
        parts.append(self._load_template("marcher.glsl"))

        # Scene contract injection
        parts.append("// ------------------------------------------------------------------")
        parts.append("// USER SCENE")
        parts.append("// ------------------------------------------------------------------")
        scene_body = _strip_leading_version(project.scene_source)
        if scene_body != project.scene_source:
            parts.append("// NOTE: removed scene-level #version directive(s) during composition")
        parts.append(scene_body)

        # Provide default hooks only for functions the scene omitted.
        parts.extend(self._detect_scene_hooks(scene_body))
        parts.append(self._load_template("scene_defaults.glsl"))

        # Integrator: preview is always included for shared helpers;
        # pathtrace is added on top when needed.
        parts.append(self._load_template("preview.glsl"))
        if cfg.integrator == "pathtrace":
            parts.append(self._load_template("pathtrace.glsl"))

        parts.append(self._load_template("display.glsl"))
        parts.append(self._load_template("generated_main.frag.template"))

        source = "\n".join(parts)
        if cfg.integrator != "pathtrace":
            source = _remove_double_buffer_blocks(source)
        return source

    @staticmethod
    def _detect_scene_hooks(scene_source: str) -> list[str]:
        """Return #define sentinels for scene hooks that exist in scene.glsl."""
        import re
        # Strip comments so commented-out function declarations do not fool us.
        code = re.sub(r"/\*.*?\*/", "", scene_source, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)
        hooks = [
            ("HAS_BASECOLOR", r"\bvec3\s+baseColor\s*\("),
            ("HAS_EMISSION", r"\bvec3\s+emissionAt\s*\("),
            ("HAS_INITSCENE", r"\bvoid\s+initScene\s*\("),
        ]
        result = []
        for macro, pattern in hooks:
            if re.search(pattern, code):
                result.append(f"#define {macro}")
        return result

    def generate(self, output_path: Path | str | None = None) -> Path:
        """Compose and write the shader to disk."""
        source = self.compose()
        if output_path is None:
            output_path = self.project.generated_frag_path
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(source)
        return output_path

    def _load_template(self, name: str) -> str:
        path = TEMPLATES_DIR / name
        if not path.exists():
            return f"// MISSING TEMPLATE: {name}\n"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_sdf_project(path: str | Path) -> bool:
    """Return True if the path points to a valid SDF project directory or file.

    Validation is intentionally strict: project.json must declare
    ``"type": "sdf_project"`` and reference a scene file that exists.
    """
    p = Path(path)
    json_path: Path | None = None
    if p.is_file() and p.name == "project.json":
        json_path = p
    elif p.is_dir() and (p / "project.json").exists():
        json_path = p / "project.json"
    if json_path is None:
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    if data.get("type") != "sdf_project":
        return False

    # The "config" wrapper is preferred; older files may store keys at top level.
    cfg = data.get("config", data)
    scene_rel = cfg.get("scene", "scene.glsl")
    scene_path = (json_path.parent / scene_rel).resolve()
    return scene_path.exists()


def load_sdf_project(path: str | Path) -> SdfProject:
    """Load an existing SDF project from a directory or project.json file."""
    p = Path(path)
    if p.is_file() and p.name == "project.json":
        project_dir = p.parent
    else:
        project_dir = p
    project = SdfProject(project_dir=project_dir).load()
    if not project.is_valid:
        raise FileNotFoundError(
            f"SDF project at {project_dir} is missing or unreadable scene file"
        )
    return project


def copy_example_project(destination: Path | str, overwrite: bool = False) -> SdfProject:
    """Copy the bundled Apollonian example to a user directory.

    Pass ``overwrite=True`` to delete an existing destination. Callers
    are expected to confirm with the user before doing so.
    """
    src = PACKAGE_DIR / "examples" / "sdf_apollonian"
    dst = Path(destination)
    if dst.exists():
        if not overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing folder without confirmation: {dst}"
            )
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return load_sdf_project(dst)
