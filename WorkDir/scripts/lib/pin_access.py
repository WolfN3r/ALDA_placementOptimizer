"""
Block pins as access segments (user 2026-11-09): a routed block (lib/block_router) may be entered
anywhere on its nets' access segments (trunk ends on the left / right edge, stretches of the top /
bottom edge over an outer-channel trunk, side-channel tracks), not only at one pin point.

- attach(v, pin_nets): variant["pin_access"] = {pin name: {"net", "segs"}} in the placer's variant
  frame (rotated variants turned 90 deg CW); pin_positions moved to the mean access point (the ILP
  and the old pin placer still use one fixed point per pin).
- net_hpwl(pins): HPWL of one net where every pin takes the point of its segments nearest to the
  other pins (used in the placement cost).
- assign(placed, nets, blocks, variant_map): after placement, the chosen point per net and routed
  block becomes its pin; the trunk ends nobody uses are cut (block_router.apply_access) and the
  result is stored as placed[bid]["routing"]; the chosen points replace the old pin placer's
  squares in placed[bid]["pins"]; the power pin P0 becomes the guard-ring side facing the rail.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

PASSES = 3          # nearest-point refinement passes per net
MARK = 0.24         # µm: pin marker of a block without trimmable trunks (old pin placer square size)
_TOL = 1e-6

# =============================================================================
# LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# ALGORITHM
# =============================================================================

def _near(a0: float, a1: float, b0: float, b1: float) -> float:
    """Point of [a0, a1] nearest to [b0, b1] (middle of the overlap when they overlap)."""
    if a1 < b0:
        return a1
    if a0 > b1:
        return a0
    return (max(a0, b0) + min(a1, b1)) / 2


def net_hpwl(pins: list) -> tuple:
    """(hpwl, [(x, y) per pin]); pins: [[(x0, y0, x1, y1), ...] per pin], a point = zero-length segment.
    Fixed pins (one point) first decide where the others go; then each pin moves to its point nearest
    to the bounding box of all the others, PASSES times."""
    fixed = [len(p) == 1 and p[0][0] == p[0][2] and p[0][1] == p[0][3] for p in pins]
    pts = [((p[0][0] + p[0][2]) / 2, (p[0][1] + p[0][3]) / 2) for p in pins]
    for it in range(PASSES):
        for i, segs in enumerate(pins):
            if fixed[i]:
                continue
            others = [pts[j] for j in range(len(pins))
                      if j != i and (it > 0 or fixed[j] or not any(fixed))]
            if not others:
                continue
            bx0, bx1 = min(x for x, _ in others), max(x for x, _ in others)
            by0, by1 = min(y for _, y in others), max(y for _, y in others)
            best = None
            for x0, y0, x1, y1 in segs:
                x, y = _near(x0, x1, bx0, bx1), _near(y0, y1, by0, by1)
                d = max(0.0, bx0 - x, x - bx1) + max(0.0, by0 - y, y - by1)
                if best is None or d < best[0]:
                    best = (d, (x, y))
            pts[i] = best[1]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys)), pts


def _segments(v: dict, net: str) -> list:
    """Access segments of `net` in the variant's own (unrotated) frame: the router's access list, or
    the centres of its fixed pins (chains, caps)."""
    routing = v["routing"]
    if "access" in routing:
        return [tuple(a["seg"]) for a in routing["access"] if a["net"] == net]
    out = []
    for p in routing["pins"]:
        if p["net"] == net:
            x, y = (p["rect"][0] + p["rect"][2]) / 2, (p["rect"][1] + p["rect"][3]) / 2
            out.append((x, y, x, y))
    return out


def attach(v: dict, routed: dict, pin_nets: dict) -> None:
    """Set v["pin_access"] (and pin_positions of those pins) from the routed variant `routed`;
    pin_nets: {pin name: net}. A 90 deg variant: (x, y) -> (y, W0 - x), W0 = unrotated width = its height."""
    if not routed.get("routing"):
        return
    rot = v.get("rotation_deg") == 90
    w0 = v["main_bbox"]["y_max"]
    access = {}
    for pname, net in pin_nets.items():
        segs = _segments(routed, net)
        if not segs:
            continue
        if rot:
            segs = [(min(y0, y1), min(w0 - x0, w0 - x1), max(y0, y1), max(w0 - x0, w0 - x1))
                    for x0, y0, x1, y1 in segs]
        access[pname] = {"net": net, "segs": [list(s) for s in segs]}
        n = len(segs)
        v["pin_positions"][pname] = {"x": round(sum(s[0] + s[2] for s in segs) / (2 * n), 6),
                                     "y": round(sum(s[1] + s[3] for s in segs) / (2 * n), 6)}
    if access:
        v["pin_access"] = access


def assign(placed: dict, nets: list, blocks: dict, variant_map: dict) -> dict:
    """placed (from _compute_placed_blocks) with each routed block's chosen access points as pins."""
    import block_router
    from cost_evaluator import resolve_variant      # cost_evaluator imports this module
    pts, segs, var = {}, {}, {}
    for bid, pb in placed.items():
        if "main_bbox" not in pb:           # chip rails added by pin_optimizer
            continue
        bx, by = pb["main_bbox"]["x_min"], pb["main_bbox"]["y_min"]
        v = resolve_variant(blocks.get(bid, {}), bid, variant_map or {})
        var[bid] = v
        for pname, pc in v.get("pin_positions", {}).items():
            ref = f"B{bid}_{pname}"
            pts[ref] = (bx + pc["x"], by + pc["y"])
            if pname in v.get("pin_access", {}):
                segs[ref] = [(bx + s[0], by + s[1], bx + s[2], by + s[3]) for s in v["pin_access"][pname]["segs"]]
    picks: dict = {}
    for net in nets:
        if net.get("net_type") == "power":
            continue
        refs = [r for r in net.get("pins", []) if r in pts]
        if len(refs) < 2 or not any(r in segs for r in refs):
            continue
        _, chosen = net_hpwl([segs.get(r) or [(*pts[r], *pts[r])] for r in refs])
        for r, pt in zip(refs, chosen):
            if r in segs:
                bid, pname = r[1:].split("_", 1)
                picks.setdefault(bid, []).append((pname, pt))
    for bid, chosen in picks.items():
        v, pb = var[bid], placed[bid]
        routed = v.get("routed") or v
        pb["pins"] = {k: p for k, p in pb.get("pins", {}).items() if k not in v["pin_access"]}
        bx, by = pb["main_bbox"]["x_min"], pb["main_bbox"]["y_min"]
        for pname, (x, y) in chosen:        # marker at the chosen point (replaced by the real pin below)
            pb["pins"][pname] = {"layer": "pin", "side": "", "x_min": round(x - MARK / 2, 6), "y_min": round(y - MARK / 2, 6),
                                 "x_max": round(x + MARK / 2, 6), "y_max": round(y + MARK / 2, 6)}
        if "trunks" not in routed.get("routing", {}):
            continue
        out = []
        for pname, (x, y) in chosen:
            net, px, py = v["pin_access"][pname]["net"], x - bx, y - by
            a = next(a for a in routed["routing"]["access"] if a["net"] == net
                     and a["seg"][0] - _TOL <= px <= a["seg"][2] + _TOL and a["seg"][1] - _TOL <= py <= a["seg"][3] + _TOL)
            out.append({"pname": pname, "net": net, "side": a["side"], "point": [px, py]})
        pb["routing"] = block_router.apply_access(routed, out)["routing"]
        for c in out:                       # the block pin drawn at that point, absolute
            r = next(p["rect"] for p in pb["routing"]["pins"] if p["net"] == c["net"] and p["side"] == c["side"]
                     and p["rect"][0] - _TOL <= c["point"][0] <= p["rect"][2] + _TOL
                     and p["rect"][1] - _TOL <= c["point"][1] <= p["rect"][3] + _TOL)
            pb["pins"][c["pname"]] = {"layer": next(p["layer"] for p in pb["routing"]["pins"] if p["rect"] == r),
                                      "side": c["side"], "x_min": round(bx + r[0], 6), "y_min": round(by + r[1], 6),
                                      "x_max": round(bx + r[2], 6), "y_max": round(by + r[3], 6)}
        logger.debug("pin_access: block %s pins %s", bid, [(c["net"], c["side"]) for c in out])
    for bid, v in var.items():              # power pin = the ring side facing the block's rail, full length
        routed, pb = v.get("routed") or v, placed[bid]
        side = "top" if blocks.get(bid, {}).get("power_rail") == "VDD" else "bottom"
        ring = [p for p in routed.get("routing", {}).get("power_pins", []) if p["side"] == side]
        if not ring or v.get("rotation_deg") == 90 or "P0" not in pb.get("pins", {}):
            continue
        r, bx, by = ring[0]["rect"], pb["main_bbox"]["x_min"], pb["main_bbox"]["y_min"]
        pb["pins"]["P0"] = {"layer": "met1", "type": "power", "side": side, "net": ring[0]["net"],
                            "x_min": round(bx + r[0], 6), "y_min": round(by + r[1], 6),
                            "x_max": round(bx + r[2], 6), "y_max": round(by + r[3], 6)}
    return placed
