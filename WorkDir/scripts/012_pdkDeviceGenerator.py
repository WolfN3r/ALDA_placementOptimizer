#!/usr/bin/env python3
"""
Read a SPICE netlist of real PDK devices (e.g. sky130 from xschem), size every
device from the netlist (+ optional parameter JSON files such as an
optimizer's result.json), take its footprint from WorkDir/pdk/<pdk>/pdk.json
via lib/pcell, detect symmetry groups and emit the same JSON schema as
011_netlisBlocksGenerator.

One block per netlist device, its m copies arranged as a rows x cols grid
(x gap: every contact can take its own via; row gap: lib/structure_placer
rule) inside one tight guard ring. Devices with every terminal on one supply
are the netlist's own dummies: they are dropped and listed in
"netlist_dummies" (the dummies a placement needs are added after placement).
Last step: lib/structure_placer builds the matched structures (rows of
copies, row-end dummies, one ring) as groups[].matching_variants for every
active MOS group, every single transistor on a sensitive net (DP core nets,
symmetric nets) and every single-copy resistor or chain of equal series
resistors, each resistor split into s series segments (one variant per s, and
its 90° copy; a lone resistor has no row-end dummies). MIM caps stay one device, reshaped to W/L 1/3..3 at their W*L.
Every MOS structure and resistor chain variant is routed inside its ring (lib/block_router:
"routing" shapes and block pins; sizes grow to the routed ones; unroutable variants dropped).

Standalone:  python 012_pdkDeviceGenerator.py <netlist> <seed> --pdk sky130 [--params result.json ...]
             Returns JSON on stdout  (intended for debugging only)
Pipeline:    called via run(netlist_path, seed, pdk_name, params_paths, sym_mode) from main.py
Output file: s{seed}_n{N}_py012_v01.json  (written by main.py)
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import importlib.util
import itertools
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup         import get_logger
from spice_parser      import parse_netlist
from symmetry_detector import detect_symmetries
from hierarchy_builder import build_groups
from netlist_blocks    import (POWER_ALIASES, build_netlist_json, classify_nets,
                               collapse_passive_arrays, pin_assignment_for, placement_config)
import block_router
import pcell
import pin_access
import structure_placer

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

# Aspect-ratio band (W/H) for the rows x cols arrangements of a device's copies;
# outside it only the closest-to-square arrangement is kept.
_AR_MIN = 0.25
_AR_MAX = 4.0

# MIM cap W/L ratios at constant W*L (user 2026-11-08: roughly 1:3 to 3:1, one device)
_CAP_RATIOS = (1 / 3, 1 / 2, 2 / 3, 1.0, 3 / 2, 2.0, 3.0)

_PASSIVE_CLASSES = frozenset({"res", "cap"})
_MOS_CLASSES = frozenset({"nmos", "pmos"})
_CC_TOPOLOGIES = frozenset({"diff_pair", "cross_coupled"})   # gates inward, common centroid first
_COPY_ROW_NETS = 3          # gate + source + drain wires in the channel between copy rows
_ENDS = ("n1", "n2")        # res "ends" pin group, k = 0 (bottom) first
_IDENT_RE = re.compile(r"[A-Za-z_]\w*(?!\w|\s*\()")     # names, not function calls (sqrt(...))
_ROUND = 6

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

_gen001_cache = None

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _get_gen001():
    """001's pin helpers (centre pins, power pin to the rail edge, 90° rotation)."""
    global _gen001_cache
    if _gen001_cache is None:
        spec = importlib.util.spec_from_file_location("gen001", Path(__file__).parent / "001_L1blocksGenerator.py")
        _gen001_cache = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_gen001_cache)
    return _gen001_cache


# --- 4a. Netlist -> devices ----------------------------------------------------

def _needed_values(entry: dict) -> set:
    """Netlist parameter names the device's PCell map refers to (e.g. W, L, nf)."""
    return {n for expr in entry["map"].values() for n in _IDENT_RE.findall(str(expr))}


def netlist_devices(path, pdk: dict, params: dict) -> tuple:
    """(top_ports, devices, hierarchy_map). Device: inst, pdk_type (model),
    device_class, device_group, terminals, parsed (netlist values the PCell
    needs, None when unresolvable), copies (instance copies x enclosing m)."""
    models = {m.lower(): m for m in pdk["devices"]}
    ports, raw, hier = parse_netlist(path, set(models), params)
    devices = []
    for r in raw:
        model = models[r["model"]]
        entry = pdk["devices"][model]
        vals = r["values"]
        parsed = {n: vals.get(n.lower(), pdk["netlist_defaults"].get(n)) for n in _needed_values(entry)}
        present = [k for k in pdk["netlist_copies"] if vals.get(k) is not None]
        if len({vals[k] for k in present}) > 1:
            logger.warning("%s: copy keywords disagree (%s), using %s",
                           r["inst"], {k: vals[k] for k in present}, present[0])
        copies = int(round((vals[present[0]] if present else 1.0) * r["hier_m"]))
        if len(r["nets"]) != len(entry["terminals"]):
            logger.warning("%s: %d nets for %d terminals %s", r["inst"], len(r["nets"]),
                           len(entry["terminals"]), entry["terminals"])
        devices.append({
            "inst":         r["inst"],
            "pdk_type":     model,
            "device_class": entry["class"],
            "device_group": entry["device_group"],
            "terminals":    dict(zip(entry["terminals"], r["nets"])),
            "parsed":       parsed,
            "copies":       copies,
        })
    return ports, devices, hier


# --- 4b. Copy arrays -------------------------------------------------------------

def copy_array(w: float, h: float, rows: int, cols: int, gx: float, gy: float) -> tuple[float, float]:
    return (round(cols * w + (cols - 1) * gx, _ROUND), round(rows * h + (rows - 1) * gy, _ROUND))


def copy_variants(w: float, h: float, copies: int, gx: float, gy: float) -> list:
    """Every rows x cols factorisation of `copies` inside [_AR_MIN, _AR_MAX],
    closest to square first (is_used); the closest-to-square one alone when
    none is inside. Pins are added by the caller."""
    cands = []
    for rows in range(1, copies + 1):
        if copies % rows:
            continue
        cols = copies // rows
        W, H = copy_array(w, h, rows, cols, gx, gy)
        cands.append((max(W / H, H / W), rows, cols, W, H))
    cands.sort()
    kept = [c for c in cands if _AR_MIN <= c[3] / c[4] <= _AR_MAX] or cands[:1]
    return [{
        "layout":        {"rows": rows, "cols": cols, "aspect_ratio": round(W / H, 3)},
        "main_bbox":     {"x_min": 0.0, "y_min": 0.0, "x_max": W, "y_max": H},
        "pin_positions": {},
        "is_used":       i == 0,
        "rotation_deg":  0,
    } for i, (_, rows, cols, W, H) in enumerate(kept)]


def segment_pcell(pdk: dict, model: str, L: float, s: int) -> dict | None:
    """PCell parameters of one of s equal series segments of a resistor of
    netlist length L, None when shorter than the PCell allows. Every segment
    brings its own end resistance (R = rcon + r_per_um * L), so the s
    segments together are shorter than L by (s - 1) * rcon / r_per_um."""
    ser = pdk["devices"][model]["series"]
    L_seg = (L - (s - 1) * ser["rcon"] / ser["r_per_um"]) / s
    if s > 1 and L_seg < ser["L_min"]:
        return None
    return pcell.pcell_params(pdk, model, {"L": L_seg})


def segment_counts(pdk: dict, model: str, L: float, k: int) -> list:
    """Segment counts s = 1, 2, ... for a chain of k equal resistors of length
    L, up to the first whose one row of k*s segments is at least as wide as tall.
    Only s = 1 for a model without a series (end-resistance) model in pdk.json."""
    if "series" not in pdk["devices"][model]:
        return [1]
    gx = pdk["devices"][model]["gap"]["x"]
    counts, s = [], 1
    while (p := segment_pcell(pdk, model, L, s)) is not None:
        counts.append(s)
        uw, uh = pcell.footprint(pdk, model, p)
        W, H = copy_array(uw, uh, 1, k * s, gx, 0.0)
        if W >= H:
            break
        s += 1
    return counts


def cap_shapes(pdk: dict, model: str, W: float, L: float) -> list:
    """PCell parameters of the cap reshaped to each _CAP_RATIOS W/L at its W*L."""
    area = W * L
    return [pcell.pcell_params(pdk, model, {"W": math.sqrt(area * r), "L": math.sqrt(area / r)})
            for r in _CAP_RATIOS]


def _gaps(pdk: dict, model: str, params: dict) -> tuple[float, float]:
    """Same-model gaps (x in a row, y between equal rows); MOS rows use the
    routed x gap and the structure_placer channel rule; ringless classes use
    their structure-to-structure gap."""
    d = pdk["devices"][model]
    if "x_routed" in d.get("gap", {}):
        return d["gap"]["x_routed"], structure_placer.channel_gap(pdk, model, _COPY_ROW_NETS, "R0", "R0", params)
    if "gap" in d:
        return d["gap"]["x"], d["gap"]["y"]["r0_r0"]
    g = pdk["structure_gap"][f"{d['class']}|{d['class']}"]["min"]
    return g, g


def _cap_detail(pdk: dict, model: str, params: dict, slots: list, terminals: dict) -> dict:
    """Viewer / export detail of a MIM cap variant in the block frame (same "routing" shape as
    lib/block_router): per copy the met3 bottom plate (the whole cell), capm (w x l at the PCell
    origin), the met4 top plate and the met4 bottom-plate strap (pdk.json pins), both as block
    pins. magic extracts the cap as (*mimcap, *m3): n1 = top plate, n2 = bottom plate."""
    fp = pdk["devices"][model]["footprint"]
    x0, y0 = pcell._linear(fp["x0"], params), pcell._linear(fp["y0"], params)
    layer = {g: next(n for n, l in pdk["routing"]["layers"].items() if l["gds"] == pg["layer"])
             for g, pg in pdk["devices"][model]["pins"].items()}      # met4 (cap_mim_m3_1), met5 (m3_2 top)
    pins, devices = [], []
    for s in slots:
        ox, oy = s["x"] - s["w"] / 2 - x0, s["y"] - s["h"] / 2 - y0
        mv = lambda r: [round(r[0] + ox, _ROUND), round(r[1] + oy, _ROUND), round(r[2] + ox, _ROUND), round(r[3] + oy, _ROUND)]
        top = mv(pcell.pin_rects(pdk, model, params, "top")[0])
        bottom = mv(pcell.pin_rects(pdk, model, params, "bottom")[0])
        pins += [{"net": terminals["n1"], "layer": layer["top"], "rect": top, "side": "top_plate"},
                 {"net": terminals["n2"], "layer": layer["bottom"], "rect": bottom, "side": "bottom_plate"}]
        devices.append({"row": s["row"], "col": s["col"], "block_id": s["block_id"],
                        "cap": {"met3": [round(s["x"] - s["w"] / 2, _ROUND), round(s["y"] - s["h"] / 2, _ROUND),
                                         round(s["x"] + s["w"] / 2, _ROUND), round(s["y"] + s["h"] / 2, _ROUND)],
                                "capm": mv((0.0, 0.0, params["w"], params["l"])), "top": top, "bottom": bottom}})
    return {"shapes": [], "pins": pins, "devices": devices}


def _pin_detail(pdk: dict, model: str, params: dict, slots: list, terminals: dict) -> dict:
    """Viewer detail of a variant without in-block routing: per copy every pdk.json pin
    rect in the block frame with its layer (gds) and terminal. A group named after a
    terminal is that terminal; "ends" (res) are _ENDS by order; others (MOS sd) have none."""
    fp = pdk["devices"][model]["footprint"]
    x0, y0 = pcell._linear(fp["x0"], params), pcell._linear(fp["y0"], params)
    rects = {g: pcell.pin_rects(pdk, model, params, g) for g in pdk["devices"][model]["pins"]}
    devices = []
    for s in slots:
        ox, oy = s["x"] - s["w"] / 2 - x0, s["y"] - s["h"] / 2 - y0
        pins = []
        for g, rs in rects.items():
            for k, r in enumerate(rs):
                term = g if g in terminals else _ENDS[k] if g == "ends" and k < len(_ENDS) else None
                pins.append({"terminal": term or g, "net": terminals.get(term) or "",
                             "layer": pdk["devices"][model]["pins"][g]["layer"],
                             "rect": [round(r[0] + ox, _ROUND), round(r[1] + oy, _ROUND),
                                      round(r[2] + ox, _ROUND), round(r[3] + oy, _ROUND)]})
        devices.append({"row": s["row"], "col": s["col"], "block_id": s["block_id"], "pins": pins})
    return {"devices": devices}


# --- 4c. Blocks --------------------------------------------------------------------

def _device_block(dev: dict, pdk: dict, hierarchy_map: dict) -> dict:
    model, cls = dev["pdk_type"], dev["device_class"]
    missing = [k for k, v in dev["parsed"].items() if v is None]
    if missing:
        return {"block_id": dev["block_id"], "inst": dev["inst"],
                "error": f"unresolved netlist values {missing}", "generation_attempts": 1}
    p = pcell.pcell_params(pdk, model, dev["parsed"])
    uw, uh = pcell.footprint(pdk, model, p)
    shapes = cap_shapes(pdk, model, dev["parsed"]["W"], dev["parsed"]["L"]) if cls == "cap" else [p]
    variants = []
    for shape in shapes:
        sw, sh = pcell.footprint(pdk, model, shape)
        gx, gy = _gaps(pdk, model, shape)
        for v in copy_variants(sw, sh, dev["copies"], gx, gy):
            wrap = structure_placer.ring_wrap(pdk, model, v["main_bbox"]["x_max"], v["main_bbox"]["y_max"], "R0", "R0")
            ox, oy = (wrap[2], wrap[3]) if wrap else (0.0, 0.0)
            if wrap:
                v["main_bbox"]["x_max"], v["main_bbox"]["y_max"] = wrap[0], wrap[1]
            # copy positions (centres, unrotated frame) + ring, for the GDS export and the blueprint
            v["slots"] = [{"block_id": dev["block_id"], "dummy": False, "row": r, "col": c, "orient": "R0",
                           "x": round(ox + c * (sw + gx) + sw / 2, _ROUND), "y": round(oy + r * (sh + gy) + sh / 2, _ROUND),
                           "w": sw, "h": sh}
                          for r in range(v["layout"]["rows"]) for c in range(v["layout"]["cols"])]
            v["guard_ring"] = wrap[4] if wrap else None
            v["unit_pcell"] = shape
            if cls == "cap":
                v["routing"] = _cap_detail(pdk, model, shape, v["slots"], dev["terminals"])
            else:
                v["detail"] = _pin_detail(pdk, model, shape, v["slots"], dev["terminals"])
            variants.append(v)
    if len(shapes) > 1:
        variants.sort(key=lambda v: max(v["layout"]["aspect_ratio"], 1 / v["layout"]["aspect_ratio"]))
        for i, v in enumerate(variants):
            v["is_used"] = i == 0
    g01 = _get_gen001()
    if cls in _PASSIVE_CLASSES:
        for v in list(variants):
            if abs(v["main_bbox"]["x_max"] - v["main_bbox"]["y_max"]) >= pdk["grid"]:
                rv = g01.rotate_variant_90cw(v, pdk["grid"])
                # slots stay in the unrotated frame; consumers rotate them by rotation_deg (90° CW)
                rv["slots"], rv["guard_ring"], rv["unit_pcell"] = v["slots"], v["guard_ring"], v["unit_pcell"]
                for key in ("routing", "detail"):
                    if key in v:
                        rv[key] = v[key]
                variants.append(rv)
    num_pins = len(dev["terminals"])
    for v in variants:
        v["pin_positions"] = g01.center_pin_positions(
            num_pins, v["main_bbox"]["x_max"], v["main_bbox"]["y_max"], pdk["grid"])
    parameters = {"width": dev["parsed"].get("W"), "length": dev["parsed"].get("L"),
                  "multiplier": dev["copies"], "pcell": p}
    if "nf" in dev["parsed"]:
        parameters["num_fingers"] = int(dev["parsed"]["nf"])
    block = {
        "device_type":         model,
        "device_class":        cls,
        "block_id":            dev["block_id"],
        "inst":                dev["inst"],
        "hierarchy_path":      hierarchy_map.get(dev["inst"], ""),
        "parameters":          parameters,
        "variants":            variants,
        "num_pins":            num_pins,
        "generation_attempts": 1,
    }
    if cls not in _PASSIVE_CLASSES:
        block["unit_cell_w"], block["unit_cell_h"] = uw, uh
    return block


def generate_blocks(devices: list, pdk: dict, top_ports: list, hierarchy_map: dict) -> tuple:
    """(blocks, netlist, symmetry_constraints) — same steps as 011's
    wmi_generate_netlist_blocks, sizes from the netlist, shapes from pdk.json."""
    all_nets = {n for d in devices for n in d["terminals"].values() if n}
    power_nets  = {n for n in all_nets if n.lower() in POWER_ALIASES}
    signal_nets = {p for p in top_ports if p.lower() not in POWER_ALIASES}
    net_class   = classify_nets(all_nets, top_ports)

    collapsed, inst_to_mult, passive_cluster_info = collapse_passive_arrays(devices)
    sym_result = detect_symmetries(collapsed, signal_nets, power_nets)
    self_sym = {bid for g in sym_result["groups"] for bid in g["self_symmetric"]}

    blocks = []
    for dev in collapsed:
        block = _device_block(dev, pdk, hierarchy_map)
        if "error" in block:
            logger.warning("Block %d (%s): %s", dev["block_id"], dev["inst"], block["error"])
        else:
            if dev["block_id"] in self_sym:
                block["variants"] = [v for v in block["variants"] if v["rotation_deg"] == 0]
            if inst_to_mult.get(dev["inst"], 1) > 1:
                block["array_multiplier"] = inst_to_mult[dev["inst"]]
            block["pin_assignment"] = pin_assignment_for(dev)
            block["terminals"] = dev["terminals"]
            pin_nets = {lbl: dev["terminals"][t] for t, lbl in block["pin_assignment"].items() if dev["terminals"].get(t)}
            for v in block["variants"]:
                if v.get("routing"):
                    pin_access.attach(v, v, pin_nets)
            bulk = dev["terminals"].get("bulk", "") or dev["terminals"].get("substrate", "")
            if bulk and bulk.lower() in POWER_ALIASES:
                block["power_rail"] = "VDD" if "vdd" in bulk.lower() else "VSS"
        blocks.append(block)

    _get_gen001().wmi_adjust_power_pin_positions(
        [b for b in blocks if "error" not in b and "power_rail" in b], pdk["grid"])
    netlist = build_netlist_json([b for b in blocks if "error" not in b], net_class)
    sym_constraints = {
        "groups":              sym_result["groups"],
        "passive_clusters":    passive_cluster_info,
        "symmetric_net_pairs": sym_result["symmetric_net_pairs"],
        "self_symmetric_nets": sym_result["self_symmetric_nets"],
        "building_blocks":     sym_result["building_blocks"],
        "logical_devices":     sym_result["logical_devices"],
    }
    return blocks, netlist, sym_constraints


# --- 4d. Netlist dummies -----------------------------------------------------------

def split_netlist_dummies(devices: list) -> tuple[list, list]:
    """(devices, dummies): a dummy has every terminal on one supply net."""
    keep, dummies = [], []
    for d in devices:
        nets = set(d["terminals"].values())
        if len(nets) == 1 and next(iter(nets)).lower() in POWER_ALIASES:
            dummies.append({"inst": d["inst"], "model": d["pdk_type"], "parsed": d["parsed"], "copies": d["copies"]})
        else:
            keep.append(d)
    return keep, dummies


# --- 4e. Matched structures ----------------------------------------------------------

def _member(b: dict) -> dict:
    return {"block_id": b["block_id"], "copies": b["parameters"]["multiplier"], "model": b["device_type"],
            "pcell": b["parameters"]["pcell"], "terminals": b["terminals"]}


def _rail(b: dict) -> str:
    return b["terminals"].get("bulk") or b["terminals"].get("substrate")


def _external_nets(bids: list, by_id: dict, top_ports: list, rail: str) -> set:
    """Nets of the members that leave the group (another block or a top port), not the rail."""
    outside = {n for b in by_id.values() if b["block_id"] not in bids for n in b["terminals"].values()}
    nets = {n for x in bids for t, n in by_id[x]["terminals"].items() if t not in ("bulk", "substrate")}
    return {n for n in nets if n != rail and (n in outside or n in top_ports)}


def _routed(pdk: dict, variants: list, members: list, rail: str, external: set) -> list:
    """Every variant with its in-block routing (lib/block_router; size, ring and orientation
    may change). Unroutable variants are dropped; if none routes, the unrouted ones stay."""
    routed = [r for r in (block_router.route_structure(pdk, v, members, rail, external) for v in variants) if r]
    if not routed:
        logger.warning("Structure %s: no variant routable, kept unrouted", [m["block_id"] for m in members])
        return variants
    for i, v in enumerate(routed):
        v["is_used"] = i == 0
    return routed


def _sensitive_nets(sym_constraints: dict) -> set:
    nets = {n for cg in sym_constraints["groups"] for n in cg.get("core_nets", [])}
    nets |= {p[k] for p in sym_constraints["symmetric_net_pairs"] for k in ("net_a", "net_b")}
    nets |= set(sym_constraints["self_symmetric_nets"])
    return {n for n in nets if n.lower() not in POWER_ALIASES}


def resistor_chains(blocks: list, top_ports: list) -> list:
    """Chains (series order) of >= 2 equal single-copy resistors joined by
    internal nets that touch exactly two terminals, both in the chain."""
    degree: dict = {}
    for b in blocks:
        for term, net in b["terminals"].items():
            if term not in ("bulk", "substrate"):
                degree[net] = degree.get(net, 0) + 1
    outside = {p.lower() for p in top_ports} | POWER_ALIASES
    res = [b for b in blocks if b["device_class"] == "res" and b["parameters"]["multiplier"] == 1
           and "array_multiplier" not in b]
    key = lambda b: (b["device_type"], tuple(sorted(b["parameters"]["pcell"].items())), _rail(b))
    links: dict = {b["block_id"]: [] for b in res}
    for a, b in itertools.combinations(res, 2):
        if key(a) != key(b):
            continue
        shared = {a["terminals"]["n1"], a["terminals"]["n2"]} & {b["terminals"]["n1"], b["terminals"]["n2"]}
        if any(degree[n] == 2 and n.lower() not in outside for n in shared):
            links[a["block_id"]].append(b["block_id"])
            links[b["block_id"]].append(a["block_id"])
    chains, seen = [], set()
    for start in sorted(links):
        if start in seen or len(links[start]) != 1:
            continue
        chain, prev = [start], None
        while True:
            nxt = [x for x in links[chain[-1]] if x != prev]
            if not nxt:
                break
            prev = chain[-1]
            chain.append(nxt[0])
        seen.update(chain)
        if len(chain) >= 2 and all(len(links[x]) <= 2 for x in chain):
            chains.append(chain)
    return chains


def _segmented_variants(pdk: dict, mem: list, ar: tuple, external: set) -> list:
    """One row per segment count s (segment_counts) of the chain's equal
    resistors, each split into s series segments and routed, plus its 90° copy;
    closest to square first (is_used)."""
    model, L = mem[0]["device_type"], mem[0]["parameters"]["length"]
    variants = []
    for s in segment_counts(pdk, model, L, len(mem)):
        # s = 1 is the resistor itself (also for models whose PCell needs more than L, e.g. W)
        seg = mem[0]["parameters"]["pcell"] if s == 1 else segment_pcell(pdk, model, L, s)
        members = [dict(_member(m), copies=s, pcell=seg) for m in mem]
        v = structure_placer.structure_variants(pdk, members, "chain", _rail(mem[0]), ar)[0]
        v = block_router.route_structure(pdk, v, members, _rail(mem[0]), external)
        v.update(segments=s, rotation_deg=0)
        variants.append(v)
        if abs(v["width_um"] - v["height_um"]) >= pdk["grid"]:
            # slots stay in the unrotated frame; consumers rotate them by rotation_deg (90° CW)
            variants.append(dict(v, width_um=v["height_um"], height_um=v["width_um"], rotation_deg=90))
    variants.sort(key=lambda v: max(v["width_um"] / v["height_um"], v["height_um"] / v["width_um"]))
    for i, v in enumerate(variants):
        v["is_used"] = i == 0
    return variants


def add_structures(groups: list, blocks: list, sym_constraints: dict, top_ports: list, pdk: dict) -> list:
    """Structure variants for every active MOS group; new groups for sensitive
    single transistors and resistor chains (replacing their passive groups)."""
    by_id = {b["block_id"]: b for b in blocks if "error" not in b}
    ar = (_AR_MIN, _AR_MAX)
    in_active = set()
    for g in groups:
        mem = [by_id[b] for b in g["block_ids"] if b in by_id]
        proximity = any(v.get("matching_type") == "proximity" for v in g.get("matching_variants", []))
        if g["topology_type"] == "passive_free":
            continue
        in_active.update(g["block_ids"])
        if proximity:
            rows = [[_member(m) for m in mem if m["device_class"] == cls] for cls in ("nmos", "pmos")]
            g["matching_variants"] = [structure_placer.digital_variant(pdk, [r for r in rows if r])]
            continue
        if mem and all(m["device_class"] in _MOS_CLASSES for m in mem):
            kind = "cc" if g["topology_type"] in _CC_TOPOLOGIES else "mirror"
            members, rail = [_member(m) for m in mem], _rail(mem[0])
            g["matching_variants"] = _routed(
                pdk, structure_placer.structure_variants(pdk, members, kind, rail, ar), members, rail,
                _external_nets([m["block_id"] for m in mem], by_id, top_ports, rail))

    next_id = max((g["group_id"] for g in groups), default=-1) + 1
    new = []
    sensitive = _sensitive_nets(sym_constraints)
    for b in by_id.values():
        if b["device_class"] in _MOS_CLASSES and b["block_id"] not in in_active \
                and {b["terminals"]["gate"], b["terminals"]["drain"]} & sensitive:
            members = [_member(b)]
            new.append(("single_sensitive", [b["block_id"]], _routed(
                pdk, structure_placer.structure_variants(pdk, members, "single", _rail(b), ar), members, _rail(b),
                _external_nets([b["block_id"]], by_id, top_ports, _rail(b)))))
    chains = [c for c in resistor_chains(list(by_id.values()), top_ports) if not set(c) & in_active]
    in_chain = {x for c in chains for x in c} | in_active
    chains += [[b["block_id"]] for b in by_id.values() if b["device_class"] == "res" and b["block_id"] not in in_chain
               and b["parameters"]["multiplier"] == 1 and "array_multiplier" not in b]
    for chain in chains:
        new.append(("res_chain", chain, _segmented_variants(
            pdk, [by_id[x] for x in chain], ar, _external_nets(chain, by_id, top_ports, _rail(by_id[chain[0]])))))
    chained = {x for c in chains for x in c}
    groups = [g for g in groups if not (g["topology_type"] == "passive_free" and set(g["block_ids"]) & chained)]
    for k, (topo, bids, variants) in enumerate(new):
        groups.append({"group_id": next_id + k, "topology_type": topo, "block_ids": bids,
                       "matching_variants": variants, "intra_spacing": {"x_um": 0.0, "y_um": 0.0},
                       "symmetry": None, "ungroup": False})
        logger.info("Structure group %d: %s %s", next_id + k, topo, bids)
    return groups


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def _load_params(paths) -> dict:
    params: dict = {}
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not all(isinstance(v, (int, float)) for v in data.values()):
            raise ValueError(f"{p}: expected a flat JSON object of numbers")
        params.update(data)
    return params


def run(netlist_path: str, seed: int, pdk_name: str = "sky130", params_paths=(),
        sym_mode: str = "balanced") -> dict:
    path = Path(netlist_path)
    if not path.exists():
        raise FileNotFoundError(f"Netlist not found: {path}")
    pdk = pcell.load_pdk(pdk_name)
    for key in ("pdk", "grid", "devices", "netlist_defaults", "netlist_copies", "structure_gap",
                "guard_rings", "tracks", "layout_policy"):
        if key not in pdk:
            raise KeyError(f"run: pdk.json missing {key!r}")
    params = _load_params(params_paths)

    logger.info("Parsing: %s  pdk=%s  params=%s  sym_mode=%s", path.name, pdk_name, list(params_paths), sym_mode)
    top_ports, devices, hierarchy_map = netlist_devices(path, pdk, params)
    if not devices:
        raise ValueError(f"No {pdk['pdk']} devices found in {path.name}")
    devices, netlist_dummies = split_netlist_dummies(devices)
    if netlist_dummies:
        logger.info("Netlist dummies dropped: %s", [d["inst"] for d in netlist_dummies])

    blocks, netlist, sym_constraints = generate_blocks(devices, pdk, top_ports, hierarchy_map)
    n_valid = sum(1 for b in blocks if "error" not in b)
    logger.info("Done: %d blocks (%d valid), %d nets", len(blocks), n_valid, netlist["num_nets"])

    pconf = placement_config(sym_mode)
    groups = add_structures(build_groups(sym_constraints, blocks, pconf), blocks, sym_constraints, top_ports, pdk)
    return {
        "generation_params": {
            "num_of_blocks":  len(blocks),
            "seed":           seed,
            "source_netlist": path.name,
            "pdk":            pdk_name,
            "params_files":   [Path(p).name for p in params_paths],
        },
        "technology":           pdk["pdk"],
        "placement_config":     pconf,
        "blocks":               blocks,
        "netlist":              netlist,
        "symmetry_constraints": sym_constraints,
        "groups":               groups,
        "netlist_dummies":      netlist_dummies,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate placement JSON from a PDK-device SPICE netlist")
    parser.add_argument("netlist", help="Path to SPICE netlist")
    parser.add_argument("seed", type=int, help="Seed (recorded; generation is deterministic)")
    parser.add_argument("--pdk", default="sky130", help="Folder under WorkDir/pdk/ (default: sky130)")
    parser.add_argument("--params", action="append", default=[],
                        help="JSON file of design parameter values (repeatable, later files win)")
    parser.add_argument("--sym-mode", default="balanced", choices=["matched", "balanced", "mirrored"],
                        dest="sym_mode")
    args = parser.parse_args()
    try:
        result = run(args.netlist, args.seed, pdk_name=args.pdk, params_paths=args.params,
                     sym_mode=args.sym_mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
