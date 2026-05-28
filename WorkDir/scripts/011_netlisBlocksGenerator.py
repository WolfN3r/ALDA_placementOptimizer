#!/usr/bin/env python3
"""
Read a SPICE (.sp) netlist, flatten hierarchy, generate random W/L/M/Nf for
every device, detect symmetry groups from circuit topology, and emit the same
JSON schema as 001_L1blocksGenerator.

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
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup import get_logger
from symmetry_detector import detect_symmetries, find_passive_arrays

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
    "rppolywo", "rppoly", "rpoly", "rpolyh", "rppolyw", "rppo", "poly_res",
})
_CAPACITOR_MODELS: frozenset = frozenset({
    "cfmom", "cfmom_2t", "mimcap", "nwcap", "mim", "mimcap2", "cfmom2",
    "moscap", "gatecap",
})

# Module-level cache: loaded lazily to avoid circular imports at startup
_gen001_cache = None

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


def _get_x_type(line: str) -> str | None:
    tok = line.lstrip()
    if not tok or tok[0].upper() != "X":
        return None
    tokens = tok.split()
    pos = [t for t in tokens[1:] if "=" not in t]
    return pos[-1].lower() if pos else None


# --- 4c. Subcircuit definition parser -----------------------------------------

def _parse_all_subckts(lines: list) -> OrderedDict:
    defs: OrderedDict = OrderedDict()
    in_sub = False
    name: str         = ""
    ports: list       = []
    body: list        = []

    for line in lines:
        lo = line.lower().lstrip()
        if lo.startswith(".subckt"):
            parts = line.split()
            name  = parts[1].lower()
            ports = [p.lower() for p in parts[2:]]
            body  = []
            in_sub = True
        elif lo.startswith(".ends"):
            if in_sub and name:
                defs[name] = (ports, body)
            in_sub = False
            name = ""
        elif in_sub and not lo.startswith(".param"):
            body.append(line)

    return defs


# --- 4d. Net mapper -----------------------------------------------------------

def _map_net(net: str, port_map: dict, prefix: str) -> str:
    lo = net.lower()
    if lo in port_map:
        return port_map[lo]
    return f"{prefix}{lo}" if prefix else lo


# --- 4e. Device line parsers --------------------------------------------------

def _parse_mosfet_line(line: str, port_map: dict, prefix: str) -> dict | None:
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

    return {
        "inst":         f"{prefix}{inst}",
        "pdk_type":     pdk_type,
        "device_group": "LV" if pdk_type not in ("nmos_hvt", "pmos_hvt") else "HV",
        "terminals":    {"drain": drain, "gate": gate, "source": source, "bulk": bulk},
    }


def _parse_passive_line(
    line: str, port_map: dict, prefix: str, pdk_type_out: str
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
    return {
        "inst":         f"{prefix}{inst}",
        "pdk_type":     pdk_type_out,
        "device_group": "passive",
        "terminals":    terminals,
    }


# --- 4f. Hierarchy flattener --------------------------------------------------

def _expand_body(
    body_lines: list,
    subckt_name: str,
    port_map: dict,
    subckt_defs: OrderedDict,
    flat_devices: list,
    hierarchy_map: dict,
    prefix: str,
) -> None:
    for line in body_lines:
        lo = line.lstrip().lower()
        if not lo or lo.startswith("*") or lo.startswith("."):
            continue
        fc = lo[0]

        if fc == "m":
            dev = _parse_mosfet_line(line, port_map, prefix)
            if dev:
                flat_devices.append(dev)
                hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "r":
            dev = _parse_passive_line(line, port_map, prefix, "res_poly")
            if dev:
                flat_devices.append(dev)
                hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "c":
            dev = _parse_passive_line(line, port_map, prefix, "cap_mom")
            if dev:
                flat_devices.append(dev)
                hierarchy_map[dev["inst"]] = subckt_name

        elif fc == "x":
            x_type = _get_x_type(line)
            if x_type is None:
                continue
            if x_type in _RESISTOR_MODELS:
                dev = _parse_passive_line(line, port_map, prefix, "res_poly")
                if dev:
                    flat_devices.append(dev)
                    hierarchy_map[dev["inst"]] = subckt_name
            elif x_type in _CAPACITOR_MODELS:
                dev = _parse_passive_line(line, port_map, prefix, "cap_mom")
                if dev:
                    flat_devices.append(dev)
                    hierarchy_map[dev["inst"]] = subckt_name
            elif x_type in subckt_defs:
                tokens    = _tokenise(line)
                inst_name = tokens[0].lower()
                pos_nets  = [
                    _map_net(t, port_map, prefix)
                    for t in tokens[1:] if "=" not in t
                ][:-1]
                child_ports, child_body = subckt_defs[x_type]
                n = min(len(child_ports), len(pos_nets))
                if n < len(child_ports):
                    logger.warning(
                        "Port mismatch expanding '%s' (%d/%d ports)",
                        x_type, len(pos_nets), len(child_ports),
                    )
                child_port_map = dict(zip(child_ports[:n], pos_nets[:n]))
                _expand_body(
                    child_body, x_type, child_port_map,
                    subckt_defs, flat_devices, hierarchy_map,
                    f"{prefix}{inst_name}.",
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

    subckt_defs = _parse_all_subckts(cleaned)
    if not subckt_defs:
        raise ValueError(f"No .subckt definitions found in {path}")

    top_name            = list(subckt_defs.keys())[-1]
    top_ports, top_body = subckt_defs[top_name]
    logger.info("Top-level subckt '%s' (%d ports)", top_name, len(top_ports))

    flat_devices: list  = []
    hierarchy_map: dict = {}
    _expand_body(top_body, top_name, {}, subckt_defs, flat_devices, hierarchy_map, "")
    logger.info("Flattened to %d devices", len(flat_devices))

    return list(top_ports), flat_devices, hierarchy_map


# --- 4g. Net classification ---------------------------------------------------

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


# --- 4h. Passive block variant generator -------------------------------------

def _generate_passive_block(
    W: float, L: float, pdk_type: str, num_pins: int, grid: float
) -> dict:
    g01 = _get_gen001()
    W_s = g01.snap_to_grid(W, grid)
    L_s = g01.snap_to_grid(L, grid)
    if W_s <= 0 or L_s <= 0:
        return {"device_type": pdk_type, "parameters": {"width": W, "length": L}, "variants": []}

    ar       = round(W_s / L_s, 3)
    variants = [{
        "layout":        {"rows": 1, "cols": 1, "aspect_ratio": ar},
        "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": W_s, "y_max": L_s},
        "pin_positions": g01.center_pin_positions(num_pins, W_s, L_s, grid),
        "is_used":       False,
        "rotation_deg":  0,
    }]
    if abs(W_s - L_s) > grid:
        ar_rot = round(L_s / W_s, 3)
        variants.append({
            "layout":        {"rows": 1, "cols": 1, "aspect_ratio": ar_rot},
            "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": L_s, "y_max": W_s},
            "pin_positions": g01.center_pin_positions(num_pins, L_s, W_s, grid),
            "is_used":       False,
            "rotation_deg":  90,
        })
    return {"device_type": pdk_type, "parameters": {"width": W, "length": L}, "variants": variants}


# --- 4i. Netlist JSON builder -------------------------------------------------

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


# --- 4j. Pin assignment -------------------------------------------------------

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


# --- 4k. Main block generator ------------------------------------------------

def wmi_generate_netlist_blocks(
    flat_devices: list,
    tech_file: dict,
    config: dict,
    seed: int,
    top_ports: list,
    hierarchy_map: dict,
) -> tuple:
    random.seed(seed)
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

    inst_to_mult: dict  = {}
    insts_to_drop: set  = set()
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
    sym_result    = detect_symmetries(collapsed, signal_nets, power_nets)
    self_sym_set  = {bid for g in sym_result["groups"] for bid in g["self_symmetric"]}
    pair_b2a: dict = {}
    for group in sym_result["groups"]:
        for a, b in group["pairs"]:
            pair_b2a[b] = a

    # Step 3 — generate sizes
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
                tb = _generate_passive_block(W, L, pdk_type, num_pins, grid)
                if tb["variants"]:
                    block = {
                        "device_type":         pdk_type,
                        "block_id":            bid,
                        "inst":                dev["inst"],
                        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                        "parameters":          tb["parameters"],
                        "variants":            tb["variants"],
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
                        block = {
                            "device_type":         tb["device_type"],
                            "block_id":            bid,
                            "inst":                dev["inst"],
                            "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
                            "parameters":          tb["parameters"],
                            "variants":            tb["variants"],
                            "num_pins":            num_pins,
                            "generation_attempts": attempt + 1,
                        }
                        logger.debug("Block %d (%s): %d variant(s)", bid, pdk_type,
                                     len(block["variants"]))
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
    }
    return blocks, netlist, sym_constraints


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(netlist_path: str, seed: int) -> dict:
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

    logger.info("Parsing: %s  seed=%d", path.name, seed)
    top_ports, flat_devices, hierarchy_map = parse_and_flatten(str(path))

    if not flat_devices:
        raise ValueError(f"No devices found in {path.name}")

    blocks, netlist, sym_constraints = wmi_generate_netlist_blocks(
        flat_devices, tech_file, config, seed, top_ports, hierarchy_map
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

    return {
        "generation_params": {
            "num_of_blocks":  len(blocks),
            "seed":           seed,
            "source_netlist": path.name,
        },
        "technology": tech_file["technology_info"]["name"],
        "blocks":     blocks,
        "netlist":    netlist,
        "symmetry_constraints": sym_constraints,
    }


if __name__ == "__main__":
    if len(sys.argv) == 3:
        try:
            run(sys.argv[1], int(sys.argv[2]))
        except (FileNotFoundError, ValueError) as exc:
            logger.error("%s", exc)
            sys.exit(1)
    else:
        logger.error("Usage: 011_netlisBlocksGenerator.py <netlist.sp> <seed>")
        sys.exit(1)
