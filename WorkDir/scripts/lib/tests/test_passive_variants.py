"""
012 passive variants: resistors split into s series segments (one row, row-end
dummies, ring), MIM caps reshaped at constant area — tests P1..P8, approved 2026-11-08.

Sources of expected values:
  [MODEL] sky130A spice models (container): R = rcon + r_per_um * L;
          res_high_po_0p69 rcon 389.90, r_per_um 491.36 -> rcon / r_per_um = 0.793512 µm;
          res_xhigh_po_0p35 rcon -46.62/0.35² + 331.73/0.35 + 20.576 = 587.8046,
          r_per_um 2000 / 0.35 = 5714.2857 -> 0.102866 µm
  [PDK]   pdk.json: res unit 1.27 x (4.72 + len), PCell len = L - 0.12 on 0.01, segment L >= 0.62 (len 0.5);
          x gap 0p69 -0.37, 0p35 -0.71; res ring adds 2*0.155 + 0.46 + 0.25 = 1.02 (x, 0p35),
          2*0.415 + 0.71 = 1.54 (y); MIM footprint (w + 1.86) x (l + 0.40), w/l on 0.005
  [NET]   tests/data/ota1.spice + ota1_params.json: xr25 res_high_po_0p69 L = 2.9972
  [HAND]  hand calculation shown in the comment
"""
import importlib.util
from pathlib import Path

import pytest

import pcell
import structure_placer as sp

_SCRIPTS = Path(__file__).resolve().parents[2]
_DATA = Path(__file__).resolve().parent / "data"
_spec = importlib.util.spec_from_file_location("g012", _SCRIPTS / "012_pdkDeviceGenerator.py")
g012 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g012)

PDK = pcell.load_pdk("sky130")
R069, R035 = "sky130_fd_pr__res_high_po_0p69", "sky130_fd_pr__res_xhigh_po_0p35"
CAP = "sky130_fd_pr__cap_mim_m3_1"
AR = (0.25, 4.0)
TOL = 1e-6


def _res(bid, n1, n2, copies, L=1.27):
    return {"block_id": bid, "copies": copies, "model": R035,
            "pcell": pcell.pcell_params(PDK, R035, {"L": L}),
            "terminals": {"n1": n1, "n2": n2, "substrate": "vss"}}


# ── P1 / P2: segment length with the end-resistance correction ────────────────

def test_p1_segment_len_high_po_short():
    # [MODEL]+[HAND] L 2.37, s 2: (2.37 - 0.793512) / 2 = 0.788244 -> len 0.668244 -> 0.67
    # R check: 2*389.90 + 491.36*2*0.79 = 1556.2 vs 389.90 + 491.36*2.37 = 1554.4 (+0.1 %)
    assert g012.segment_pcell(PDK, R069, 2.37, 2)["len"] == pytest.approx(0.67, abs=TOL)
    assert g012.segment_pcell(PDK, R069, 2.37, 1)["len"] == pytest.approx(2.25, abs=TOL)
    # [HAND] s 3: (2.37 - 2*0.793512) / 3 = 0.260992 < 0.62
    assert g012.segment_pcell(PDK, R069, 2.37, 3) is None


def test_p2_segment_len_xhigh_long():
    # [MODEL]+[HAND] L 50, s 2: (50 - 0.102866) / 2 = 24.948567 -> len 24.828567 -> 24.83
    assert g012.segment_pcell(PDK, R035, 50.0, 2)["len"] == pytest.approx(24.83, abs=TOL)


# ── P3: how many segments ─────────────────────────────────────────────────────

def test_p3_segment_counts_stop_at_square():
    # [PDK]+[HAND] high_po_0p69, L 50, one row of s segments: W = 1.27 s - 0.37 (s - 1)
    #   s 9:  (50 - 8*0.793512) / 9 = 4.850204 -> len 4.73, H 9.45, W 8.47  (W < H)
    #   s 10: (50 - 9*0.793512) / 10 = 4.285839 -> len 4.17, H 8.89, W 9.37 (W >= H, last)
    assert g012.segment_counts(PDK, R069, 50.0, 1) == list(range(1, 11))
    # [NET]+[HAND] xr25 L 2.9972: s 2 len 0.98 (W 2.17 < H 5.70); s 3 L 0.47 < 0.62 -> stop
    assert g012.segment_counts(PDK, R069, 2.9972030887418635, 1) == [1, 2]


# ── P4 / P5: one row, series order, dummies at both ends ──────────────────────

def test_p4_single_resistor_three_segments():
    vs = sp.structure_variants(PDK, [_res(7, "a", "b", 3)], "chain", "vss", AR)
    assert len(vs) == 1 and vs[0]["rows"] == 1
    # user 2026-11-08: a lone resistor has no partner to match -> no row-end dummies
    assert vs[0]["pattern"] == ["AAA"]                         # A1 A2 A3
    assert [s["block_id"] for s in vs[0]["slots"]] == [7, 7, 7]
    assert vs[0]["dummies"]["count"] == 0
    # [PDK]+[HAND] 3*1.27 - 2*0.71 = 2.39 + 1.02 = 3.41; 1.27 + 4.72 - 0.12 = 5.87 + 1.54 = 7.41
    assert (vs[0]["width_um"], vs[0]["height_um"]) == (pytest.approx(3.41), pytest.approx(7.41))


def test_p5_chain_segments_in_series_order():
    rs = [_res(3, "a", "m", 2), _res(4, "m", "b", 2)]
    vs = sp.structure_variants(PDK, rs, "chain", "vss", AR)
    assert [v["rows"] for v in vs] == [1]                      # user: single-row generator
    assert vs[0]["pattern"] == ["dAABBd"]                      # D A1 A2 B1 B2 D


# ── P6: cap shapes at constant area ───────────────────────────────────────────

def test_p6_cap_shapes():
    shapes = g012.cap_shapes(PDK, CAP, 19.095, 19.095)
    assert len(shapes) == 7                                    # ratios 1/3 1/2 2/3 1 3/2 2 3
    by_ratio = {round(p["w"] / p["l"], 1): p for p in shapes}
    # [HAND] A = 364.619; r 3: w sqrt(3A) = 33.0735 -> 33.075, l sqrt(A/3) = 11.0245 -> 11.025
    assert (by_ratio[3.0]["w"], by_ratio[3.0]["l"]) == (pytest.approx(33.075), pytest.approx(11.025))
    assert pcell.footprint(PDK, CAP, by_ratio[3.0]) == (pytest.approx(34.935), pytest.approx(11.425))
    assert (by_ratio[1.0]["w"], by_ratio[1.0]["l"]) == (pytest.approx(19.095), pytest.approx(19.095))
    for p in shapes:                                           # area kept within the 5 nm snap
        assert p["w"] * p["l"] == pytest.approx(364.619025, rel=1e-3)


# ── P7 / P8: 012 end to end (ota1) ────────────────────────────────────────────

def _ota1():
    return g012.run(str(_DATA / "ota1.spice"), 1, pdk_name="sky130",
                    params_paths=[str(_DATA / "ota1_params.json")])


def test_p7_ota1_resistor_groups():
    out = _ota1()
    bid = next(b["block_id"] for b in out["blocks"] if b["inst"] == "xr25")
    groups = [g for g in out["groups"] if bid in g["block_ids"]]
    assert len(groups) == 1 and groups[0]["topology_type"] == "res_chain"
    vs = groups[0]["matching_variants"]
    # [HAND] P3: s in {1, 2}, each at 0° and 90°
    assert sorted((v["segments"], v["rotation_deg"]) for v in vs) == [(1, 0), (1, 90), (2, 0), (2, 90)]
    assert [v["is_used"] for v in vs].count(True) == 1
    for v in vs:
        rot = next(r for r in vs if r["segments"] == v["segments"] and r["rotation_deg"] != v["rotation_deg"])
        assert (v["width_um"], v["height_um"]) == (rot["height_um"], rot["width_um"])


def test_p8_ota1_cap_variants():
    out = _ota1()
    xc1 = next(b for b in out["blocks"] if b["inst"] == "xc1")
    vs = xc1["variants"]
    # [HAND] 7 shapes, none with a square footprint (w + 1.86 vs l + 0.40), each also at 90°
    assert len(vs) == 14 and [v["is_used"] for v in vs].count(True) == 1
    w, l = xc1["parameters"]["pcell"]["w"], xc1["parameters"]["pcell"]["l"]
    for v in vs:
        assert v["unit_pcell"]["w"] * v["unit_pcell"]["l"] == pytest.approx(w * l, rel=1e-3)
