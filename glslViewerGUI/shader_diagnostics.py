# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import re


def _strip_comments(source: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    s = re.sub(r"//.*", "", s)
    return s


def _extract_version(source: str) -> str | None:
    m = re.search(r"#version\s+(\d+\s+\w+)", source)
    return m.group(1) if m else None


def _extract_ins(source: str) -> set[str]:
    cleaned = _strip_comments(source)
    return {m.group("name") for m in re.finditer(
        r"\bin\s+\w+\s+(?P<name>\w+)\s*;", cleaned
    )}


def _extract_outs(source: str) -> set[str]:
    cleaned = _strip_comments(source)
    return {m.group("name") for m in re.finditer(
        r"\bout\s+\w+\s+(?P<name>\w+)\s*;", cleaned
    )}


def _extract_attribs(source: str) -> set[str]:
    cleaned = _strip_comments(source)
    names = set()
    for m in re.finditer(
        r"\b(?:layout\s*\(\s*location\s*=\s*\d+\s*\)\s+)?in\s+\w+\s+(?P<name>\w+)\s*;", cleaned
    ):
        names.add(m.group("name"))
    for m in re.finditer(r"\battribute\s+\w+\s+(?P<name>\w+)\s*;", cleaned):
        names.add(m.group("name"))
    return names


def _extract_uniforms(source: str) -> set[str]:
    cleaned = _strip_comments(source)
    return {m.group("name") for m in re.finditer(
        r"\buniform\s+\w+\s+(?P<name>\w+)\s*;", cleaned
    )}


VERA_BUILTIN_ATTRIBS = {"position", "normal", "texcoord", "color", "tangent"}
VERA_BUILTIN_UNIFORMS = {
    "u_time", "u_delta", "u_frame", "u_date",
    "u_mouse", "u_resolution", "u_resolutionChange",
    "u_view2d", "u_pixelDensity", "u_play",
    "u_modelViewProjectionMatrix",
}


def diagnose_shader_pair(frag_source: str, vert_source: str) -> list[dict]:
    diagnostics = []

    frag_ver = _extract_version(frag_source)
    vert_ver = _extract_version(vert_source)
    if frag_ver and vert_ver and frag_ver != vert_ver:
        diagnostics.append({
            "severity": "warning",
            "message": f"GLSL version mismatch: fragment has #version {frag_ver}, vertex has #version {vert_ver}",
        })

    frag_outs = _extract_outs(frag_source)
    vert_ins = _extract_ins(vert_source)

    if vert_source:
        vert_has_position = bool(re.search(r"\bgl_Position\s*=", _strip_comments(vert_source)))
        if not vert_has_position:
            diagnostics.append({
                "severity": "warning",
                "message": "Vertex shader does not write gl_Position",
            })

    frag_ins = _extract_ins(frag_source)
    vert_outs = _extract_outs(vert_source)

    for name in frag_ins:
        if name.startswith("gl_"):
            continue
        if name not in vert_outs:
            diagnostics.append({
                "severity": "warning",
                "message": f"Fragment input '{name}' has no matching vertex output",
            })

    for name in vert_outs:
        if name.startswith("gl_"):
            continue
        if name not in frag_ins:
            diagnostics.append({
                "severity": "info",
                "message": f"Vertex output '{name}' is not used by fragment shader",
            })

    vert_attribs = _extract_attribs(vert_source)
    for attrib in vert_attribs:
        if attrib.startswith("gl_"):
            continue
        if attrib not in VERA_BUILTIN_ATTRIBS and not attrib.startswith("a_"):
            diagnostics.append({
                "severity": "warning",
                "message": (
                    f"Vertex attribute '{attrib}' is not a standard vera attribute "
                    f"(expected 'a_position', 'a_normal', 'a_texcoord', etc.). "
                    f"glslViewer binds attributes by name with 'a_' prefix."
                ),
            })

    frag_uniforms = _extract_uniforms(frag_source)
    vert_uniforms = _extract_uniforms(vert_source)
    all_uniforms = frag_uniforms | vert_uniforms
    for u in all_uniforms:
        if u in VERA_BUILTIN_UNIFORMS:
            continue
        if u.startswith("u_tex") or u.startswith("u_buffer") or u.startswith("u_double"):
            continue
        if u.startswith("u_scene"):
            continue

    return diagnostics


def diagnose_single_frag(source: str) -> list[dict]:
    diagnostics = []
    ins = _extract_ins(source)
    outs = _extract_outs(source)
    attribs = _extract_attribs(source)

    if not outs and not re.search(r"\bgl_FragColor\s*=", _strip_comments(source)):
        diagnostics.append({
            "severity": "info",
            "message": "Fragment shader has no declared outputs (will use default rendering)",
        })

    for attrib in attribs:
        if attrib.startswith("gl_"):
            continue
        if attrib not in VERA_BUILTIN_ATTRIBS and not attrib.startswith("a_"):
            diagnostics.append({
                "severity": "info",
                "message": f"Fragment shader declares attribute '{attrib}' (unusual in fragment stage)",
            })

    return diagnostics
