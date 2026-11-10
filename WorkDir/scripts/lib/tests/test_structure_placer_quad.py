"""
lib/structure_placer — worst-angle quadratic term Q1..Q6 (approved 2026-11-05) and
odd-row labelling Q7 (user request 2026-11-05).

Sources of expected values:
  [HAND]    directional field q·(x cosθ + y sinθ)²; per device pair with A = Δ<x²>, B = Δ<y²>,
            C = Δ<xy>: Δ(θ) = (A+B)/2 + (A-B)/2·cos2θ + C·sin2θ, worst angle
            max|Δ| = |A+B|/2 + hypot((A-B)/2, C); q = GRAD["quad"] = 0.01 µV/µm²
  [SHARMA]  Sharma et al., ICCAD 2021, Fig. 7(b) "Proposed": BDDDDA / CCDDCC / ADDDDB,
            x pitch 1, y pitch K = 2
  [USER]    rows alternate R0/R180, so an odd row count has unequal gaps above and below
            the middle row: such shapes are not labelled common centroid
"""
import pytest

import pcell
import structure_placer as sp

PDK = pcell.load_pdk("sky130")
NFET = "sky130_fd_pr__nfet_01v8"
AR = (0.25, 4.0)


def _means(a, b, c):
    """Two members whose means differ only in <x²> by a, <y²> by b, <xy> by c."""
    return [[0, 0, a, b, c, 0, 0, 0, 0, 0], [0.0] * 10]


def _mos(bid, copies, d, g, s, W=2.17, L=0.585):
    return {"block_id": bid, "copies": copies, "model": NFET,
            "pcell": pcell.pcell_params(PDK, NFET, {"W": W, "L": L, "nf": 1}),
            "terminals": {"drain": d, "gate": g, "source": s, "bulk": "vss"}}


def test_q1_pure_x2():
    # [HAND] A=4, B=0, C=0: 4/2 + hypot(2, 0) = 4 -> 0.04
    assert sp.offset_parts(_means(4, 0, 0))["quad"] == pytest.approx(0.04, abs=1e-9)


def test_q2_saddle():
    # [HAND] A=+1, B=-1, C=0: 0 + hypot(1, 0) = 1 -> 0.01 (θ=0: +1, θ=90°: -1);
    # every other term is 0, so total = quad
    p = sp.offset_parts(_means(1, -1, 0))
    assert p["quad"] == pytest.approx(0.01, abs=1e-9)
    assert p["total"] == pytest.approx(0.01, abs=1e-9)


def test_q3_equal_x2_y2():
    # [HAND] A=B=1, C=0: Δ(θ) = cos²θ + sin²θ = 1 at every angle -> 0.01
    assert sp.offset_parts(_means(1, 1, 0))["quad"] == pytest.approx(0.01, abs=1e-9)


def test_q4_pure_xy():
    # [HAND] A=B=0, C=1: Δ(θ) = sin2θ, max 1 at 45° -> 0.01
    assert sp.offset_parts(_means(0, 0, 1))["quad"] == pytest.approx(0.01, abs=1e-9)


def test_q5_mixed():
    # [HAND] A=3, B=1, C=1: Δ(θ) = 2 + cos2θ + sin2θ, max 2 + √2 = 3.414214 -> 0.03414214
    assert sp.offset_parts(_means(3, 1, 1))["quad"] == pytest.approx(0.0341421356, abs=1e-9)


def test_q6_sharma_fig7b():
    # [SHARMA] [HAND] worst pair A-B: A at (2.5, 2), (-2.5, -2), B at (-2.5, 2), (2.5, -2):
    # A = B = 0, C = 5 - (-5) = 10 -> hypot(0, 10) = 10 -> 0.10
    # (A-D: 3 + hypot(2.2, 5) = 8.46, C-D: 3.2 are lower)
    rows = ["BDDDDA", "CCDDCC", "ADDDDB"]
    pts = {}
    for r, row in enumerate(rows):
        for c, lab in enumerate(row):
            pts.setdefault(lab, []).append((c - 2.5, (1 - r) * 2.0))
    means = []
    for lab in sorted(pts):
        v = [sp._terms(x, y, False) for x, y in pts[lab]]
        means.append([sum(col) / len(v) for col in zip(*v)])
    assert sp.offset_parts(means)["quad"] == pytest.approx(0.10, abs=1e-6)


@pytest.mark.parametrize("members, kind", [
    ([_mos(0, 4, "outp", "inn", "tail"), _mos(1, 4, "outn", "inp", "tail")], "cc"),
    ([_mos(4, 4, "tail", "bias", "vss", 2.125, 0.525), _mos(6, 12, "out", "bias", "vss", 2.125, 0.525),
      _mos(7, 4, "bias", "bias", "vss", 2.125, 0.525)], "mirror"),
])
def test_q7_odd_rows_not_common_centroid(members, kind):
    # [USER] odd row count -> never "common_centroid"; the inputs do produce odd-row shapes
    vs = sp.structure_variants(PDK, members, kind, "vss", AR)
    odd = [v for v in vs if v["rows"] % 2]
    assert odd
    assert all(v["matching_type"] != "common_centroid" for v in odd)
