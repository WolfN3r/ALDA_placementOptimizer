"""
lib/structure_placer (matched structures for 012) — tests S1..S11, approved 2026-11-04.

Sources of expected values:
  [PDK]  WorkDir/pdk/sky130/pdk.json (DRC-characterised): nfet x gap 0.02 (also with a
         met2 via on every S/D contact), pfet x gap -0.34, res x gap -0.71, res y gap 0.84;
         ring clearance nfet l/r 0.145 bottom 0.07 top 0.145, pfet -0.035 / -0.11 / -0.08,
         res 0.155 / 0.415 / 0.415 (top/bottom swap for R180); grw 0.23; ring PCell bbox =
         opening + 2*grw + 0.25; n-well fill sticks out 0.18 - 0.125 = 0.055 per side;
         poly insets nfet bottom 0 / top 0.01, pfet 0.18 / 0.19; met2 track 0.14 + 0.14 space;
         layout_policy row_gap_poly_min 1.0, row_gap_round 0.1
  [GDS]  unit sizes measured in 05_miller_ota miller_ota.gds: M1 1.435 x 2.91,
         M8 1.375 x 2.865, M3 2.07 x 2.71, M6 4.23 x 3.955, R1A 1.27 x 5.87
  [05]   05_miller_ota hand placement (rows extracted from the GDS)
  [HAND] hand calculation shown in the comment
Ring adds per axis: nfet 2*0.145 + 2*0.23 + 0.25 = 1.00 (x), 2*0.07 + 0.46 + 0.25 = 0.85 (y, R0 bottom
row + R180 top row) or 0.07 + 0.145 + 0.71 = 0.925 (one R0 row).
"""
from pathlib import Path
import importlib.util

import pytest

import pcell
import structure_placer as sp

_SCRIPTS = Path(__file__).resolve().parents[2]
_DATA = Path(__file__).resolve().parent / "data"
PDK = pcell.load_pdk("sky130")
NFET, PFET = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"
RES = "sky130_fd_pr__res_xhigh_po_0p35"
AR = (0.25, 4.0)
TOL = 1e-6


def _mos(bid, copies, d, g, s, b="vss", model=NFET, W=2.17, L=0.585, nf=1):
    return {"block_id": bid, "copies": copies, "model": model,
            "pcell": pcell.pcell_params(PDK, model, {"W": W, "L": L, "nf": nf}),
            "terminals": {"drain": d, "gate": g, "source": s, "bulk": b}}


def _res(bid, n1, n2):
    return {"block_id": bid, "copies": 1, "model": RES,
            "pcell": pcell.pcell_params(PDK, RES, {"L": 1.27}),
            "terminals": {"n1": n1, "n2": n2, "substrate": "vss"}}


def _dp(copies):
    # [NET] miller_ota_sized: XM1 n1 inm tail VSS, XM2 n2 inp tail VSS, W 2.17 L 0.585 nf 1
    return [_mos(0, copies, "n1", "inm", "tail"), _mos(1, copies, "n2", "inp", "tail")]


def _bias_mirror():
    # [NET] XM5 tail bias VSS m=4, XM7 OUT bias VSS m=12, XM8 bias bias VSS m=4, W 2.125 L 0.525
    return [_mos(4, 4, "tail", "bias", "vss", W=2.125, L=0.525),
            _mos(6, 12, "out", "bias", "vss", W=2.125, L=0.525),
            _mos(7, 4, "bias", "bias", "vss", W=2.125, L=0.525)]


def _shape(variants, rows, cols):
    return next((v for v in variants if v["rows"] == rows and v["cols"] == cols), None)


def _size(v):
    return v["width_um"], v["height_um"]


# ── S1: DP 2+2, two rows ──────────────────────────────────────────────────────

def test_s1_dp_2x2_cross_quad():
    vs = sp.structure_variants(PDK, _dp(2), "cc", "vss", AR)
    v = _shape(vs, 2, 2)
    # [05] cross-quad dABd (R0, bottom) / dBAd (R180, top), or its mirror image
    assert tuple(reversed(v["pattern"])) in {("dABd", "dBAd"), ("dBAd", "dABd")}
    assert v["orient"] == ["R0", "R180"]                      # gates face the channel (user: DP inward)
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)      # [HAND] A (1,0),(2,1) B (2,0),(1,1): same centroid
    assert v["score"]["orient"] == pytest.approx(0, abs=TOL)   # one R0 + one R180 copy each
    # [HAND] A|B can face source|source (tail) in both rows; d|A and B|d never match (no VSS side)
    assert v["facing_mismatches"] == 4
    for row in range(2):
        a, b = [s for s in v["slots"] if s["row"] == row and s["block_id"] is not None]
        left, right = sorted((a, b), key=lambda s: s["x"])
        assert left["right"] == "source" and right["left"] == "source"
    # [HAND] poly gap max(1.0, 2*0.28 + 0.14 = 0.70) = 1.0 -> bbox gap 1.0 - 0.01 - 0.01 = 0.98
    # width 4*1.435 + 3*0.02 = 5.80 + 1.00; height 2*2.91 + 0.98 = 6.80 + 0.85
    assert _size(v) == (pytest.approx(6.80), pytest.approx(7.65))
    assert vs[0] is v and v["is_used"]                         # user: DP prefers common centroid


# ── S2: DP 2+2, one row ───────────────────────────────────────────────────────

def test_s2_dp_2x2_one_row():
    v = _shape(sp.structure_variants(PDK, _dp(2), "cc", "vss", AR), 1, 4)
    assert v["pattern"] in (["dABBAd"], ["dBAABd"])           # [HAND] only ABBA/BAAB have lin = 0
    assert v["facing_mismatches"] == 2                         # [HAND] only the two dummy sides
    # [HAND] 6*1.435 + 5*0.02 = 8.71 + 1.00; 2.91 + 0.925 = 3.835
    assert _size(v) == (pytest.approx(9.71), pytest.approx(3.835))


# ── S3: DP 1+1 ────────────────────────────────────────────────────────────────

def test_s3_dp_1x1():
    vs = sp.structure_variants(PDK, _dp(1), "cc", "vss", AR)
    assert vs[0]["pattern"] in (["dABd"], ["dBAd"])
    assert vs[0]["matching_type"] == "interdigitated"
    # [HAND] 4*1.435 + 3*0.02 = 5.80 + 1.00; 3.835
    assert _size(vs[0]) == (pytest.approx(6.80), pytest.approx(3.835))


# ── S4: load mirror 2+2, one row (pfet) ───────────────────────────────────────

def test_s4_pmos_load_mirror_one_row():
    # [NET] XM3 n1 n1 VDD VDD, XM4 n2 n1 VDD VDD, W 1.61 L 0.86 nf 1 m=2
    ms = [_mos(2, 2, "n1", "n1", "vdd", "vdd", PFET, 1.61, 0.86),
          _mos(3, 2, "n2", "n1", "vdd", "vdd", PFET, 1.61, 0.86)]
    v = _shape(sp.structure_variants(PDK, ms, "mirror", "vdd", AR), 1, 4)
    assert v["pattern"] in (["dABBAd"], ["dBAABd"])
    assert v["guard_ring"]["ring"] == "n_ring"
    # [HAND] 6*2.07 - 5*0.34 = 10.72; + 2*(-0.035) + 0.46 + 0.25 + 0.11 = 11.47
    #        2.71 - 0.11 - 0.08 + 0.46 + 0.25 + 0.11 = 3.34
    assert _size(v) == (pytest.approx(11.47), pytest.approx(3.34))


# ── S5: bias mirror 4:12:4 ────────────────────────────────────────────────────

def test_s5_bias_mirror_shapes():
    vs = sp.structure_variants(PDK, _bias_mirror(), "mirror", "vss", AR)
    for v in vs:
        counts = {}
        for s in v["slots"]:
            if s["block_id"] is not None:
                counts[s["block_id"]] = counts.get(s["block_id"], 0) + 1
        assert counts == {4: 4, 6: 12, 7: 4}
    assert _shape(vs, 1, 20) is None                           # [HAND] aspect 31.42 / 3.54 = 8.9 > 4
    for rows, cols in ((2, 10), (4, 5)):
        v = _shape(vs, rows, cols)
        # [HAND] point-symmetric patterns exist (row r = row R-1-r reversed, e.g. 4x5
        # BCBAB / BABCB / BCBAB / BABCB): every centroid at the centre, half R0 half R180
        assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
        assert v["score"]["orient"] == pytest.approx(0, abs=TOL)
    v = _shape(vs, 2, 10)
    # [HAND] gates inward: 1 gate net -> poly 1.0 -> bbox gap 0.98; S/D inward: 4 nets ->
    # 4*0.28 + 0.14 = 1.26 -> 1.3. Smaller one kept: gates inward.
    # 12*1.375 + 11*0.02 = 16.72 + 1.00; 2*2.865 + 0.98 = 6.71 + 0.85    (05: 17.98 x 8.36)
    assert v["orient"] == ["R0", "R180"]
    assert _size(v) == (pytest.approx(17.72), pytest.approx(7.56))


# ── S6: row gap rule ──────────────────────────────────────────────────────────

def test_s6_channel_gap():
    # [HAND] see module docstring; (lower row, upper row) orientation
    assert sp.channel_gap(PDK, NFET, 2, "R0", "R180") == pytest.approx(0.98)   # DP gates
    assert sp.channel_gap(PDK, NFET, 4, "R180", "R0") == pytest.approx(1.30)   # mirror S/D
    assert sp.channel_gap(PDK, PFET, 1, "R0", "R180") == pytest.approx(0.62)   # 1.0 - 0.19 - 0.19


# ── S7: best S/D flips on a fixed row ─────────────────────────────────────────

def test_s7_row_flips_05_bias_row():
    # [05] top bias row d 777 8 55 8 777 d drawn with 5 mismatched facings.
    # [HAND] optimum 2: each M8 drain (bias) has no M8 neighbour; everything else pairs up
    m5 = {"source": "vss", "drain": "tail", "nf": 1}
    m7 = {"source": "vss", "drain": "out", "nf": 1}
    m8 = {"source": "vss", "drain": "bias", "nf": 1}
    d = {"dummy": "vss"}
    mism, states = sp.row_facing([d, m7, m7, m7, m8, m5, m5, m8, m7, m7, m7, d])
    assert mism == 2
    assert len(states) == 12


# ── S8: sensitive single transistor with one-finger dummies ───────────────────

def test_s8_single_m6_with_dummies():
    # [NET] XM6 OUT n2 VDD VDD pfet W 11.42 L 0.38 nf 4; dummy = one finger (w 2.855, l 0.38)
    # [PDK] pfet w = 0.71 + 0.5 nf + nf l -> dummy 0.71 + 0.5 + 0.38 = 1.59, h = 1.10 + 2.855 = 3.955
    m6 = _mos(5, 1, "out", "n2", "vdd", "vdd", PFET, 11.42, 0.38, 4)
    vs = sp.structure_variants(PDK, [m6], "single", "vdd", AR)
    assert vs[0]["pattern"] == ["dAd"]
    assert vs[0]["facing_mismatches"] == 0                     # nf even: both ends VDD, like the dummies
    # [HAND] 1.59 + 4.23 + 1.59 - 2*0.34 = 6.73; - 0.07 + 0.46 + 0.25 + 0.11 = 7.48
    #        3.955 - 0.11 - 0.08 + 0.46 + 0.25 + 0.11 = 4.585
    assert _size(vs[0]) == (pytest.approx(7.48), pytest.approx(4.585))


# ── S9: resistor chain ────────────────────────────────────────────────────────

def test_s9_resistor_chain():
    # [NET] R1A n2-nr1, R1B nr2-nr1, R1C nr3-nr2, R1D nz-nr3, L 1.27, series order A..D
    rs = [_res(9, "n2", "nr1"), _res(10, "nr2", "nr1"), _res(11, "nr3", "nr2"), _res(12, "nz", "nr3")]
    vs = sp.structure_variants(PDK, rs, "chain", "vss", AR)
    assert vs[0]["pattern"] == ["dABCDd"]
    # [HAND] 6*1.27 - 5*0.71 = 4.07 + 2*0.155 + 0.46 + 0.25 = 5.09
    #        5.87 + 2*0.415 + 0.46 + 0.25 = 7.41            (05: 5.61 x 6.65 with magic poly.9 errors)
    assert _size(vs[0]) == (pytest.approx(5.09), pytest.approx(7.41))


# ── S10 / S11: 012 end to end on the copy of the 05 netlist ───────────────────

def _run_miller():
    spec = importlib.util.spec_from_file_location("g012", _SCRIPTS / "012_pdkDeviceGenerator.py")
    g012 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g012)
    return g012.run(str(_DATA / "miller_ota_sized.spice"), 1, pdk_name="sky130")


def test_s10_netlist_dummies_removed():
    out = _run_miller()
    # [NET] MD1, MD3, MD8, RD1, RD2 have every terminal on one supply
    assert sorted(d["inst"] for d in out["netlist_dummies"]) == ["xmd1", "xmd3", "xmd8", "xrd1", "xrd2"]
    assert len(out["blocks"]) == 13                            # [NET] 18 devices - 5 dummies


def test_s11_miller_structures():
    out = _run_miller()
    inst = {b["block_id"]: b["inst"] for b in out["blocks"]}
    by_members = {tuple(sorted(inst[b] for b in g["block_ids"])): g for g in out["groups"]}
    expected = {("xm1", "xm2"): "diff_pair", ("xm3", "xm4"): "current_mirror",
                ("xm5", "xm7", "xm8"): "current_mirror", ("xm6",): "single_sensitive",
                ("xr1a", "xr1b", "xr1c", "xr1d"): "res_chain"}
    for members, topo in expected.items():
        g = by_members[members]
        assert g["topology_type"] == topo
        assert g["matching_variants"]
        assert [v["is_used"] for v in g["matching_variants"]] == \
            [True] + [False] * (len(g["matching_variants"]) - 1)
