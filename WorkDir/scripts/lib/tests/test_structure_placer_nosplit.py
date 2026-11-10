"""
lib/structure_placer — variant pruning and no finger split, N1..N4, approved 2026-11-07.

Sources of expected values:
  [HAND] hand reasoning shown in the comment
  [USER] user decisions 2026-11-07: no multi-row shape with one device per row; inner
         dummies only when they lower the linear centroid error; the placer never splits a
         device (nf and m come from the netlist / simulation)
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


def _shapes(vs):
    return {(v["rows"], v["cols"]) for v in vs}


# ── N1: DP 1:1 -> only dABd ───────────────────────────────────────────────────

def test_n1_dp_1_1_single_variant():
    vs = sp.structure_variants(PDK, _dp(1), "cc", "vss", AR)
    # [USER] 2x1 dropped (one device per row). [HAND] in 1x3 / 1x4 an inner dummy can only
    # move A and B further apart, so lin never drops below 1x2 -> those are dropped too.
    assert len(vs) == 1
    assert vs[0]["pattern"] in (["dABd"], ["dBAd"])
    assert vs[0]["dummies"]["inner_full_size"] == 0


# ── N2: DP 2:2 -> no one-device-per-row shape ─────────────────────────────────

def test_n2_dp_2_2_no_single_column():
    vs = sp.structure_variants(PDK, _dp(2), "cc", "vss", AR)
    # [USER] 4x1 has one device per row
    assert all(v["cols"] > 1 for v in vs)
    # [HAND] 2x2 AB/BA and 1x4 ABBA both have rows with two devices
    assert {(2, 2), (1, 4)} <= _shapes(vs)


# ── N3: DP m=1 nf=10 -> not split ─────────────────────────────────────────────

def test_n3_no_finger_split():
    vs = sp.structure_variants(PDK, _dp(1, W=10.0, L=0.5, nf=10), "cc", "vss", AR)
    for v in vs:
        # [USER] the device keeps its netlist nf: one slot per device
        assert v["unit_pcell"]["nf"] == 10
        assert sum(1 for s in v["slots"] if s["block_id"] == 0) == 1
        assert sum(1 for s in v["slots"] if s["block_id"] == 1) == 1
    assert vs[0]["pattern"] in (["dABd"], ["dBAd"])


# ── N4: inner dummies only when they lower lin ────────────────────────────────

@pytest.mark.parametrize("members, kind", [
    (_dp(3), "cc"),
    ([_mos(0, 1, "g", "g", "vss"), _mos(1, 1, "o1", "g", "vss"), _mos(2, 3, "o2", "g", "vss")], "mirror"),
])
def test_n4_inner_dummy_only_if_better(members, kind, caplog):
    with caplog.at_level(logging.WARNING, logger="structure_placer"):
        vs = sp.structure_variants(PDK, members, kind, "vss", AR)
    plain = [v["score"]["lin"] for v in vs if v["dummies"]["inner_full_size"] == 0]
    assert plain
    # [USER] every kept inner-dummy variant beats the best variant without inner dummies
    for v in vs:
        if v["dummies"]["inner_full_size"] > 0:
            assert v["score"]["lin"] < min(plain) - TOL
