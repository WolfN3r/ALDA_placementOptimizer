"""
SPICE netlist reader for PDK-primitive netlists (e.g. sky130 from xschem):
devices are X- or M-instances whose model is in a given primitive set,
parameters are SPICE expressions ({...} or '...') over .param values, subckt
defaults, instance overrides and an external parameter dict (an optimizer's
result.json).

parse_netlist(path, primitives, params) -> (top_ports, devices, hierarchy_map)
eval_expr(text, env)                    -> float
"""
from __future__ import annotations

import ast
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

_SUFFIX = {"meg": 1e6, "t": 1e12, "g": 1e9, "k": 1e3, "m": 1e-3,
           "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
_NUM_SUFFIX_RE = re.compile(r"(?<![\w.])((?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf])(?!\w)",
                            re.IGNORECASE)
_MAX_DEPTH = 20     # .param reference chain length before it counts as a cycle


def _nint(x: float) -> float:
    """ngspice nint: nearest integer, halves away from zero."""
    return math.copysign(math.floor(abs(x) + 0.5), x)


_FUNCS = {"nint": _nint, "int": math.trunc, "abs": abs, "sqrt": math.sqrt, "min": min,
          "max": max, "pow": pow, "exp": math.exp, "log": math.log, "ln": math.log,
          "log10": math.log10, "floor": math.floor, "ceil": math.ceil}
_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
           ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b}

logger = get_logger(__name__, DEBUG)

# =============================================================================
# ALGORITHM
# =============================================================================

# --- Expressions ----------------------------------------------------------------

def eval_expr(text, env: dict, _depth: int = 0) -> float:
    """Value of a SPICE number or expression. Names are case-insensitive;
    an env value may itself be an expression string (.param chains)."""
    if isinstance(text, (int, float)):
        return float(text)
    if _depth > _MAX_DEPTH:
        raise ValueError(f"parameter chain too deep (cycle?): {text}")
    src = str(text).strip().replace("{", "").replace("}", "").replace("'", "").replace("^", "**")
    src = _NUM_SUFFIX_RE.sub(lambda m: repr(float(m.group(1)) * _SUFFIX[m.group(2).lower()]), src)
    low = {k.lower(): v for k, v in env.items()}

    def walk(n):
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            key = n.id.lower()
            if key not in low:
                raise KeyError(f"unresolved parameter {n.id!r}")
            return eval_expr(low[key], env, _depth + 1)
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            return _BINOPS[type(n.op)](walk(n.left), walk(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = walk(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id.lower() in _FUNCS:
            return float(_FUNCS[n.func.id.lower()](*(walk(a) for a in n.args)))
        raise ValueError(f"unsupported expression element in {text!r}")

    return walk(ast.parse(src, mode="eval"))


# --- Lines and tokens ----------------------------------------------------------

def _tokens(line: str) -> list:
    """Split on whitespace outside '...' and {...}; '$' or ';' outside them
    starts a comment."""
    out, cur, depth, quoted = [], "", 0, False
    for ch in line:
        if ch == "'":
            quoted = not quoted
        elif not quoted and ch == "{":
            depth += 1
        elif not quoted and ch == "}":
            depth -= 1
        elif not quoted and depth == 0:
            if ch in "$;":
                break
            if ch.isspace():
                if cur:
                    out.append(cur)
                cur = ""
                continue
        cur += ch
    if cur:
        out.append(cur)
    return out


def _logical_lines(path: Path) -> list:
    lines: list = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("*"):
            continue
        if s.startswith("+") and lines:
            lines[-1] += " " + s[1:].strip()
        else:
            lines.append(s)
    return lines


def _kv(tokens: list) -> dict:
    return {k.lower(): v for k, v in (t.split("=", 1) for t in tokens if "=" in t)}


# --- Netlist ---------------------------------------------------------------------

def _read_subckts(lines: list) -> tuple:
    """{name: (ports, defaults, local_params, body)}, global .params."""
    subckts: dict = {}
    global_params: dict = {}
    cur = None
    for line in lines:
        tok = _tokens(line)
        if not tok:
            continue
        head = tok[0].lower()
        if head == ".subckt":
            cur = (tok[1].lower(), [t.lower() for t in tok[2:] if "=" not in t], _kv(tok[2:]), {}, [])
        elif head == ".ends":
            if cur:
                subckts[cur[0]] = cur[1:]
            cur = None
        elif head == ".param":
            (cur[3] if cur else global_params).update(_kv(tok[1:]))
        elif cur and not head.startswith("."):
            cur[4].append(tok)
    return subckts, global_params


def _expand(body, scope, port_map, prefix, hier_m, subckt, ctx) -> None:
    subckts, primitives, devices, hier, globals_, unknown = ctx
    for tok in body:
        inst = tok[0].lower()
        if inst[0] not in "xm":
            unknown.append(f"{tok[0]} in {subckt}: only X/M instances of PDK models are placeable")
            continue
        pos = [t for t in tok[1:] if "=" not in t]
        if not pos:
            unknown.append(f"{tok[0]} in {subckt}: no model name")
            continue
        model, nets = pos[-1].lower(), pos[:-1]
        nets = [port_map.get(n.lower(), f"{prefix}{n.lower()}") for n in nets]
        kv = _kv(tok[1:])
        name = f"{prefix}{inst}"
        if model in primitives:
            values = {}
            for k, v in kv.items():
                try:
                    values[k] = eval_expr(v, scope)
                except (KeyError, ValueError, SyntaxError, ZeroDivisionError, TypeError):
                    values[k] = None
            devices.append({"inst": name, "model": model, "nets": nets,
                            "values": values, "hier_m": hier_m})
            hier[name] = subckt
        elif model in subckts:
            ports, defaults, local, child_body = subckts[model]
            if len(nets) != len(ports):
                logger.warning("Port mismatch expanding %s as %s (%d/%d)", model, name, len(nets), len(ports))
            child = {**globals_, **defaults, **local}
            m = 1.0
            for k, v in kv.items():
                val = eval_expr(v, scope)
                if k == "m":
                    m = val
                else:
                    child[k] = val
            _expand(child_body, child, dict(zip(ports, nets)), f"{name}.", hier_m * m, model, ctx)
        else:
            unknown.append(f"{tok[0]} in {subckt}: model {model} is neither in the PDK nor a .subckt")


def parse_netlist(path, primitives: set, params: dict) -> tuple:
    """Flatten the last .subckt of `path`. primitives = lowercase model names
    that are devices; params = external values, they override the netlist's
    global .param of the same name.

    Returns (top_ports, devices, hierarchy_map). Each device:
    {"inst", "model", "nets" (positional, top-level names), "values"
    (lowercase key -> float, None if unresolvable), "hier_m" (product of the
    enclosing subckt instances' m=)}. Raises ValueError listing every
    instance that is not an X/M instance of a primitive or a .subckt."""
    path = Path(path)
    subckts, netlist_params = _read_subckts(_logical_lines(path))
    if not subckts:
        raise ValueError(f"No .subckt in {path}")
    top = list(subckts)[-1]
    ports, defaults, local, body = subckts[top]
    globals_ = {**netlist_params, **params}
    scope = {**globals_, **defaults, **local}
    devices: list = []
    hier: dict = {}
    unknown: list = []
    _expand(body, scope, {}, "", 1.0, top, (subckts, primitives, devices, hier, globals_, unknown))
    if unknown:
        msg = f"{path.name}: {len(unknown)} unplaceable instance(s):\n  " + "\n  ".join(unknown)
        logger.error(msg)
        raise ValueError(msg)
    logger.info("Parsed %s: top %s, %d devices", path.name, top, len(devices))
    return ports, devices, hier
