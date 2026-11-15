"""
lib/block_router (in-block routing of 012 structures) — tests B1..B9, proposed 2026-11-09.

API under test:
  exit_channels(row, orient, terminal) -> [channel]   channel c lies below row c (c0 = bottom, rows+1 channels)
  order_tracks(stubs, min_dx, matched=()) -> {net: track} | None
        stubs: (x, net, "below" | "above") = stub from the row under / over the channel; one track per net,
        track 0 lowest; None when the vertical constraints have a cycle
  chain_jumpers(pads) -> (jumpers, (first_free_pad, last_free_pad))   pads: [(bottom, top)] in series order
  route_structure(pdk, variant, members, rail, external) -> routed variant | None
        routed variant: slots / width_um / height_um / guard_ring updated, plus
        "routing": {"shapes": [{"net", "layer", "rect"}], "pins": [{"net", "layer", "rect", "side"}]}
        layers "met1", "met2", "met3", "via1", "via2"; rects absolute in the block frame

Sources of expected values:
  [LIN]   Lin et al., "A Matching-based Placement and Routing System for Analog Design", 2007,
          Sec. IV-B / Fig. 6: backbone = one trunk per net per channel, stubs straight from the pins,
          matching-backbone = the two nets of a matched pair on neighbouring tracks
  [USER]  decisions 2026-11-08 (knowledge/notes/2026-11-08_block-router-decisions-and-pin-fit.md):
          gate wires only into the channel the gates face, S/D either side; no wire over an active
          area (rectangle spanned by a device's S, D and G pins) or over a dummy except straight out
          of its own pin; everything inside the ring except the block pins; M2 stubs, M3 trunks,
          M3 block pins on the left/right edge (MOS); resistor chains: pad-to-pad jumpers, M2 pins
  [DRC]   SkyWater sky130 periphery rules: m1.1/m1.2 0.14/0.14, m2.1/m2.2 0.14/0.14, m3.1/m3.2 0.30/0.30,
          via.1a 0.15, via.4a/5a 0.055/0.085, m2.4/m2.5 0.055/0.085, via2.1a 0.20, via2.4/2.5 0.04/0.085,
          m3.4 0.065 (used until characterize_pdk.py measures pdk["routing"])
  [PROBE] container probe 2026-11-08: res_high_po_0p69 len=3 met1 end pads (-0.295,-3.63,0.295,-1.525),
          (-0.295,1.525,0.295,3.63); [PDK] res gap.x -0.37, width 1.27 -> segment pitch 0.9
  [HAND]  hand calculation shown in the comment
"""
import itertools
import math

import pytest

import block_router as br
import pcell
import structure_placer as sp

PDK = pcell.load_pdk("sky130")
NFET, RES = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__res_high_po_0p69"
AR = (0.25, 4.0)
GRID = 0.005
TOL = 1e-6
MIN_DX = 0.42      # [HAND] M2 stub 0.28 (via2 M2 landing 0.20 + 2*0.04) + M2 space 0.14
ROUTING = {        # [DRC]
    "layers": {"met1": {"gds": [68, 20], "width": 0.14, "space": 0.14},
               "met2": {"gds": [69, 20], "width": 0.14, "space": 0.14},
               "met3": {"gds": [70, 20], "width": 0.30, "space": 0.30}},
    "vias": {"via1": {"gds": [68, 44], "cut": 0.15, "below": "met1", "above": "met2",
                      "enc_below": [0.055, 0.085], "enc_above": [0.055, 0.085]},
             "via2": {"gds": [69, 44], "cut": 0.20, "below": "met2", "above": "met3",
                      "enc_below": [0.04, 0.085], "enc_above": [0.065, 0.065]}},
}
METALS = ("met1", "met2", "met3")
VIA_LAYERS = {"via1": ("met1", "met2"), "via2": ("met2", "met3")}


# --- B1..B5: channel and track rules ------------------------------------------------

def test_b1_exit_channels():
    # [USER] gates only into the channel they face; [PDK] gate_con_pos top -> R0 gates face up, R180 down.
    # Channel c lies below row c: row r has channel r below it and r+1 above it.
    assert br.exit_channels(0, "R0", "gate") == [1]
    assert br.exit_channels(1, "R180", "gate") == [1]
    assert br.exit_channels(0, "R0", "source") == [0, 1]
    assert br.exit_channels(1, "R180", "drain") == [1, 2]


def test_b2_backbone_one_track():
    # [LIN] Fig. 6(a): one net, three pins -> one trunk on one track
    assert br.order_tracks([(0.0, "A", "below"), (1.0, "A", "below"), (2.0, "A", "below")], MIN_DX) == {"A": 0}


def test_b3_vertical_constraint():
    # [HAND] A below and B above at the same x: A's stub reaches up to t(A), B's down to t(B); no overlap
    # needs t(A) < t(B).
    # Unconstrained, B would go lowest: B below x3 at x = 3, 5, 7 plus B above, A below x1:
    #   B0 A1: stubs 3*0 + (2-1-0) + 1 = 2;  A0 B1: 0 + 3*1 + 0 = 3  -> B0 A1 (B3b)
    # With B's above stub at A's x = 1 the constraint forces A0 B1 (B3a).
    base = [(1.0, "A", "below"), (3.0, "B", "below"), (5.0, "B", "below"), (7.0, "B", "below")]
    assert br.order_tracks(base + [(1.0, "B", "above")], MIN_DX) == {"A": 0, "B": 1}
    assert br.order_tracks(base + [(9.0, "B", "above")], MIN_DX) == {"B": 0, "A": 1}


def test_b4_constraint_cycle_unroutable():
    # [HAND] x=1: A below, B above -> t(A) < t(B); x=3: B below, A above -> t(B) < t(A): no order
    stubs = [(1.0, "A", "below"), (1.0, "B", "above"), (3.0, "B", "below"), (3.0, "A", "above")]
    assert br.order_tracks(stubs, MIN_DX) is None


def test_b5_matched_pair_neighbouring_tracks():
    # [LIN] matching-backbone: matched nets on neighbouring tracks.
    # [HAND] all stubs from below, cost = sum of tracks over stubs; A x4, B x1, C x2:
    #   free:            A0 C1 B2 = 0 + 2 + 2 = 4 (best)
    #   A, B neighbours: A0 B1 C2 = 0 + 1 + 4 = 5, C0 A1 B2 = 0 + 4 + 2 = 6, B0 A1 C2 = 7, C0 B1 A2 = 9
    stubs = [(float(i), "A", "below") for i in range(4)] + [(10.0, "B", "below")] + \
            [(20.0, "C", "below"), (21.0, "C", "below")]
    assert br.order_tracks(stubs, MIN_DX) == {"A": 0, "C": 1, "B": 2}
    assert br.order_tracks(stubs, MIN_DX, matched=[("A", "B")]) == {"A": 0, "B": 1, "C": 2}


# --- B6: resistor chain -----------------------------------------------------------------

def test_b6_chain_jumpers():
    # [PROBE] pads relative to the segment centre, segments at x = 0, 0.9, 1.8 ([PDK] pitch 0.9).
    # [USER] series starts at seg0's top pad (even count: both free ends on top, odd: top + bottom);
    # [HAND] 3 segments: seg0 bottom - seg1 bottom, seg1 top - seg2 top, free ends seg0 top, seg2 bottom;
    # a met1 jumper fills the gap between the two pads at the pads' full height.
    bot, top = (-0.295, -3.63, 0.295, -1.525), (-0.295, 1.525, 0.295, 3.63)
    mv = lambda r, dx: (r[0] + dx, r[1], r[2] + dx, r[3])
    pads = [(mv(bot, x), mv(top, x)) for x in (0.0, 0.9, 1.8)]
    jumpers, (first, last) = br.chain_jumpers(pads)
    assert [tuple(j) for j in jumpers] == [pytest.approx((0.295, -3.63, 0.605, -1.525), abs=TOL),
                                           pytest.approx((1.195, 1.525, 1.505, 3.63), abs=TOL)]
    assert tuple(first) == pytest.approx(top, abs=TOL)
    assert tuple(last) == pytest.approx((1.505, -3.63, 2.095, -1.525), abs=TOL)
    # [HAND] 2 segments: one bottom jumper, both free ends on top
    jumpers, (first, last) = br.chain_jumpers(pads[:2])
    assert [tuple(j) for j in jumpers] == [pytest.approx((0.295, -3.63, 0.605, -1.525), abs=TOL)]
    assert tuple(first) == pytest.approx(top, abs=TOL)
    assert tuple(last) == pytest.approx((0.605, 1.525, 1.195, 3.63), abs=TOL)


# --- B7..B9: routed structures, checked by geometric properties ---------------------------

def _pdk():
    return PDK if "routing" in PDK else {**PDK, "routing": ROUTING}


def _mos(bid, copies, d, g, s, W=2.17, L=0.585):
    return {"block_id": bid, "copies": copies, "model": NFET,
            "pcell": pcell.pcell_params(PDK, NFET, {"W": W, "L": L, "nf": 1}),
            "terminals": {"drain": d, "gate": g, "source": s, "bulk": "vss"}}


def _abs_pins(v: dict, s: dict, members: dict, rail: str) -> list:
    """[(net, kind, rect)] of one slot in the block frame; S/D columns alternate the slot's left/right
    terminal from the left, dummies are all on the rail."""
    if s["block_id"] is None:
        model = v["dummies"]["model"]
        params = v["unit_pcell"] if s["full_size_dummy"] else v["dummies"]["pcell"]
    else:
        model, params = members[s["block_id"]]["model"], v["unit_pcell"]
    fp = PDK["devices"][model]["footprint"]
    w, h = pcell.footprint(PDK, model, params)
    cx, cy = pcell._linear(fp["x0"], params) + w / 2, pcell._linear(fp["y0"], params) + h / 2
    sgn = 1 if s["orient"] == "R0" else -1

    def place(r):
        xs = sorted((s["x"] + sgn * (r[0] - cx), s["x"] + sgn * (r[2] - cx)))
        ys = sorted((s["y"] + sgn * (r[1] - cy), s["y"] + sgn * (r[3] - cy)))
        return (xs[0], ys[0], xs[1], ys[1])

    out = []
    for group in PDK["devices"][model]["pins"]:
        rects = sorted((place(r) for r in pcell.pin_rects(PDK, model, params, group)), key=lambda r: r[0])
        for i, r in enumerate(rects):
            if s["block_id"] is None:
                net = rail
            elif group == "gate":
                net = members[s["block_id"]]["terminals"]["gate"]
            else:
                net = members[s["block_id"]]["terminals"][s["left"] if i % 2 == 0 else s["right"]]
            out.append((net, group, r))
    return out


def _overlap(a, b, strict=True):
    if strict:
        return a[0] < b[2] - TOL and b[0] < a[2] - TOL and a[1] < b[3] - TOL and b[1] < a[3] - TOL
    return a[0] <= b[2] + TOL and b[0] <= a[2] + TOL and a[1] <= b[3] + TOL and b[1] <= a[3] + TOL


def _inside(r, o):
    return r[0] >= o[0] - TOL and r[1] >= o[1] - TOL and r[2] <= o[2] + TOL and r[3] <= o[3] + TOL


def _dist(a, b):
    dx, dy = max(0.0, b[0] - a[2], a[0] - b[2]), max(0.0, b[1] - a[3], a[1] - b[3])
    return math.hypot(dx, dy) if dx and dy else max(dx, dy)


def _on_grid(r):
    return all(abs(c / GRID - round(c / GRID)) < 1e-6 for c in r)


def _inner_active(pins: list):
    """[USER 2026-11-09] active area of one copy: inside its innermost met1 pin edges; None if empty."""
    sd = sorted((r for _, k, r in pins if k == "sd"), key=lambda r: r[0])
    gate = [r for _, k, r in pins if k == "gate"]
    up = (gate[0][1] + gate[0][3]) / 2 > (sd[0][1] + sd[0][3]) / 2
    y0, y1 = (min(r[1] for r in sd), min(r[1] for r in gate)) if up else (max(r[3] for r in gate), max(r[3] for r in sd))
    a = (sd[0][2], y0, sd[-1][0], y1)
    return a if a[0] < a[2] and a[1] < a[3] else None


def _ring_band(v):
    """Ring tap metal (met1) as 4 rects: opening grown by grw."""
    o, g = v["guard_ring"]["opening"], v["guard_ring"]["grw"]
    x0, y0, x1, y1 = o["x_min"], o["y_min"], o["x_max"], o["y_max"]
    return [(x0 - g, y0 - g, x1 + g, y0), (x0 - g, y1, x1 + g, y1 + g),
            (x0 - g, y0, x0, y1), (x1, y0, x1 + g, y1)]


def _check_routed(v: dict, members: list, rail: str, external: set):
    """Properties every routed MOS structure must have ([USER], [DRC])."""
    by_id = {m["block_id"]: m for m in members}
    shapes = [(s["net"], s["layer"], tuple(s["rect"])) for s in v["routing"]["shapes"]]
    pins = [(p["net"], p["layer"], tuple(p["rect"])) for p in v["routing"]["pins"]]
    W, H = v["width_um"], v["height_um"]
    o = v["guard_ring"]["opening"]
    opening = (o["x_min"], o["y_min"], o["x_max"], o["y_max"])
    dev = [(sl, *p) for sl in v["slots"] for p in _abs_pins(v, sl, by_id, rail)]

    # F1 on grid (pin centres may be half-grid, e.g. gate pads at l = 0.585 / 0.525 approached vertically:
    # the wire centreline must still land on grid); F3 inside the block
    for _, _, r in shapes + pins:
        assert _on_grid(r), r
        assert _inside(r, (0.0, 0.0, W, H)), r
    # F6 inside the ring opening, except the ring connection of the rail (= bulk) net on the band
    for net, layer, r in shapes:
        assert _inside(r, opening) or net == rail, (net, layer, r)
    # F7 every external net has a met3 pin on the left or right block edge
    for net in external:
        assert any(n == net and l == "met3" and (abs(r[0]) < TOL or abs(r[2] - W) < TOL) for n, l, r in pins), net

    # F2 nothing over an active area except straight out of a pin of the same net.
    # [USER 2026-11-09] active area = inside the innermost met1 pin edges: x between the inner edges of the
    # outer S/D strips, y from the S/D strip end to the gate pad's inner edge (pad row and end strips are not
    # active); an inner S/D strip (nf > 1) inside it may carry its own wire.
    for sl in v["slots"]:
        sp_pins = [(n, k, r) for (s2, n, k, r) in dev if s2 is sl]
        active = _inner_active(sp_pins)
        for net, layer, r in shapes + pins:
            if active is None or not _overlap(r, active):
                continue
            i = (max(r[0], active[0]), max(r[1], active[1]), min(r[2], active[2]), min(r[3], active[3]))
            ok = any(n == net and k == "sd" and i[0] >= (p[0] + p[2]) / 2 - 0.16 - TOL and
                     i[2] <= (p[0] + p[2]) / 2 + 0.16 + TOL for n, k, p in sp_pins)
            assert ok, ("over active", net, layer, r, sl["row"], sl["col"])

    # F8 [USER] dummies tie to the ring in met1 only: no met2/met3/via2 over a dummy's active area
    # ([USER 2026-11-09] same inner area as F2: an M3 trunk may cross a dummy's gate pad row)
    for sl in v["slots"]:
        if sl["block_id"] is not None:
            continue
        area = _inner_active([(n, k, r) for (s2, n, k, r) in dev if s2 is sl])
        for net, layer, r in shapes + pins:
            assert not (layer in ("met2", "met3", "via2") and _overlap(r, area)), ("over dummy", net, layer, r)

    # F9 [USER 2026-11-09] every routed S/D strip (device copy, not a diode drain) is covered by met2 over its
    # whole length, with via1 cuts on it no more than 0.32 apart ([GDS] miller_ota bias mirror pitch 0.32;
    # via.1a 0.15 + via.2 0.17) and the first / last cut within 0.32 of the strip ends
    for sl in v["slots"]:
        if sl["block_id"] is None:
            continue
        gate = by_id[sl["block_id"]]["terminals"]["gate"]
        for n, k, p in [(n, k, r) for (s2, n, k, r) in dev if s2 is sl]:
            if k != "sd" or n == gate:
                continue
            m2 = [r for nn, l, r in shapes if nn == n and l == "met2" and _overlap(r, p)]
            assert any(r[1] <= p[1] + TOL and r[3] >= p[3] - TOL and r[0] <= p[0] + 0.03 and r[2] >= p[2] - 0.03
                       for r in m2), ("no full-length met2 strap", n, p)
            cuts = sorted((r[1] + r[3]) / 2 for nn, l, r in shapes if nn == n and l == "via1" and _inside(r, p))
            assert cuts, ("no via1 on strip", n, p)
            assert cuts[0] - p[1] <= 0.32 + TOL and p[3] - cuts[-1] <= 0.32 + TOL, ("via1 array short", n, p)
            assert all(b - a <= 0.32 + TOL for a, b in zip(cuts, cuts[1:])), ("via1 pitch", n, p)

    # F5 no shorts / spacing on each metal (device pins against each other are the PCell's business)
    metal = [(n, l, r, False) for n, l, r in shapes + pins if l in METALS] + \
            [(n, "met1", r, True) for (_, n, _, r) in dev] + [("vss", "met1", r, True) for r in _ring_band(v)]
    for (na, la, ra, da), (nb, lb, rb, db) in itertools.combinations(metal, 2):
        if la != lb or na == nb or (da and db):
            continue
        assert _dist(ra, rb) >= ROUTING["layers"][la]["space"] - TOL, ("spacing", la, na, ra, nb, rb)

    # F4 connectivity: every device pin and block pin of a net in one component, nets never merged
    nodes = [(n, l, r) for n, l, r in shapes + pins] + [(n, "met1", r) for (_, n, _, r) in dev] + \
            [("vss", "met1", r) for r in _ring_band(v)]
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in itertools.combinations(range(len(nodes)), 2):
        (_, li, ri), (_, lj, rj) = nodes[i], nodes[j]
        same = li == lj and li in METALS
        via = (li in VIA_LAYERS and lj in VIA_LAYERS[li]) or (lj in VIA_LAYERS and li in VIA_LAYERS[lj])
        if (same or via) and _overlap(ri, rj, strict=False):
            parent[find(i)] = find(j)
    comps: dict = {}
    for i, (n, _, _) in enumerate(nodes):
        comps.setdefault(find(i), set()).add(n)
    assert all(len(nets) == 1 for nets in comps.values()), [c for c in comps.values() if len(c) > 1]
    for net in {n for n, _, _ in nodes}:     # one component per net: all pins joined, no floating metal
        roots = {find(i) for i, (n, _, _) in enumerate(nodes) if n == net}
        assert len(roots) == 1, (net, len(roots))


def test_b7_dp_2x2_routed():
    # S1 input (test_structure_placer): DP 2 copies each -> 2x2 common centroid, gates facing inward.
    members = [_mos(0, 2, "n1", "inm", "tail"), _mos(1, 2, "n2", "inp", "tail")]
    v = sp.structure_variants(PDK, members, "cc", "vss", AR)[0]
    external = {"n1", "n2", "inm", "inp", "tail"}
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    _check_routed(r, members, "vss", external)
    # [USER] the ring grows to hold the channels: never smaller than the unrouted structure
    assert r["width_um"] >= v["width_um"] - TOL and r["height_um"] >= v["height_um"] - TOL


def test_b8_bias_mirror_with_diode_routed():
    # S5 input: XM5 tail/bias, XM7 out/bias, XM8 bias/bias (diode: gate = drain), sources on vss.
    members = [_mos(4, 4, "tail", "bias", "vss", W=2.125, L=0.525),
               _mos(6, 12, "out", "bias", "vss", W=2.125, L=0.525),
               _mos(7, 4, "bias", "bias", "vss", W=2.125, L=0.525)]
    v = sp.structure_variants(PDK, members, "mirror", "vss", AR)[0]
    external = {"tail", "out", "bias"}      # vss = ring net, joined through the ring
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    _check_routed(r, members, "vss", external)
    # [USER] diode XM8: drain joined to its gate in met1 inside the copy, no via on its drain strips
    by_id = {m["block_id"]: m for m in members}
    shapes = [(s["net"], s["layer"], tuple(s["rect"])) for s in r["routing"]["shapes"]]
    for sl in (s for s in r["slots"] if s["block_id"] == 7):
        pins = _abs_pins(r, sl, by_id, "vss")
        drains = [p for n, k, p in pins if k == "sd" and n == "bias"]
        for d in drains:     # met1 extension on the strip (F4 proves it reaches the gate); no via1 on it
            assert any(l == "met1" and n == "bias" and _overlap(m, d, strict=False) for n, l, m in shapes), d
            assert not any(l == "via1" and _overlap(m, d) for n, l, m in shapes), ("via on diode drain", d)
    # [USER 2026-11-09] each block also tried with every device rotated 180 deg, the smaller routed one wins;
    # [GDS] the hand-routed miller_ota bias mirror (same devices) is 17.98 x 8.36 = 150.3 um2: the router must
    # not be larger
    assert r["width_um"] * r["height_um"] <= 150.3 + TOL
    # [USER 2026-11-09] one gate net per row -> M3 gate trunk on the pad row ([GDS] miller_ota y 4.26-4.60)
    for sl in (s for s in r["slots"] if s["block_id"] is not None):
        gate = [p for n, k, p in _abs_pins(r, sl, by_id, "vss") if k == "gate"]
        assert all(any(n == "bias" and l == "met3" and _overlap(m, g) for n, l, m in shapes) for g in gate), sl


def test_b10_dp_neighbour_strips_bridged():
    # [USER 2026-11-09] facing S/D strips of neighbouring copies on one net: met1 bridge, one M2 from the
    # bridge middle into the channel. DP 2x2 bottom row dABd: A = (drain n1 | source tail),
    # B = (source tail | drain n2) -> A's right strip and B's left strip are both tail.
    # [HAND] the single tail via2 sits at the centre of the gap between the two strips' inner edges.
    members = [_mos(0, 2, "n1", "inm", "tail"), _mos(1, 2, "n2", "inp", "tail")]
    v = sp.structure_variants(PDK, members, "cc", "vss", AR)[0]
    r = br.route_structure(_pdk(), v, members, "vss", {"n1", "n2", "inm", "inp", "tail"})
    assert r is not None
    by_id = {m["block_id"]: m for m in members}
    row0 = sorted((s for s in r["slots"] if s["row"] == 0 and s["block_id"] is not None), key=lambda s: s["x"])
    a = max((p for n, k, p in _abs_pins(r, row0[0], by_id, "vss") if k == "sd"), key=lambda p: p[0])
    b = min((p for n, k, p in _abs_pins(r, row0[1], by_id, "vss") if k == "sd"), key=lambda p: p[0])
    shapes = [(s["net"], s["layer"], tuple(s["rect"])) for s in r["routing"]["shapes"]]
    assert any(n == "tail" and l == "met1" and _overlap(m, a, strict=False) and _overlap(m, b, strict=False)
               for n, l, m in shapes)
    # below the bottom row's strips = its outer channel (DP outputs go outside); the top row has its own pair
    between = [m for n, l, m in shapes if n == "tail" and l == "via2" and a[0] < (m[0] + m[2]) / 2 < b[2]
               and m[3] <= min(a[1], b[1])]
    assert len(between) == 1
    assert (between[0][0] + between[0][2]) / 2 == pytest.approx((a[2] + b[0]) / 2, abs=GRID / 2 + TOL)


def test_b11_dp_inputs_middle_outputs_outside():
    # [USER 2026-11-09] DP: only the inputs (gate nets) in the middle channel; drains and tail through the
    # outer channels; input pins on one edge (left), output and tail pins on the other (right).
    members = [_mos(0, 2, "n1", "inm", "tail"), _mos(1, 2, "n2", "inp", "tail")]
    v = sp.structure_variants(PDK, members, "cc", "vss", AR)[0]
    r = br.route_structure(_pdk(), v, members, "vss", {"n1", "n2", "inm", "inp", "tail"})
    assert r is not None
    lo = max(s["y"] + s["h"] / 2 for s in r["slots"] if s["row"] == 0)
    hi = min(s["y"] - s["h"] / 2 for s in r["slots"] if s["row"] == 1)
    for s in r["routing"]["shapes"]:
        m = s["rect"]
        if s["layer"] == "met3" and m[1] >= lo - TOL and m[3] <= hi + TOL:
            assert s["net"] in ("inm", "inp"), s
    W = r["width_um"]
    for p in r["routing"]["pins"]:
        left, right = abs(p["rect"][0]) < TOL, abs(p["rect"][2] - W) < TOL
        if p["net"] in ("inm", "inp"):
            assert left and not right, p
        else:
            assert right and not left, p


def test_b9_resistor_chain_routed():
    # One res_high_po_0p69 member cut into 3 series segments (one row, no dummies), ends n1 = a, n2 = b.
    # [HAND] series: a = seg0 bottom pad, seg0 top - seg1 top, seg1 bottom - seg2 bottom, b = seg2 top.
    member = {"block_id": 3, "copies": 3, "model": RES, "pcell": pcell.pcell_params(PDK, RES, {"L": 3.12}),
              "terminals": {"n1": "a", "n2": "b", "substrate": "vss"}}
    v = sp.structure_variants(PDK, [member], "chain", "vss", AR)[0]
    r = br.route_structure(_pdk(), v, [member], "vss", {"a", "b"})
    assert r is not None
    shapes = [(s["net"], s["layer"], tuple(s["rect"])) for s in r["routing"]["shapes"]]
    pins = [(p["net"], p["layer"], tuple(p["rect"])) for p in r["routing"]["pins"]]
    W, H = r["width_um"], r["height_um"]
    for _, _, rect in shapes + pins:
        assert _on_grid(rect) and _inside(rect, (0.0, 0.0, W, H)), rect
    segs = sorted(r["slots"], key=lambda s: s["x"])
    pads = []
    for s in segs:
        b, t = pcell.pin_rects(PDK, RES, r["unit_pcell"], "ends")      # res PCell origin = bbox centre [PROBE]
        pads.append(tuple((x0 + s["x"], y0 + s["y"], x1 + s["x"], y1 + s["y"]) for x0, y0, x1, y1 in (b, t)))
    # no wire over a resistor body (between its two pads)
    for (b, t) in pads:
        body = (b[0], b[3], b[2], t[1])
        for net, layer, rect in shapes + pins:
            assert not _overlap(rect, body), ("over body", net, layer, rect)
    # [USER] resistor pins: met2 on top of the free end pads (3 segments: a = seg0 top, b = seg2 bottom),
    # joined to the pad by a via1
    for net, pad in (("a", pads[0][1]), ("b", pads[2][0])):
        assert any(n == net and l == "met2" and _inside(rc, pad) for n, l, rc in pins), net
        assert any(l == "via1" and _inside(rc, pad) for n, l, rc in shapes if n == net), net
    # [USER] jumpers are met1 at full pad height and join exactly the series neighbours
    m1 = [rect for _, layer, rect in shapes if layer == "met1"]
    assert any(_overlap(j, pads[0][0], strict=False) and _overlap(j, pads[1][0], strict=False) for j in m1)
    assert any(_overlap(j, pads[1][1], strict=False) and _overlap(j, pads[2][1], strict=False) for j in m1)
    assert not any(_overlap(j, pads[0][1], strict=False) and _overlap(j, pads[1][1], strict=False) for j in m1)
    for j in m1:
        if not any(_inside(j, p) for seg in pads for p in seg):
            assert j[3] - j[1] == pytest.approx(pads[0][0][3] - pads[0][0][1], abs=TOL)


def test_b12_dp_even_fingers_drains_routed():
    # [USER 2026-11-10] DP with nf = 2 per copy: strips alternate S / D from the slot's left terminal, so a copy
    # is S D S or D S D ([HAND]: 3 strips, both outer strips the same terminal). Every drain strip carries its
    # drain net (full-length met2 + via1 of that net, no met2 / via1 of another net on it) and is joined to that
    # net's block pin; no net is merged with another (the bug: all strips labelled source -> drains on tail).
    members = [{**_mos(bid, 2, d, g, "tail"), "pcell": pcell.pcell_params(PDK, NFET, {"W": 2.17, "L": 0.585, "nf": 2})}
               for bid, d, g in ((0, "n1", "inm"), (1, "n2", "inp"))]
    v = sp.structure_variants(PDK, members, "cc", "vss", AR)[0]
    external = {"n1", "n2", "inm", "inp", "tail"}
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    by_id = {m["block_id"]: m for m in members}
    other = {"source": "drain", "drain": "source"}
    shapes = [(s["net"], s["layer"], tuple(s["rect"])) for s in r["routing"]["shapes"]]
    pins = [(p["net"], p["layer"], tuple(p["rect"])) for p in r["routing"]["pins"]]
    dev = []                                   # (net, rect) of every device pin, nets by the [HAND] rule
    for sl in r["slots"]:
        for net, kind, rect in _abs_pins(r, sl, by_id, "vss"):
            dev.append((net, kind, rect))
        if sl["block_id"] is None:
            continue
        t = by_id[sl["block_id"]]["terminals"]
        sd = sorted((rc for _, k, rc in _abs_pins(r, sl, by_id, "vss") if k == "sd"), key=lambda rc: rc[0])
        assert len(sd) == 3
        dev = [(n, k, rc) for n, k, rc in dev if not (k == "sd" and rc in sd)]
        for i, p in enumerate(sd):
            net = t[sl["left"] if i % 2 == 0 else other[sl["left"]]]
            dev.append((net, "sd", p))
            m2 = [(n, rc) for n, l, rc in shapes if l == "met2" and _overlap(rc, p)]
            assert any(n == net and rc[1] <= p[1] + TOL and rc[3] >= p[3] - TOL for n, rc in m2), (net, p)
            assert all(n == net for n, _ in m2), (net, p, m2)
            v1 = [n for n, l, rc in shapes if l == "via1" and _inside(rc, p)]
            assert v1 and all(n == net for n in v1), (net, p)
    for net in ("n1", "n2"):
        assert any(n == net and l == "met3" for n, l, _ in pins), net
    # connectivity: device pins, ring, wires and block pins; one net per component, one component per net
    nodes = shapes + pins + [(n, "met1", rc) for n, _, rc in dev] + [("vss", "met1", rc) for rc in _ring_band(r)]
    parent = list(range(len(nodes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in itertools.combinations(range(len(nodes)), 2):
        (_, li, ri), (_, lj, rj) = nodes[i], nodes[j]
        via = (li in VIA_LAYERS and lj in VIA_LAYERS[li]) or (lj in VIA_LAYERS and li in VIA_LAYERS[lj])
        if ((li == lj and li in METALS) or via) and _overlap(ri, rj, strict=False):
            parent[find(i)] = find(j)
    comps: dict = {}
    for i, (n, _, _) in enumerate(nodes):
        comps.setdefault(find(i), set()).add(n)
    assert all(len(c) == 1 for c in comps.values()), [c for c in comps.values() if len(c) > 1]
    for net in external:
        assert len({find(i) for i, (n, _, _) in enumerate(nodes) if n == net}) == 1, net


# --- D1, D2: channel choice by DP (approved 2026-11-10) -------------------------------------------

def _orientations(v, members):
    return [v] + ([sp.flip_variant(PDK, v, members, "vss")] if v.get("kind") in ("mirror", "single") else [])


@pytest.mark.parametrize("kind, members", [
    ("cc", [_mos(0, 2, "n1", "inm", "tail"), _mos(1, 2, "n2", "inp", "tail")]),
    ("mirror", [_mos(4, 4, "tail", "bias", "vss", W=2.125, L=0.525), _mos(6, 12, "out", "bias", "vss", W=2.125, L=0.525),
                _mos(7, 4, "bias", "bias", "vss", W=2.125, L=0.525)]),
    ("mirror", [_mos(0, 2, "out", "bias", "vss"), _mos(1, 2, "bias", "bias", "vss")]),
    ("mirror", [_mos(0, 4, "out", "bias", "vss"), _mos(1, 4, "bias", "bias", "vss")]),
])
def test_d1_dp_equals_brute_force(kind, members):
    # [USER 2026-11-10] the DP channel choice reaches the smallest routed block area of all combinations;
    # oracle = brute force over every combination in this test
    by_id = {m["block_id"]: m for m in members}
    ru = br._rules(_pdk())
    external = {n for m in members for t, n in m["terminals"].items() if t != "bulk" and n != "vss"}
    checked = 0
    for v0 in sp.structure_variants(PDK, members, kind, "vss", AR):
        for v in _orientations(v0, members):
            ctx = br._plan_ctx(v, br._rows(_pdk(), v, by_id, "vss"), "vss", [], external, ru)
            areas = [res[0][0] for ch in itertools.product(*ctx["options"]) if (res := br._evaluate(ctx, ch))]
            choice = br._dp_choice(ctx)
            if not areas:
                assert choice is None
                continue
            assert choice is not None
            assert br._evaluate(ctx, choice)[0][0] == pytest.approx(min(areas), abs=1e-6)
            checked += 1
    assert checked


def test_d2_big_mirror_routes_both_orientations():
    # [USER 2026-11-10] a mirror with more S/D choices than MAX_SIDE_COMBOS (sky01 [3,7,8,12]-like: two outputs,
    # a tail and a diode on one bias, sources on the rail) routes in both row orientations (gates in / gates out)
    # and every routed block passes the routed-block checks
    members = [_mos(3, 12, "outm", "vb", "vss"), _mos(7, 12, "outp", "vb", "vss"),
               _mos(8, 4, "tail", "vb", "vss"), _mos(12, 4, "vb", "vb", "vss")]
    external = {"outm", "outp", "tail", "vb"}
    by_id = {m["block_id"]: m for m in members}
    ru = br._rules(_pdk())
    big = 0
    for v0 in sp.structure_variants(PDK, members, "mirror", "vss", AR):
        ctx = br._plan_ctx(v0, br._rows(_pdk(), v0, by_id, "vss"), "vss", [], external, ru)
        if math.prod(len(o) for o in ctx["options"]) <= br.MAX_SIDE_COMBOS:
            continue
        big += 1
        for v in _orientations(v0, members):
            r = br._route_one(_pdk(), v, members, "vss", external, ru)
            assert r is not None, v["orient"]
            r["routing"]["power_pins"] = br._power_pins(r, "vss")
            _check_routed(r, members, "vss", external)
    assert big


# --- R1: same-net spacing (approved 2026-11-10) ----------------------------------------------

def test_r1_same_net_met2_and_via2_spacing():
    # [USER 2026-11-10] sky01 LS run, B10003 (5x14 [3,7,8,12] mirror): two outm stubs from the rows below and
    # above landed 0.285 apart -> met2 gap 0.005 (KLayout m2.2) and via2 cuts 0.085 apart (via2.2).
    # [DRC] m2.2 0.14: two met2 shapes of one net either touch or keep 0.14; via2.2 0.20 between cuts.
    members = [_mos(3, 12, "outm", "vb", "vss"), _mos(7, 12, "outp", "vb", "vss"),
               _mos(8, 4, "tail", "vb", "vss"), _mos(12, 4, "vb", "vb", "vss")]
    external = {"outm", "outp", "tail", "vb"}
    ru = br._rules(_pdk())
    routed = 0
    for v0 in sp.structure_variants(PDK, members, "mirror", "vss", AR):
        for v in _orientations(v0, members):
            r = br._route_one(_pdk(), v, members, "vss", external, ru)
            if r is None:
                continue
            routed += 1
            shapes = r["routing"]["shapes"] + r["routing"]["pins"]
            m2 = [(s["net"], tuple(s["rect"])) for s in shapes if s["layer"] == "met2"]
            for (na, ra), (nb, rb) in itertools.combinations(m2, 2):
                if na == nb:
                    d = _dist(ra, rb)
                    assert d < TOL or d >= 0.14 - TOL, ("met2 same-net gap", na, ra, rb, d, v["orient"])
            cuts = [tuple(s["rect"]) for s in shapes if s["layer"] == "via2"]
            for ra, rb in itertools.combinations(cuts, 2):
                assert _dist(ra, rb) >= 0.20 - TOL, ("via2 spacing", ra, rb, v["orient"])
    assert routed
