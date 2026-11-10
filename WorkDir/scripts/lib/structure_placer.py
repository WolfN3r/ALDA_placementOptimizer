"""
Matched structures for 012: places the copies of one group (diff pair, mirror,
sensitive single transistor, resistor chain) as rows of separate PCells with a
dummy at each row end and one tight guard ring, and returns one variant per
grid shape for the placer (groups[].matching_variants).

Per grid shape (rows x cols of device slots, every shape whose ring bbox is
inside the aspect band) the arrangement of copies is searched — every
exact common-centroid arrangement when the shape is small enough, else
point-symmetric ones (every odd gradient term cancels; one descent from a
centre-outward ratio seed when too many), else any arrangement with the
linear term first; up to EXTRA_DUMMIES inner dummies only when no shape has
an exact centroid, kept only when they lower the linear term; no shape with
one device per row; devices are never split (nf, m from the netlist) — and scored like
05_miller_ota klayout_matching.py: the V_T difference that assumed gradients
leave between the devices (linear, 2nd/3rd order, beta, R0/R180 balance),
plus W_FACE per neighbouring S/D sides on different nets (each copy may swap
S and D; the best swaps per row are exact), plus W_WIRE per µm of each
device's copy spanning tree.

Geometry from pdk.json only: x gap = gap.x_routed (every contact can take its
own via), row gap poly to poly = max(layout_policy.row_gap_poly_min,
n_nets * track pitch + track space) rounded up to row_gap_round, n_nets =
distinct gate nets (gates face each other) or S/D nets (S/D face each other)
of the group; ring opening = content + clearance per side, ring bbox from
the ring footprint fit, plus the ring fill where it sticks out.

Kinds: "cc" (DP, latch: gates face inward, 2-row common centroid preferred),
"mirror" and "single" (row orientation: the smaller bbox), "chain" (series
resistors, each member's copies = its series segments, in series order in
one row, no search; a one-member chain has no row-end dummies).
"""
from __future__ import annotations

import itertools
import math
import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger
import pcell

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

# Gradient magnitudes (05_miller_ota klayout_matching.py defaults; assumptions, not data)
GRAD = {"lin": 1.0,      # µV/µm
        "quad": 0.01,    # µV/µm²
        "cubic": 1e-4,   # µV/µm³
        "beta": 1.0,     # %/mm current-factor gradient
        "vov": 0.1,      # V overdrive (beta term = vov/2 · Δβ/β)
        "orient": 100.0}  # µV V_T step between R0 and R180 copies
W_FACE = 1.0             # µV per mismatched S/D facing (= 1 µm of linear centroid error)
W_WIRE = 0.001           # µV per µm of copy spanning tree (tie-break)

EXHAUSTIVE_LIMIT = 30000  # arrangements per shape searched exhaustively below this (~20 ms per 13k, measured)
RESTARTS = 8             # local search starts above it (no symmetric family)
KICKS = 4                # random double swaps + descent after each local minimum
SEED = 1
EXTRA_DUMMIES = 2        # inner dummies tried when no shape reaches an exact common centroid
LIN_FIRST = 1000.0       # search weight on the linear term when no exact centroid is possible
DIGITAL_RING_GAP_MIN = 0.02  # µm between the stacked rings of a digital gate (user, 2026-11-06)
_CC_TOL = 1e-6           # µm per unit: centroid sums of rounded slot coordinates

DUMMY = "d"
_EMPTY = -1
_ROUND = 6
_EPS = 1e-9

# =============================================================================
# LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# ALGORITHM
# =============================================================================

# --- geometry ------------------------------------------------------------------

def _ceil_to(v: float, step: float) -> float:
    return round(math.ceil(v / step - _EPS) * step, _ROUND)


def _side_inset(fp: dict, params: dict, orient: str, side: str) -> float:
    """Poly inset on the placed top/bottom side (R180 shows the device's other side)."""
    own = side if orient == "R0" else ("bottom" if side == "top" else "top")
    return pcell._linear(fp[f"inset_{own}"], params)


def channel_gap(pdk: dict, model: str, n_nets: int, lower: str, upper: str, params: dict | None = None) -> float:
    """bbox gap between a row (orientation `lower`) and the row above it."""
    d = pdk["devices"][model]
    pol, tr = pdk["layout_policy"], pdk["tracks"]
    poly = _ceil_to(max(pol["row_gap_poly_min"], n_nets * tr["pitch"] + tr["space"]), pol["row_gap_round"])
    gap = poly - _side_inset(d["footprint"], params or {}, lower, "top") \
               - _side_inset(d["footprint"], params or {}, upper, "bottom")
    drc_key = {("R0", "R180"): "r0_r180", ("R180", "R0"): "m0_r0"}.get((lower, upper), "r0_r0")
    return round(max(gap, d["gap"]["y"][drc_key]), _ROUND)


def ring_wrap(pdk: dict, model: str, w: float, h: float, bottom: str, top: str) -> tuple | None:
    """Ring around a w x h content whose bottom/top rows are oriented bottom/top.
    Returns (W, H, content x offset, content y offset, ring dict) or None (ringless)."""
    d = pdk["devices"][model]
    if not d.get("ring"):
        return None
    clr = d["clearance"]
    side = {"R0": {"bottom": clr["bottom"], "top": clr["top"]},
            "R180": {"bottom": clr["top"], "top": clr["bottom"]}}
    cl, cr, cb, ct = clr["left"], clr["right"], side[bottom]["bottom"], side[top]["top"]
    r = pdk["guard_rings"][d["ring"]]
    env = {"IW": pcell.snap(w + cl + cr, pdk["grid"]), "IL": pcell.snap(h + cb + ct, pdk["grid"]),
           "GRW": r["grw_min"]}
    fp = r["footprint"]
    over = max([f["enclosure"] - r["tap_inset"] for f in r["fill"]] + [0.0])
    W = pcell._linear(fp["w"], env) + 2 * over
    H = pcell._linear(fp["h"], env) + 2 * over
    ox = over - pcell._linear(fp["x0"], env) + cl
    oy = over - pcell._linear(fp["y0"], env) + cb
    ring = {"ring": d["ring"], "grw": r["grw_min"], "in_w": env["IW"], "in_l": env["IL"],
            "opening": {"x_min": round(ox - cl, _ROUND), "y_min": round(oy - cb, _ROUND),
                        "x_max": round(ox - cl + env["IW"], _ROUND), "y_max": round(oy - cb + env["IL"], _ROUND)}}
    return round(W, _ROUND), round(H, _ROUND), ox, oy, ring


def _orients(kind: str, rows: int) -> list:
    """Candidate row orientations (bottom row first) for this kind."""
    if rows == 1 or kind == "chain":
        return [["R0"] * rows]
    gates_in = ["R0" if r % 2 == 0 else "R180" for r in range(rows)]
    gates_out = ["R180" if r % 2 == 0 else "R0" for r in range(rows)]
    return [gates_in] if kind == "cc" else [gates_in, gates_out]


def _layout(pdk: dict, ctx: dict, rows: int, cols: int, orients: list) -> dict:
    """Slot boxes (label independent): row-end dummies (if ctx["ends"]) + rows x cols device slots."""
    model, (w, h), (dw, _) = ctx["model"], ctx["unit"], ctx["dummy_unit"]
    e = 1 if ctx["ends"] else 0
    d = pdk["devices"][model]
    gx = d["gap"].get("x_routed", d["gap"]["x"])
    ys, y = [], 0.0
    for r in range(rows):
        ys.append(y)
        if r + 1 < rows:
            if ctx["mos"]:
                n = ctx["n_gate"] if (orients[r], orients[r + 1]) == ("R0", "R180") else ctx["n_sd"]
                y += h + channel_gap(pdk, model, n, orients[r], orients[r + 1], ctx["params"])
            else:
                y += h + d["gap"]["y"]["r0_r0"]
    cw, ch = 2 * e * dw + cols * w + (cols - 1 + 2 * e) * gx, y + h
    wrap = ring_wrap(pdk, model, cw, ch, orients[0], orients[-1])
    W, H, ox, oy, ring = wrap if wrap else (cw, ch, 0.0, 0.0, None)
    boxes = []                      # (row, col incl. dummies, x centre, y centre, width)
    for r in range(rows):
        x = ox
        for k in range(cols + 2 * e):
            sw = dw if e and k in (0, cols + 1) else w
            boxes.append((r, k, round(x + sw / 2, _ROUND), round(oy + ys[r] + h / 2, _ROUND), sw))
            x += sw + gx
    return {"W": round(W, _ROUND), "H": round(H, _ROUND), "ring": ring, "boxes": boxes,
            "rows": rows, "cols": cols, "orients": orients, "ends": e}


# --- S/D facing -----------------------------------------------------------------

def row_facing(sides: list) -> tuple:
    """Fewest neighbouring sides on different nets in one row and the S/D order
    that reaches it. sides: {"dummy": net} or {"source", "drain", "nf"}.
    Returns (mismatches, [None | (left terminal, right terminal)])."""
    def states(s):
        if "dummy" in s:
            return [(None, None, s["dummy"], s["dummy"])]
        out = []
        for left in ("source", "drain"):
            right = left if s["nf"] % 2 == 0 else ("drain" if left == "source" else "source")
            out.append((left, right, s[left], s[right]))
        return out

    layers = [states(s) for s in sides]
    cost = [0] * len(layers[0])
    back: list = []
    for prev, cur in zip(layers, layers[1:]):
        new, bp = [], []
        for c in cur:
            best = min(range(len(prev)), key=lambda i: cost[i] + (prev[i][3] != c[2]))
            new.append(cost[best] + (prev[best][3] != c[2]))
            bp.append(best)
        cost, back = new, back + [bp]
    i = min(range(len(cost)), key=cost.__getitem__)
    total, picks = cost[i], [i]
    for bp in reversed(back):
        i = bp[i]
        picks.append(i)
    picks.reverse()
    order = [None if "dummy" in s else layers[k][p][:2] for k, (s, p) in enumerate(zip(sides, picks))]
    return total, order


# --- scoring ---------------------------------------------------------------------

def _terms(x: float, y: float, flipped: bool) -> list:
    return [x, y, x * x, y * y, x * y, x ** 3, x * x * y, x * y * y, y ** 3, 1.0 if flipped else 0.0]


def offset_parts(means: list) -> dict:
    """Worst device pair per gradient term (µV); total = RSS of lin, quad, 3rd,
    beta, orient. quad: field q·(x cosθ + y sinθ)² at its worst angle θ;
    x2y2 / xy are its components, reported only."""
    parts = dict.fromkeys(("lin", "x2y2", "xy", "quad", "3rd", "beta", "orient"), 0.0)
    beta_per_um = GRAD["beta"] / 100 / 1000
    for mi, mj in itertools.combinations(means, 2):
        d = [p - q for p, q in zip(mi, mj)]
        centroid = math.hypot(d[0], d[1])
        new = {"lin": GRAD["lin"] * centroid,
               "x2y2": GRAD["quad"] * math.hypot(d[2], d[3]),
               "xy": GRAD["quad"] * abs(d[4]),
               # Δ(θ) = (A+B)/2 + (A-B)/2·cos2θ + C·sin2θ with A, B, C = Δ<x²>, Δ<y²>, Δ<xy>
               "quad": GRAD["quad"] * (abs(d[2] + d[3]) / 2 + math.hypot((d[2] - d[3]) / 2, d[4])),
               "3rd": GRAD["cubic"] * math.sqrt(d[5] ** 2 + d[6] ** 2 + d[7] ** 2 + d[8] ** 2),
               "beta": GRAD["vov"] / 2 * beta_per_um * centroid * 1e6,
               "orient": GRAD["orient"] * abs(d[9])}
        for k, v in new.items():
            parts[k] = max(parts[k], v)
    parts["total"] = math.sqrt(sum(parts[k] ** 2 for k in ("lin", "quad", "3rd", "beta", "orient")))
    return parts


def _mst_length(points: list) -> float:
    if len(points) < 2:
        return 0.0
    inside, rest, total = [points[0]], list(points[1:]), 0.0
    while rest:
        dist, q = min((abs(p[0] - q[0]) + abs(p[1] - q[1]), q) for p in inside for q in rest)
        total += dist
        inside.append(q)
        rest.remove(q)
    return total


class _Scorer:
    """Cost of a label vector (member index per device slot, row-major from the
    bottom row; _EMPTY = inner dummy) on one layout."""

    def __init__(self, ctx: dict, lay: dict, use_gradient: bool, use_facing: bool):
        self.ctx, self.lay = ctx, lay
        self.use_gradient, self.use_facing = use_gradient, use_facing
        self.dev_boxes = [b for b in lay["boxes"] if lay["ends"] <= b[1] < lay["cols"] + lay["ends"]]
        cx = sum(b[2] for b in self.dev_boxes) / len(self.dev_boxes)
        cy = sum(b[3] for b in self.dev_boxes) / len(self.dev_boxes)
        self.vectors = [_terms(b[2] - cx, b[3] - cy, lay["orients"][b[0]] == "R180") for b in self.dev_boxes]
        self._rows: dict = {}       # row labels -> row_facing result (a swap changes at most two rows)

    def gradient(self, labels: list) -> dict:
        k = len(self.ctx["members"])
        if not self.use_gradient or k < 2:
            return offset_parts([])
        sums, counts = [[0.0] * 10 for _ in range(k)], [0] * k
        for lab, vec in zip(labels, self.vectors):
            if lab != _EMPTY:
                sums[lab] = [p + q for p, q in zip(sums[lab], vec)]
                counts[lab] += 1
        return offset_parts([[v / counts[i] for v in sums[i]] for i in range(k)])

    def facing(self, labels: list) -> tuple:
        if not self.use_facing:
            return 0, []
        rail, cols, members = self.ctx["rail"], self.lay["cols"], self.ctx["members"]
        total, orders = 0, []
        for r in range(self.lay["rows"]):
            key = tuple(labels[r * cols:(r + 1) * cols])
            if key not in self._rows:
                sides = [{"dummy": rail}] * self.lay["ends"]
                for lab in key:
                    if lab == _EMPTY:
                        sides.append({"dummy": rail})
                    else:
                        t = members[lab]["terminals"]
                        sides.append({"source": t["source"], "drain": t["drain"], "nf": self.ctx["nf"]})
                sides += [{"dummy": rail}] * self.lay["ends"]
                self._rows[key] = row_facing(sides)
            m, order = self._rows[key]
            total += m
            orders.append(order)
        return total, orders

    def cost(self, labels: list, lin_w: float = 0.0) -> float:
        g = self.gradient(labels)
        return g["total"] + lin_w * g["lin"] + W_FACE * self.facing(labels)[0]


# --- search ----------------------------------------------------------------------

def _multiset_permutations(items: list):
    seq = sorted(items)
    while True:
        yield list(seq)
        i = len(seq) - 2
        while i >= 0 and seq[i] >= seq[i + 1]:
            i -= 1
        if i < 0:
            return
        j = len(seq) - 1
        while seq[j] <= seq[i]:
            j -= 1
        seq[i], seq[j] = seq[j], seq[i]
        seq[i + 1:] = reversed(seq[i + 1:])


def _n_arrangements(items: list) -> int:
    n = math.factorial(len(items))
    for c in {x: items.count(x) for x in items}.values():
        n //= math.factorial(c)
    return n


def _search(items: list, cost, rng, seed: list | None = None) -> list:
    """Lowest-cost ordering of items: exhaustive below EXHAUSTIVE_LIMIT, else
    one swap descent from `seed`, or (no seed) descent with restarts and kicks."""
    if len(set(items)) < 2:
        return list(items)
    if _n_arrangements(items) <= EXHAUSTIVE_LIMIT:
        return min(_multiset_permutations(items), key=cost)

    def descend(seq, c):
        improved = True
        while improved:
            improved = False
            for i, j in itertools.combinations(range(len(seq)), 2):
                if seq[i] == seq[j]:
                    continue
                seq[i], seq[j] = seq[j], seq[i]
                cj = cost(seq)
                if cj < c - _EPS:
                    c, improved = cj, True
                else:
                    seq[i], seq[j] = seq[j], seq[i]
        return seq, c

    if seed is not None:
        return descend(list(seed), cost(seed))[0]
    best, best_c = None, math.inf
    for _ in range(RESTARTS):
        seq = list(items)
        rng.shuffle(seq)
        seq, c = descend(seq, cost(seq))
        for _ in range(KICKS):
            trial = list(seq)
            for _ in range(2):
                i, j = rng.sample(range(len(trial)), 2)
                trial[i], trial[j] = trial[j], trial[i]
            trial, tc = descend(trial, cost(trial))
            if tc < c:
                seq, c = trial, tc
        if c < best_c:
            best, best_c = seq, c
    return best


def _point_symmetric(counts: list, empties: int, n_slots: int) -> tuple | None:
    """(pair items, centre label) when every device (and the inner dummies) can
    be split into slot pairs i <-> n_slots-1-i, else None."""
    labels = [(i, c) for i, c in enumerate(counts)] + [(_EMPTY, empties)]
    odd = [lab for lab, c in labels if c % 2]
    if len(odd) > n_slots % 2:
        return None
    items = [lab for lab, c in labels for _ in range(c // 2)]
    return items, (odd[0] if odd else None)


def _exact_cc(xy: list, groups: list) -> list:
    """Every label vector whose labels (incl. _EMPTY) all have their centroid
    at the array centre. xy: slot coordinates relative to the centre;
    groups: [(label, count)]. All labels centred <=> all devices share one
    centroid, since the slots average to the centre."""
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    order = sorted(groups, key=lambda g: g[1])      # few units first: strongest pruning
    out = []

    def rec(k, free, labels):
        if k == len(order) - 1:                     # last label takes the rest, centred by the others
            for i in free:
                labels[i] = order[k][0]
            out.append(list(labels))
            return
        lab, c = order[k]
        for comb in itertools.combinations(free, c):
            if abs(sum(map(xs.__getitem__, comb))) > _CC_TOL * c or abs(sum(map(ys.__getitem__, comb))) > _CC_TOL * c:
                continue
            for i in comb:
                labels[i] = lab
            taken = set(comb)
            rec(k + 1, [i for i in free if i not in taken], labels)

    rec(0, list(range(len(xy))), [None] * len(xy))
    return out


def _ratio_seed(items: list, dist: list) -> list:
    """Half-vector seed after Sharma et al., ICCAD 2021, Alg. 1: positions from
    the centre outward each take the device with the largest unplaced share;
    inner dummies take the outermost positions."""
    total = {lab: items.count(lab) for lab in set(items) if lab != _EMPTY}
    left = dict(total)
    order = sorted(range(len(items)), key=lambda p: dist[p])
    n_dev = len(items) - items.count(_EMPTY)
    seq = [_EMPTY] * len(items)
    for p in order[:n_dev]:
        lab = max((l for l in total if left[l]), key=lambda l: (left[l] / total[l], -l))
        seq[p] = lab
        left[lab] -= 1
    return seq


def _expand_pairs(units: list, centre, n_slots: int) -> list:
    labels = [None] * n_slots
    for p, lab in enumerate(units):
        labels[p] = labels[n_slots - 1 - p] = lab
    if n_slots % 2:
        labels[n_slots // 2] = centre
    return labels


# --- variants --------------------------------------------------------------------

def _chain_labels(counts: list, rows: int, cols: int) -> list:
    """Series order (each member's segments together), snaking row by row so
    consecutive segments are neighbours."""
    series = [i for i, c in enumerate(counts) for _ in range(c)]
    labels = []
    for r in range(rows):
        row = list(range(r * cols, (r + 1) * cols))
        row = [series[i] if i < len(series) else _EMPTY for i in row]
        labels += row if r % 2 == 0 else row[::-1]
    return labels


def _variant(ctx: dict, lay: dict, labels: list, scorer: _Scorer, cc2d: bool) -> dict:
    members, rows, cols, e = ctx["members"], lay["rows"], lay["cols"], lay["ends"]
    letters = string.ascii_uppercase
    grad = scorer.gradient(labels)
    mism, orders = scorer.facing(labels)
    slots, text = [], []
    for r in range(rows):
        row_labels = [None] * e + labels[r * cols:(r + 1) * cols] + [None] * e
        line = ""
        for k, lab in enumerate(row_labels):
            box = lay["boxes"][r * (cols + 2 * e) + k]
            dev = lab is not None and lab != _EMPTY
            side = orders[r][k] if orders else None
            slots.append({"block_id": members[lab]["block_id"] if dev else None,
                          "dummy": not dev, "full_size_dummy": lab == _EMPTY,
                          "row": r, "col": k, "x": box[2], "y": box[3], "w": box[4], "h": ctx["unit"][1],
                          "orient": lay["orients"][r],
                          "left": side[0] if side else None, "right": side[1] if side else None})
            line += letters[lab] if dev else DUMMY
        text.append(line)
    wire = sum(_mst_length([(s["x"], s["y"]) for s in slots if s["block_id"] == m["block_id"]])
               for m in members) if scorer.use_gradient else 0.0
    rank = grad["total"] + W_FACE * mism + W_WIRE * wire
    n_inner = labels.count(_EMPTY)
    return {
        "kind": ctx["kind"], "rows": rows, "cols": cols, "cols_per_device": cols,
        "matching_type": ("common_centroid" if cc2d else "interdigitated") if ctx["kind"] in ("cc", "mirror")
                         else "array",
        "dummy_cols_per_side": e, "dummy_rows_top_bottom": 0,
        "width_um": lay["W"], "height_um": lay["H"],
        "pattern": list(reversed(text)), "orient": lay["orients"],
        "slots": slots, "guard_ring": lay["ring"], "unit_pcell": ctx["params"],
        "dummies": {"model": ctx["model"], "pcell": ctx["dummy_params"], "count": 2 * rows * e,
                    "inner_full_size": n_inner},
        "facing_mismatches": mism,
        "score": {**{k: round(v, 6) for k, v in grad.items()}, "wire_um": round(wire, 4), "rank": round(rank, 6)},
    }


def digital_variant(pdk: dict, rows: list) -> dict:
    """Digital gate (inv, nand2, nor2, tg): rows bottom first (N row, P row) of
    members [{"block_id", "copies", "model", "pcell"}], each row left to right in
    member order at the routed x gap inside its own tight ring; the rings are
    stacked at the PDK ring-to-ring gap (at least DIGITAL_RING_GAP_MIN) and
    centred on one vertical axis. No dummies."""
    parts = []
    for row in rows:
        model = row[0]["model"]
        gx = pdk["devices"][model]["gap"]["x_routed"]
        units = [(m["block_id"], pcell.footprint(pdk, m["model"], m["pcell"])) for m in row for _ in range(m["copies"])]
        w = sum(u[1][0] for u in units) + gx * (len(units) - 1)
        h = max(u[1][1] for u in units)
        parts.append((units, gx, h, ring_wrap(pdk, model, w, h, "R0", "R0")))
    width = max(p[3][0] for p in parts)
    slots, rings, y0 = [], [], 0.0
    for r, (units, gx, h, (W, H, ox, oy, ring)) in enumerate(parts):
        if r:
            sg = pdk["structure_gap"]
            a, b = rings[-1]["ring"], ring["ring"]
            y0 += max((sg.get(f"{a}|{b}") or sg[f"{b}|{a}"])["min"], DIGITAL_RING_GAP_MIN)
        dx = pcell.snap((width - W) / 2, pdk["grid"])
        x = dx + ox
        for c, (bid, (uw, uh)) in enumerate(units):
            slots.append({"block_id": bid, "dummy": False, "full_size_dummy": False, "row": r, "col": c,
                          "x": round(x + uw / 2, _ROUND), "y": round(y0 + oy + h / 2, _ROUND), "w": uw, "h": uh,
                          "orient": "R0", "left": None, "right": None})
            x += uw + gx
        o = ring["opening"]
        rings.append({**ring, "opening": {"x_min": round(o["x_min"] + dx, _ROUND), "y_min": round(o["y_min"] + y0, _ROUND),
                                          "x_max": round(o["x_max"] + dx, _ROUND), "y_max": round(o["y_max"] + y0, _ROUND)}})
        y0 = round(y0 + H, _ROUND)
    return {"rows": len(rows), "cols": max(len(p[0]) for p in parts), "cols_per_device": 1,
            "matching_type": "proximity", "dummy_cols_per_side": 0, "dummy_rows_top_bottom": 0,
            "width_um": width, "height_um": y0, "orient": ["R0"] * len(rows),
            "slots": slots, "guard_ring": None, "guard_rings": rings, "is_used": True}


def _context(pdk: dict, members: list, kind: str, rail: str) -> dict:
    model, params = members[0]["model"], members[0]["pcell"]
    dparams = {**params, "nf": 1} if "nf" in params else dict(params)
    return {"kind": kind, "members": members, "model": model, "params": params, "rail": rail,
            "mos": "x_routed" in pdk["devices"][model].get("gap", {}),
            "unit": pcell.footprint(pdk, model, params), "dummy_unit": pcell.footprint(pdk, model, dparams),
            "dummy_params": dparams, "nf": int(params.get("nf", 1)),
            # user 2026-11-08: a lone resistor gets no row-end dummies (no partner to match)
            "ends": not (kind == "chain" and len(members) == 1),
            "n_gate": len({m["terminals"].get("gate") for m in members}),
            "n_sd": len({m["terminals"].get(t) for m in members for t in ("source", "drain")})}


def flip_variant(pdk: dict, variant: dict, members: list, rail: str) -> dict:
    """The same arrangement with every device rotated 180 deg (all row orientations
    swapped), laid out and scored again (block_router keeps the smaller routed one)."""
    ctx = _context(pdk, members, variant["kind"], rail)
    orients = ["R180" if o == "R0" else "R0" for o in variant["orient"]]
    lay = _layout(pdk, ctx, variant["rows"], variant["cols"], orients)
    ids = {m["block_id"]: i for i, m in enumerate(members)}
    e = variant["dummy_cols_per_side"]
    labels = [_EMPTY if s["block_id"] is None else ids[s["block_id"]]
              for s in variant["slots"] if e <= s["col"] < variant["cols"] + e]
    scorer = _Scorer(ctx, lay, use_gradient=ctx["kind"] != "chain", use_facing=ctx["mos"])
    out = _variant(ctx, lay, labels, scorer, variant["matching_type"] == "common_centroid")
    out["is_used"] = variant.get("is_used", False)
    return out


def structure_variants(pdk: dict, members: list, kind: str, rail: str, ar_band: tuple) -> list:
    """members: [{"block_id", "copies", "model", "pcell", "terminals"}] (same
    model and size; chain members in series order). rail: net of the dummies.
    Returns variants, best first, first one is_used."""
    ctx = _context(pdk, members, kind, rail)
    mos = ctx["mos"]
    counts = [m["copies"] for m in members]
    n = sum(counts)

    def layouts_for(shapes):
        out = []
        for rows, cols in shapes:
            cands = [_layout(pdk, ctx, rows, cols, o) for o in _orients(kind, rows)]
            out.append(min(cands, key=lambda l: l["W"] * l["H"] - _EPS * (l is cands[0])))
        return out, [l for l in out if ar_band[0] <= l["W"] / l["H"] <= ar_band[1]]

    base = [(rows, math.ceil(n / rows)) for rows in range(1, n + 1)
            if rows * math.ceil(n / rows) - n < math.ceil(n / rows) and (n == 1 or math.ceil(n / rows) > 1)]
    if kind == "chain":
        base = [(1, n)]       # user 2026-11-08: one row; extra rows cost a row gap and 2 dummies each
    layouts, inside = layouts_for(base)
    if not inside:
        inside = [min(layouts, key=lambda l: max(l["W"] / l["H"], l["H"] / l["W"]))]

    rng = random.Random(SEED)

    def place(lay):
        rows, cols = lay["rows"], lay["cols"]
        slots_n = rows * cols
        empties = slots_n - n
        scorer = _Scorer(ctx, lay, use_gradient=kind != "chain", use_facing=mos)
        cc2d = False
        if kind == "chain":
            return _variant(ctx, lay, _chain_labels(counts, rows, cols), scorer, cc2d)
        items = [i for i, c in enumerate(counts) for _ in range(c)] + [_EMPTY] * empties
        exact = []
        if len(members) > 1 and _n_arrangements(items) <= EXHAUSTIVE_LIMIT:
            groups = [(i, c) for i, c in enumerate(counts)] + ([(_EMPTY, empties)] if empties else [])
            exact = _exact_cc([v[:2] for v in scorer.vectors], groups)
        sym = None if exact else _point_symmetric(counts, empties, slots_n)
        if exact:
            labels = min(exact, key=scorer.cost)
            cc2d = rows % 2 == 0        # odd rows: unequal R0/R180 gaps around the middle row
        elif sym:
            half, centre = sym
            seed = _ratio_seed(half, [math.hypot(*scorer.vectors[p][:2]) for p in range(len(half))])
            units = _search(half, lambda u: scorer.cost(_expand_pairs(u, centre, slots_n)), rng, seed)
            labels = _expand_pairs(units, centre, slots_n)
            cc2d = rows % 2 == 0
        else:
            labels = _search(items, lambda l: scorer.cost(l, LIN_FIRST), rng)
        return _variant(ctx, lay, labels, scorer, cc2d)

    variants = [place(lay) for lay in inside]
    if kind in ("cc", "mirror") and len(members) > 1 and min(v["score"]["lin"] for v in variants) > _CC_TOL:
        extra = [(r, c) for r in range(1, n + EXTRA_DUMMIES + 1) for c in range(1, n + EXTRA_DUMMIES + 1)
                 if n < r * c <= n + EXTRA_DUMMIES and r * c - n < c and (r, c) not in base]
        variants += [place(lay) for lay in layouts_for(extra)[1]]
        if min(v["score"]["lin"] for v in variants) > _CC_TOL:
            logger.warning("Structure %s %s: no common-centroid arrangement (counts %s), best interdigitated",
                           kind, [m["block_id"] for m in members], counts)
    kept = []
    for v in sorted(variants, key=lambda v: v["dummies"]["inner_full_size"]):
        fewer = [k["score"]["lin"] for k in kept if k["dummies"]["inner_full_size"] < v["dummies"]["inner_full_size"]]
        if not fewer or v["score"]["lin"] < min(fewer) - _CC_TOL:    # an inner dummy must lower lin
            kept.append(v)
    variants = kept

    def key(v):
        squareness = max(v["width_um"] / v["height_um"], v["height_um"] / v["width_um"])
        preferred = kind == "cc" and v["matching_type"] == "common_centroid"
        lin = v["score"]["lin"]
        return (lin > _CC_TOL, lin, not preferred, v["score"]["rank"], squareness)
    variants.sort(key=key)
    for i, v in enumerate(variants):
        v["is_used"] = i == 0
    logger.info("Structure %s %s: %d variant(s), first %dx%d %s rank %.3f", kind,
                [m["block_id"] for m in members], len(variants), variants[0]["rows"], variants[0]["cols"],
                variants[0]["pattern"], variants[0]["score"]["rank"])
    return variants
