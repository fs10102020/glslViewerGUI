# NEVER use PyQt / PyQt6 — this codebase uses PySide6 ONLY.
import re

UNIFORM_PATTERN = re.compile(
    r"\buniform\s+"
    r"(?P<type>float|int|bool|sampler2D|samplerCube|vec2|vec3|vec4|ivec2|ivec3|ivec4|bvec2|bvec3|bvec4|mat2|mat3|mat4)"
    r"\s+"
    r"(?P<name>\w+)"
    r"\s*;"
)

BUILTIN_UNIFORMS = frozenset({
    "u_time", "u_delta", "u_frame", "u_date",
    "u_mouse", "u_resolution", "u_resolutionChange",
    "u_view2d", "u_pixelDensity", "u_play",
    "u_modelViewProjectionMatrix",
})

UNIFORM_DEFAULTS = {
    "float": 0.0,
    "int": 0,
    "bool": False,
    "vec2": (0.0, 0.0),
    "vec3": (0.0, 0.0, 0.0),
    "vec4": (0.0, 0.0, 0.0, 0.0),
}

UNIFORM_WIDGET_META = {
    "float": {"widget": "float", "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    "int": {"widget": "int", "default": 0, "min": 0, "max": 100, "step": 1},
    "bool": {"widget": "bool", "default": False},
    "vec2": {"widget": "vec", "size": 2, "default": (0.0, 0.0), "min": 0.0, "max": 1.0, "step": 0.01},
    "vec3": {"widget": "vec", "size": 3, "default": (0.0, 0.0, 0.0), "min": 0.0, "max": 1.0, "step": 0.01},
    "vec4": {"widget": "vec", "size": 4, "default": (0.0, 0.0, 0.0, 0.0), "min": 0.0, "max": 1.0, "step": 0.01},
    "mat2": {"widget": "mat", "rows": 2, "cols": 2, "default": (0.0, 0.0, 0.0, 0.0), "min": -1e6, "max": 1e6, "step": 0.01},
    "mat3": {"widget": "mat", "rows": 3, "cols": 3, "default": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "min": -1e6, "max": 1e6, "step": 0.01},
    "mat4": {"widget": "mat", "rows": 4, "cols": 4, "default": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), "min": -1e6, "max": 1e6, "step": 0.01},
}

WIDGET_ALIASES: dict[str, str] = {
    "slider": "float",
    "float": "float",
    "number": "float",
    "range": "float",
    "integer": "int",
    "int": "int",
    "color": "color",
    "colour": "color",
}

_UI_TOKENS_RE = re.compile(r'(?:(\w+)(?:\s*=\s*("[^"]*"|\S+))?)')
_COMMA_LIST_RE = re.compile(r"^[\d.,\s]+$")


def _strip_comments(source: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    s = re.sub(r"//.*", "", s)
    return s


def _parse_ui_comment(line: str) -> dict | None:
    idx = line.find("// @ui")
    if idx < 0:
        return None
    comment = line[idx:]
    tokens = _UI_TOKENS_RE.findall(comment)
    meta: dict = {}
    for token, value in tokens:
        token_lower = token.lower()
        if value:
            value = value.strip('"')
        if token_lower in WIDGET_ALIASES:
            meta["widget"] = WIDGET_ALIASES[token_lower]
        elif token_lower in ("min", "max", "step", "default", "group"):
            if token_lower == "group":
                meta["group"] = value
            elif token_lower == "default":
                if _COMMA_LIST_RE.match(value):
                    parts = [float(x.strip()) for x in value.split(",") if x.strip()]
                    meta["value"] = parts if len(parts) > 1 else parts[0]
                else:
                    try:
                        meta["value"] = float(value)
                    except ValueError:
                        meta["value"] = value
            elif token_lower in ("min", "max", "step"):
                try:
                    meta[token_lower] = float(value)
                except ValueError:
                    pass
    return meta if meta else None


def parse_uniforms(source: str) -> list[dict]:
    uniforms = []
    lines = source.splitlines()
    cleaned = _strip_comments(source)

    uniform_matches = list(UNIFORM_PATTERN.finditer(cleaned))
    if not uniform_matches:
        return uniforms

    for m in uniform_matches:
        name = m.group("name")
        glsl_type = m.group("type")
        if name in BUILTIN_UNIFORMS:
            continue
        base = UNIFORM_WIDGET_META.get(glsl_type)
        if base is None:
            continue
        entry = {**base}
        entry["name"] = name
        entry["glsl_type"] = glsl_type
        default_val = base["default"]
        entry["value"] = list(default_val) if isinstance(default_val, tuple) else default_val

        ui_meta = _find_ui_for_uniform(lines, name)
        if ui_meta:
            if "widget" in ui_meta:
                entry["widget"] = ui_meta["widget"]
            if "group" in ui_meta:
                entry["group"] = ui_meta["group"]
            if "min" in ui_meta:
                entry["min"] = ui_meta["min"]
            if "max" in ui_meta:
                entry["max"] = ui_meta["max"]
            if "step" in ui_meta:
                entry["step"] = ui_meta["step"]
            if "value" in ui_meta:
                entry["value"] = ui_meta["value"]

        uniforms.append(entry)
    return uniforms


def _find_ui_for_uniform(lines: list[str], target_name: str) -> dict | None:
    name_escaped = re.escape(target_name)
    uniform_re = re.compile(rf"\buniform\s+\w+\s+{name_escaped}\s*;")
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if uniform_re.search(stripped):
            meta = _parse_ui_comment(stripped)
            if meta:
                return meta
            if i > 0 and "// @ui" in lines[i - 1]:
                meta = _parse_ui_comment(lines[i - 1])
                if meta:
                    return meta
            break
    return None
