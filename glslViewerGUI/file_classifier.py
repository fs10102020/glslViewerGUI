# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
"""Centralized classification of arbitrary files passed to the GUI.

This module takes a list of file or directory paths and decides what each
of them is, returning a `LoadPlan` that the main window can act on. The
intent is to be the single entry point for all "load this" calls so that
"load any arbitrary shader" goes through one predictable path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from session_config import (
    ASSET_NAMED_TEXTURE,
    ASSET_STREAM_TEXTURE,
    ASSET_CUBEMAP_SHOW,
    ASSET_CUBEMAP_ENV,
    ASSET_MODEL,
    ASSET_SEQUENCE_UNIFORM,
    ASSET_CAMERA_SEQUENCE,
)
from sdf_project import is_sdf_project


# ---------------------------------------------------------------------------
# Extension and content categories
# ---------------------------------------------------------------------------

FRAG_EXTS = (".frag", ".fs")
VERT_EXTS = (".vert", ".vs")
GEOM_EXTS = ()
GLSL_EXTS = (".glsl",)

MESH_EXTS = (".ply", ".obj", ".stl", ".glb", ".gltf", ".splat")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tga", ".psd", ".gif", ".bmp", ".hdr", ".exr")
VIDEO_EXTS = (".mov", ".mp4", ".mkv", ".mpg", ".mpeg", ".h264")
CSV_EXTS = (".csv",)


class AssetKind(str, Enum):
    SDF_PROJECT = "sdf_project"
    SDF_SCENE = "sdf_scene"
    FRAGMENT_SHADER = "fragment_shader"
    VERTEX_SHADER = "vertex_shader"
    GENERIC_GLSL = "generic_glsl"
    SHADERTOY_LIKE = "shadertoy_like"
    MESH = "mesh"
    CUBEMAP = "cubemap"
    TEXTURE = "texture"
    VIDEO_STREAM = "video_stream"
    UNIFORM_CSV = "uniform_csv"
    CAMERA_CSV = "camera_csv"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedItem:
    """One classified path with the data needed to load it."""

    path: Path
    kind: AssetKind
    confidence: float = 1.0
    reason: str = ""
    is_sdf_scene_candidate: bool = False
    has_main: bool = False
    stage_hint: Optional[str] = None


@dataclass
class LoadPlan:
    """Result of classifying one or more paths.

    All path lists store raw strings (never :class:`Path` objects) so that
    stream-like values such as ``https://`` URLs, ``/dev/video0`` capture
    devices, and wildcard sequences survive the classification round-trip
    without being normalized by :class:`pathlib.Path` (which collapses
    consecutive ``/`` to a single ``/`` and would corrupt URLs).
    """

    items: list[ClassifiedItem] = field(default_factory=list)
    sdf_project: Optional[str] = None
    project_config_path: Optional[str] = None
    sdf_scene: Optional[str] = None
    frag_path: Optional[str] = None
    vert_path: Optional[str] = None
    geom_path: Optional[str] = None
    mesh_paths: list[str] = field(default_factory=list)
    texture_paths: list[str] = field(default_factory=list)
    video_paths: list[str] = field(default_factory=list)
    csv_paths: list[str] = field(default_factory=list)
    cubemap_paths: list[str] = field(default_factory=list)
    shadertoy_candidates: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_anything(self) -> bool:
        return any([
            self.sdf_project, self.frag_path, self.vert_path, self.geom_path,
            self.sdf_scene, self.mesh_paths, self.texture_paths,
            self.video_paths, self.csv_paths, self.cubemap_paths,
        ])

    @property
    def is_sdf_mode(self) -> bool:
        return self.sdf_project is not None

    @property
    def primary_shader(self) -> Optional[Path]:
        return self.sdf_scene or self.frag_path


# ---------------------------------------------------------------------------
# Content sniffing helpers
# ---------------------------------------------------------------------------

_RE_HAS_DE = re.compile(r"\bfloat\s+DE\s*\(\s*vec3\s+\w+\s*\)")
_RE_HAS_BASECOLOR = re.compile(r"\bvec3\s+baseColor\s*\(")
_RE_HAS_EMISSION = re.compile(r"\bvec3\s+emissionAt\s*\(")
_RE_HAS_INITSCENE = re.compile(r"\bvoid\s+initScene\s*\(")
_RE_HAS_VOID_MAIN = re.compile(r"\bvoid\s+main\s*\(")
_RE_HAS_MAIN_IMAGE = re.compile(r"\bvoid\s+mainImage\s*\(")
_RE_HAS_FRAG_COLOR = re.compile(r"\bgl_FragColor\b|fragColor\b")
_RE_HAS_GL_POSITION = re.compile(r"\bgl_Position\b")
_RE_HAS_STAGE = re.compile(r"#pragma\s+stage\s+(\w+)")
_RE_SHADERTOY_UNIFORMS = re.compile(
    r"\b(iTime|iResolution|iMouse|iFrame|iDate|iSampleRate|iChannel[0-9])\b"
)


def _quick_sniff(path: Path) -> dict:
    """Read a slice of a file to support content-based classification."""
    if path.is_dir():
        return {"is_dir": True}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(64_000)
    except (OSError, UnicodeDecodeError, IsADirectoryError):
        return {"readable": False}
    return {
        "text": text,
        "has_de": bool(_RE_HAS_DE.search(text)),
        "has_basecolor": bool(_RE_HAS_BASECOLOR.search(text)),
        "has_emission": bool(_RE_HAS_EMISSION.search(text)),
        "has_initscene": bool(_RE_HAS_INITSCENE.search(text)),
        "has_main": bool(_RE_HAS_VOID_MAIN.search(text)),
        "has_main_image": bool(_RE_HAS_MAIN_IMAGE.search(text)),
        "has_frag_color": bool(_RE_HAS_FRAG_COLOR.search(text)),
        "has_gl_position": bool(_RE_HAS_GL_POSITION.search(text)),
        "has_shadertoy_uniforms": bool(_RE_SHADERTOY_UNIFORMS.search(text)),
        "stage_hint": ((m.group(1).lower())
                        if (m := _RE_HAS_STAGE.search(text)) else None),
    }


def _looks_like_stream(path: str) -> bool:
    lower = path.lower()
    return (
        lower.startswith(("http://", "https://", "rtsp://", "rtmp://", "/dev/"))
        or "*" in lower
        or lower.startswith("http:/")  # Path() collapses // to /
        or lower.startswith("https:/")
        or lower.startswith("rtsp:/")
        or lower.startswith("rtmp:/")
    )


def _classify_single(p: Path, *, force_stage: str | None = None) -> ClassifiedItem:
    """Classify a single path, falling back to content heuristics when needed."""
    suffix = p.suffix.lower()
    raw = str(p)

    if p.is_dir():
        if is_sdf_project(p):
            return ClassifiedItem(
                path=p,
                kind=AssetKind.SDF_PROJECT,
                confidence=1.0,
                reason="project.json + scene.glsl",
            )
        # Non-SDF directories can be treated as streaming image sequences by glslViewer
        # when used as a custom uniform asset. We leave that decision to the caller.
        return ClassifiedItem(
            path=p,
            kind=AssetKind.UNKNOWN,
            confidence=0.0,
            reason="directory without a valid SDF project.json",
        )

    if p.is_file() and p.name == "project.json":
        if is_sdf_project(p):
            return ClassifiedItem(
                path=p,
                kind=AssetKind.SDF_PROJECT,
                confidence=1.0,
                reason="project.json + scene.glsl",
            )
        return ClassifiedItem(
            path=p,
            kind=AssetKind.UNKNOWN,
            confidence=0.0,
            reason="invalid project.json",
        )

    if not p.exists():
        if _looks_like_stream(raw):
            return ClassifiedItem(
                path=p,
                kind=AssetKind.VIDEO_STREAM,
                confidence=0.8,
                reason="URL or stream-like path",
            )
        return ClassifiedItem(
            path=p,
            kind=AssetKind.UNKNOWN,
            confidence=0.0,
            reason="path does not exist",
        )

    # Stream-like paths (URLs, /dev/*, wildcards) may have arbitrary extensions or
    # none at all; check before extension-based dispatch.
    if _looks_like_stream(raw):
        return ClassifiedItem(
            path=p, kind=AssetKind.VIDEO_STREAM, confidence=0.8,
            reason="URL or stream-like path",
        )

    if suffix in FRAG_EXTS:
        return ClassifiedItem(
            path=p, kind=AssetKind.FRAGMENT_SHADER,
            confidence=1.0, reason=f"extension {suffix}",
            stage_hint="fragment",
        )
    if suffix in VERT_EXTS:
        return ClassifiedItem(
            path=p, kind=AssetKind.VERTEX_SHADER,
            confidence=1.0, reason=f"extension {suffix}",
            stage_hint="vertex",
        )
    if suffix in MESH_EXTS:
        return ClassifiedItem(
            path=p, kind=AssetKind.MESH, confidence=1.0,
            reason=f"extension {suffix}",
        )
    if suffix in (".hdr",):
        return ClassifiedItem(
            path=p, kind=AssetKind.CUBEMAP, confidence=0.9,
            reason=f"extension {suffix}",
        )
    if suffix in IMAGE_EXTS:
        if suffix in (".hdr", ".exr"):
            return ClassifiedItem(
                path=p, kind=AssetKind.CUBEMAP, confidence=0.7,
                reason=f"{suffix} environment candidate",
            )
        return ClassifiedItem(
            path=p, kind=AssetKind.TEXTURE, confidence=1.0,
            reason=f"extension {suffix}",
        )
    if suffix in VIDEO_EXTS:
        return ClassifiedItem(
            path=p, kind=AssetKind.VIDEO_STREAM, confidence=1.0,
            reason=f"extension {suffix}",
        )
    if suffix in CSV_EXTS:
        return ClassifiedItem(
            path=p, kind=AssetKind.UNIFORM_CSV, confidence=0.6,
            reason=f"extension {suffix}",
        )

    if suffix in GLSL_EXTS:
        # If a menu action explicitly requested a stage, force that interpretation
        # for .glsl files even before content sniffing.
        if force_stage == "fragment":
            return ClassifiedItem(
                path=p, kind=AssetKind.FRAGMENT_SHADER, confidence=0.95,
                reason="forced fragment stage by menu",
                stage_hint="fragment",
            )
        if force_stage == "vertex":
            return ClassifiedItem(
                path=p, kind=AssetKind.VERTEX_SHADER, confidence=0.95,
                reason="forced vertex stage by menu",
                stage_hint="vertex",
            )

        info = _quick_sniff(p)
        if not info.get("readable", True):
            return ClassifiedItem(
                path=p, kind=AssetKind.GENERIC_GLSL, confidence=0.0,
                reason="unreadable file",
            )
        info.setdefault("text", "")
        info.setdefault("has_de", False)
        info.setdefault("has_main", False)
        info.setdefault("has_main_image", False)
        info.setdefault("has_frag_color", False)
        info.setdefault("has_gl_position", False)
        info.setdefault("has_shadertoy_uniforms", False)
        stage = info.get("stage_hint")

        # Explicit stage hints take priority.
        if stage == "fragment":
            return ClassifiedItem(
                path=p, kind=AssetKind.FRAGMENT_SHADER, confidence=0.95,
                reason="#pragma stage fragment",
                stage_hint="fragment",
                has_main=info["has_main"],
            )

        if stage == "vertex" or info["has_gl_position"]:
            return ClassifiedItem(
                path=p, kind=AssetKind.VERTEX_SHADER, confidence=0.85,
                reason="vertex stage hint or gl_Position found",
                stage_hint="vertex",
                has_main=info["has_main"],
            )

        if info["has_de"] and not info["has_main"]:
            return ClassifiedItem(
                path=p, kind=AssetKind.SDF_SCENE, confidence=0.95,
                reason="float DE(vec3) without main()",
                is_sdf_scene_candidate=True,
                has_main=False,
            )

        if info["has_frag_color"] and not info["has_gl_position"]:
            return ClassifiedItem(
                path=p, kind=AssetKind.FRAGMENT_SHADER, confidence=0.9,
                reason="fragColor output",
                stage_hint="fragment",
                has_main=info["has_main"],
            )

        if info["has_main_image"] or info["has_shadertoy_uniforms"]:
            return ClassifiedItem(
                path=p, kind=AssetKind.SHADERTOY_LIKE, confidence=0.9,
                reason="mainImage or Shadertoy uniforms",
                stage_hint="fragment",
                has_main=info["has_main_image"] or info["has_main"],
            )

        if info["has_main"]:
            return ClassifiedItem(
                path=p, kind=AssetKind.GENERIC_GLSL, confidence=0.7,
                reason="has main()",
                has_main=True,
            )

        return ClassifiedItem(
            path=p, kind=AssetKind.GENERIC_GLSL, confidence=0.4,
            reason=".glsl with no stage hints",
        )

    return ClassifiedItem(
        path=p, kind=AssetKind.UNKNOWN, confidence=0.0,
        reason=f"unrecognized extension {suffix!r}",
    )


def classify_paths(paths: Iterable[str | Path], *, force_stage: str | None = None) -> LoadPlan:
    """Classify a list of paths and produce a load plan.

    Pair detection (e.g. matching `<name>.frag` with `<name>.vert`) is
    handled automatically; everything else is forwarded as-is.

    Stream-like inputs (URLs, ``/dev/*`` paths, wildcards) are stored as the
    raw original string so that the round-trip to :class:`pathlib.Path`
    does not corrupt them.
    """
    plan = LoadPlan()
    for raw in paths:
        if raw is None:
            continue
        raw_str = str(raw)
        p = Path(raw_str)
        item = _classify_single(p, force_stage=force_stage)
        plan.items.append(item)

        if item.kind == AssetKind.SDF_PROJECT:
            if plan.sdf_project is not None and plan.sdf_project != raw_str:
                plan.warnings.append(
                    f"Multiple SDF projects provided; using {plan.sdf_project}, ignored {raw_str}"
                )
            else:
                plan.sdf_project = raw_str
                plan.project_config_path = (
                    raw_str if p.name == "project.json" else str(p / "project.json")
                )

        elif item.kind == AssetKind.SDF_SCENE:
            if plan.sdf_scene is not None and plan.sdf_scene != raw_str:
                plan.warnings.append(
                    f"Multiple SDF scenes provided; using {plan.sdf_scene}, ignored {raw_str}"
                )
            else:
                plan.sdf_scene = raw_str
                if is_sdf_project(p.parent):
                    plan.sdf_project = str(p.parent)
                    plan.project_config_path = str(p.parent / "project.json")

        elif item.kind == AssetKind.FRAGMENT_SHADER:
            if plan.frag_path is None:
                plan.frag_path = raw_str
            else:
                plan.warnings.append(
                    f"Multiple fragment shaders; using {plan.frag_path}, ignored {raw_str}"
                )

        elif item.kind == AssetKind.VERTEX_SHADER:
            if plan.vert_path is None:
                plan.vert_path = raw_str

        elif item.kind == AssetKind.MESH:
            plan.mesh_paths.append(raw_str)

        elif item.kind == AssetKind.CUBEMAP:
            plan.cubemap_paths.append(raw_str)

        elif item.kind == AssetKind.TEXTURE:
            plan.texture_paths.append(raw_str)

        elif item.kind == AssetKind.VIDEO_STREAM:
            plan.video_paths.append(raw_str)

        elif item.kind == AssetKind.UNIFORM_CSV:
            if p.stem.lower().startswith("camera"):
                item.kind = AssetKind.CAMERA_CSV
            plan.csv_paths.append(raw_str)

        elif item.kind == AssetKind.UNKNOWN and p.is_dir():
            # Non-SDF directories may be streaming image sequences.
            plan.video_paths.append(raw_str)

        elif item.kind == AssetKind.SHADERTOY_LIKE:
            plan.shadertoy_candidates.append(raw_str)
            if plan.frag_path is None:
                plan.frag_path = raw_str
                item.reason += " (used as fragment)"

        elif item.kind == AssetKind.GENERIC_GLSL:
            if plan.frag_path is None:
                plan.frag_path = raw_str
                if item.confidence < 0.9:
                    plan.warnings.append(
                        f"Treating {p.name} as a fragment shader (confidence: {item.confidence})"
                    )
            else:
                plan.warnings.append(
                    f"Multiple fragment shaders; using {plan.frag_path}, ignored {raw_str}"
                )

        elif item.kind == AssetKind.UNKNOWN:
            plan.unknown.append(raw_str)

    if plan.frag_path and plan.vert_path is None:
        candidate = _find_sibling(plan.frag_path, VERT_EXTS)
        if candidate:
            plan.vert_path = str(candidate)
            plan.warnings.append(
                f"Auto-paired {Path(candidate).name} as vertex shader"
            )
    if plan.vert_path and plan.frag_path is None:
        candidate = _find_sibling(plan.vert_path, FRAG_EXTS)
        if candidate:
            plan.frag_path = str(candidate)
            plan.warnings.append(
                f"Auto-paired {Path(candidate).name} as fragment shader"
            )

    return plan


def _find_sibling(path: str | Path, exts: Iterable[str]) -> Optional[Path]:
    p = Path(path)
    base = p.with_suffix("")
    for ext in exts:
        candidate = base.with_suffix(ext)
        if candidate != p and candidate.is_file():
            return candidate
    return None


def _safe_uniform_name(name: str, fallback: str, used: set[str]) -> str:
    name = re.sub(r"\W+", "_", name).strip("_") or fallback
    if not re.match(r"^[A-Za-z_]", name):
        name = f"u_{name}"
    if name not in used:
        used.add(name)
        return name
    stem = re.sub(r"\d+$", "", name) or name
    index = 1
    while f"{stem}{index}" in used:
        index += 1
    result = f"{stem}{index}"
    used.add(result)
    return result


def build_session_from_plan(plan, base_session=None):
    """Convert a LoadPlan into session-config updates.

    The caller is responsible for actually starting the process; this only
    mutates the relevant fields. Pass an existing RenderSessionConfig as
    ``base_session`` to preserve window options, defines, etc.
    """
    from session_config import AssetSpec, RenderSessionConfig  # local

    if base_session is None:
        base_session = RenderSessionConfig()

    if plan.frag_path is not None:
        base_session.frag_path = plan.frag_path
    if plan.vert_path is not None:
        base_session.vert_path = plan.vert_path
    if plan.geom_path is not None:
        base_session.geom_path = plan.geom_path
    elif plan.mesh_paths:
        base_session.geom_path = plan.mesh_paths[0]

    base_session.assets = list(base_session.assets)

    for mesh in plan.mesh_paths[1:]:
        base_session.assets.append(
            AssetSpec(kind=ASSET_MODEL, name="", path=mesh)
        )

    used_names = {a.name for a in base_session.assets if a.name}

    for i, tex in enumerate(plan.texture_paths):
        base_session.assets.append(
            AssetSpec(kind=ASSET_NAMED_TEXTURE, name=_safe_uniform_name(f"u_tex{i}", "u_tex0", used_names), path=tex)
        )

    for i, vid in enumerate(plan.video_paths):
        base_session.assets.append(
            AssetSpec(
                kind=ASSET_STREAM_TEXTURE,
                name=_safe_uniform_name(f"u_texStream{i}", "u_texStream0", used_names),
                path=vid,
            )
        )

    for cubemap in plan.cubemap_paths:
        base_session.assets.append(
            AssetSpec(kind=ASSET_CUBEMAP_ENV, name="", path=cubemap)
        )

    for csv in plan.csv_paths:
        stem = Path(csv).stem.lower()
        if stem.startswith("camera"):
            base_session.assets.append(
                AssetSpec(kind=ASSET_CAMERA_SEQUENCE, name="", path=csv)
            )
        else:
            raw_name = _safe_uniform_name(stem, "u_values0", used_names)
            if not raw_name.startswith("u_"):
                raw_name = f"u_{raw_name}"
            base_session.assets.append(
                AssetSpec(kind=ASSET_SEQUENCE_UNIFORM, name=raw_name, path=csv)
            )

    return base_session
