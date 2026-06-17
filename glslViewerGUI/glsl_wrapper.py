import hashlib
from pathlib import Path

from glslViewer_config import CONFIG_DIR


def is_backend_shader_path(path: str | None) -> bool:
    if not path:
        return False
    return Path(path).suffix.lower() in {".frag", ".fs", ".vert", ".vs"}


def write_glsl_wrapper(source_path: str, stage: str) -> str:
    """Copy a .glsl source to a backend-recognized .frag/.vert path."""
    src = Path(source_path)
    suffix = ".vert" if stage == "vertex" else ".frag"
    digest = hashlib.sha1(str(src.resolve()).encode("utf-8")).hexdigest()[:12]
    out_dir = Path(CONFIG_DIR) / "generated" / "glsl_wrappers"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}_{digest}{suffix}"
    text = src.read_text(encoding="utf-8", errors="replace")
    out_path.write_text(text, encoding="utf-8")
    return str(out_path)
