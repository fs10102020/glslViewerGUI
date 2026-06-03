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

USER_ATTR_PATTERN = re.compile(
    r"@uniform\s+(?P<name>\w+)\s*"
    r"(?P<min>[-\d.]+)?\s*"
    r"(?P<max>[-\d.]+)?\s*"
    r"(?P<step>[-\d.]+)?",
)

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


def _strip_comments(source: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    s = re.sub(r"//.*", "", s)
    return s


def parse_uniforms(source: str) -> list[dict]:
    uniforms = []
    cleaned = _strip_comments(source)
    for m in UNIFORM_PATTERN.finditer(cleaned):
        name = m.group("name")
        glsl_type = m.group("type")
        if name in BUILTIN_UNIFORMS:
            continue
        meta = UNIFORM_WIDGET_META.get(glsl_type)
        if meta is None:
            continue
        entry = {"name": name, "glsl_type": glsl_type, **meta}
        default_val = meta["default"]
        entry["value"] = list(default_val) if isinstance(default_val, tuple) else default_val
        uniforms.append(entry)
    return uniforms


def build_uniform_command(name: str, value) -> str:
    if isinstance(value, list):
        parts = ",".join(str(v) for v in value)
        return f"uniform,{name},{parts}"
    return f"uniform,{name},{value}"
