"""
lib/structure_placer — common-centroid search tests T1..T7, approved 2026-11-05
(debate verdict, scratchpad debate/judge/final.md; dummies tied to the rail per user).

Sources of expected values:
  [HAND]     hand calculation shown in the comment (lattice: x = column, rows symmetric
             about the array centre because the channel gaps alternate a, b, a, ...)
  [HASTINGS] Hastings, The Art of Analog Layout, §7.2: matched devices share a common
             centroid and have equal shares of each orientation
  [PDK]      WorkDir/pdk/sky130/pdk.json: nfet footprint w = 0.35 + 0.5 nf + nf*l
DP terminals are tail / out / gate, never the dummy rail (vss): the two row-end dummies of
every DP row always face a mismatched side, so the minimum facing count is 2 per row.
"""
import logging

import pytest

import pcell
import structure_placer as sp

PDK = pcell.load_pdk("sky130")
NFET = "sky130_fd_pr__nfet_01v8"
AR = (0.25, 4.0)
TOL = 1e-6


def _mos(bid, copies, d, g, s, W=2.17, L=0.585, nf=1):
    return {"block_id": bid, "copies": copies, "model": NFET,
            "pcell": pcell.pcell_params(PDK, NFET, {"W": W, "L": L, "nf": nf}),
            "terminals": {"drain": d, "gate": g, "source": s, "bulk": "vss"}}


def _dp(copies, **kw):
    return [_mos(0, copies, "outp", "inn", "tail", **kw), _mos(1, copies, "outn", "inp", "tail", **kw)]


def _units(v, bid):
    return [s for s in v["slots"] if s["block_id"] == bid]


# ── T1: DP 4:4 ────────────────────────────────────────────────────────────────

def test_t1_dp_4_4_quad_zero():
    v = sp.structure_variants(PDK, _dp(4), "cc", "vss", AR)[0]
    # [HAND] 2x4 ABBA/BAAB: x = ±0.5, ±1.5 -> A bottom {±1.5}, top {±0.5}, B the opposite rows:
    # Σx = 0 and Σx² = 5 for both, equal y moments, Σxy = 0. [HASTINGS] common centroid.
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
    assert v["score"]["x2y2"] == pytest.approx(0, abs=TOL)
    assert v["score"]["xy"] == pytest.approx(0, abs=TOL)
    # [HAND] A|B face tail|tail, B|B outn|outn, B|A tail|tail: only the 2 row-end dummy sides per row
    assert v["facing_mismatches"] == 2 * v["rows"]


# ── T2: DP 8:8 ────────────────────────────────────────────────────────────────

def test_t2_dp_8_8_quad_zero():
    v = sp.structure_variants(PDK, _dp(8), "cc", "vss", AR)[0]
    # [HAND] 2x8 BAABBAAB / ABBAABBA (x = col - 3.5): A Σx² = 17 + 25 = 42 = B, Σx = 0 each row
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
    assert v["score"]["x2y2"] == pytest.approx(0, abs=TOL)
    assert v["score"]["xy"] == pytest.approx(0, abs=TOL)
    assert v["facing_mismatches"] == 2 * v["rows"]


# ── T3: DP 3:3 (odd) -> one inner dummy ───────────────────────────────────────

def test_t3_dp_3_3_inner_dummy():
    v = sp.structure_variants(PDK, _dp(3), "cc", "vss", AR)[0]
    # [HAND] no 6-slot shape has an exact centroid (3 units would need Σx = 7.5 / 3 / 1.5).
    # 1x7 ABBDAAB: A {0,4,5}, B {1,2,6}, dummy at the centre 3: Σx 9 = 9, Σx² 41 = 41.
    # The only exact 7-slot sets are this one and its A/B swap.
    assert v["pattern"] in (["dABBdAABd"], ["dBAAdBBAd"])
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
    assert v["dummies"]["inner_full_size"] == 1
    # [HAND] 2 row-end sides + both sides of the inner rail dummy; all device|device pairs share
    assert v["facing_mismatches"] == 4


# ── T4: mirror 1:1:3 -> no common centroid possible ───────────────────────────

def test_t4_mirror_1_1_3_not_cc(caplog):
    ms = [_mos(0, 1, "g", "g", "vss"), _mos(1, 1, "o1", "g", "vss"), _mos(2, 3, "o2", "g", "vss")]
    with caplog.at_level(logging.WARNING, logger="structure_placer"):
        v = sp.structure_variants(PDK, ms, "mirror", "vss", AR)[0]
    # [HAND] two single-unit devices sit on different slots, so their centroids differ
    assert v["matching_type"] != "common_centroid"
    assert v["score"]["lin"] > TOL
    assert any(r.levelno == logging.WARNING for r in caplog.records)


# ── T5: mirror 2+2 ────────────────────────────────────────────────────────────

def test_t5_mirror_2_2_facing():
    ms = [_mos(0, 2, "g", "g", "vss"), _mos(1, 2, "outb", "g", "vss")]
    v = sp.structure_variants(PDK, ms, "mirror", "vss", AR)[0]
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
    # [HAND] each unit has one vss side and one private side (g or outb). Zero mismatches needs
    # every private side to face the same device (AABB rows), which is never common centroid.
    # 1x4 ABBA and 2x2 AB/BA both reach 2 (one A|B private contact per pair of rows / ends).
    assert v["facing_mismatches"] == 2


# ── T6: mirror 4+12+4, orientation balance ────────────────────────────────────

def test_t6_bias_mirror_orientation_balanced():
    ms = [_mos(4, 4, "tail", "bias", "vss", W=2.125, L=0.525),
          _mos(6, 12, "out", "bias", "vss", W=2.125, L=0.525),
          _mos(7, 4, "bias", "bias", "vss", W=2.125, L=0.525)]
    v = sp.structure_variants(PDK, ms, "mirror", "vss", AR)[0]
    # [HASTINGS] equal R0/R180 shares; [HAND] point-symmetric 2x10 pairs every R0 slot with an R180 slot
    assert v["score"]["orient"] == pytest.approx(0, abs=TOL)
    assert v["score"]["lin"] == pytest.approx(0, abs=TOL)
