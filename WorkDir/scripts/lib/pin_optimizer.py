#!/usr/bin/env python3
"""
Post-placement pin position optimizer.

Rules applied in order:
  1. Power pins (P0 + any pin whose net matches the block's power_rail type) →
     full-width M1 stripe at top (VDD) or bottom (VSS).  Co-located for
     same-net power pins on the same block (merged).

  2. Signal pins on symmetric block pairs:
     - Shared nets (net connects BOTH blocks in the pair) → inner side (facing
       the symmetry axis).  Y position is the same for corresponding mirrored
       pins to maintain layout symmetry.
     - Non-shared nets → outer side.

  3. All remaining signal pins → ILP-minimises net HPWL.
     Routing-grid aligned, fully inside main_bbox, no power-stripe overlap.

  4. Chip-level power rails → wide M1 rectangles above (VDD) and below (VSS)
     the full placement bounding box, stored as "__chip_*" keys.

All pin rectangles are guaranteed to lie fully within their block's main_bbox.
"""
from __future__ import annotations

import json
import math
from itertools import combinations
from pathlib import Path

# PDK geometry constants (gpdk090, from gpdk090_tech_simple.json)
_PIN_W       = 0.24   # signal pin rectangle width/height (µm); VIA1 cut+2×enc
_PIN_HALF    = _PIN_W / 2     # 0.12
_M1_SPC      = 0.12   # M1 min_spacing (µm)
_MIN_CC      = _PIN_W + _M1_SPC   # 0.36 µm min centre-to-centre for two signal pins
_PWR_W       = 0.20   # block-level power rail stripe width (µm)
_CHIP_RAIL_W = 0.50   # chip-level power rail width (µm, from routing_widths.power)
_SIDES       = ("left", "right")

# Power net name sets — must stay consistent with cost_evaluator._VDD/_VSS_NET_IDS
_VDD_NAMES: frozenset[str] = frozenset({"VDD", "AVDD", "VCC", "VDDA"})
_VSS_NAMES: frozenset[str] = frozenset({"VSS", "GND", "AGND", "VSSA"})

_DEFAULT_PDK_PATH = Path(__file__).parent.parent.parent / "myPDK" / "gpdk090_tech_simple.json"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _s6(v: float) -> float:
    return round(v, 6)


def _load_default_pdk() -> dict:
    return json.loads(_DEFAULT_PDK_PATH.read_text(encoding="utf-8"))


def _net_rail(net_id: str) -> str | None:
    """Return 'VDD', 'VSS', or None for a net identifier."""
    nid = net_id.upper()
    if nid in _VDD_NAMES:
        return "VDD"
    if nid in _VSS_NAMES:
        return "VSS"
    return None


def _power_net_names(nets: list) -> tuple[str, str]:
    """Return the actual VDD and VSS net names (e.g. 'vdda', 'vssa')."""
    vdd_name, vss_name = "VDD", "VSS"
    for net in nets:
        nid = net.get("net_id", "")
        if net.get("net_type") == "power":
            rail = _net_rail(nid)
            if rail == "VDD":
                vdd_name = nid
            elif rail == "VSS":
                vss_name = nid
    return vdd_name, vss_name


# ---------------------------------------------------------------------------
# Grid slot enumeration
# ---------------------------------------------------------------------------

def _grid_slots(bbox: dict, pdk: dict, rail: str | None = None) -> list[float]:
    """
    Return absolute routing-grid Y centres valid for a signal pin inside bbox.

    Power-stripe exclusion (prevents signal pins from overlapping the stripe):
      VDD  → y_ctr  ≤  y_max − _PWR_W − _M1_SPC − _PIN_HALF  (= y_max − 0.44)
      VSS  → y_ctr  ≥  y_min + _PWR_W + _M1_SPC + _PIN_HALF  (= y_min + 0.44)
    """
    pitch  = pdk["routing_grid"]["vertical_pitch"]   # 0.28
    offset = pdk["routing_grid"]["offset_y"]         # 0.14
    y_lo   = bbox["y_min"] + _PIN_HALF
    y_hi   = bbox["y_max"] - _PIN_HALF

    if rail == "VDD":
        y_hi = min(y_hi, bbox["y_max"] - _PWR_W - _M1_SPC - _PIN_HALF)
    elif rail == "VSS":
        y_lo = max(y_lo, bbox["y_min"] + _PWR_W + _M1_SPC + _PIN_HALF)

    if y_hi < y_lo - 1e-9:
        return []
    k = math.ceil((y_lo - offset - 1e-9) / pitch)
    slots: list[float] = []
    while True:
        y = _s6(offset + k * pitch)
        if y > y_hi + 1e-9:
            break
        if y >= y_lo - 1e-9:
            slots.append(y)
        k += 1
    return slots


# ---------------------------------------------------------------------------
# Pin rectangle constructors
# ---------------------------------------------------------------------------

def power_pin_rect(bbox: dict, rail: str, pdk: dict) -> dict:  # noqa: ARG001
    """Full-width M1 stripe on top edge (VDD) or bottom edge (VSS), inside bbox."""
    x0, y0, x1, y1 = bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]
    if rail == "VDD":
        ry0, ry1 = _s6(y1 - _PWR_W), _s6(y1)
    else:
        ry0, ry1 = _s6(y0), _s6(y0 + _PWR_W)
    return {
        "layer": "M1", "type": "power",
        "side": "top" if rail == "VDD" else "bottom",
        "x_min": _s6(x0), "y_min": ry0,
        "x_max": _s6(x1), "y_max": ry1,
    }


def _sig_rect(bbox: dict, side: str, y_ctr: float) -> dict:
    """0.24 × 0.24 µm M1 rectangle for a signal pin, fully inside bbox."""
    if side == "left":
        rx0, rx1 = _s6(bbox["x_min"]), _s6(bbox["x_min"] + _PIN_W)
    else:
        rx0, rx1 = _s6(bbox["x_max"] - _PIN_W), _s6(bbox["x_max"])
    return {
        "layer": "M1", "type": "signal", "side": side,
        "x_min": rx0, "y_min": _s6(y_ctr - _PIN_HALF),
        "x_max": rx1, "y_max": _s6(y_ctr + _PIN_HALF),
    }


def _pin_x_ctr(bbox: dict, side: str) -> float:
    return bbox["x_min"] + _PIN_HALF if side == "left" else bbox["x_max"] - _PIN_HALF


# ---------------------------------------------------------------------------
# Power pin map builder
# ---------------------------------------------------------------------------

def _build_pwr_map(
    placed_blocks: dict,
    blocks: dict,
    nets: list,
) -> dict[str, dict[str, str]]:
    """
    Return {bid_str: {pname: rail_type}} for every pin that should be rendered
    as a power stripe.  Includes P0 (designated power pin) and any additional
    pin on the same block whose net matches the block's power_rail type.
    """
    pin_net: dict[str, str] = {
        pref: net.get("net_id", "")
        for net in nets
        for pref in net.get("pins", [])
    }
    pwr: dict[str, dict[str, str]] = {}
    for bid_str, pb in placed_blocks.items():
        block_rail = (blocks.get(bid_str) or {}).get("power_rail")
        if not block_rail:
            continue
        for pname in pb["pins"]:
            pref   = f"B{bid_str}_{pname}"
            nid    = pin_net.get(pref, "")
            p_rail = _net_rail(nid)
            if pname == "P0" or p_rail == block_rail:
                pwr.setdefault(bid_str, {})[pname] = block_rail
    return pwr


# ---------------------------------------------------------------------------
# Symmetry-aware side/Y info
# ---------------------------------------------------------------------------

def _build_sym_info(
    placed_blocks: dict,
    sym_groups: list,
    nets: list,
    pwr: dict,
) -> tuple[dict[tuple[str, str], int], list[tuple]]:
    """
    Analyse placed symmetry pairs and return:

    forced_side : {(bid_str, pname): side_index}
        0 = left, 1 = right.
        Shared nets (connecting both blocks) → inner side (facing the other block).
        Non-shared nets → outer side.

    y_pairs : [(bid_L, pname_L, si_L, bid_R, pname_R, si_R), ...]
        Pin pairs that must use the same routing-grid slot index.
        Covers same-net pairs (hard Y symmetry) and same-label non-shared pairs
        (mirror-position symmetry from symmetric_net_pairs).
    """
    # pin_ref → net_id, and net_id → set of block IDs that participate
    pin_net: dict[str, str] = {}
    net_blocks: dict[str, set[str]] = {}
    for net in nets:
        nid = net.get("net_id", "")
        for pref in net.get("pins", []):
            pin_net[pref] = nid
            bid_str = pref.split("_", 1)[0][1:]
            net_blocks.setdefault(nid, set()).add(bid_str)

    forced_side: dict[tuple[str, str], int] = {}
    y_pairs: list[tuple] = []

    for group in sym_groups:
        axis = group.get("axis", "vertical")
        if axis != "vertical":
            continue  # only vertical symmetry axes for left/right side logic

        for pair in group.get("pairs", []):
            if len(pair) != 2:
                continue
            bid_a, bid_b = str(pair[0]), str(pair[1])
            if bid_a not in placed_blocks or bid_b not in placed_blocks:
                continue

            # Determine left (smaller x_center) and right blocks
            bb_a = placed_blocks[bid_a]["main_bbox"]
            bb_b = placed_blocks[bid_b]["main_bbox"]
            cx_a = (bb_a["x_min"] + bb_a["x_max"]) / 2
            cx_b = (bb_b["x_min"] + bb_b["x_max"]) / 2
            left_bid  = bid_a if cx_a <= cx_b else bid_b
            right_bid = bid_b if cx_a <= cx_b else bid_a

            # Signal pin sets (power pins already merged, skip them)
            left_sig  = [p for p in placed_blocks[left_bid]["pins"]
                         if p not in pwr.get(left_bid, {})]
            right_sig = [p for p in placed_blocks[right_bid]["pins"]
                         if p not in pwr.get(right_bid, {})]

            left_sig_set  = set(left_sig)
            right_sig_set = set(right_sig)

            # Classify each signal pin: shared (net touches both blocks) or not
            # Left block: shared → inner = right (si=1), non-shared → outer = left (si=0)
            for pname in left_sig:
                pref = f"B{left_bid}_{pname}"
                nid  = pin_net.get(pref, "")
                is_shared = right_bid in net_blocks.get(nid, set())
                forced_side[(left_bid, pname)] = 1 if is_shared else 0

            # Right block: shared → inner = left (si=0), non-shared → outer = right (si=1)
            for pname in right_sig:
                pref = f"B{right_bid}_{pname}"
                nid  = pin_net.get(pref, "")
                is_shared = left_bid in net_blocks.get(nid, set())
                forced_side[(right_bid, pname)] = 0 if is_shared else 1

            # Y-symmetry pairs: pins with the same label in both blocks must share the
            # same routing-grid slot index to maintain physical layout symmetry
            for pname in left_sig_set & right_sig_set:
                si_l = forced_side.get((left_bid, pname), 0)
                si_r = forced_side.get((right_bid, pname), 0)
                y_pairs.append((left_bid, pname, si_l, right_bid, pname, si_r))

    return forced_side, y_pairs


# ---------------------------------------------------------------------------
# Chip-level power rails
# ---------------------------------------------------------------------------

def _compute_chip_rails(placed_blocks: dict, nets: list, pdk: dict) -> dict:
    """Wide M1 rails above (VDD) and below (VSS) the full placement bounding box."""
    chip_bboxes = [
        pb["main_bbox"] for pb in placed_blocks.values()
        if isinstance(pb, dict) and "main_bbox" in pb
    ]
    if not chip_bboxes:
        return {}

    x_min = min(b["x_min"] for b in chip_bboxes)
    x_max = max(b["x_max"] for b in chip_bboxes)
    y_min = min(b["y_min"] for b in chip_bboxes)
    y_max = max(b["y_max"] for b in chip_bboxes)

    m1_spc  = float(pdk["metal_layers"]["M1"]["min_spacing"])
    tables  = pdk["routing_widths"]["wire_width_tables"].get("power", [[0, _CHIP_RAIL_W]])
    rail_w  = float(tables[0][1]) if tables else _CHIP_RAIL_W

    vdd_name, vss_name = _power_net_names(nets)

    return {
        "__chip_vdd_rail__": {
            "layer": "M1", "net": vdd_name,
            "x_min": _s6(x_min), "y_min": _s6(y_max + m1_spc),
            "x_max": _s6(x_max), "y_max": _s6(y_max + m1_spc + rail_w),
        },
        "__chip_vss_rail__": {
            "layer": "M1", "net": vss_name,
            "x_min": _s6(x_min), "y_min": _s6(y_min - m1_spc - rail_w),
            "x_max": _s6(x_max), "y_max": _s6(y_min - m1_spc),
        },
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def optimize_pin_positions(
    placed_blocks: dict,
    nets: list,
    blocks: dict,
    pdk: dict | None = None,
    sym_groups: list | None = None,
) -> dict:
    """
    Replace center-point pins with physical M1 rectangles.

    placed_blocks : output of _compute_placed_blocks
        {bid_str: {"main_bbox": {...}, "pins": {pname: {x,y}}}}
    nets          : [{net_id, net_type, pins: ["B0_P1", ...]}, ...]
    blocks        : {bid_str: {"power_rail": "VDD"|"VSS"|None, ...}}
    pdk           : PDK tech dict (auto-loaded if None)
    sym_groups    : symmetry group list from symmetry_constraints["groups"]
                    If provided, enables symmetry-aware side/Y placement.
    """
    if pdk is None:
        pdk = _load_default_pdk()

    pwr = _build_pwr_map(placed_blocks, blocks, nets)

    # Symmetry info (forced sides + Y pairs)
    sym_info: tuple | None = None
    if sym_groups:
        sym_info = _build_sym_info(placed_blocks, sym_groups, nets, pwr)

    # Routing-grid slots (power stripe zone excluded)
    slots_by: dict[str, list[float]] = {
        bid_str: _grid_slots(
            pb["main_bbox"], pdk,
            rail=(blocks.get(bid_str) or {}).get("power_rail"),
        )
        for bid_str, pb in placed_blocks.items()
    }

    sig: list[tuple[str, str]] = [
        (bid_str, pname)
        for bid_str, pb in placed_blocks.items()
        for pname in pb["pins"]
        if pname not in pwr.get(bid_str, {})
    ]

    ref_idx: dict[str, tuple[str, str]] = {
        f"B{bid_str}_{pname}": (bid_str, pname)
        for bid_str, pb in placed_blocks.items()
        for pname in pb["pins"]
    }

    try:
        selected = _ilp(placed_blocks, nets, pdk, blocks, pwr, slots_by, sig, ref_idx, sym_info)
    except Exception as exc:
        import warnings
        warnings.warn(f"pin_optimizer ILP failed ({exc}); using greedy fallback", stacklevel=2)
        selected = _greedy(placed_blocks, nets, pdk, blocks, pwr, slots_by, sig, ref_idx, sym_info)

    result = _build(placed_blocks, blocks, pwr, pdk, selected, slots_by)
    _tag_nets(result, nets, ref_idx)
    result.update(_compute_chip_rails(result, nets, pdk))
    return result


# ---------------------------------------------------------------------------
# ILP optimizer
# ---------------------------------------------------------------------------

def _ilp(
    placed_blocks, nets, pdk, blocks, pwr, slots_by, sig, ref_idx,
    sym_info,
) -> dict[tuple[str, str], tuple[str, float]]:
    import gurobipy as gp
    from gurobipy import GRB

    m = gp.Model("pin_opt")
    m.setParam("OutputFlag", 0)
    m.setParam("TimeLimit", 60)

    z: dict = {}
    combos: dict[tuple[str, str], list[tuple[int, int, float]]] = {}

    for bid_str, pname in sig:
        slots = slots_by[bid_str]
        c: list[tuple[int, int, float]] = []
        for si in range(2):
            for ki, yc in enumerate(slots):
                key = (bid_str, pname, si, ki)
                z[key] = m.addVar(vtype=GRB.BINARY, name=f"z_{bid_str}_{pname}_{si}_{ki}")
                c.append((si, ki, yc))
        combos[(bid_str, pname)] = c
    m.update()

    # Assignment: exactly one position per signal pin
    for bid_str, pname in sig:
        c = combos[(bid_str, pname)]
        if c:
            m.addConstr(
                gp.quicksum(z[bid_str, pname, si, ki] for si, ki, _ in c) == 1,
                name=f"assign_{bid_str}_{pname}",
            )

    # Spacing: no two pins on same block-edge within _MIN_CC
    block_pins: dict[str, list[str]] = {}
    for bid_str, pname in sig:
        block_pins.setdefault(bid_str, []).append(pname)

    for bid_str, pnames in block_pins.items():
        if len(pnames) < 2:
            continue
        slots = slots_by[bid_str]
        for si in range(2):
            for ki1, y1 in enumerate(slots):
                for ki2, y2 in enumerate(slots):
                    if abs(y1 - y2) < _MIN_CC - 1e-9:
                        for p1, p2 in combinations(pnames, 2):
                            k1 = (bid_str, p1, si, ki1)
                            k2 = (bid_str, p2, si, ki2)
                            if k1 in z and k2 in z:
                                m.addConstr(z[k1] + z[k2] <= 1)

    # Symmetry constraints: force sides and enforce Y parity
    if sym_info is not None:
        forced_side, y_pairs = sym_info

        # Side forcing: zero out variables on the non-preferred side
        for (bid_str, pname), si_forced in forced_side.items():
            if not slots_by.get(bid_str):
                continue  # block has no valid slots — skip
            si_other = 1 - si_forced
            for ki in range(len(slots_by[bid_str])):
                key = (bid_str, pname, si_other, ki)
                if key in z:
                    m.addConstr(z[key] == 0, name=f"side0_{bid_str}_{pname}_{ki}")

        # Y equality: corresponding mirror pins must land on the same slot index
        for lid, lpname, lsi, rid, rpname, rsi in y_pairs:
            slots_l = slots_by.get(lid, [])
            slots_r = slots_by.get(rid, [])
            if not slots_l or not slots_r:
                continue
            n_common = min(len(slots_l), len(slots_r))
            for ki in range(n_common):
                kl = (lid, lpname, lsi, ki)
                kr = (rid, rpname, rsi, ki)
                if kl in z and kr in z:
                    m.addConstr(z[kl] == z[kr], name=f"ysym_{lid}_{lpname}_{rid}_{rpname}_{ki}")
            # Force out-of-range slots to 0 if one block has more slots than the other
            for ki in range(n_common, len(slots_l)):
                kl = (lid, lpname, lsi, ki)
                if kl in z:
                    m.addConstr(z[kl] == 0)
            for ki in range(n_common, len(slots_r)):
                kr = (rid, rpname, rsi, ki)
                if kr in z:
                    m.addConstr(z[kr] == 0)

    # HPWL bounding-box linearisation per net
    chip_x = [pb["main_bbox"]["x_min"] for pb in placed_blocks.values()] + \
             [pb["main_bbox"]["x_max"] for pb in placed_blocks.values()]
    chip_y = [pb["main_bbox"]["y_min"] for pb in placed_blocks.values()] + \
             [pb["main_bbox"]["y_max"] for pb in placed_blocks.values()]
    X0, X1 = min(chip_x), max(chip_x)
    Y0, Y1 = min(chip_y), max(chip_y)

    hpwl_parts: list = []
    for net in nets:
        pin_refs = net.get("pins", [])
        if not pin_refs:
            continue
        xl = m.addVar(lb=X0, ub=X1)
        xh = m.addVar(lb=X0, ub=X1)
        yl = m.addVar(lb=Y0, ub=Y1)
        yh = m.addVar(lb=Y0, ub=Y1)
        active = False

        for pref in pin_refs:
            if pref not in ref_idx:
                continue
            bid_str, pname = ref_idx[pref]
            bbox  = placed_blocks[bid_str]["main_bbox"]
            p_pwr = pwr.get(bid_str, {})

            if pname in p_pwr:
                rail = p_pwr[pname]
                px = (bbox["x_min"] + bbox["x_max"]) / 2
                py = (bbox["y_max"] - _PWR_W / 2) if rail == "VDD" else (bbox["y_min"] + _PWR_W / 2)
                m.addConstr(xl <= px); m.addConstr(xh >= px)
                m.addConstr(yl <= py); m.addConstr(yh >= py)
                active = True
            else:
                c = combos.get((bid_str, pname), [])
                if not c:
                    continue
                x_expr = gp.quicksum(
                    z[bid_str, pname, si, ki] * _pin_x_ctr(bbox, _SIDES[si])
                    for si, ki, _ in c
                )
                y_expr = gp.quicksum(
                    z[bid_str, pname, si, ki] * yc
                    for si, ki, yc in c
                )
                m.addConstr(xl <= x_expr); m.addConstr(xh >= x_expr)
                m.addConstr(yl <= y_expr); m.addConstr(yh >= y_expr)
                active = True

        if active:
            hpwl_parts += [xh - xl, yh - yl]

    m.setObjective(gp.quicksum(hpwl_parts) if hpwl_parts else 0.0, GRB.MINIMIZE)
    m.optimize()

    if m.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL):
        raise RuntimeError(f"Gurobi status {m.status}")

    selected: dict[tuple[str, str], tuple[str, float]] = {}
    for bid_str, pname in sig:
        for si, ki, yc in combos[(bid_str, pname)]:
            if z.get((bid_str, pname, si, ki)) and z[bid_str, pname, si, ki].X > 0.5:
                selected[(bid_str, pname)] = (_SIDES[si], yc)
                break
        if (bid_str, pname) not in selected:
            c = combos[(bid_str, pname)]
            if c:
                selected[(bid_str, pname)] = (_SIDES[c[0][0]], c[0][2])
    return selected


# ---------------------------------------------------------------------------
# Greedy fallback (coordinate descent)
# ---------------------------------------------------------------------------

def _greedy(
    placed_blocks, nets, pdk, blocks, pwr, slots_by, sig, ref_idx,  # noqa: ARG001
    sym_info,
) -> dict[tuple[str, str], tuple[str, float]]:
    """Coordinate descent with optional symmetry side constraints."""
    forced_side: dict[tuple[str, str], int] = {}
    y_pairs: list[tuple] = []
    if sym_info is not None:
        forced_side, y_pairs = sym_info

    # Initialise: forced side (if any) or left, closest grid slot to block centre
    current: dict[tuple[str, str], tuple[str, float]] = {}
    for bid_str, pname in sig:
        slots = slots_by[bid_str]
        bbox  = placed_blocks[bid_str]["main_bbox"]
        cy    = (bbox["y_min"] + bbox["y_max"]) / 2
        yc    = min(slots, key=lambda y: abs(y - cy)) if slots else _s6(cy)
        si    = forced_side.get((bid_str, pname), 0)
        current[(bid_str, pname)] = (_SIDES[si], yc)

    nets_by_pref: dict[str, list[list[str]]] = {}
    for net in nets:
        prefs = net.get("pins", [])
        for pref in prefs:
            nets_by_pref.setdefault(pref, []).append(prefs)

    def _net_hpwl(pin_refs: list[str]) -> float:
        xs, ys = [], []
        for pref in pin_refs:
            if pref not in ref_idx:
                continue
            bid_str, pname = ref_idx[pref]
            bbox  = placed_blocks[bid_str]["main_bbox"]
            p_pwr = pwr.get(bid_str, {})
            if pname in p_pwr:
                rail = p_pwr[pname]
                xs.append((bbox["x_min"] + bbox["x_max"]) / 2)
                ys.append(bbox["y_max"] - _PWR_W / 2 if rail == "VDD" else bbox["y_min"] + _PWR_W / 2)
            else:
                side, yc = current.get((bid_str, pname), ("left", (bbox["y_min"] + bbox["y_max"]) / 2))
                xs.append(_pin_x_ctr(bbox, side))
                ys.append(yc)
        if len(xs) < 2:
            return 0.0
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    # Build Y-pair lookup for fast partner retrieval
    y_partner: dict[tuple[str, str], tuple[str, str, int]] = {}
    for lid, lpname, lsi, rid, rpname, rsi in y_pairs:
        y_partner[(lid, lpname)] = (rid, rpname, rsi)
        y_partner[(rid, rpname)] = (lid, lpname, lsi)

    for _ in range(20):
        improved = False
        for bid_str, pname in sig:
            slots = slots_by[bid_str]
            pref  = f"B{bid_str}_{pname}"
            relevant = nets_by_pref.get(pref, [])
            if not relevant or not slots:
                continue

            # Restrict to forced side if set
            si_forced = forced_side.get((bid_str, pname))
            allowed_sides = [_SIDES[si_forced]] if si_forced is not None else list(_SIDES)

            best_cost = sum(_net_hpwl(rp) for rp in relevant)
            best_pos  = current[(bid_str, pname)]

            for side in allowed_sides:
                for yc in slots:
                    # Check spacing
                    conflict = any(
                        b == bid_str and p != pname
                        and s == side and abs(yc - y2) < _MIN_CC - 1e-9
                        for (b, p), (s, y2) in current.items()
                    )
                    if conflict:
                        continue
                    old = current[(bid_str, pname)]
                    current[(bid_str, pname)] = (side, yc)
                    cost = sum(_net_hpwl(rp) for rp in relevant)
                    current[(bid_str, pname)] = old
                    if cost < best_cost - 1e-9:
                        best_cost = cost
                        best_pos  = (side, yc)

            if best_pos != current[(bid_str, pname)]:
                current[(bid_str, pname)] = best_pos
                improved = True
                # Propagate Y to symmetric partner if applicable
                partner = y_partner.get((bid_str, pname))
                if partner is not None:
                    par_bid, par_pname, par_si = partner
                    _, new_yc = best_pos
                    # Find nearest slot on partner's forced side
                    par_slots = slots_by.get(par_bid, [])
                    if par_slots and new_yc in par_slots:
                        current[(par_bid, par_pname)] = (_SIDES[par_si], new_yc)
                    elif par_slots:
                        nearest = min(par_slots, key=lambda y: abs(y - new_yc))
                        current[(par_bid, par_pname)] = (_SIDES[par_si], nearest)

        if not improved:
            break
    return current


# ---------------------------------------------------------------------------
# Build result dict
# ---------------------------------------------------------------------------

def _build(
    placed_blocks: dict,
    blocks: dict,
    pwr: dict,
    pdk: dict,
    selected: dict,
    slots_by: dict,
) -> dict:
    result: dict = {}
    for bid_str, pb in placed_blocks.items():
        bbox      = pb["main_bbox"]
        block_pwr = pwr.get(bid_str, {})
        new_pins: dict = {}
        for pname in pb["pins"]:
            if pname in block_pwr:
                rail = block_pwr[pname]
                new_pins[pname] = power_pin_rect(bbox, rail, pdk)
            else:
                choice = selected.get((bid_str, pname))
                if choice:
                    side, yc = choice
                else:
                    slots = slots_by[bid_str]
                    cy    = (bbox["y_min"] + bbox["y_max"]) / 2
                    yc    = min(slots, key=lambda y: abs(y - cy)) if slots else _s6(cy)
                    side  = "left"
                new_pins[pname] = _sig_rect(bbox, side, yc)
        result[bid_str] = {**pb, "pins": new_pins}
    return result


# ---------------------------------------------------------------------------
# Annotate pins with net name (viewer tooltip)
# ---------------------------------------------------------------------------

def _tag_nets(placed_blocks: dict, nets: list, ref_idx: dict) -> None:
    pin_net: dict[str, str] = {
        pref: net.get("net_id", "")
        for net in nets
        for pref in net.get("pins", [])
    }
    for bid_str, pb in placed_blocks.items():
        for pname, rect in pb.get("pins", {}).items():
            if isinstance(rect, dict) and "layer" in rect:
                pref = f"B{bid_str}_{pname}"
                if pref in pin_net:
                    rect["net"] = pin_net[pref]
