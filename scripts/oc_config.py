"""Config loading for outreach-conductor scripts. Standard library only.

Uses PyYAML when it is installed. Otherwise falls back to a small reader that handles the
YAML subset used in config.example.yaml: nested maps, lists of scalars, lists of maps,
inline [a, b] lists, {} and [] literals, quoted strings, numbers, booleans and comments.
Block scalars (| and >) are not supported by the fallback; quote long text on one line.

Config path: --config, else $OUTREACH_CONDUCTOR_CONFIG, else config.yaml next to the skill.
"""
import os
import re

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _strip_comment(line):
    out, q = [], None
    for i, ch in enumerate(line):
        if q:
            if ch == "\\" and q == '"':
                out.append(ch)
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _split_flow(s):
    parts, cur, q = [], [], None
    for ch in s:
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _scalar(s):
    s = s.strip()
    if s == "":
        return None
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return re.sub(r'\\(["\\n])', lambda m: {"n": "\n"}.get(m.group(1), m.group(1)), s[1:-1])
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if s == "{}":
        return {}
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(x) for x in _split_flow(s[1:-1])]
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    for cast in (int, float):
        try:
            return cast(s)
        except ValueError:
            pass
    return s


_KEY = re.compile(r"^(\"[^\"]*\"|'[^']*'|[A-Za-z0-9_.-]+)\s*:(\s|$)")


def _parse(lines, i, indent):
    if lines[i][1] == "-" or lines[i][1].startswith("- "):
        out = []
        while i < len(lines) and lines[i][0] == indent and (lines[i][1] == "-" or lines[i][1].startswith("- ")):
            text = lines[i][1]
            rest = text[1:].strip()
            if not rest:
                i += 1
                if i < len(lines) and lines[i][0] > indent:
                    v, i = _parse(lines, i, lines[i][0])
                else:
                    v = None
                out.append(v)
            elif _KEY.match(rest):
                off = len(text) - len(text[1:].lstrip())
                lines[i] = (indent + off, rest)
                v, i = _parse(lines, i, indent + off)
                out.append(v)
            else:
                out.append(_scalar(rest))
                i += 1
        return out, i
    out = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        m = _KEY.match(lines[i][1])
        if not m:
            raise ValueError(f"config: cannot read line: {lines[i][1]!r}")
        key = m.group(1).strip("\"'")
        val = lines[i][1][m.end():].strip()
        i += 1
        if val in ("|", ">", "|-", ">-"):
            raise ValueError(f"config: block scalars are not supported without PyYAML (key {key!r}); quote the text on one line")
        if val == "":
            if i < len(lines) and lines[i][0] > indent:
                v, i = _parse(lines, i, lines[i][0])
            elif i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                v, i = _parse(lines, i, indent)
            else:
                v = None
        else:
            v = _scalar(val)
        out[key] = v
    return out, i


def parse_yaml(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_comment(raw.replace("\t", "  "))
        if not line.strip():
            continue
        lines.append((len(line) - len(line.lstrip()), line.strip()))
    if not lines:
        return {}
    v, _ = _parse(lines, 0, lines[0][0])
    return v


def config_path(explicit=None):
    return explicit or os.environ.get("OUTREACH_CONDUCTOR_CONFIG") or os.path.join(SKILL_DIR, "config.yaml")


def load_config(explicit=None):
    p = config_path(explicit)
    if not os.path.exists(p):
        raise SystemExit(f"no config at {p}. Copy config.example.yaml to config.yaml and fill it in, "
                         "or set OUTREACH_CONDUCTOR_CONFIG.")
    text = open(p, encoding="utf-8").read()
    try:
        import yaml  # optional
        cfg = yaml.safe_load(text) or {}
    except ImportError:
        cfg = parse_yaml(text)
    cfg["_path"] = os.path.abspath(p)
    cfg["_dir"] = os.path.dirname(os.path.abspath(p))
    return cfg


def resolve(cfg, rel):
    """A config path, made absolute relative to the config file."""
    if not rel:
        return ""
    rel = os.path.expanduser(str(rel))
    return rel if os.path.isabs(rel) else os.path.join(cfg["_dir"], rel)


def state_root(cfg):
    return os.environ.get("OUTREACH_STATE_DIR") or resolve(cfg, cfg.get("state_dir") or "state")


def get(cfg, dotted, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return default
        cur = cur[part]
    return cur
