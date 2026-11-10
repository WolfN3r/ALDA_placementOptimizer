"""
In-block routing of 012 structures (lib/structure_placer variants), after Lin et al., "A
Matching-based Placement and Routing System for Analog Design", 2007, Sec. IV-B: channel
routing between the device rows, decisions in knowledge/notes/2026-11-08_block-router-*.md.

MOS structures (cc, mirror, single):
- channel c lies below row c (rows + 1 channels, c0 / cR between the outer rows and the ring);
  gate pins exit only into the channel the gates face; S/D pins into either (cc / DP: only the
  outer side, the middle channel carries only the inputs); chosen per row and net: smallest
  routed block area, then shortest stubs;
- every routed S/D strip: full-length M2 strap with a via1 array; facing strips of neighbouring
  copies on one net are bridged in met1 under one M2 plate and leave from the gap centre; the
  strap / plate continues straight into the channel to the net's M3 trunk (one track per net
  per channel, order by order_tracks: vertical constraints, matched pairs on neighbouring tracks);
- gates: met1 strap over the copy's pads; a row whose copies share one gate net (not cc) gets an
  M3 trunk on the pad row (via stack per copy, no channel track); otherwise one stub per copy
  from the middle pad, or from the gap to a neighbouring copy (row under a channel both rows'
  gates face, so the two rows' gate stubs never stack);
- diode copies: drain strips joined to the gate strap in met1;
- rail (= ring net): dummies tie to the ring in met1; a rail S/D strip facing the ring may drop
  onto it in met1 (that channel then takes no M3 trunk) or join an M3 trunk that drops onto the
  ring band through a via stack;
- nets with several trunks: one vertical M2 track in a side channel (cc: inputs left, the rest
  right; otherwise left);
- access (routing["access"], user 2026-11-09): every trunk end of an external net on the left /
  right edge (cc: inputs left, outputs and tail right, nothing else); a trunk in an outer channel
  also anywhere along it from the top / bottom edge (M2 straight through the ring), a side-channel
  track at its x; among equal areas the plan with external nets in outer channels wins;
- block pins: by default each external net's first trunk on its edge(s) (met3 to the block edge);
  apply_access puts them at the access points chosen after placement and cuts unused trunk ends;
  power pins (routing["power_pins"]): the guard ring band, tied to the rail, on all four sides;
- each block is also routed with every device rotated 180 deg (not cc); the smaller routed
  footprint wins. Rows, ring and block grow to hold the channels (structure_placer.ring_wrap).
Resistor chains: met1 jumpers between neighbouring end pads (the series starts at segment 0's
top pad), block pins = met2 on the free end pads.
Every wire / via centreline is on the grid and every half width a grid multiple, so all
edges are on grid even where a pin centre is not; spacing uses the bigger via landing.
"""
from __future__ import annotations

import copy
import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger
import pcell
import structure_placer as sp

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

EXHAUSTIVE_TRACKS = 7       # nets per channel ordered exhaustively up to this, greedy above
MAX_SIDE_COMBOS = 20000     # S/D side choices searched exhaustively up to this, else first option
_ROUND = 6
_EPS = 1e-9
_GRID_TOL = 1e-6            # in grid steps

# =============================================================================
# LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# ALGORITHM
# =============================================================================

# --- channel and track rules -----------------------------------------------------

def exit_channels(row: int, orient: str, terminal: str) -> list:
    """Channels a pin of a device in `row` may exit into (gate_con_pos top: R0 gates face up)."""
    if terminal == "gate":
        return [row + 1] if orient == "R0" else [row]
    return [row, row + 1]


def _order(stubs: list, min_dx: float, matched=()) -> tuple | None:
    """({net: track}, stub cost) or None; cost = tracks crossed by all stubs."""
    nets = sorted({n for _, n, _ in stubs})
    below = [(x, n) for x, n, s in stubs if s == "below"]
    above = [(x, n) for x, n, s in stubs if s == "above"]
    before = {(a, b) for xa, a in below for xb, b in above if a != b and abs(xa - xb) < min_dx - _EPS}
    t_max = len(nets) - 1
    n_below = {n: sum(1 for _, m in below if m == n) for n in nets}
    n_above = {n: sum(1 for _, m in above if m == n) for n in nets}

    def cost(tr):
        return sum(n_below[n] * tr[n] + n_above[n] * (t_max - tr[n]) for n in nets)

    if len(nets) <= EXHAUSTIVE_TRACKS:
        legal = [tr for tr in ({n: i for i, n in enumerate(p)} for p in itertools.permutations(nets))
                 if all(tr[a] < tr[b] for a, b in before)]
        if not legal:
            return None
        pairs = [(a, b) for a, b in matched if a in n_below and b in n_below]
        pool = [tr for tr in legal if all(abs(tr[a] - tr[b]) == 1 for a, b in pairs)] or legal
        best = min(pool, key=cost)
        return best, cost(best)
    succ = {n: {b for a, b in before if a == n} for n in nets}
    indeg = {n: sum(1 for _, b in before if b == n) for n in nets}
    ready, order = [n for n in nets if indeg[n] == 0], []
    while ready:
        n = max(ready, key=lambda m: (n_below[m] - n_above[m], m))
        ready.remove(n)
        order.append(n)
        for m in succ[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
    if len(order) < len(nets):
        return None
    tr = {n: i for i, n in enumerate(order)}
    return tr, cost(tr)


def order_tracks(stubs: list, min_dx: float, matched=()) -> dict | None:
    """One track per net (0 = lowest). stubs: (x, net, "below" | "above") = stub from the row
    under / over the channel; a below and an above stub of different nets closer than min_dx
    force the below net lower. Matched pairs on neighbouring tracks when any legal order
    allows it, then fewest crossed tracks. None when the constraints have a cycle."""
    res = _order(stubs, min_dx, matched)
    return res[0] if res else None


def chain_jumpers(pads: list) -> tuple:
    """pads: [(bottom, top)] per segment in series order. The series enters segment 0 at its
    top pad, so jumpers alternate bottom, top, ...; each fills the gap between the two pads
    at their common height. Returns (jumpers, (first free pad, last free pad))."""
    jumpers = []
    for i in range(len(pads) - 1):
        side = 0 if i % 2 == 0 else 1
        a, b = sorted((pads[i][side], pads[i + 1][side]), key=lambda r: r[0])
        jumpers.append(_r(a[2], max(a[1], b[1]), b[0], min(a[3], b[3])))
    last = pads[-1][0] if len(pads) % 2 else pads[-1][1]
    return jumpers, (pads[0][1], last)


# --- geometry helpers --------------------------------------------------------------

def _r(*v) -> tuple:
    return tuple(round(x, _ROUND) for x in v)


def _box(cx: float, cy: float, w: float, h: float) -> tuple:
    return _r(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def _ceil_grid(v: float, grid: float) -> float:
    return round(math.ceil(v / grid - _GRID_TOL) * grid, _ROUND)


def _floor_grid(v: float, grid: float) -> float:
    return round(math.floor(v / grid + _GRID_TOL) * grid, _ROUND)


def _rules(pdk: dict) -> dict:
    """Wire and via sizes from pdk["routing"]: wires as wide as the via landings, every
    size rounded up to two grid steps (half widths on grid); spacing from the bigger landing."""
    r, g2 = pdk["routing"], 2 * pdk["grid"]
    lay, v1, v2 = r["layers"], r["vias"]["via1"], r["vias"]["via2"]
    up = lambda v: _ceil_grid(v, g2)

    def landing(v, side):           # (short side, long side)
        return up(v["cut"] + 2 * v[side][0]), up(v["cut"] + 2 * v[side][1])

    v1m1, v1m2, v2m2, v2m3 = landing(v1, "enc_below"), landing(v1, "enc_above"), \
        landing(v2, "enc_below"), landing(v2, "enc_above")
    stub_w = up(max(v1m2[0], v2m2[0], lay["met2"]["width"]))
    trunk_w = up(max(v2m3[0], lay["met3"]["width"]))
    side_w = max(stub_w, v2m3[0])           # side track: its via2 M3 landing is the bigger one
    return {"grid": pdk["grid"], "cut1": up(v1["cut"]), "cut2": up(v2["cut"]),
            "v1m1": v1m1, "v1m2": v1m2, "v2m2": v2m2, "v2m3": v2m3,
            "stub_w": stub_w, "trunk_w": trunk_w, "side_w": side_w,
            "space2": lay["met2"]["space"], "space3": lay["met3"]["space"],
            "pitch2": round(stub_w + lay["met2"]["space"], _ROUND),
            "pitch3": round(trunk_w + lay["met3"]["space"], _ROUND),
            "v1_pitch": v1m1[1],            # adjacent via1 landings abut along a strip
            "track_need": max(v2m2[1], trunk_w),
            # gate via stack on the pad row: its M2 landing (long side along the row) vs an S/D stub
            "gate_keep": round(max(v1m2[1], v2m2[1]) / 2 + lay["met2"]["space"] + stub_w / 2, _ROUND)}


def _slot_geom(pdk: dict, v: dict, s: dict, by_id: dict, rail: str) -> dict:
    """Pins of one slot in the block frame: groups sorted along their order; S/D columns
    alternate the slot's left / right terminal from the left; dummies all on the rail."""
    dummy = s["block_id"] is None
    if dummy:
        model = v["dummies"]["model"]
        params = v["unit_pcell"] if s["full_size_dummy"] else v["dummies"]["pcell"]
    else:
        model, params = by_id[s["block_id"]]["model"], v["unit_pcell"]
    fp = pdk["devices"][model]["footprint"]
    w, h = pcell.footprint(pdk, model, params)
    cx, cy = pcell._linear(fp["x0"], params) + w / 2, pcell._linear(fp["y0"], params) + h / 2
    sgn = 1 if s["orient"] == "R0" else -1

    def place(r):
        xs = sorted((s["x"] + sgn * (r[0] - cx), s["x"] + sgn * (r[2] - cx)))
        ys = sorted((s["y"] + sgn * (r[1] - cy), s["y"] + sgn * (r[3] - cy)))
        return _r(xs[0], ys[0], xs[1], ys[1])

    groups = {}
    for name, g in pdk["devices"][model]["pins"].items():
        axis = 0 if g["order"] == "x" else 1
        groups[name] = sorted((place(r) for r in pcell.pin_rects(pdk, model, params, name)), key=lambda r: r[axis])
    out = {"slot": s, "dummy": dummy, "groups": groups,
           "bbox": _r(s["x"] - s["w"] / 2, s["y"] - s["h"] / 2, s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)}
    if "sd" in groups:
        t = None if dummy else by_id[s["block_id"]]["terminals"]
        # strips alternate S / D; with an even nf both outer strips are the same terminal (left == right)
        other = {"source": "drain", "drain": "source"}
        out["sd"] = [(r, rail if dummy else t[s["left"] if i % 2 == 0 else other[s["left"]]])
                     for i, r in enumerate(groups["sd"])]
        out["gate"] = groups["gate"]
        out["gate_net"] = rail if dummy else t["gate"]
    return out


def _rows(pdk: dict, v: dict, by_id: dict, rail: str) -> list:
    rows: dict = {}
    for s in v["slots"]:
        rows.setdefault(s["row"], []).append(_slot_geom(pdk, v, s, by_id, rail))
    return [sorted(rows[r], key=lambda g: g["slot"]["x"]) for r in sorted(rows)]


def _up(row: list) -> bool:
    return row[0]["slot"]["orient"] == "R0"


def _strip_x(c: tuple, grid: float) -> float:
    return pcell.snap((c[0] + c[2]) / 2, grid)


# --- MOS: gates and S/D units ----------------------------------------------------------

def _gate_modes(rows: list, kind: str) -> list:
    """"pad" (M3 trunk on the pad row) when every copy of the row has the same gate net and
    the structure is not a DP / latch (its gates belong in the middle channel), else "stub"."""
    return ["pad" if kind != "cc" and len({q["gate_net"] for q in row if not q["dummy"]}) == 1 else "stub"
            for row in rows]


def _gate_x(q: dict, grid: float) -> float:
    p = q["gate"][(len(q["gate"]) - 1) // 2]
    return pcell.snap((p[0] + p[2]) / 2, grid)


def _pad_band(row: list, trunk_w: float) -> tuple:
    """y range of the pad-row M3 trunk: inner edge on the pads' inner edge."""
    pads = [p for q in row for p in q["gate"]]
    if _up(row):
        y0 = min(p[1] for p in pads)
        return y0, round(y0 + trunk_w, _ROUND)
    y1 = max(p[3] for p in pads)
    return round(y1 - trunk_w, _ROUND), y1


def _gate_stubs(rows: list, modes: list, grid: float) -> list:
    """One gate stub per device copy of a "stub" row: middle pad, or (row under a channel both
    rows' gates face) the gap to a neighbouring device copy, each gap used once."""
    n = len(rows)
    gch = [exit_channels(r, row[0]["slot"]["orient"], "gate")[0] for r, row in enumerate(rows)]
    stubs = []
    for r, row in enumerate(rows):
        if modes[r] != "stub":
            continue
        c = gch[r]
        side = "below" if c == r + 1 else "above"
        shared = side == "below" and r + 1 < n and gch[r + 1] == c and modes[r + 1] == "stub"
        used = set()
        for i, g in enumerate(row):
            if g["dummy"]:
                continue
            gap = None
            if shared:
                for j in (i + 1, i - 1):
                    if 0 <= j < len(row) and not row[j]["dummy"] and frozenset((i, j)) not in used:
                        used.add(frozenset((i, j)))
                        gap = j
                        break
            if gap is None:
                x = _gate_x(g, grid)
            else:
                a, b = sorted((g, row[gap]), key=lambda q: q["slot"]["x"])
                x = pcell.snap((a["sd"][-1][0][2] + b["sd"][0][0][0]) / 2, grid)
            stubs.append({"row": r, "i": i, "x": x, "net": g["gate_net"], "ch": c, "side": side, "gap": gap})
    return stubs


def _sd_units(rows: list, grid: float) -> dict:
    """{(row, net): [{"x", "cols"}]} of the S/D strips that need a route (not dummies, not diode
    drains = the copy's gate net). Facing strips of neighbouring copies on one net form one
    unit at the gap centre."""
    cols: dict = {}
    for r, row in enumerate(rows):
        for i, q in enumerate(row):
            if q["dummy"]:
                continue
            for k, (_, net) in enumerate(q["sd"]):
                if net != q["gate_net"]:
                    cols.setdefault((r, net), []).append((i, k))
    units = {}
    for (r, net), cs in cols.items():
        todo, out = sorted(cs), []
        while todo:
            i, k = todo.pop(0)
            q = rows[r][i]
            if k == len(q["sd"]) - 1 and (i + 1, 0) in todo:
                todo.remove((i + 1, 0))
                a, b = q["sd"][k][0], rows[r][i + 1]["sd"][0][0]
                out.append({"x": pcell.snap((a[2] + b[0]) / 2, grid), "cols": [(i, k), (i + 1, 0)]})
            else:
                out.append({"x": _strip_x(q["sd"][k][0], grid), "cols": [(i, k)]})
        units[(r, net)] = out
    return units


# --- MOS: geometry of channels -----------------------------------------------------------

def _bounds(v: dict, rows: list, modes: list, ru: dict) -> list:
    """(lo, hi) of every channel's track region: between the row boxes (or row and ring
    opening), minus a pad-row trunk sticking into it plus met3 space."""
    o = v["guard_ring"]["opening"]
    rb = [(min(q["bbox"][1] for q in row), max(q["bbox"][3] for q in row)) for row in rows]
    b = [[o["y_min"], rb[0][0]]] + [[rb[c - 1][1], rb[c][0]] for c in range(1, len(rows))] + [[rb[-1][1], o["y_max"]]]
    for r, row in enumerate(rows):
        if modes[r] == "pad":
            y0, y1 = _pad_band(row, ru["trunk_w"])
            if _up(row):
                b[r + 1][0] = max(b[r + 1][0], round(y1 + ru["space3"], _ROUND))
            else:
                b[r][1] = min(b[r][1], round(y0 - ru["space3"], _ROUND))
    return [tuple(x) for x in b]


def _need(t: int, ru: dict) -> float:
    return 0.0 if t == 0 else (t - 1) * ru["pitch3"] + ru["track_need"]


def _side_off(v: dict, side: str, stack_side: str | None, ru: dict) -> float:
    """Distance from the opening edge to the first side track's left / right edge: clear of
    the rail via stack on the ring band on that side."""
    if side != stack_side:
        return 0.0
    protrude = max(ru["v1m2"][0], ru["v2m2"][0]) / 2 - v["guard_ring"]["grw"] / 2
    return round(max(0.0, protrude) + ru["space2"], _ROUND)


def _extras(v: dict, rows: list, bounds: list, tracks: list, sides: dict, stack_side, ru: dict) -> tuple:
    """Grid-rounded growth per channel and of the left / right side channels."""
    g, o = ru["grid"], v["guard_ring"]["opening"]
    ch = [_ceil_grid(max(0.0, _need(len(t), ru) - (hi - lo)), g) for (lo, hi), t in zip(bounds, tracks)]
    avail = {"left": min(q["bbox"][0] for row in rows for q in row) - o["x_min"],
             "right": o["x_max"] - max(q["bbox"][2] for row in rows for q in row)}
    grow = {}
    for side in ("left", "right"):
        n = len(sides[side])
        need = 0.0 if n == 0 else _side_off(v, side, stack_side, ru) + ru["side_w"] + (n - 1) * ru["pitch2"]
        grow[side] = _ceil_grid(max(0.0, need - avail[side]), g)
    return ch, grow


# --- MOS: plan -------------------------------------------------------------------------

def _plan(v: dict, rows: list, rail: str, matched: list, external: set, ru: dict) -> dict | None:
    """Exit channel (and rail drop or trunk) per (row, S/D net) and track order per channel:
    smallest routed block area, then fewest external nets without an outer-channel trunk (those
    can be entered from the top / bottom edge), then fewest crossed tracks."""
    n, g = len(rows), ru["grid"]
    kind = v.get("kind")
    modes = _gate_modes(rows, kind)
    gstubs = _gate_stubs(rows, modes, g)
    gvias = {r: [_gate_x(q, g) for q in row if not q["dummy"]] for r, row in enumerate(rows) if modes[r] == "pad"}
    units = _sd_units(rows, g)
    keys = sorted(units)
    gch = [exit_channels(r, rows[r][0]["slot"]["orient"], "gate")[0] for r in range(n)]
    gate_nets = {q["gate_net"] for row in rows for q in row if not q["dummy"]}
    options = []
    for r, net in keys:
        opts = []
        for c in exit_channels(r, rows[r][0]["slot"]["orient"], "source"):
            if kind == "cc" and c == gch[r]:
                continue                                    # DP: only the inputs in the middle channel
            if net == rail and c != gch[r] and c in (0, n):
                opts.append((c, "drop"))
            opts.append((c, "trunk"))
        options.append(opts)
    if math.prod(len(o) for o in options) > MAX_SIDE_COMBOS:
        logger.warning("block_router: too many S/D side choices, using the first option per net")
        options = [o[:1] for o in options]
    bounds = _bounds(v, rows, modes, ru)

    best = None
    for choice in itertools.product(*options):
        per = [[] for _ in range(n + 1)]
        drops, ok = set(), True
        for st in gstubs:
            per[st["ch"]].append((st["x"], st["net"], st["side"]))
        for (r, net), (c, mode) in zip(keys, choice):
            if mode == "drop":
                drops.add(c)
                continue
            for u in units[(r, net)]:
                if c == gch[r] and r in gvias and any(abs(u["x"] - x) < ru["gate_keep"] - _EPS for x in gvias[r]):
                    ok = False
                per[c].append((u["x"], net, "below" if c == r + 1 else "above"))
        if not ok or any(per[c] for c in drops):
            continue
        orders, stub_cost = [], 0
        for st in per:
            close = any(a[2] == b[2] and a[1] != b[1] and abs(a[0] - b[0]) < ru["pitch2"] - _EPS
                        for a, b in itertools.combinations(st, 2))
            res = None if close else (_order(st, ru["pitch2"], matched) if st else ({}, 0))
            if res is None:
                break
            orders.append(res[0])
            stub_cost += res[1]
        if len(orders) < n + 1:
            continue
        trunks: dict = {}
        for c, tr in enumerate(orders):
            for net in tr:
                trunks.setdefault(net, []).append(("c", c))
        for r in gvias:
            trunks.setdefault(next(q["gate_net"] for q in rows[r] if not q["dummy"]), []).append(("p", r))
        sides = {"left": [], "right": []}
        for net in sorted(trunks):
            if net != rail and len(trunks[net]) > 1:
                sides["left" if kind != "cc" or net in gate_nets else "right"].append(net)
        stack_side = None
        if rail in trunks:
            stack_side = "right" if not sides["right"] else ("left" if not sides["left"] else "right")
        ch, grow = _extras(v, rows, bounds, orders, sides, stack_side, ru)
        area = (v["width_um"] + grow["left"] + grow["right"]) * (v["height_um"] + sum(ch))
        inner = sum(1 for net in external if any(t[0] == "c" for t in trunks.get(net, []))
                    and not any(net in orders[c] for c in (0, n)))
        key = (round(area, _ROUND), inner, stub_cost)
        if best is None or key < best[0]:
            best = (key, {"choice": dict(zip(keys, choice)), "tracks": orders, "trunks": trunks, "sides": sides,
                          "stack_side": stack_side, "extra_ch": ch, "grow": grow, "modes": modes,
                          "gate_nets": gate_nets})
    return best[1] if best else None


# --- MOS: relayout and realize -----------------------------------------------------

def _relayout(pdk: dict, v: dict, model: str, plan: dict) -> dict:
    """Variant with the channels and side channels grown and the ring re-wrapped."""
    out = copy.deepcopy(v)
    ring, clr = v["guard_ring"], pdk["devices"][model]["clearance"]
    orients = v["orient"]
    cb = clr["bottom"] if orients[0] == "R0" else clr["top"]
    ct = clr["top"] if orients[-1] == "R0" else clr["bottom"]
    dl, dr = plan["grow"]["left"], plan["grow"]["right"]
    cw = ring["in_w"] - clr["left"] - clr["right"] + dl + dr
    chh = ring["in_l"] - cb - ct + sum(plan["extra_ch"])
    W, H, ox, oy, new_ring = sp.ring_wrap(pdk, model, cw, chh, orients[0], orients[-1])
    old_x0, old_y0 = ring["opening"]["x_min"] + clr["left"], ring["opening"]["y_min"] + cb
    below = list(itertools.accumulate(plan["extra_ch"][:-1]))
    for s in out["slots"]:
        s["x"] = round(s["x"] - old_x0 + ox + dl, _ROUND)
        s["y"] = round(s["y"] - old_y0 + oy + below[s["row"]], _ROUND)
    out.update(width_um=W, height_um=H, guard_ring=new_ring)
    return out


def _realize(v: dict, rows: list, plan: dict, rail: str, external: set, ru: dict) -> dict:
    o, grw = v["guard_ring"]["opening"], v["guard_ring"]["grw"]
    g = ru["grid"]
    n, modes = len(rows), plan["modes"]
    shapes = []

    def add(net, layer, rect):
        shapes.append({"net": net, "layer": layer, "rect": list(_r(*rect))})

    def via1(net, x, y, along_x=False):
        w, h = ru["v1m1"] if not along_x else ru["v1m1"][::-1]
        add(net, "via1", _box(x, y, ru["cut1"], ru["cut1"]))
        add(net, "met1", _box(x, y, w, h))
        # own met2 landing: a strap ending at a short strip does not enclose the cut enough (m2.5)
        w, h = ru["v1m2"] if not along_x else ru["v1m2"][::-1]
        add(net, "met2", _box(x, y, w, h))

    def via2(net, x, y, along_x=False):
        w, h = ru["v2m2"] if not along_x else ru["v2m2"][::-1]
        add(net, "via2", _box(x, y, ru["cut2"], ru["cut2"]))
        add(net, "met2", _box(x, y, w, h))
        add(net, "met3", _box(x, y, *ru["v2m3"]))

    # trunk y: channel tracks centred in their region, pad-row trunks on the pad row
    track_y = {}
    for c, ((lo, hi), tr) in enumerate(zip(_bounds(v, rows, modes, ru), plan["tracks"])):
        base = lo + _floor_grid((hi - lo - _need(len(tr), ru)) / 2, g) + ru["track_need"] / 2
        for net, i in tr.items():
            track_y[("c", c, net)] = round(base + i * ru["pitch3"], _ROUND)
    for r, row in enumerate(rows):
        if modes[r] == "pad":
            y0, y1 = _pad_band(row, ru["trunk_w"])
            net = next(q["gate_net"] for q in row if not q["dummy"])
            track_y[("p", r, net)] = round((y0 + y1) / 2, _ROUND)
    trunk_x: dict = {k: [] for k in track_y}

    def to_track(net, x, y_from, c, up):
        ty = track_y[("c", c, net)]
        lo, hi = (y_from, ty + ru["v2m2"][1] / 2) if up else (ty - ru["v2m2"][1] / 2, y_from)
        add(net, "met2", (x - ru["stub_w"] / 2, lo, x + ru["stub_w"] / 2, hi))
        via2(net, x, ty)
        trunk_x[("c", c, net)].append(x)

    # gates
    gstubs = {(st["row"], st["i"]): st for st in _gate_stubs(rows, modes, g)}
    for r, row in enumerate(rows):
        up = _up(row)
        for i, q in enumerate(row):
            pads = q["gate"]
            py0, py1 = pads[0][1], pads[-1][3]
            xs = [p[0] for p in pads] + [p[2] for p in pads]
            if q["dummy"]:                              # whole dummy in met1 to the ring
                cols = [c for c, _ in q["sd"]]
                xs += [c[0] for c in cols] + [c[2] for c in cols]
                xs.append(o["x_min"] - grw / 2 if i == 0 else o["x_max"] + grw / 2)
                for c in cols:
                    add(rail, "met1", (c[0], c[1], c[2], py1) if up else (c[0], py0, c[2], c[3]))
                add(rail, "met1", (min(xs), py0, max(xs), py1))
                continue
            net = q["gate_net"]
            for c, sd_net in q["sd"]:
                if sd_net == net:                       # diode: drain strip up to the strap
                    xs += [c[0], c[2]]
                    add(net, "met1", (c[0], c[1], c[2], py1) if up else (c[0], py0, c[2], c[3]))
            if modes[r] == "pad":                       # via stack into the pad-row trunk
                x, y = _gate_x(q, g), track_y[("p", r, net)]
                via1(net, x, y, along_x=True)
                add(net, "met2", _box(x, y, max(ru["v1m2"][1], ru["v2m2"][1]), max(ru["v1m2"][0], ru["v2m2"][0])))
                add(net, "via2", _box(x, y, ru["cut2"], ru["cut2"]))
                add(net, "met3", _box(x, y, *ru["v2m3"]))
                trunk_x[("p", r, net)].append(x)
                add(net, "met1", (min(xs), py0, max(xs), py1))
                continue
            st = gstubs[(r, i)]
            vy = py0 + ru["v1m1"][1] / 2 if up else py1 - ru["v1m1"][1] / 2
            if st["gap"] is not None:
                xs += [st["x"] - ru["v1m1"][0] / 2, st["x"] + ru["v1m1"][0] / 2]
            add(net, "met1", (min(xs), py0, max(xs), py1))
            via1(net, st["x"], vy)
            to_track(net, st["x"], vy - ru["v1m2"][1] / 2 if up else vy + ru["v1m2"][1] / 2, st["ch"], up)

    # S/D: full-length straps with via1 arrays, bridges, stubs into the channel or drops onto the ring
    def strap(net, c):
        x, h = _strip_x(c, g), c[3] - c[1]
        add(net, "met2", (x - ru["stub_w"] / 2, c[1], x + ru["stub_w"] / 2, c[3]))
        p = ru["v1_pitch"]
        k = max(1, int(math.floor((h - p) / p + _GRID_TOL)) + 1)
        y = c[1] + _floor_grid((h - k * p) / 2, g) + p / 2
        for j in range(k):
            via1(net, x, round(y + j * p, _ROUND))

    units = _sd_units(rows, g)
    for (r, net), (c, mode) in plan["choice"].items():
        up = c == r + 1
        for u in units[(r, net)]:
            strips = [rows[r][i]["sd"][k][0] for i, k in u["cols"]]
            for s in strips:
                strap(net, s)
            if mode == "drop":
                band = o["y_max"] + grw / 2 if up else o["y_min"] - grw / 2
                for s in strips:
                    add(net, "met1", (s[0], s[1], s[2], band) if up else (s[0], band, s[2], s[3]))
                continue
            end = max(s[3] for s in strips) if up else min(s[1] for s in strips)
            if len(strips) == 2:                        # bridge + plate over the gap
                a, b = strips
                lo_x, hi_x = _strip_x(a, g) - ru["stub_w"] / 2, _strip_x(b, g) + ru["stub_w"] / 2
                add(net, "met2", (lo_x, max(a[1], b[1]), hi_x, min(a[3], b[3])))
                h1 = ru["v1m1"][1]
                add(net, "met1", (a[0], end - h1, b[2], end) if up else (a[0], end, b[2], end + h1))
            to_track(net, u["x"], end, c, up)

    # side channels: one M2 track per net with several trunks
    for side in ("left", "right"):
        off = _side_off(v, side, plan["stack_side"], ru)
        for j, net in enumerate(plan["sides"][side]):
            d = off + ru["side_w"] / 2 + j * ru["pitch2"]
            x = round(o["x_min"] + d if side == "left" else o["x_max"] - d, _ROUND)
            keys = [k for k in track_y if k[2] == net]
            ys = [track_y[k] for k in keys]
            add(net, "met2", (x - ru["stub_w"] / 2, min(ys) - ru["v2m2"][1] / 2, x + ru["stub_w"] / 2,
                              max(ys) + ru["v2m2"][1] / 2))
            for k in keys:
                via2(net, x, track_y[k])
                trunk_x[k].append(x)

    # rail trunks onto the ring band
    if plan["stack_side"]:
        band_x = round(o["x_max"] + grw / 2 if plan["stack_side"] == "right" else o["x_min"] - grw / 2, _ROUND)
        for k in track_y:
            if k[2] == rail:
                via2(rail, band_x, track_y[k])
                via1(rail, band_x, track_y[k])
                trunk_x[k].append(band_x)
    trunks = [{"net": k[2], "key": [k[0], k[1]], "y": track_y[k], "x0": min(xs), "x1": max(xs)}
              for k, xs in trunk_x.items() if xs]
    routing = {"shapes": shapes, "pins": [], "trunks": trunks,
               "access": _access(v, trunks, plan, shapes, n, external, ru),
               # wire sizes apply_access needs to place pins after placement (no pdk there)
               "rules": {k: ru[k] for k in ("grid", "trunk_w", "stub_w", "side_w", "cut2", "v2m2", "v2m3")}}
    default = []
    for net in sorted(external):        # first trunk, on the edge(s) the block's rule allows
        ends = [a for a in routing["access"] if a["net"] == net and a["side"] in ("left", "right")]
        default += [{"net": net, "side": a["side"], "point": a["seg"][:2]} for a in ends if a["trunk"] == ends[0]["trunk"]]
    _connect(v, routing, default, ru)
    return routing


def _free(shapes: list, net: str, lo: float, hi: float, y0: float, y1: float, w: float, ru: dict) -> list:
    """Grid intervals of x in [lo, hi] where a vertical met2 wire of width w spanning y0..y1 keeps
    met2 space to every other net's met2."""
    s, g = ru["space2"], ru["grid"]
    blocked = sorted((r[0] - s - w / 2, r[2] + s + w / 2) for sh in shapes
                     if sh["layer"] == "met2" and sh["net"] != net
                     for r in [sh["rect"]] if r[1] < y1 + s - _EPS and r[3] > y0 - s + _EPS)
    out, x = [], lo
    for b0, b1 in blocked:
        if b1 <= x + _EPS:
            continue
        if b0 > x + _EPS:
            out.append((x, min(hi, b0)))
        x = max(x, b1)
        if x > hi:
            break
    if x <= hi + _EPS:
        out.append((x, hi))
    snapped = [(round(_ceil_grid(a, g), _ROUND), round(_floor_grid(b, g), _ROUND)) for a, b in out]
    return [(a, b) for a, b in snapped if a <= b + _EPS]


def _access(v: dict, trunks: list, plan: dict, shapes: list, n: int, external: set, ru: dict) -> list:
    """Every place an external net may enter the block ([USER 2026-11-09]): each trunk's ends on the
    left / right edge (cc: inputs left, the rest right, nothing else); a trunk in an outer channel
    also anywhere along it from the top / bottom edge (M2 straight down through the ring); a net's
    side-channel track at its x from the top / bottom edge."""
    o, W, H = v["guard_ring"]["opening"], v["width_um"], v["height_um"]
    kind = v.get("kind")
    out = []
    for net in sorted(external):
        mine = sorted((t for t in trunks if t["net"] == net), key=lambda t: t["key"])
        edges = ["left", "right"] if kind != "cc" else (["left"] if net in plan["gate_nets"] else ["right"])
        for t in mine:
            for e in edges:
                x = 0.0 if e == "left" else W
                out.append({"net": net, "side": e, "seg": [x, t["y"], x, t["y"]], "trunk": t["key"]})
        if kind == "cc":
            continue
        w = max(ru["stub_w"], ru["v2m2"][0])
        for t in mine:
            if t["key"][0] != "c" or t["key"][1] not in (0, n):
                continue
            bottom = t["key"][1] == 0
            y0, y1 = (0.0, t["y"] + ru["v2m2"][1] / 2) if bottom else (t["y"] - ru["v2m2"][1] / 2, H)
            edge, side = (0.0, "bottom") if bottom else (H, "top")
            for a, b in _free(shapes, net, t["x0"], t["x1"], y0, y1, w, ru):
                out.append({"net": net, "side": side, "seg": [a, edge, b, edge], "trunk": t["key"]})
        for sd in ("left", "right"):
            if net not in plan["sides"][sd]:
                continue
            j = plan["sides"][sd].index(net)
            d = _side_off(v, sd, plan["stack_side"], ru) + ru["side_w"] / 2 + j * ru["pitch2"]
            x = round(o["x_min"] + d if sd == "left" else o["x_max"] - d, _ROUND)
            ys = [t["y"] for t in mine]
            for side, y0, y1, edge in (("bottom", 0.0, min(ys), 0.0), ("top", max(ys), H, H)):
                if _free(shapes, net, x, x, y0, y1, ru["side_w"], ru):
                    out.append({"net": net, "side": side, "seg": [x, edge, x, edge], "track": [x, min(ys), max(ys)]})
    return out


def _connect(v: dict, routing: dict, chosen: list, ru: dict) -> None:
    """Pins at the chosen access points and every trunk cut to its stubs plus the chosen points;
    chosen: [{"net", "side", "point": [x, y]}] on the net's access segments."""
    o, W, H, g = v["guard_ring"]["opening"], v["width_um"], v["height_um"], ru["grid"]
    half = ru["trunk_w"] / 2
    shapes, pins = routing["shapes"], routing["pins"]
    xs = {(t["net"], *t["key"]): [t["x0"], t["x1"]] for t in routing["trunks"]}
    y_of = {(t["net"], *t["key"]): t["y"] for t in routing["trunks"]}

    def add(net, layer, rect, tag, side=None):
        sh = {"net": net, "layer": layer, "rect": list(_r(*rect))}
        if side:
            sh["side"] = side
            pins.append(sh)
        else:
            sh["tag"] = tag
            shapes.append(sh)

    for c in chosen:
        net, side, (px, py) = c["net"], c["side"], c["point"]
        a = next(a for a in routing["access"] if a["net"] == net and a["side"] == side
                 and a["seg"][0] - _EPS <= px <= a["seg"][2] + _EPS and a["seg"][1] - _EPS <= py <= a["seg"][3] + _EPS)
        if side in ("left", "right"):
            k = (net, *a["trunk"])
            y = y_of[k]
            if side == "left":
                xs[k].append(o["x_min"] + half)
                add(net, "met3", (0.0, y - half, o["x_min"], y + half), None, side)
            else:
                xs[k].append(o["x_max"] - half)
                add(net, "met3", (o["x_max"], y - half, W, y + half), None, side)
            continue
        bottom = side == "bottom"
        if "trunk" in a:            # M2 drop from the trunk through the ring
            k = (net, *a["trunk"])
            x, y, w = min(max(round(_floor_grid(px + g / 2, g), _ROUND), a["seg"][0]), a["seg"][2]), y_of[k], ru["stub_w"]
            xs[k].append(x)
            add(net, "met2", (x - w / 2, o["y_min"], x + w / 2, y) if bottom else (x - w / 2, y, x + w / 2, o["y_max"]), "access")
            for layer, (bw, bh) in (("via2", (ru["cut2"], ru["cut2"])), ("met2", ru["v2m2"]), ("met3", ru["v2m3"])):
                add(net, layer, _box(x, y, bw, bh), "access")
        else:                       # the side-channel track continued to the edge
            x, lo, hi = a["track"]
            w = ru["side_w"]
            add(net, "met2", (x - w / 2, o["y_min"], x + w / 2, lo) if bottom else (x - w / 2, hi, x + w / 2, o["y_max"]), "access")
        add(net, "met2", (x - w / 2, 0.0, x + w / 2, o["y_min"]) if bottom else (x - w / 2, o["y_max"], x + w / 2, H), None, side)
    for k, xx in xs.items():
        y = y_of[k]
        add(k[0], "met3", (min(xx) - half, y - half, max(xx) + half, y + half), "trunk")


def apply_access(v: dict, chosen: list) -> dict:
    """Copy of a routed variant with pins only at the chosen access points (nets not in chosen keep
    their current pins) and the trunk ends nobody uses cut."""
    out = copy.deepcopy(v)
    routing = out["routing"]
    if "trunks" not in routing:             # chains / caps: fixed pins, nothing to cut
        return out
    nets = {c["net"] for c in chosen}
    keep = [{"net": p["net"], "side": p["side"],
             "point": [(p["rect"][0] + p["rect"][2]) / 2 if p["side"] in ("top", "bottom") else
                       (0.0 if p["side"] == "left" else out["width_um"]),
                       (p["rect"][1] + p["rect"][3]) / 2 if p["side"] in ("left", "right") else
                       (0.0 if p["side"] == "bottom" else out["height_um"])]}
            for p in routing["pins"] if p["net"] not in nets]
    routing["shapes"] = [s for s in routing["shapes"] if s.get("tag") not in ("trunk", "access")]
    routing["pins"] = []
    _connect(out, routing, keep + list(chosen), routing["rules"])
    return out


def _devices(rows: list) -> list:
    """Pins of every slot in the block frame, for viewers (no PDK needed): MOS S/D strips with
    their nets, gate pads, gate net and active area (inside the innermost pin edges)."""
    out = []
    for row in rows:
        for q in row:
            s, sd = q["slot"], sorted((c for c, _ in q["sd"]), key=lambda c: c[0])
            if _up(row):
                y0, y1 = min(c[1] for c in sd), min(p[1] for p in q["gate"])
            else:
                y0, y1 = max(p[3] for p in q["gate"]), max(c[3] for c in sd)
            out.append({"row": s["row"], "col": s["col"], "block_id": s["block_id"],
                        "sd": [[list(c), n] for c, n in q["sd"]], "gate": [list(p) for p in q["gate"]],
                        "gate_net": q["gate_net"], "active": list(_r(sd[0][2], y0, sd[-1][0], y1))})
    return out


def _route_one(pdk: dict, v: dict, members: list, rail: str, external: set, ru: dict) -> dict | None:
    by_id = {m["block_id"]: m for m in members}
    rows = _rows(pdk, v, by_id, rail)
    matched = []
    if len(members) == 2:
        for t in ("drain", "gate", "source"):
            a, b = members[0]["terminals"][t], members[1]["terminals"][t]
            if a != b and rail not in (a, b):
                matched.append((a, b))
    plan = _plan(v, rows, rail, matched, external, ru)
    if plan is None:
        logger.info("block_router: %s %s no legal channel plan", v.get("pattern"), v.get("orient"))
        return None
    out = _relayout(pdk, v, members[0]["model"], plan)
    rows = _rows(pdk, out, by_id, rail)
    out["routing"] = {**_realize(out, rows, plan, rail, external, ru), "devices": _devices(rows)}
    return out


# --- resistor chain ------------------------------------------------------------------------

def _route_chain(pdk: dict, v: dict, members: list, external: set, ru: dict) -> dict:
    by_id = {m["block_id"]: m for m in members}
    segs = [_slot_geom(pdk, v, s, by_id, "") for s in sorted(v["slots"], key=lambda s: s["x"])
            if s["block_id"] is not None]           # row-end dummy resistors stay unconnected
    pads = [tuple(q["groups"]["ends"]) for q in segs]
    jumpers, (first, last) = chain_jumpers(pads)
    shapes, pins = [], []
    ends = [(by_id[segs[0]["slot"]["block_id"]]["terminals"]["n1"], first),
            (by_id[segs[-1]["slot"]["block_id"]]["terminals"]["n2"], last)]
    for i, j in enumerate(jumpers):
        a, b = segs[i]["slot"]["block_id"], segs[i + 1]["slot"]["block_id"]
        net = by_id[a]["terminals"]["n2"] if a != b else f"{a}.{i}"
        shapes.append({"net": net, "layer": "met1", "rect": list(j)})
        if a != b:
            ends.append((net, j))
    for net, rect in ends:
        if net not in external:
            continue
        x, y = pcell.snap((rect[0] + rect[2]) / 2, ru["grid"]), pcell.snap((rect[1] + rect[3]) / 2, ru["grid"])
        shapes.append({"net": net, "layer": "via1", "rect": list(_box(x, y, ru["cut1"], ru["cut1"]))})
        side = "top" if (rect[1] + rect[3]) / 2 > v["height_um"] / 2 else "bottom"
        pins.append({"net": net, "layer": "met2", "rect": list(rect), "side": side})
    out = copy.deepcopy(v)
    devices = [{"row": q["slot"]["row"], "col": q["slot"]["col"], "block_id": q["slot"]["block_id"],
                "pads": [list(p) for p in q["groups"]["ends"]]} for q in segs]
    out["routing"] = {"shapes": shapes, "pins": pins, "devices": devices}
    return out


def _power_pins(v: dict, rail: str) -> list:
    """The guard ring band (met1, tied to the rail) as power pins on its four sides."""
    ring = v.get("guard_ring")
    if not ring:
        return []
    o, g = ring["opening"], ring["grw"]
    sides = {"bottom": (o["x_min"] - g, o["y_min"] - g, o["x_max"] + g, o["y_min"]),
             "top": (o["x_min"] - g, o["y_max"], o["x_max"] + g, o["y_max"] + g),
             "left": (o["x_min"] - g, o["y_min"], o["x_min"], o["y_max"]),
             "right": (o["x_max"], o["y_min"], o["x_max"] + g, o["y_max"])}
    return [{"net": rail, "layer": "met1", "rect": list(_r(*r)), "side": s, "type": "power"} for s, r in sides.items()]


# --- entry ---------------------------------------------------------------------------------

def route_structure(pdk: dict, variant: dict, members: list, rail: str, external: set) -> dict | None:
    """Routed copy of a structure variant (slots / size / ring / orientation updated, plus
    "routing": {"shapes": [{net, layer, rect}], "pins": [{net, layer, rect, side}], "access",
    "trunks", "rules"}), or None
    when neither orientation can be routed (vertical constraint cycle) or the structure is not
    supported yet (digital gates, caps, inner full-size dummies)."""
    ru = _rules(pdk)
    cls = pdk["devices"][members[0]["model"]]["class"]
    if cls == "res":
        out = _route_chain(pdk, variant, members, external, ru)
        out["routing"]["power_pins"] = _power_pins(out, rail)
        return out
    if cls not in ("nmos", "pmos") or variant.get("guard_rings") or variant["dummies"]["inner_full_size"]:
        logger.warning("block_router: %s structure not routed (class %s, inner dummies %s)", variant.get("pattern"),
                       cls, variant.get("dummies", {}).get("inner_full_size"))
        return None
    candidates = [variant]
    if variant.get("kind") in ("mirror", "single"):
        candidates.append(sp.flip_variant(pdk, variant, members, rail))
    routed = [r for r in (_route_one(pdk, c, members, rail, external, ru) for c in candidates) if r]
    if not routed:
        logger.warning("block_router: %s no legal channel plan in either orientation", variant.get("pattern"))
        return None
    best = min(routed, key=lambda r: r["width_um"] * r["height_um"])
    best["routing"]["power_pins"] = _power_pins(best, rail)
    return best
