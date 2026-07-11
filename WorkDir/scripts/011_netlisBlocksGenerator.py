#!/usr/bin/env python3
"""
Read a SPICE (.sp) netlist, flatten hierarchy, resolve real W/L/M/Nf sizes
from the netlist's own .param cascade for every device, detect symmetry
groups from circuit topology, and emit the same JSON schema as
001_L1blocksGenerator.

Standalone:  python 011_netlisBlocksGenerator.py <netlist.sp> <seed>
             Returns JSON on stdout  (intended for debugging only)
Pipeline:    called via run(netlist_path, seed) from main.py
Output file: s{seed}_n{N}_py011_v01.json  (written by main.py)
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import copy
import importlib.util
import json
import random
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup        import get_logger
from symmetry_detector import detect_symmetries, find_passive_arrays
from hierarchy_builder import build_groups

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG    = False
_PDK_DIR = Path(__file__).parent.parent / "myPDK"

# SPICE power supply aliases (case-insensitive match)
POWER_ALIASES: frozenset = frozenset({
    "vdda", "vssa", "vddd", "vssd", "vdd", "vss", "gnd", "gnd!",
    "vcc", "vee", "avdd", "avss",
})

# Maps lowercase SPICE model name → PDK device type
_MODEL_MAP: dict = {
    "nmos_rvt": "nmos_rvt", "nmos_lvt": "nmos_lvt", "nmos_hvt": "nmos_hvt",
    "pmos_rvt": "pmos_rvt", "pmos_lvt": "pmos_lvt", "pmos_hvt": "pmos_hvt",
    "nmos":     "nmos_rvt", "pmos":     "pmos_rvt",
    "nfet":     "nmos_rvt", "pfet":     "pmos_rvt",
    "nch":      "nmos_rvt", "pch":      "pmos_rvt",
    "nch_rvt":  "nmos_rvt", "pch_rvt":  "pmos_rvt",
    "nch_lvt":  "nmos_lvt", "pch_lvt":  "pmos_lvt",
    "nch_hvt":  "nmos_hvt", "pch_hvt":  "pmos_hvt",
    "nch_mac":       "nmos_rvt", "pch_mac":       "pmos_rvt",
    "nch_lvt_mac":   "nmos_lvt", "pch_lvt_mac":   "pmos_lvt",
    "nch_25ud18mac": "nmos_hvt", "pch_25ud18mac": "pmos_hvt",
    "svt_nmos": "nmos_rvt", "svt_pmos": "pmos_rvt",
    "lvt_nmos": "nmos_lvt", "lvt_pmos": "pmos_lvt",
    "hvt_nmos": "nmos_hvt", "hvt_pmos": "pmos_hvt",
}

# Known PDK resistor / capacitor subcircuit type names (lowercase)
_RESISTOR_MODELS: frozenset = frozenset({
    "rppolywo", "rppolywo_m", "rppoly", "rpoly", "rpolyh", "rppolyw", "rppo",
    "poly_res",
})
_CAPACITOR_MODELS: frozenset = frozenset({
    "cfmom", "cfmom_2t", "mimcap", "nwcap", "mim", "mimcap2", "cfmom2",
    "moscap", "gatecap",
})

# Module-level cache: loaded lazily to avoid circular imports at startup
_gen001_cache = None

# --- Parameter resolution ------------------------------------------------
_PARAM_ASSIGN_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_<>]*)\s*=\s*(\S+)')

# SPICE-standard whole-subcircuit replication key. Confirmed the ONLY
# spelling actually used on a locally-defined-subckt call anywhere in the
# corpus ("multi="/"mult=" only ever appear on passive PDK-primitive lines,
# a completely different code path — see _expand_body). Kept as an explicit
# set (not a single literal comparison) so a future netlist spelling it
# "multi="/"mult=" on a LOCAL subckt call is at least logged, not silently
# missed the way "m=" itself was for two review rounds.
_INSTANCE_MULTIPLIER_KEYS: frozenset = frozenset({"m"})

_SPICE_SUFFIXES: dict = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
    "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9,
}

# --- MOSFET generation ----------------------------------------------------
_REAL_MOSFET_ASPECT_MIN = 0.2   # dedicated constant, not reused from generation_config.json
_REAL_MOSFET_ASPECT_MAX = 2.0

# --- Resistor serpentine cutter --------------------------------------------
_RESISTOR_SPLIT_TARGET_N_COUNT = 4    # distinct N values per resistor (x2 for the 0/90 twin
                                       # => up to 8 variants) — a per-resistor shape-diversity
                                       # budget. Sampling is even in N-index, not aspect ratio.
_PASSIVE_ASPECT_MIN = 1.0
_PASSIVE_ASPECT_MAX = 5.0
_M1_SPACING = 0.12                    # myPDK/gpdk090_tech_simple.json: metal_layers.M1.min_spacing

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

# --- 4a. Shared physics loader -------------------------------------------------

def _get_gen001():
    global _gen001_cache
    if _gen001_cache is None:
        path = Path(__file__).parent / "001_L1blocksGenerator.py"
        spec = importlib.util.spec_from_file_location("gen001", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _gen001_cache = mod
    return _gen001_cache


# --- 4b. SPICE parsing helpers ------------------------------------------------

def _join_continuations(lines: list) -> list:
    result: list = []
    for raw in lines:
        s = raw.rstrip("\n")
        stripped = s.lstrip()
        if stripped.startswith("+") and result:
            result[-1] = result[-1] + " " + stripped[1:].strip()
        else:
            result.append(s)
    return result


def _tokenise(line: str) -> list:
    tokens: list = []
    for t in line.split():
        for c in ("$", ";"):
            idx = t.find(c)
            if idx >= 0:
                t = t[:idx]
        if t:
            tokens.append(t)
    return tokens


def _kv_map(tokens: list) -> dict:
    """Lowercase-key map of every 'key=value' token; positional tokens ignored."""
    kv: dict = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            kv[k.lower()] = v
    return kv


def _get_x_type(line: str) -> str | None:
    tok = line.lstrip()
    if not tok or tok[0].upper() != "X":
        return None
    tokens = tok.split()
    pos = [t for t in tokens[1:] if "=" not in t]
    return pos[-1].lower() if pos else None


# --- 4c. Numeric & parameter-scope resolution ----------------------------------

def _try_parse_spice_number(text: str) -> float | None:
    t = text.strip()
    try:
        return float(t)
    except ValueError:
        pass
    low = t.lower()
    for suffix in ("meg", "f", "p", "n", "u", "m", "k", "g"):   # "meg" before "m"
        if low.endswith(suffix) and len(low) > len(suffix):
            try:
                return float(t[: -len(suffix)]) * _SPICE_SUFFIXES[suffix]
            except ValueError:
                return None
    return None


def _parse_param_assignments(line: str) -> dict:
    body = line.split(None, 1)[1] if line.strip().lower().startswith(".param") else line
    for marker in ("$", ";"):
        idx = body.find(marker)
        if idx >= 0:
            body = body[:idx]
    return {m.group(1).lower(): m.group(2) for m in _PARAM_ASSIGN_RE.finditer(body)}


def _resolve_scalar(token, scope: dict, _depth: int = 0) -> float:
    if isinstance(token, float):
        return token
    name = token[1:-1] if token.startswith("{") and token.endswith("}") else token
    lit = _try_parse_spice_number(name)
    if lit is not None:
        return lit
    if _depth > 10:
        raise ValueError(f"parameter reference chain too deep (possible cycle): {name}")
    key = name.lower()
    if key in scope:
        return _resolve_scalar(scope[key], scope, _depth + 1)
    raise KeyError(f"unresolved parameter reference: {name}")


def _resolve_or_none(raw: str | None, scope: dict) -> float | None:
    """None on structural absence (decision #8/#9); propagates on a present-but-
    unresolvable token so the caller's per-device error handling can catch it."""
    if raw is None:
        return None
    return _resolve_scalar(raw, scope)


# --- 4d. Subcircuit definition parser -----------------------------------------

def _parse_all_subckts(lines: list) -> tuple:
    defs: OrderedDict   = OrderedDict()
    global_params: dict = {}
    in_sub = False
    name: str          = ""
    ports: list        = []
    body: list         = []
    local_params: dict = {}

    for line in lines:
        lo = line.lower().lstrip()
        if lo.startswith(".subckt"):
            parts = line.split()
            name  = parts[1].lower()
            ports = [p.lower() for p in parts[2:]]
            body  = []
            local_params = {}
            in_sub = True
        elif lo.startswith(".ends"):
            if in_sub and name:
                defs[name] = (ports, body, local_params)
            in_sub = False
            name = ""
        elif lo.startswith(".param"):
            params = _parse_param_assignments(line)
            if in_sub:
                local_params.update(params)
            else:
                global_params.update(params)
        elif in_sub:
            body.append(line)

    return defs, global_params


# --- 4e. Net mapper -----------------------------------------------------------

def _map_net(net: str, port_map: dict, prefix: str) -> str:
    lo = net.lower()
    if lo in port_map:
        return port_map[lo]
    return f"{prefix}{lo}" if prefix else lo


# --- 4f. Device line parsers --------------------------------------------------

def _parse_mosfet_line(line: str, port_map: dict, prefix: str, param_scope: dict) -> dict | None:
    tokens = _tokenise(line)
    if len(tokens) < 6:
        return None
    inst   = tokens[0].lower()
    drain  = _map_net(tokens[1], port_map, prefix)
    gate   = _map_net(tokens[2], port_map, prefix)
    source = _map_net(tokens[3], port_map, prefix)
    bulk   = _map_net(tokens[4], port_map, prefix)
    model  = tokens[5].lower()

    pdk_type = _MODEL_MAP.get(model)
    if pdk_type is None:
        ch = "nmos" if model.startswith("n") else "pmos"
        pdk_type = f"{ch}_rvt"
        logger.warning("Unknown MOSFET model '%s' → mapped to %s", model, pdk_type)

    kv = _kv_map(tokens)
    parsed_params = {
        "width":       _resolve_or_none(kv.get("w"), param_scope),
        "length":      _resolve_or_none(kv.get("l"), param_scope),
        "multiplier":  _resolve_or_none(kv.get("m"), param_scope) or 1.0,
        "num_fingers": _resolve_or_none(kv.get("nf"), param_scope) or 1.0,
    }

    return {
        "inst":          f"{prefix}{inst}",
        "pdk_type":      pdk_type,
        "device_group":  "LV" if pdk_type not in ("nmos_hvt", "pmos_hvt") else "HV",
        "terminals":     {"drain": drain, "gate": gate, "source": source, "bulk": bulk},
        "parsed_params": parsed_params,
    }


def _parse_passive_line(
    line: str, port_map: dict, prefix: str, pdk_type_out: str, param_scope: dict
) -> dict | None:
    tokens = _tokenise(line)
    if len(tokens) < 3:
        return None
    inst = tokens[0].lower()
    # Positional tokens (before any key=val): skip instance name, drop model/type (last one)
    pos = [t for t in tokens[1:] if "=" not in t]
    nets_raw = pos[:-1] if len(pos) > 1 else pos
    nets     = [_map_net(n, port_map, prefix) for n in nets_raw]
    if len(nets) < 2:
        return None
    terminals: dict = {"n1": nets[0], "n2": nets[1]}
    if len(nets) >= 3:
        terminals["substrate"] = nets[2]

    kv = _kv_map(tokens)
    width  = _resolve_or_none(kv.get("w", kv.get("wr")), param_scope)
    length = _resolve_or_none(kv.get("l", kv.get("lr")), param_scope)
    series = _resolve_or_none(kv.get("series"), param_scope) or 1.0
    if length is not None:
        length = length * series

    return {
        "inst":          f"{prefix}{inst}",
        "pdk_type":      pdk_type_out,
        "device_group":  "passive",
        "terminals":     terminals,
        "parsed_params": {"width": width, "length": length},
    }


def _safe_parse_passive(
    line: str, port_map: dict, prefix: str, pdk_type_out: str,
    param_scope: dict, subckt_name: str,
) -> dict | None:
    """Wraps _parse_passive_line: a present-but-unresolvable geometry token drops
    just this device (logged), never the whole subtree — same policy as MOSFETs."""
    try:
        return _parse_passive_line(line, port_map, prefix, pdk_type_out, param_scope)
    except (KeyError, ValueError) as exc:
        logger.warning("Skipping passive line in %r (%s): %s", subckt_name, line.strip(), exc)
        return None


# --- 4g. Hierarchy flattener --------------------------------------------------

class _ExpandCtx(NamedTuple):
    """File-constant + accumulator state threaded unchanged through the
    recursion, kept separate from the genuinely per-frame state
    (port_map, prefix, param_scope, cumulative_m) passed positionally."""
    subckt_defs: OrderedDict
    global_params: dict
    flat_devices: list
    hierarchy_map: dict


def _expand_body(
    body_lines: list,
    subckt_name: str,
    port_map: dict,
    prefix: str,
    param_scope: dict,
    cumulative_m: float,
    ctx: _ExpandCtx,
) -> None:
    for line in body_lines:
        lo = line.lstrip().lower()
        if not lo or lo.startswith("*") or lo.startswith("."):
            continue
        fc = lo[0]

        if fc == "m":
            try:
                dev = _parse_mosfet_line(line, port_map, prefix, param_scope)
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping MOSFET line in %r (%s): %s", subckt_name, line.strip(), exc)
                dev = None
            if dev:
                dev["parsed_params"]["multiplier"] *= cumulative_m
                ctx.flat_devices.append(dev)
                ctx.hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "r":
            dev = _safe_parse_passive(line, port_map, prefix, "res_poly", param_scope, subckt_name)
            if dev:
                ctx.flat_devices.append(dev)
                ctx.hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "c":
            dev = _safe_parse_passive(line, port_map, prefix, "cap_mom", param_scope, subckt_name)
            if dev:
                ctx.flat_devices.append(dev)
                ctx.hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "x":
            x_type = _get_x_type(line)
            if x_type is None:
                continue
            if x_type in _RESISTOR_MODELS:
                dev = _safe_parse_passive(line, port_map, prefix, "res_poly", param_scope, subckt_name)
                if dev:
                    ctx.flat_devices.append(dev)
                    ctx.hierarchy_map[dev["inst"]] = subckt_name
            elif x_type in _CAPACITOR_MODELS:
                dev = _safe_parse_passive(line, port_map, prefix, "cap_mom", param_scope, subckt_name)
                if dev:
                    ctx.flat_devices.append(dev)
                    ctx.hierarchy_map[dev["inst"]] = subckt_name
            elif x_type in ctx.subckt_defs:
                tokens    = _tokenise(line)
                inst_name = tokens[0].lower()
                pos_nets  = [
                    _map_net(t, port_map, prefix)
                    for t in tokens[1:] if "=" not in t
                ][:-1]
                override_tokens = [t for t in tokens[1:] if "=" in t]
                child_ports, child_body, child_local_params = ctx.subckt_defs[x_type]
                n = min(len(child_ports), len(pos_nets))
                if n < len(child_ports):
                    logger.warning(
                        "Port mismatch expanding '%s' (%d/%d ports)",
                        x_type, len(pos_nets), len(child_ports),
                    )
                child_port_map = dict(zip(child_ports[:n], pos_nets[:n]))
                child_scope    = {**ctx.global_params, **child_local_params}
                child_cumulative_m    = cumulative_m
                multiplier_unresolved = False

                for tok in override_tokens:
                    k, v = tok.split("=", 1)
                    k_lo = k.lower()
                    try:
                        resolved = _resolve_scalar(v, param_scope)
                    except (KeyError, ValueError) as exc:
                        if k_lo in _INSTANCE_MULTIPLIER_KEYS:
                            # Round-3 fix (decision #10): unlike an ordinary named
                            # override, nothing ever looks this up except this
                            # expansion step itself — silently continuing would mean
                            # assuming "no replication" for a value the netlist
                            # explicitly specified as something else.
                            logger.warning(
                                "Instance multiplier %s=%s on %r could not be resolved (%s) — "
                                "skipping this instance's subtree instead of guessing its "
                                "replication count", k, v, inst_name, exc)
                            multiplier_unresolved = True
                            break
                        # Round-2 fix (decision #6): an ordinary override that fails
                        # to resolve must not abort the whole subtree.
                        logger.warning(
                            "Override %s=%s on %r could not be resolved (%s) — "
                            "child keeps its own default for %s", k, v, inst_name, exc, k)
                        continue
                    child_scope[k_lo] = resolved
                    if k_lo in _INSTANCE_MULTIPLIER_KEYS:
                        child_cumulative_m *= resolved
                    elif k_lo in ("multi", "mult"):
                        # Canary (round-3 hardening): never seen on a local-subckt
                        # call in the current corpus — surface it instead of
                        # silently treating it as an ordinary unused named param.
                        logger.warning(
                            "Override %s=%s on %r looks like an instance-multiplier spelling "
                            "but isn't in _INSTANCE_MULTIPLIER_KEYS — treated as an ordinary "
                            "(likely unused) named parameter; verify this is intended", k, v, inst_name)

                if multiplier_unresolved:
                    continue  # next line in body_lines — do not expand with an unknown replication count

                _expand_body(
                    child_body, x_type, child_port_map, f"{prefix}{inst_name}.",
                    child_scope, child_cumulative_m, ctx,
                )
            else:
                logger.warning("Unknown X-instance type '%s' in '%s'", x_type, subckt_name)


def parse_and_flatten(path: str) -> tuple:
    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.readlines()

    joined  = _join_continuations(raw)
    cleaned: list = []
    for line in joined:
        s = line.strip()
        if not s or s.startswith("*") or s.startswith("//"):
            continue
        for marker in ("$", ";"):
            idx = s.find(marker)
            if idx > 0:
                s = s[:idx].strip()
        if s:
            cleaned.append(s)

    subckt_defs, global_params = _parse_all_subckts(cleaned)
    if not subckt_defs:
        raise ValueError(f"No .subckt definitions found in {path}")

    top_name = list(subckt_defs.keys())[-1]
    top_ports, top_body, top_local_params = subckt_defs[top_name]
    logger.info("Top-level subckt '%s' (%d ports)", top_name, len(top_ports))

    flat_devices: list  = []
    hierarchy_map: dict = {}
    ctx        = _ExpandCtx(subckt_defs, global_params, flat_devices, hierarchy_map)
    root_scope = {**global_params, **top_local_params}
    _expand_body(top_body, top_name, {}, "", root_scope, 1.0, ctx)
    logger.info("Flattened to %d devices", len(flat_devices))

    return list(top_ports), flat_devices, hierarchy_map


# --- 4h. Net classification ---------------------------------------------------

def classify_nets(all_nets: set, top_ports: list) -> dict:
    port_set = {p.lower() for p in top_ports}
    result: dict = {}
    for net in all_nets:
        lo = net.lower()
        if lo in POWER_ALIASES:
            result[net] = "power"
        elif lo in port_set:
            result[net] = "signal"
        else:
            result[net] = "internal"
    return result


# --- 4i. Resistor serpentine cutter --------------------------------------------

def _accepted_split_range(L: float, W: float, grid: float, L_min: float) -> list:
    g01 = _get_gen001()
    accepted: list = []
    n = 1
    while True:
        seg_len = L / n
        if seg_len < L_min:
            break
        w_block = g01.snap_to_grid(seg_len, grid)
        h_block = g01.snap_to_grid(W * n + (n - 1) * _M1_SPACING, grid)
        if w_block > 0 and h_block > 0:
            long_side, short_side = max(w_block, h_block), min(w_block, h_block)
            if _PASSIVE_ASPECT_MIN <= long_side / short_side <= _PASSIVE_ASPECT_MAX:
                accepted.append(n)
        n += 1
    return accepted


def _select_representative_ns(accepted: list, target_count: int) -> list:
    if len(accepted) <= target_count:
        return accepted
    lo, hi = accepted[0], accepted[-1]
    picked = {lo + round(i * (hi - lo) / (target_count - 1)) for i in range(target_count)}
    return sorted(picked)


def _generate_resistor_variants(L: float, W: float, num_pins: int, grid: float, L_min: float) -> list:
    g01 = _get_gen001()
    accepted = _accepted_split_range(L, W, grid, L_min)
    variants: list = []
    for n in _select_representative_ns(accepted, _RESISTOR_SPLIT_TARGET_N_COUNT):
        seg_len = L / n
        w_block = g01.snap_to_grid(seg_len, grid)
        h_block = g01.snap_to_grid(W * n + (n - 1) * _M1_SPACING, grid)
        variants.append({
            "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": w_block, "y_max": h_block},
            "pin_positions": g01.center_pin_positions(num_pins, w_block, h_block, grid),
            "is_used":       False,
            "rotation_deg":  0,
        })
        variants.append({
            "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": h_block, "y_max": w_block},
            "pin_positions": g01.center_pin_positions(num_pins, h_block, w_block, grid),
            "is_used":       False,
            "rotation_deg":  90,
        })
    return variants


# --- 4j. Passive block variant generator / capacitor placeholder seam ---------

def _generate_passive_block(
    W: float, L: float, pdk_type: str, num_pins: int, grid: float
) -> dict:
    g01 = _get_gen001()
    W_s = g01.snap_to_grid(W, grid)
    L_s = g01.snap_to_grid(L, grid)
    if W_s <= 0 or L_s <= 0:
        return {"device_type": pdk_type, "parameters": {"width": W, "length": L}, "variants": []}

    variants = [{
        "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": W_s, "y_max": L_s},
        "pin_positions": g01.center_pin_positions(num_pins, W_s, L_s, grid),
        "is_used":       False,
        "rotation_deg":  0,
    }]
    if abs(W_s - L_s) > grid:
        variants.append({
            "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": L_s, "y_max": W_s},
            "pin_positions": g01.center_pin_positions(num_pins, L_s, W_s, grid),
            "is_used":       False,
            "rotation_deg":  90,
        })
    return {"device_type": pdk_type, "parameters": {"width": W, "length": L}, "variants": variants}


def _generate_capacitor_variants(L: float, W: float, num_pins: int, grid: float) -> list:
    """Placeholder — identical to the pre-existing simple-rectangle behavior.
    Real capacitor-specific variant/symmetry logic is future work; kept as its
    own function so that work has an obvious home."""
    return _generate_passive_block(W, L, "cap_mom", num_pins, grid)["variants"]


# --- 4k. Netlist JSON builder -------------------------------------------------

def _build_netlist_json(blocks: list, net_class: dict) -> dict:
    net_pins: dict = defaultdict(list)
    for blk in blocks:
        if "error" in blk:
            continue
        bid = blk["block_id"]
        for term, pin_lbl in blk.get("pin_assignment", {}).items():
            net = blk["terminals"].get(term)
            if net:
                net_pins[net].append(f"B{bid}_{pin_lbl}")

    nets = [
        {"net_id": net, "net_type": net_class.get(net, "internal"), "pins": pins}
        for net, pins in sorted(net_pins.items())
    ]
    n_power    = sum(1 for n in nets if n["net_type"] == "power")
    n_signal   = sum(1 for n in nets if n["net_type"] == "signal")
    n_internal = sum(1 for n in nets if n["net_type"] == "internal")
    tot_pins   = sum(blk["num_pins"] for blk in blocks if "error" not in blk)
    return {
        "num_nets":          len(nets),
        "num_power_nets":    n_power,
        "num_signal_nets":   n_signal,
        "num_internal_nets": n_internal,
        "num_pins":          tot_pins,
        "nets":              nets,
    }


# --- 4l. Pin assignment -------------------------------------------------------

def _pin_assignment_for(dev: dict) -> dict:
    if dev["device_group"] != "passive":
        return {"bulk": "P0", "drain": "P1", "gate": "P2", "source": "P3"}
    terms  = list(dev["terminals"].keys())
    subs   = [t for t in terms if t == "substrate"]
    others = [t for t in terms if t != "substrate"]
    pa: dict = {}
    if subs:
        pa["substrate"] = "P0"
        for k, t in enumerate(others):
            pa[t] = f"P{k + 1}"
    else:
        for k, t in enumerate(others):
            pa[t] = f"P{k}"
    return pa


# --- 4m. Main block generator ------------------------------------------------

def _generate_blocks_random_sizes(
    collapsed: list,
    tech_file: dict,
    config: dict,
    sym_result: dict,
    hierarchy_map: dict,
    inst_to_mult: dict,
) -> list:
    """Legacy path: random W/L/M/Nf per device, seeded via the caller's
    random.seed(), with pair_b2a forced-copy for detected symmetric pairs.
    This is wmi_generate_netlist_blocks()'s original device loop, restored
    verbatim (opt-in via --random-sizes) once real netlist sizing became
    the default."""
    g01 = _get_gen001()

    grid    = tech_file["technology_info"]["manufacturing_grid"]
    gen_p   = config["generation_params"]
    L_step  = gen_p["length_range"]["step"]
    W_step  = gen_p["width_range"]["step"]
    M_min   = gen_p["multiplier_range"]["min"]
    M_max   = gen_p["multiplier_range"]["max"]
    NF_min  = gen_p["num_fingers_range"]["min"]
    NF_max  = gen_p["num_fingers_range"]["max"]
    ar_cfg  = gen_p["aspect_ratio"]
    dc      = config["design_constraints"]
    max_att = config["validation"]["max_generation_attempts"]
    rot_cfg = config.get("rotation_variants")

    self_sym_set = {bid for g in sym_result["groups"] for bid in g["self_symmetric"]}
    pair_b2a: dict = {}
    for group in sym_result["groups"]:
        for a, b in group["pairs"]:
            pair_b2a[b] = a

    res_L_min = tech_file["device_constraints"].get("res_poly", {}).get("L", {}).get("min", 1.0)

    blocks: list    = []
    gen_cache: dict = {}

    for dev in collapsed:
        bid      = dev["block_id"]
        pdk_type = dev["pdk_type"]
        is_pass  = (dev["device_group"] == "passive")
        num_pins = len(dev["terminals"]) if is_pass else 4
        m_mult   = inst_to_mult.get(dev["inst"], 1)

        if bid in pair_b2a:
            ab = gen_cache.get(pair_b2a[bid])
            if ab and "error" not in ab:
                block = {
                    "device_type":         ab["device_type"],
                    "block_id":            bid,
                    "inst":                dev["inst"],
                    "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                    "parameters":          copy.deepcopy(ab["parameters"]),
                    "variants":            copy.deepcopy(ab["variants"]),
                    "num_pins":            ab["num_pins"],
                    "generation_attempts": 1,
                    "unit_cell_w":         ab.get("unit_cell_w", 0.0),
                    "unit_cell_h":         ab.get("unit_cell_h", 0.0),
                }
            else:
                block = {
                    "block_id": bid, "inst": dev["inst"],
                    "error": f"Pair partner {pair_b2a[bid]} failed",
                    "generation_attempts": 0,
                }

        elif is_pass:
            constraints = dc.get(pdk_type, {"W": {"min": 0.5, "max": 10.0},
                                             "L": {"min": 1.0, "max": 50.0}})
            block = None
            for attempt in range(max_att):
                W  = g01.snap_to_step(random.uniform(
                    constraints["W"]["min"], constraints["W"]["max"]), W_step)
                L  = g01.snap_to_step(random.uniform(
                    constraints["L"]["min"], constraints["L"]["max"]), L_step)
                if pdk_type == "res_poly":
                    variants   = _generate_resistor_variants(L, W, num_pins, grid, res_L_min)
                    parameters = {"width": W, "length": L}
                else:
                    tb         = _generate_passive_block(W, L, pdk_type, num_pins, grid)
                    variants   = tb["variants"]
                    parameters = tb["parameters"]
                if variants:
                    block = {
                        "device_type":         pdk_type,
                        "block_id":            bid,
                        "inst":                dev["inst"],
                        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                        "parameters":          parameters,
                        "variants":            variants,
                        "num_pins":            num_pins,
                        "generation_attempts": attempt + 1,
                    }
                    break
            if block is None:
                block = {"block_id": bid, "inst": dev["inst"],
                         "error": "No variants", "generation_attempts": max_att}

        else:  # MOSFET
            constraints = dc.get(pdk_type, dc.get("nmos_rvt"))
            block = None
            for attempt in range(max_att):
                try:
                    L  = g01.snap_to_step(
                        random.uniform(constraints["L"]["min"], constraints["L"]["max"]), L_step)
                    W  = g01.snap_to_step(
                        random.uniform(constraints["W"]["min"], constraints["W"]["max"]), W_step)
                    M  = random.randrange(M_min, M_max + 1, 2)
                    NF = random.randint(NF_min, NF_max)
                    min_ar = round(random.uniform(ar_cfg["min_aspect_min"],
                                                  ar_cfg["min_aspect_max"]), 2)
                    max_ar = round(random.uniform(ar_cfg["max_aspect_min"],
                                                  ar_cfg["max_aspect_max"]), 2)
                    tb = g01.wmi_generate_transistor_block(
                        tech_file, W, L, M, NF, min_ar, max_ar, pdk_type, num_pins
                    )
                    if tb["variants"]:
                        g01.append_rotation_90(tb["variants"], rot_cfg, grid)
                        uw, uh = g01.compute_unit_cell_bbox(tech_file, W, L, NF)
                        block = {
                            "device_type":         tb["device_type"],
                            "block_id":            bid,
                            "inst":                dev["inst"],
                            "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                            "parameters":          tb["parameters"],
                            "variants":            tb["variants"],
                            "num_pins":            num_pins,
                            "generation_attempts": attempt + 1,
                            "unit_cell_w":         uw,
                            "unit_cell_h":         uh,
                        }
                        logger.debug("Block %d (%s): %d variant(s)  unit_cell=%.3f×%.3f",
                                     bid, pdk_type, len(block["variants"]), uw, uh)
                        break
                except Exception as exc:
                    logger.debug("Block %d attempt %d: %s", bid, attempt, exc)

            if block is None:
                block = {"block_id": bid, "inst": dev["inst"],
                         "error": "No valid variants", "generation_attempts": max_att}
                logger.warning("Block %d (%s): failed after %d attempts", bid, pdk_type, max_att)

        if bid in self_sym_set and "error" not in block:
            block["variants"] = [v for v in block["variants"] if v.get("rotation_deg", 0) == 0]

        if "error" not in block and block.get("variants"):
            block["variants"][0]["is_used"] = True

        if m_mult > 1 and "error" not in block:
            block["array_multiplier"] = m_mult

        if "error" not in block:
            pa = _pin_assignment_for(dev)
            block["pin_assignment"] = pa
            block["terminals"]      = dev["terminals"]
            bulk_net = dev["terminals"].get("bulk", "") or dev["terminals"].get("substrate", "")
            if bulk_net and bulk_net.lower() in POWER_ALIASES:
                block["power_rail"] = "VDD" if "vdd" in bulk_net.lower() else "VSS"

        blocks.append(block)
        gen_cache[bid] = block

    return blocks


def _generate_blocks_real_sizes(
    collapsed: list,
    tech_file: dict,
    config: dict,
    sym_result: dict,
    hierarchy_map: dict,
    inst_to_mult: dict,
) -> list:
    """Real-sizing path: parsed W/L/M/Nf from the netlist's own .param
    cascade, resistor serpentine splitter, no pair_b2a forced-copy (real
    sizes make detected symmetric pairs match without it)."""
    g01 = _get_gen001()

    grid               = tech_file["technology_info"]["manufacturing_grid"]
    rot_cfg            = config.get("rotation_variants")
    device_constraints = tech_file["device_constraints"]
    res_L_min          = device_constraints.get("res_poly", {}).get("L", {}).get("min", 1.0)

    self_sym_set = {bid for g in sym_result["groups"] for bid in g["self_symmetric"]}

    blocks: list = []

    for dev in collapsed:
        bid      = dev["block_id"]
        pdk_type = dev["pdk_type"]
        is_pass  = (dev["device_group"] == "passive")
        num_pins = len(dev["terminals"]) if is_pass else 4
        m_mult   = inst_to_mult.get(dev["inst"], 1)
        pp       = dev["parsed_params"]

        if is_pass:
            W, L = pp["width"], pp["length"]
            if W is None or L is None:
                # Decision #9 — passives get NO PDK-default fallback for a missing
                # dimension (unlike MOSFETs): there's no sensible "default resistor
                # length", so this is always a clean error block, never a crash.
                block = {"block_id": bid, "inst": dev["inst"],
                         "error": "no resolvable L/W for passive device", "generation_attempts": 0}
            elif pdk_type == "res_poly":
                variants = _generate_resistor_variants(L, W, num_pins, grid, res_L_min)
                if variants:
                    block = {
                        "device_type":         pdk_type,
                        "block_id":            bid,
                        "inst":                dev["inst"],
                        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                        "parameters":          {"width": W, "length": L},
                        "variants":            variants,
                        "num_pins":            num_pins,
                        "generation_attempts": 1,
                    }
                else:
                    block = {"block_id": bid, "inst": dev["inst"],
                             "error": "no accepted split variants", "generation_attempts": 1}
            else:
                variants = _generate_capacitor_variants(L, W, num_pins, grid)
                if variants:
                    block = {
                        "device_type":         pdk_type,
                        "block_id":            bid,
                        "inst":                dev["inst"],
                        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                        "parameters":          {"width": W, "length": L},
                        "variants":            variants,
                        "num_pins":            num_pins,
                        "generation_attempts": 1,
                    }
                else:
                    block = {"block_id": bid, "inst": dev["inst"],
                             "error": "no variants", "generation_attempts": 1}

        else:  # MOSFET
            pdk_dc = device_constraints.get(pdk_type, device_constraints.get("nmos_rvt"))
            W = pp["width"]  if pp["width"]  is not None else pdk_dc["W"]["default"]
            L = pp["length"] if pp["length"] is not None else pdk_dc["L"]["default"]
            if pp["width"] is None or pp["length"] is None:
                logger.warning("Block %d (%s): missing W or L on device line, using PDK default (%s/%s)",
                                bid, pdk_type, W, L)
            # multiplier/num_fingers already include any cumulative_m from subckt
            # replication; cast to int — wmi_generate_transistor_block enumerates
            # divisor pairs of total_fingers via range(), which requires an int.
            M  = int(round(pp["multiplier"]))
            Nf = int(round(pp["num_fingers"]))

            try:
                tb = g01.wmi_generate_transistor_block(
                    tech_file, W, L, M, Nf, _REAL_MOSFET_ASPECT_MIN, _REAL_MOSFET_ASPECT_MAX,
                    pdk_type, num_pins)
                if not tb["variants"]:
                    logger.warning(
                        "Block %d (%s): no variant within aspect [%.1f,%.1f], retrying unrestricted",
                        bid, pdk_type, _REAL_MOSFET_ASPECT_MIN, _REAL_MOSFET_ASPECT_MAX)
                    tb = g01.wmi_generate_transistor_block(
                        tech_file, W, L, M, Nf, 0.0, float("inf"), pdk_type, num_pins)
                if tb["variants"]:
                    g01.append_rotation_90(tb["variants"], rot_cfg, grid)
                    uw, uh = g01.compute_unit_cell_bbox(tech_file, W, L, Nf)
                    block = {
                        "device_type":         tb["device_type"],
                        "block_id":            bid,
                        "inst":                dev["inst"],
                        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                        "parameters":          tb["parameters"],
                        "variants":            tb["variants"],
                        "num_pins":            num_pins,
                        "generation_attempts": 1,
                        "unit_cell_w":         uw,
                        "unit_cell_h":         uh,
                    }
                    logger.debug("Block %d (%s): %d variant(s)  unit_cell=%.3f×%.3f",
                                 bid, pdk_type, len(block["variants"]), uw, uh)
                else:
                    block = {"block_id": bid, "inst": dev["inst"],
                             "error": "no variants even with unrestricted aspect bounds",
                             "generation_attempts": 1}
            except Exception as exc:
                block = {"block_id": bid, "inst": dev["inst"], "error": str(exc), "generation_attempts": 1}
                logger.warning("Block %d (%s): generation failed: %s", bid, pdk_type, exc)

        if bid in self_sym_set and "error" not in block:
            block["variants"] = [v for v in block["variants"] if v.get("rotation_deg", 0) == 0]

        if "error" not in block and block.get("variants"):
            block["variants"][0]["is_used"] = True

        if m_mult > 1 and "error" not in block:
            block["array_multiplier"] = m_mult

        if "error" not in block:
            pa = _pin_assignment_for(dev)
            block["pin_assignment"] = pa
            block["terminals"]      = dev["terminals"]
            bulk_net = dev["terminals"].get("bulk", "") or dev["terminals"].get("substrate", "")
            if bulk_net and bulk_net.lower() in POWER_ALIASES:
                block["power_rail"] = "VDD" if "vdd" in bulk_net.lower() else "VSS"

        blocks.append(block)

    return blocks


def wmi_generate_netlist_blocks(
    flat_devices: list,
    tech_file: dict,
    config: dict,
    seed: int,
    top_ports: list,
    hierarchy_map: dict,
    random_sizes: bool = False,
) -> tuple:
    random.seed(seed)
    g01 = _get_gen001()

    grid = tech_file["technology_info"]["manufacturing_grid"]

    all_nets: set = set()
    for dev in flat_devices:
        for net in dev["terminals"].values():
            if net:
                all_nets.add(net)

    power_nets  = {n for n in all_nets if n.lower() in POWER_ALIASES}
    signal_nets = {p for p in top_ports if p.lower() not in POWER_ALIASES}
    net_class   = classify_nets(all_nets, top_ports)

    # Step 1 — assign temp block_ids and collapse parallel passive arrays
    temp_devs = [dict(d, block_id=i) for i, d in enumerate(flat_devices)]
    raw_clusters = find_passive_arrays(temp_devs)

    inst_to_mult: dict = {}
    insts_to_drop: set = set()
    for cluster in raw_clusters:
        rep_inst = temp_devs[cluster["representative_block_id"]]["inst"]
        inst_to_mult[rep_inst] = len(cluster["members"])
        for extra_bid in cluster["members"][1:]:
            insts_to_drop.add(temp_devs[extra_bid]["inst"])

    old_to_new: dict = {}
    collapsed: list  = []
    for i, dev in enumerate(flat_devices):
        if dev["inst"] not in insts_to_drop:
            new_bid = len(collapsed)
            old_to_new[i] = new_bid
            collapsed.append(dict(dev, block_id=new_bid))

    passive_cluster_info: list = []
    for cluster in raw_clusters:
        new_rep = old_to_new.get(cluster["representative_block_id"])
        if new_rep is None:
            continue
        passive_cluster_info.append({
            "representative_block_id": new_rep,
            "original_count":          len(cluster["members"]),
            "topology":                cluster["topology"],
            "original_insts":          [flat_devices[m]["inst"] for m in cluster["members"]],
        })

    # Step 2 — detect symmetries on the collapsed device list
    sym_result = detect_symmetries(collapsed, signal_nets, power_nets)

    # Step 3 — generate sizes, either from the netlist's own real (W, L, M, Nf)
    # or randomized+seeded (legacy behavior, opt-in via random_sizes)
    if random_sizes:
        blocks = _generate_blocks_random_sizes(
            collapsed, tech_file, config, sym_result, hierarchy_map, inst_to_mult)
    else:
        blocks = _generate_blocks_real_sizes(
            collapsed, tech_file, config, sym_result, hierarchy_map, inst_to_mult)

    g01.wmi_adjust_power_pin_positions(
        [b for b in blocks if "error" not in b and "power_rail" in b], grid
    )

    valid   = [b for b in blocks if "error" not in b]
    netlist = _build_netlist_json(valid, net_class)

    sym_constraints = {
        "groups":               sym_result["groups"],
        "passive_clusters":     passive_cluster_info,
        "symmetric_net_pairs":  sym_result["symmetric_net_pairs"],
        "self_symmetric_nets":  sym_result["self_symmetric_nets"],
        "tail_cm_pairs":        sym_result.get("tail_cm_pairs", []),
        "compound_blocks":      sym_result.get("compound_blocks", []),
    }
    return blocks, netlist, sym_constraints


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(netlist_path: str, seed: int, sym_mode: str = "aggressive",
        random_sizes: bool = False) -> dict:
    path = Path(netlist_path)
    if not path.exists():
        raise FileNotFoundError(f"Netlist not found: {path}")

    with open(_PDK_DIR / "gpdk090_tech_simple.json", encoding="utf-8") as f:
        tech_data = json.load(f)
    with open(_PDK_DIR / "gpdk090_device_rules.json", encoding="utf-8") as f:
        device_rules = json.load(f)
    tech_file = {**tech_data, **device_rules}

    with open(_PDK_DIR / "generation_config.json", encoding="utf-8") as f:
        config = json.load(f)

    logger.info("Parsing: %s  seed=%d  sym_mode=%s  random_sizes=%s",
                 path.name, seed, sym_mode, random_sizes)
    top_ports, flat_devices, hierarchy_map = parse_and_flatten(str(path))

    if not flat_devices:
        raise ValueError(f"No devices found in {path.name}")

    blocks, netlist, sym_constraints = wmi_generate_netlist_blocks(
        flat_devices, tech_file, config, seed, top_ports, hierarchy_map,
        random_sizes=random_sizes,
    )

    n_valid = sum(1 for b in blocks if "error" not in b)
    logger.info(
        "Done: %d blocks (%d valid), %d nets (%dP / %dS / %dI)",
        len(blocks), n_valid,
        netlist["num_nets"],
        netlist["num_power_nets"],
        netlist["num_signal_nets"],
        netlist.get("num_internal_nets", 0),
    )

    placement_config = {
        "symmetry_mode":            sym_mode,
        "enable_matching":          True,
        "enable_passive_splitting": True,
        "passive_max_split":        8,
    }
    groups = build_groups(sym_constraints, blocks, placement_config)

    return {
        "generation_params": {
            "num_of_blocks":  len(blocks),
            "seed":           seed,
            "source_netlist": path.name,
            "random_sizes":   random_sizes,
        },
        "technology":           tech_file["technology_info"]["name"],
        "placement_config":     placement_config,
        "blocks":               blocks,
        "netlist":              netlist,
        "symmetry_constraints": sym_constraints,
        "groups":               groups,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate placement JSON from SPICE netlist")
    parser.add_argument("netlist", help="Path to SPICE netlist (.sp)")
    parser.add_argument("seed",    type=int, help="Random seed")
    parser.add_argument(
        "--sym-mode",
        default="aggressive",
        choices=["none", "moderate", "aggressive"],
        dest="sym_mode",
        help="Symmetry enforcement: none | moderate | aggressive (default: aggressive)",
    )
    parser.add_argument(
        "--random-sizes", dest="random_sizes", action="store_true", default=False,
        help="Randomize device sizes instead of using real netlist values (legacy pre-real-sizing behavior)",
    )
    args = parser.parse_args()
    try:
        result = run(args.netlist, args.seed, sym_mode=args.sym_mode,
                      random_sizes=args.random_sizes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
