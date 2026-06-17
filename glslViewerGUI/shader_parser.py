import re

UNIFORM_PATTERN = re.compile(
    r"\buniform\s+"
    r"(?:highp|mediump|lowp)?\s*"
    r"(?P<type>float|int|bool|sampler2D|samplerCube|vec2|vec3|vec4|ivec2|ivec3|ivec4|bvec2|bvec3|bvec4|mat2|mat3|mat4)"
    r"\s+"
    r"(?P<name>\w+)"
    r"\s*;"
)

BUILTIN_UNIFORMS = frozenset({
    # Time / frame / input
    "u_time", "u_delta", "u_frame", "u_date",
    "u_mouse", "u_resolution", "u_resolutionChange",
    "u_view2d", "u_pixelDensity", "u_play",
    "u_modelViewProjectionMatrix",
    # glslViewer camera uniforms (see glslViewer/src/core/uniforms.cpp)
    "u_camera", "u_cameraTarget", "u_cameraDistance",
    "u_cameraNearClip", "u_cameraFarClip", "u_cameraFov",
    "u_cameraEv100", "u_cameraExposure", "u_cameraAperture",
    "u_cameraShutterSpeed", "u_cameraSensitivity", "u_cameraChange",
    "u_normalMatrix",
    "u_viewMatrix", "u_inverseViewMatrix",
    "u_projectionMatrix", "u_inverseProjectionMatrix",
    "u_cameraProjectionMatrix", "u_cameraTransformMatrix", "u_cameraTex",
    "u_iblLuminance",
    # Buffers / textures (managed by renderer, not user widgets)
    "u_buffer0", "u_buffer1", "u_buffer2", "u_buffer3", "u_buffer4",
    "u_buffer5", "u_buffer6", "u_buffer7", "u_buffer8", "u_buffer9",
    "u_doubleBuffer0", "u_doubleBuffer1", "u_doubleBuffer2",
    "u_doubleBuffer3", "u_doubleBuffer4", "u_doubleBuffer5",
    "u_doubleBuffer6", "u_doubleBuffer7", "u_doubleBuffer8", "u_doubleBuffer9",
    "u_tex0", "u_tex1", "u_tex2", "u_tex3", "u_tex4",
    "u_tex5", "u_tex6", "u_tex7", "u_tex8", "u_tex9",
    # SDF renderer internal uniforms
    "u_sceneRevision",
})

def _parse_ui_attributes(text: str) -> dict:
    """Parse the tokens after `// @ui` into a key/value dict.

    The widget alias is the first bare token without an `=`. Remaining
    tokens are `key=value` pairs in any order. Values may be quoted, e.g.
    `group="My Group"`. Malformed input returns an empty dict instead
    of raising.
    """
    attrs: dict = {}
    # Tokens are bare words or key="value" pairs. We do NOT split quoted
    # values away from their key so that `group="..."` stays intact.
    tokens = re.findall(r'[^\s"]+="[^"]*"|[^\s"]+', text)
    if not tokens:
        return attrs

    # Strip the leading `@ui` sentinel if present.
    if tokens[0] == "@ui":
        tokens = tokens[1:]
    if not tokens:
        return attrs

    # The widget alias is the first token that is not a key=value pair
    # or a quoted string fragment.
    widget_index = -1
    for i, token in enumerate(tokens):
        if "=" not in token and not token.startswith('"'):
            widget_index = i
            break
    if widget_index < 0:
        return attrs

    attrs["widget"] = tokens[widget_index]
    for i, token in enumerate(tokens):
        if i == widget_index:
            continue
        m = re.match(r"(\w+)=(.+)", token)
        if not m:
            continue
        key = m.group(1)
        value = m.group(2).strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        attrs[key] = value
    return attrs


# Human-friendly metadata widget names -> internal widget ids.
WIDGET_ALIASES = {
    "slider": "float",
    "float": "float",
    "number": "float",
    "range": "float",
    "integer": "int",
    "int": "int",
    "color": "color",
    "colour": "color",
    "vec3": "vec",
    "vec4": "vec",
}

UNIFORM_DEFAULTS = {
    "float": 0.0,
    "int": 0,
    "bool": False,
    "vec2": (0.0, 0.0),
    "vec3": (0.0, 0.0, 0.0),
    "vec4": (0.0, 0.0, 0.0, 0.0),
    "ivec2": (0, 0),
    "ivec3": (0, 0, 0),
    "ivec4": (0, 0, 0, 0),
    "bvec2": (False, False),
    "bvec3": (False, False, False),
    "bvec4": (False, False, False, False),
    "mat2": (0.0, 0.0, 0.0, 0.0),
    "mat3": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "mat4": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
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


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _strip_comments(source: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    s = re.sub(r"//.*", "", s)
    return s


def _extract_comment_attributes(source: str, uniform_pos: int) -> dict:
    """Look for a `// @ui ...` comment either preceding or trailing the uniform.

    Preceding comments are preferred. The trailing `// @ui ...` form is also
    supported, e.g. ``uniform float u_x; // @ui slider min=0 max=1``.
    Malformed comments are ignored rather than crashing the parser.
    """
    attrs: dict = {}

    # Try a trailing comment first: it's the most common SDF authoring style.
    end_of_decl = source.find(";", uniform_pos)
    if end_of_decl >= 0:
        line_start = source.rfind("\n", 0, uniform_pos) + 1
        line_end = source.find("\n", end_of_decl)
        if line_end < 0:
            line_end = len(source)
        line_with_decl = source[line_start:line_end]
        inline_match = re.search(r"//\s*(@ui\b.*?)$", line_with_decl, re.MULTILINE)
        if inline_match:
            attrs = _parse_ui_attributes(inline_match.group(1))

    if attrs:
        return attrs

    # Walk backwards over adjacent comment-only lines.
    before = source[:uniform_pos]
    lines = before.splitlines(keepends=True)
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            ui_match = re.search(r"@ui\b.*", stripped)
            if ui_match:
                parsed = _parse_ui_attributes(ui_match.group(0))
                if parsed:
                    attrs = parsed
                    break
        else:
            break

    return attrs


def _parse_number(value: str | None, fallback: float | int, as_int: bool = False):
    if value is None:
        return fallback
    try:
        return int(value) if as_int else float(value)
    except ValueError:
        return fallback


def _parse_default(value: str | None, glsl_type: str):
    """Parse a default= attribute into the proper Python type."""
    if value is None:
        return None

    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    parts = [p.strip() for p in value.split(",")]

    if glsl_type == "bool":
        return value.lower() in ("1", "true", "yes", "on")
    if glsl_type in ("float", "vec2", "vec3", "vec4", "mat2", "mat3", "mat4"):
        try:
            floats = [float(p) for p in parts]
        except ValueError:
            return None
        if glsl_type == "float":
            return floats[0]
        expected = {"vec2": 2, "vec3": 3, "vec4": 4, "mat2": 4, "mat3": 9, "mat4": 16}[glsl_type]
        if len(floats) < expected:
            floats += [0.0] * (expected - len(floats))
        return tuple(floats[:expected])
    if glsl_type in ("int", "ivec2", "ivec3", "ivec4"):
        try:
            ints = [int(float(p)) for p in parts]
        except ValueError:
            return None
        if glsl_type == "int":
            return ints[0]
        expected = {"ivec2": 2, "ivec3": 3, "ivec4": 4}[glsl_type]
        if len(ints) < expected:
            ints += [0] * (expected - len(ints))
        return tuple(ints[:expected])
    return None


def parse_uniforms(source: str) -> list[dict]:
    uniforms = []
    cleaned = _strip_comments(source)

    # Use original source for position lookup so @ui comments are available.
    for cleaned_match in UNIFORM_PATTERN.finditer(cleaned):
        name = cleaned_match.group("name")
        glsl_type = cleaned_match.group("type")
        if name in BUILTIN_UNIFORMS:
            continue
        if glsl_type in ("sampler2D", "samplerCube"):
            # Texture uniforms are handled by the asset panels, not sliders.
            continue

        meta = UNIFORM_WIDGET_META.get(glsl_type)
        if meta is None:
            continue

        entry = {"name": name, "glsl_type": glsl_type, **meta}

        # Find the same declaration in the original source for metadata lookup.
        orig_match = next(
            (m for m in UNIFORM_PATTERN.finditer(source)
             if m.group("name") == name and m.group("type") == glsl_type),
            None
        )
        pos = orig_match.start() if orig_match else cleaned_match.start()
        attrs = _extract_comment_attributes(source, pos)

        if attrs.get("widget"):
            requested = attrs["widget"]
            entry["widget"] = WIDGET_ALIASES.get(requested, requested)

        is_int = glsl_type in ("int", "ivec2", "ivec3", "ivec4")

        if "min" in attrs and attrs["min"] is not None:
            entry["min"] = _parse_number(attrs["min"], entry.get("min", 0.0), as_int=is_int)
        if "max" in attrs and attrs["max"] is not None:
            entry["max"] = _parse_number(attrs["max"], entry.get("max", 1.0), as_int=is_int)
        if "step" in attrs and attrs["step"] is not None:
            entry["step"] = _parse_number(attrs["step"], entry.get("step", 0.01), as_int=is_int)
        if attrs.get("group"):
            entry["group"] = attrs["group"]
        else:
            entry["group"] = "Uniforms"

        default_override = _parse_default(attrs.get("default"), glsl_type)
        if default_override is None:
            default_override = meta["default"]
        entry["default"] = default_override

        # Value is what the widget starts with.
        entry["value"] = list(default_override) if isinstance(default_override, tuple) else default_override

        uniforms.append(entry)

    return uniforms


def build_uniform_command(name: str, value) -> str:
    if isinstance(value, list):
        parts = ",".join(str(v) for v in value)
        return f"uniform,{name},{parts}"
    return f"uniform,{name},{value}"
