"""
pcell.pin_rects — pin rectangles of one PCell copy from pdk.json "pins" (P1..P3), proposed 2026-11-08.

pin_rects(pdk, model, pcell_params, group) -> [(x0, y0, x1, y1)] in the PCell frame (same frame as
footprint x0/y0), one per pin shape in `order`; size = max(linear size, <size>_min); every edge
snapped INWARD to pdk["grid"], so the rect is on grid and inside the real metal.

Sources of expected values:
  [PROBE] container probe 2026-11-08 (klayout, sky130 PCells): nfet w=2 l=0.5 nf=2 met1 S/D strips
          (0.035,0.135,0.265,1.865) (0.935,0.135,1.165,1.865) (1.835,0.135,2.065,1.865), gate pads
          (0.365,2.25,0.735,2.48) (1.365,2.25,1.735,2.48); res_high_po_0p69 len=3 met1 end pads
          (-0.295,-3.63,0.295,-1.525) (-0.295,1.525,0.295,3.63)
  [DENSE] dense w sweep (0.42..8, 0.005): S/D strip length >= w - 0.42, centred at w/2
  [HAND]  hand calculation shown in the comment
"""
import pytest

import pcell

PDK = pcell.load_pdk("sky130")
NFET, RES = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__res_high_po_0p69"
GRID = 0.005
TOL = 1e-9


def _on_grid(v):
    return abs(v / GRID - round(v / GRID)) < 1e-6


def _inside(r, outer):
    return r[0] >= outer[0] - TOL and r[1] >= outer[1] - TOL and r[2] <= outer[2] + TOL and r[3] <= outer[3] + TOL


def test_p1_nfet_pins_inside_probe_metal():
    # [PROBE] nfet w=2 l=0.5 nf=2: 3 S/D strips, 2 gate pads; every rect on grid and inside the real metal
    p = {"w": 2.0, "l": 0.5, "nf": 2}
    probe_sd = [(0.035, 0.135, 0.265, 1.865), (0.935, 0.135, 1.165, 1.865), (1.835, 0.135, 2.065, 1.865)]
    probe_g = [(0.365, 2.25, 0.735, 2.48), (1.365, 2.25, 1.735, 2.48)]
    sd, gate = pcell.pin_rects(PDK, NFET, p, "sd"), pcell.pin_rects(PDK, NFET, p, "gate")
    assert len(sd) == 3 and len(gate) == 2
    for r, real in zip(sd + gate, probe_sd + probe_g):
        assert all(_on_grid(v) for v in r)
        assert _inside(r, real)
    # S/D x is an exact fit -> identical to the probe; [DENSE] length >= w - 0.42 = 1.58, minus one grid step per end
    for r, real in zip(sd, probe_sd):
        assert (r[0], r[2]) == pytest.approx((real[0], real[2]), abs=TOL)
        assert r[3] - r[1] >= 2.0 - 0.42 - 2 * GRID - TOL
    # gate pad y is exact (h = 0.23, cy = w + 0.365): identical to the probe
    for r, real in zip(gate, probe_g):
        assert (r[1], r[3]) == pytest.approx((real[1], real[3]), abs=TOL)


def test_p2_half_grid_centres_snapped_inward():
    # [HAND] w=0.845, l=0.155, nf=1: S/D cy = w/2 = 0.4225 and gate cx = 0.3 + l/2 = 0.3775 are half-grid.
    # S/D k=0: x = 0.15 -+ 0.115 = [0.035, 0.265]; length = max(0.999952*0.845 - 0.424966, 0.29) = 0.419993
    #   -> y = 0.4225 -+ 0.2099965 = [0.2125035, 0.6324965] -> inward [0.215, 0.630]
    # gate k=0: y = 0.365 + 0.845 -+ 0.115 = [1.095, 1.325]
    p = {"w": 0.845, "l": 0.155, "nf": 1}
    sd, gate = pcell.pin_rects(PDK, NFET, p, "sd"), pcell.pin_rects(PDK, NFET, p, "gate")
    for r in sd + gate:
        assert all(_on_grid(v) for v in r)
    assert sd[0] == pytest.approx((0.035, 0.215, 0.265, 0.630), abs=TOL)
    assert (gate[0][1], gate[0][3]) == pytest.approx((1.095, 1.325), abs=TOL)
    # inward: the snapped pad lies within the unsnapped one (cx 0.3775, width >= 0.365)
    assert gate[0][0] >= 0.3775 - 0.365 / 2 - TOL and gate[0][2] <= 0.3775 + 0.365 / 2 + TOL


def test_p3_resistor_end_pads():
    # [PROBE] res_high_po_0p69 len=3: n1 = bottom pad (k=0), n2 = top pad (k=1); exact fit, on grid
    ends = pcell.pin_rects(PDK, RES, {"len": 3.0}, "ends")
    assert ends[0] == pytest.approx((-0.295, -3.63, 0.295, -1.525), abs=TOL)
    assert ends[1] == pytest.approx((-0.295, 1.525, 0.295, 3.63), abs=TOL)
