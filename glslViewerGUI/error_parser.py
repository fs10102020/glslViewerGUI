import re

# Apple M1:  ERROR: 0:41: 'color' : syntax error
_APPLE_RE = re.compile(r"ERROR:\s*\d+:(\d+):")

# Mesa / Linux ARM:  0:41(2): error: syntax error...
_MESA_RE = re.compile(r"\d+:(\d+)\(\d+\):\s*error")

# NVIDIA:  0(41) : error C0000: syntax error...
_NVIDIA_RE = re.compile(r"\d+\((\d+)\)\s*:\s*error")


def parse_errors(text: str) -> list[dict]:
    errors = []
    for line in text.splitlines():
        m = _APPLE_RE.search(line)
        if m:
            errors.append({"line": int(m.group(1)), "message": line.strip()})
            continue
        m = _MESA_RE.search(line)
        if m:
            errors.append({"line": int(m.group(1)), "message": line.strip()})
            continue
        m = _NVIDIA_RE.search(line)
        if m:
            errors.append({"line": int(m.group(1)), "message": line.strip()})
            continue
    return errors
