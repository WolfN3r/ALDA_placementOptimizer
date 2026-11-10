"""
Block pin access (lib/pin_access, lib/block_router) — tests H1, H2, A1, A2, T1, approved 2026-11-09.

API under test:
  pin_access.net_hpwl(pins) -> (hpwl, points)
        pins: one list of access segments (x0, y0, x1, y1) per pin, absolute; a point is a zero-length
        segment. Each pin takes the point of its segments nearest to the other pins; points = the chosen
        (x, y) per pin, in input order.
  block_router.route_structure(...)["routing"]["access"]: [{"net", "side", "seg"}]
        every place a net may enter the routed block, seg on the block edge (variant frame)
  block_router.apply_access(v, chosen) -> routed variant with pins only at the chosen access points and
        the unused trunk extensions cut; chosen: [{"net", "side", "point": [x, y]}]

Sources of expected values:
  [USER]  decisions 2026-11-09: access anywhere along a trunk in an outer channel (M2 straight through the
          ring), inner trunks only at their ends (or through their side-channel track); DP only at its edge
          pins (inputs left, outputs and tail right), nothing enters the DP from top / bottom; unused trunk
          ends cut after pin assignment
  [HAND]  hand calculation shown in the comment
"""
import pytest

import block_router as br
import pin_access
import structure_placer as sp
from test_block_router import AR, GRID, PDK, TOL, _abs_pins, _check_routed, _dist, _inner_active, _mos, _on_grid, _pdk

M2_SPACE = 0.14        # [DRC] m2.2
DROP_W = 0.28          # [HAND] M2 stub width = via2 M2 landing 0.20 + 2 * 0.04
V2_M2_H = 0.37         # [HAND] via2 M2 landing along the stub: 0.20 + 2 * 0.085


# --- H1, H2: nearest access point in the HPWL -------------------------------------------------

def test_h1_nearest_access_point_of_block():
    # [HAND] block 1 offers net a at (0, 5) and (10, 5), block 2 sits at x = 20 with a at (20, 5):
    # block 1's right access is nearer -> HPWL = 20 - 10 = 10
    hpwl, points = pin_access.net_hpwl([[(0, 5, 0, 5), (10, 5, 10, 5)], [(20, 5, 20, 5)]])
    assert hpwl == pytest.approx(10.0, abs=1e-9)
    assert points[0] == pytest.approx((10.0, 5.0), abs=1e-9)


def test_h2_nearest_point_on_access_stretch():
    # [HAND] access stretch x in [2, 8] at y = 10, other pin at (12, 20): nearest point (8, 10),
    # HPWL = (12 - 8) + (20 - 10) = 14
    hpwl, points = pin_access.net_hpwl([[(2, 10, 8, 10)], [(12, 20, 12, 20)]])
    assert hpwl == pytest.approx(14.0, abs=1e-9)
    assert points[0] == pytest.approx((8.0, 10.0), abs=1e-9)


# --- A1, A2: access list of routed blocks ----------------------------------------------------------

def test_a1_dp_access_only_on_rule_edges():
    # [USER] DP: inputs only on the left edge, outputs and tail only on the right edge, no top / bottom
    members = [_mos(0, 2, "n1", "inm", "tail"), _mos(1, 2, "n2", "inp", "tail")]
    v = sp.structure_variants(PDK, members, "cc", "vss", AR)[0]
    external = {"n1", "n2", "inm", "inp", "tail"}
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    W, H = r["width_um"], r["height_um"]
    access = r["routing"]["access"]
    assert {a["net"] for a in access} == external
    for a in access:
        x0, y0, x1, y1 = a["seg"]
        edge = 0.0 if a["net"] in ("inm", "inp") else W
        assert a["side"] == ("left" if a["net"] in ("inm", "inp") else "right"), a
        assert x0 == pytest.approx(edge, abs=TOL) and x1 == pytest.approx(edge, abs=TOL), a
        assert -TOL <= y0 <= y1 <= H + TOL, a


def test_a2_outer_trunk_reachable_along_its_length():
    # [USER] one-row mirror: every external net whose trunk lies in an outer channel (below / above the
    # row) may be entered from that block edge anywhere along the stretch; an M2 drop from any point of the
    # stretch to its trunk crosses no active area and keeps M2 space to every other net's M2
    members = [_mos(0, 2, "out", "bias", "vss"), _mos(1, 2, "bias", "bias", "vss")]
    v = next(c for c in sp.structure_variants(PDK, members, "mirror", "vss", AR) if c["rows"] == 1)
    external = {"out", "bias"}
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    by_id = {m["block_id"]: m for m in members}
    H = r["height_um"]
    shapes = r["routing"]["shapes"]
    bottom = min(s["y"] - s["h"] / 2 for s in r["slots"])
    top = max(s["y"] + s["h"] / 2 for s in r["slots"])
    actives = [a for sl in r["slots"] if (a := _inner_active(_abs_pins(r, sl, by_id, "vss")))]
    outer = [(s["net"], s["rect"], "bottom" if s["rect"][3] <= bottom + TOL else "top") for s in shapes
             if s["net"] in external and s["layer"] == "met3" and s["rect"][2] - s["rect"][0] > 0.5
             and (s["rect"][3] <= bottom + TOL or s["rect"][1] >= top - TOL)]
    assert outer, "no external trunk in an outer channel"
    for net, trunk, side in outer:
        ty = (trunk[1] + trunk[3]) / 2
        segs = [a["seg"] for a in r["routing"]["access"] if a["net"] == net and a["side"] == side]
        assert segs, (net, side)
        others = [s["rect"] for s in shapes if s["layer"] == "met2" and s["net"] != net]
        for x0, y0, x1, y1 in segs:
            edge = 0.0 if side == "bottom" else H
            assert y0 == pytest.approx(edge, abs=TOL) and y1 == pytest.approx(edge, abs=TOL)
            assert trunk[0] - TOL <= x0 <= x1 <= trunk[2] + TOL, (net, (x0, x1), trunk)
            n = int(round((x1 - x0) / GRID))
            for k in range(n + 1):
                x = x0 + k * GRID
                drop = (x - DROP_W / 2, 0.0, x + DROP_W / 2, ty + V2_M2_H / 2) if side == "bottom" else \
                       (x - DROP_W / 2, ty - V2_M2_H / 2, x + DROP_W / 2, H)
                assert _on_grid((round(x, 9),)), x
                for o in others:
                    assert _dist(drop, o) >= M2_SPACE - TOL, (net, x, o)
                for a in actives:
                    assert not (drop[0] < a[2] - TOL and a[0] < drop[2] - TOL and drop[1] < a[3] - TOL
                                and a[1] < drop[3] - TOL), (net, x, a)


# --- T1: trimming after pin assignment -------------------------------------------------------------

def test_t1_unused_trunk_end_cut():
    # [USER] bias mirror (S5 input of test_b8): pins on both edges before assignment; only the left end
    # of each external net is chosen -> nothing of the net reaches past the ring opening on the right, the
    # trunk still joins every via2 on its track, and the routed-block checks still pass
    members = [_mos(4, 4, "tail", "bias", "vss", W=2.125, L=0.525),
               _mos(6, 12, "out", "bias", "vss", W=2.125, L=0.525),
               _mos(7, 4, "bias", "bias", "vss", W=2.125, L=0.525)]
    v = sp.structure_variants(PDK, members, "mirror", "vss", AR)[0]
    external = {"tail", "out", "bias"}
    r = br.route_structure(_pdk(), v, members, "vss", external)
    assert r is not None
    W = r["width_um"]
    for net in external:
        assert any(p["net"] == net and abs(p["rect"][2] - W) < TOL for p in r["routing"]["pins"]), net
    chosen = []
    for net in sorted(external):
        a = next(a for a in r["routing"]["access"] if a["net"] == net and a["side"] == "left")
        chosen.append({"net": net, "side": "left", "point": a["seg"][:2]})
    t = br.apply_access(r, chosen)
    _check_routed(t, members, "vss", external)
    x_max = t["guard_ring"]["opening"]["x_max"]
    shapes = t["routing"]["shapes"] + t["routing"]["pins"]
    for net in external:
        assert not any(s["net"] == net and s["layer"] == "met3" and s["rect"][2] > x_max + TOL for s in shapes), net
        assert all(p["side"] == "left" for p in t["routing"]["pins"] if p["net"] == net), net
        for via in (s["rect"] for s in shapes if s["net"] == net and s["layer"] == "via2"):
            cx, cy = (via[0] + via[2]) / 2, (via[1] + via[3]) / 2
            assert any(s["net"] == net and s["layer"] == "met3" and s["rect"][2] - s["rect"][0] > 0.5   # trunk, not landing
                       and s["rect"][0] <= cx <= s["rect"][2] and s["rect"][1] <= cy <= s["rect"][3]
                       for s in shapes), (net, via)
