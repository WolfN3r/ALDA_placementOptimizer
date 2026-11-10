"""
Symmetry detection vs. Eick et al., TCAD 2011 (SSFG) — tests written before the
rewrite planned in .claude/plans/eick_symmetry_detection_rewrite.md (§5).

Every circuit is an inline SPICE string parsed by 011's own flattener; nothing
is added to #Netlists/. Expected values are hand-derived from the paper's
building-block library (Fig. 5), symmetry assignment (Fig. 8/9, §III-C) and the
plan's decisions: D1 — no self-symmetric single devices (a tail stays part of
its current mirror), D2 — single transistors carry g→d and s→d SSFG edges.

Output contract assumed by the helpers (block ids → instance names):
  building_blocks: [{"type", "devices", "reference"}]
  logical_devices: [[member block ids]]   (series stacks / parallels collapsed)
  groups:          [{"pairs", "self_symmetric"}]
"""
import importlib.util
from pathlib import Path

import pytest

from symmetry_detector import detect_symmetries

_SCRIPTS = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("g011", _SCRIPTS / "011_netlisBlocksGenerator.py")
g011 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g011)

_NETLISTS = _SCRIPTS.parent / "#Netlists"

N_STACK_2 = """
.subckt n_stack_2 d g s b
mi1 d g inet b nmos w=1 l=0.1
mi2 inet g s b nmos w=1 l=0.1
.ends
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _run_file(path):
    ports, devs, _ = g011.parse_and_flatten(str(path))
    devs = [dict(d, block_id=i) for i, d in enumerate(devs)]
    nets = {n for d in devs for n in d["terminals"].values() if n}
    power = {n for n in nets if n.lower() in g011.POWER_ALIASES}
    signal = {p for p in ports if p.lower() not in g011.POWER_ALIASES}
    return detect_symmetries(devs, signal, power), {d["block_id"]: d for d in devs}


def _detect(tmp_path, spice):
    f = tmp_path / "c.sp"
    f.write_text(spice)
    r, by_id = _run_file(f)
    name = {bid: d["inst"] for bid, d in by_id.items()}
    return r, name


def _pairs(r, name):
    return {frozenset((name[a], name[b])) for g in r["groups"] for a, b in g["pairs"]}


def _selfs(r, name):
    return {name[s] for g in r["groups"] for s in g["self_symmetric"]}


def _bbs(r, name, kind):
    return [(frozenset(name[b] for b in bb["devices"]), frozenset(name[b] for b in bb["reference"]))
            for bb in r["building_blocks"] if bb["type"] == kind]


def _compounds(r, name):
    return [{frozenset((name[a], name[b])) for a, b in g["pairs"]} for g in r["groups"] if g["pairs"]]


def P(*pairs):
    return {frozenset(p) for p in pairs}


# ── T1–T2: single structures ──────────────────────────────────────────────────

def test_t1_diff_pair_with_tail(tmp_path):
    # Eick Fig. 5a (dp) + S1: input gates (inp, inn) seed → M1↔M2. D1: tail has no role.
    r, n = _detect(tmp_path, """
.subckt t1 inp inn x1 x2 vb vdd vss
m1 x1 inp tail vss nmos w=1 l=0.1
m2 x2 inn tail vss nmos w=1 l=0.1
mt tail vb vss vss nmos w=1 l=0.1
.ends
""")
    assert (frozenset({"m1", "m2"}), frozenset()) in _bbs(r, n, "dp")
    assert _pairs(r, n) == P(("m1", "m2"))
    assert _selfs(r, n) == set()
    assert _compounds(r, n) == [P(("m1", "m2"))]


def test_t2_five_transistor_ota(tmp_path):
    # Eick Fig. 4 / §III-C-2: the load mirror's edge x1→x2 connects the symmetric
    # node pair (x1, x2) → self-symmetric edge (S3, single-ended conversion) →
    # self-symmetric scm → its two devices are a pair (like scm3 → (N3, N4)).
    r, n = _detect(tmp_path, """
.subckt t2 inp inn x2 vb vdd vss
m1 x1 inp tail vss nmos w=1 l=0.1
m2 x2 inn tail vss nmos w=1 l=0.1
mt tail vb vss vss nmos w=1 l=0.1
m3 x1 x1 vdd vdd pmos w=1 l=0.1
m4 x2 x1 vdd vdd pmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "scm") == [(frozenset({"m3", "m4"}), frozenset({"m3"}))]
    assert _pairs(r, n) == P(("m1", "m2"), ("m3", "m4"))
    assert _selfs(r, n) == set()
    assert len(_compounds(r, n)) == 1


# ── T3: Eick Fig. 3 with the backtracking case of Fig. 9b ─────────────────────

def test_t3_eick_fig3_backtracking(tmp_path):
    # Eick §III-C-3: C1 = {(N1,N2),(P1,P2),(P3,P4),(N3,N4),(P6,P7),(N8,N9)};
    # N8/N9 omitted (connections not readable from Fig. 3). Device order makes
    # netlist-order pairing at (n1, n2) pick (n3, n6), (n7, n4); Fig. 9b: V2
    # rejects (n7, n4) because n4 → out (P5) has no counterpart at n7, and
    # backtracking yields (n3, n4), (n7, n6). (n3, n4) ends in the
    # self-symmetric edge e7 (V1), so P5 adds no constraint there.
    # Bias bank N5/N6/N7 is matching only (Fig. 13: MG_B,2 outside SG1).
    r, n = _detect(tmp_path, """
.subckt fig3 inn inp out bias vdd vss
mn1 n1 inn n5 vss nmos w=1 l=0.1
mn2 n2 inp n5 vss nmos w=1 l=0.1
mp1 n1 n1 vdd vdd pmos w=1 l=0.1
mp3 n3 n1 vdd vdd pmos w=1 l=0.1
mp7 n7 n1 vdd vdd pmos w=1 l=0.1
mp2 n2 n2 vdd vdd pmos w=1 l=0.1
mp6 n6 n2 vdd vdd pmos w=1 l=0.1
mp4 n4 n2 vdd vdd pmos w=1 l=0.1
mn3 n3 n3 vss vss nmos w=1 l=0.1
mn4 n4 n3 vss vss nmos w=1 l=0.1
mp5 out n4 vdd vdd pmos w=1 l=0.1
mn5 bias bias vss vss nmos w=1 l=0.1
mn6 n5 bias vss vss nmos w=1 l=0.1
mn7 out bias vss vss nmos w=1 l=0.1
.ends
""")
    expected = P(("mn1", "mn2"), ("mp1", "mp2"), ("mp3", "mp4"), ("mn3", "mn4"), ("mp7", "mp6"))
    assert _pairs(r, n) == expected
    assert _selfs(r, n) == set()
    assert _compounds(r, n) == [expected]


# ── T4: cascode current mirror ────────────────────────────────────────────────

def test_t4_cascode_mirror_with_diode_has_no_symmetry(tmp_path):
    # Eick Fig. 5d (ccm; diode: lower gate = upper reference drain) + §IV-B-2:
    # a ccm yields M_B / P_B only. No dp → no S1 seed → no symmetry at all.
    r, n = _detect(tmp_path, """
.subckt t4 iin iout vb vss
mt3 iin vb a vss nmos w=1 l=0.1
mt1 a iin vss vss nmos w=1 l=0.1
mt4 iout vb b vss nmos w=1 l=0.1
mt2 b iin vss vss nmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "ccm") == [(frozenset({"mt1", "mt2", "mt3", "mt4"}), frozenset({"mt1", "mt3"}))]
    assert _pairs(r, n) == set()
    assert _selfs(r, n) == set()


def test_t4b_cascode_without_diode_is_not_a_mirror(tmp_path):
    # Eick Fig. 5d requires the diode; both gates on external bias ports → no ccm, no scm.
    r, n = _detect(tmp_path, """
.subckt t4b iin iout vb vbn vss
mt3 iin vb a vss nmos w=1 l=0.1
mt1 a vbn vss vss nmos w=1 l=0.1
mt4 iout vb b vss nmos w=1 l=0.1
mt2 b vbn vss vss nmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "ccm") == []
    assert _bbs(r, n, "scm") == []
    assert _pairs(r, n) == set()


# ── T5: big current-mirror banks ──────────────────────────────────────────────

def test_t5_big_bank_is_one_matching_block(tmp_path):
    # Wang 2024 Fig. 1a (A..E, multipliers [1,1,6,3,1]): the whole bank is one
    # placement unit; Eick M_B only. No dp → no symmetry.
    r, n = _detect(tmp_path, """
.subckt t5 g ob oc od oe vss
ma g g vss vss nmos w=1 l=0.1
mb ob g vss vss nmos w=1 l=0.1
mc oc g vss vss nmos w=1 l=0.1 m=6
md od g vss vss nmos w=1 l=0.1 m=3
me oe g vss vss nmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "scm") == [(frozenset({"ma", "mb", "mc", "md", "me"}), frozenset({"ma"}))]
    assert _pairs(r, n) == set()
    assert _selfs(r, n) == set()


_T5B = """
.subckt t5b inp inn outp outn bias aux vdd vss
m1 x1 inp tail vss nmos w=1 l=0.1
m2 x2 inn tail vss nmos w=1 l=0.1
ml1 x1 x1 vdd vdd pmos w=1 l=0.1
mp1 outp x1 vdd vdd pmos w=1 l=0.1
ml2 x2 x2 vdd vdd pmos w=1 l=0.1
mp2 outn x2 vdd vdd pmos w=1 l=0.1
mr bias bias vss vss nmos w=1 l=0.1
mo1 outp bias vss vss nmos w=1 l=0.1
mt tail bias vss vss nmos w=1 l=0.1
mo2 outn bias vss vss nmos w=1 l=0.1
mx aux bias vss vss nmos w=1 l=0.1
.ends
"""


def test_t5b_bank_inside_two_stage_ota(tmp_path):
    # Eick §III-C-2: scm_a {ml1; mp1} and scm_b {ml2; mp2} are symmetric
    # building blocks ((x1,x2) → (outp,outn)) → (ml1,ml2), (mp1,mp2).
    # Bank outputs on (outp, outn) → (mo1, mo2); reference mr, tail mt, mx: no
    # role (D1). Listed so that netlist-order pairing would give (mr,mo1), (mt,mo2).
    # Regression for m02 vbias_n / m04 vbp.
    r, n = _detect(tmp_path, _T5B)
    assert _pairs(r, n) == P(("m1", "m2"), ("ml1", "ml2"), ("mp1", "mp2"), ("mo1", "mo2"))
    assert _selfs(r, n) == set()
    assert (frozenset({"mr", "mo1", "mt", "mo2", "mx"}), frozenset({"mr"})) in _bbs(r, n, "scm")
    assert len(_compounds(r, n)) == 1


# ── T6: level shifter ─────────────────────────────────────────────────────────

def test_t6_level_shifter_telescopic(tmp_path):
    # Eick Fig. 5b (ls: shared gate, diode reference, different sources). Its
    # sub-SSFG edge p_d↔p_b carries (a1, a2) → (outp, outn) → (mc1, mc2).
    # Loads ml1/ml2 (external vbp, single transistors) pair via (outp, outn).
    r, n = _detect(tmp_path, """
.subckt t6 inp inn outp outn vbn vbp vdd vss
m1 a1 inp tail vss nmos w=1 l=0.1
m2 a2 inn tail vss nmos w=1 l=0.1
mtail tail vbn vss vss nmos w=1 l=0.1
mc1 outp vb a1 vss nmos w=1 l=0.1
mc2 outn vb a2 vss nmos w=1 l=0.1
mb vb vb nb vss nmos w=1 l=0.1
mi nb vbn vss vss nmos w=1 l=0.1
ml1 outp vbp vdd vdd pmos w=1 l=0.1
ml2 outn vbp vdd vdd pmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "ls") == [(frozenset({"mb", "mc1", "mc2"}), frozenset({"mb"}))]
    assert _bbs(r, n, "scm") == []
    assert _pairs(r, n) == P(("m1", "m2"), ("mc1", "mc2"), ("ml1", "ml2"))
    assert _selfs(r, n) == set()


# ── T7: series stacks ─────────────────────────────────────────────────────────

def test_t7_stacked_mirror_is_scm_not_level_shifter(tmp_path):
    # Plan P0: n_stack_2 = one logical device (corpus a35). After collapse this
    # is a plain scm (common source vss), not an ls.
    r, n = _detect(tmp_path, N_STACK_2 + """
.subckt t7 vb o1 o2 vss
xr vb vb vss vss n_stack_2
xo1 o1 vb vss vss n_stack_2
xo2 o2 vb vss vss n_stack_2
.ends
""")
    logical = {frozenset(n[b] for b in grp) for grp in r["logical_devices"]}
    for x in ("xr", "xo1", "xo2"):
        assert frozenset({f"{x}.mi1", f"{x}.mi2"}) in logical
    all6 = frozenset(f"{x}.{m}" for x in ("xr", "xo1", "xo2") for m in ("mi1", "mi2"))
    assert _bbs(r, n, "scm") == [(all6, frozenset({"xr.mi1", "xr.mi2"}))]
    assert _bbs(r, n, "ls") == []
    assert _pairs(r, n) == set()


def test_t7b_stacked_dp_with_bias_stack_on_tail(tmp_path):
    # Corpus a33 net10: the tail net carries the stacked DP and a stacked ls
    # output (m11+m11s). Banks are recognised before DPs, so the DP is the
    # unique remaining pair. Stack pairs expand by position from the drain side.
    r, n = _detect(tmp_path, """
.subckt t7b inn inp x1 x2 q vt vdd vss
m3 x1 inn m3n vss nmos w=1 l=0.1
m3s m3n inn tail vss nmos w=1 l=0.1
m0 x2 inp m0n vss nmos w=1 l=0.1
m0s m0n inp tail vss nmos w=1 l=0.1
m10 vbn vbn m10n vss nmos w=1 l=0.1
m10s m10n vbn nb vss nmos w=1 l=0.1
m11 q vbn m11n vss nmos w=1 l=0.1
m11s m11n vbn tail vss nmos w=1 l=0.1
mtail tail vt vss vss nmos w=1 l=0.1
.ends
""")
    assert (frozenset({"m3", "m3s", "m0", "m0s"}), frozenset()) in _bbs(r, n, "dp")
    assert _pairs(r, n) == P(("m3", "m0"), ("m3s", "m0s"))
    assert [ref for _, ref in _bbs(r, n, "ls")] == [frozenset({"m10", "m10s"})]


# ── T8: ambiguous source ──────────────────────────────────────────────────────

def test_t8_three_devices_on_one_source_is_no_dp(tmp_path):
    # Plan P1 rule 4 (exactly two devices); corpus a26 ring oscillator vctl.
    r, n = _detect(tmp_path, """
.subckt t8 i1 i2 i3 o1 o2 o3 vctl vss
ma o1 i1 vctl vss nmos w=1 l=0.1
mb o2 i2 vctl vss nmos w=1 l=0.1
mc o3 i3 vctl vss nmos w=1 l=0.1
.ends
""")
    assert _bbs(r, n, "dp") == []
    assert _pairs(r, n) == set()


# ── T9: combined circuit ──────────────────────────────────────────────────────

def test_t9_combined_circuit(tmp_path):
    # Composition of T5b + T6 + T7 + T8: telescopic first stage (ls cascodes)
    # into mirror loads, second stage, one NMOS bank feeding tail, outputs and
    # the ls reference current; plus an unrelated stacked bias mirror and a
    # ring-oscillator stage. One compound; banks and extras carry no role.
    r, n = _detect(tmp_path, N_STACK_2 + """
.subckt t9 inp inn outp outn bias aux sb so r1 r2 r3 ri1 ri2 ri3 vctl vdd vss
m1 a1 inp tail vss nmos w=1 l=0.1
m2 a2 inn tail vss nmos w=1 l=0.1
mc1 x1 vb a1 vss nmos w=1 l=0.1
mc2 x2 vb a2 vss nmos w=1 l=0.1
mb vb vb nb vss nmos w=1 l=0.1
ml1 x1 x1 vdd vdd pmos w=1 l=0.1
mp1 outp x1 vdd vdd pmos w=1 l=0.1
ml2 x2 x2 vdd vdd pmos w=1 l=0.1
mp2 outn x2 vdd vdd pmos w=1 l=0.1
mr bias bias vss vss nmos w=1 l=0.1
mo1 outp bias vss vss nmos w=1 l=0.1
mt tail bias vss vss nmos w=1 l=0.1
mo2 outn bias vss vss nmos w=1 l=0.1
mx aux bias vss vss nmos w=1 l=0.1
mi nb bias vss vss nmos w=1 l=0.1
xs1 sb sb vss vss n_stack_2
xs2 so sb vss vss n_stack_2
mra r1 ri1 vctl vss nmos w=1 l=0.1
mrb r2 ri2 vctl vss nmos w=1 l=0.1
mrc r3 ri3 vctl vss nmos w=1 l=0.1
.ends
""")
    expected = P(("m1", "m2"), ("mc1", "mc2"), ("ml1", "ml2"), ("mp1", "mp2"), ("mo1", "mo2"))
    assert _pairs(r, n) == expected
    assert _selfs(r, n) == set()
    assert _compounds(r, n) == [expected]
    assert _bbs(r, n, "ls") == [(frozenset({"mb", "mc1", "mc2"}), frozenset({"mb"}))]
    scm = _bbs(r, n, "scm")
    assert (frozenset({"mr", "mo1", "mt", "mo2", "mx", "mi"}), frozenset({"mr"})) in scm
    assert (frozenset({"xs1.mi1", "xs1.mi2", "xs2.mi1", "xs2.mi2"}),
            frozenset({"xs1.mi1", "xs1.mi2"})) in scm
    assert _bbs(r, n, "dp") == [(frozenset({"m1", "m2"}), frozenset())]


# ── T10: passive loads [ext] ──────────────────────────────────────────────────

def test_t10_resistor_loads_pair(tmp_path):
    # Plan P4 [ext]: Eick does not cover passives; R1/R2 terminals map onto each
    # other under the net registry (x1↔x2, vdd fixed) → pair.
    r, n = _detect(tmp_path, """
.subckt t10 inp inn x1 x2 vb vdd vss
m1 x1 inp tail vss nmos w=1 l=0.1
m2 x2 inn tail vss nmos w=1 l=0.1
mt tail vb vss vss nmos w=1 l=0.1
r1 vdd x1 res w=1 l=4
r2 vdd x2 res w=1 l=4
.ends
""")
    assert _pairs(r, n) == P(("m1", "m2"), ("r1", "r2"))


# ── T11: one-role invariant on the corpus ─────────────────────────────────────

@pytest.mark.parametrize("netlist", sorted(_NETLISTS.glob("*.sp")), ids=lambda p: p.stem)
def test_t11_corpus_one_role_per_device(netlist):
    # Audit 2026-10-20 §2: a device has at most one role (one partner, or self)
    # in at most one group; a pair joins devices of the same pdk_type.
    try:
        r, by_id = _run_file(netlist)
    except ValueError:
        pytest.skip("netlist has no devices")
    roles: dict = {}
    for g in r["groups"]:
        for a, b in g["pairs"]:
            assert by_id[a]["pdk_type"] == by_id[b]["pdk_type"]
            roles[a] = roles.get(a, 0) + 1
            roles[b] = roles.get(b, 0) + 1
        for s in g["self_symmetric"]:
            roles[s] = roles.get(s, 0) + 1
    multi = {by_id[b]["inst"]: k for b, k in roles.items() if k > 1}
    assert multi == {}


# ── T12–T14: corpus regressions (hand analysis of the netlists) ───────────────

def _detect_netlist(stem):
    r, by_id = _run_file(_NETLISTS / f"{stem}.sp")
    return r, {bid: d["inst"] for bid, d in by_id.items()}


def test_t12_a30_telescopic_cascode_load():
    # a30_telescopic_ota.sp: dp m4/m3 (vinn/vinp → net014/net8); nmos cascodes
    # m6/m5 (net014/net8 → voutp/voutn, external vbiasn); pmos cascode load m8/m7
    # (voutp/voutn ↔ net012/net06) on current sources m10/m9. Reaching the load
    # from (voutp, voutn) needs the single transistor's d→s edge (Eick ls p_b↔p_d
    # analogue). m1 (diode, id) + m2 (tail) = bias mirror: matching only.
    r, n = _detect_netlist("a30_telescopic_ota")
    assert _pairs(r, n) == P(("m3", "m4"), ("m5", "m6"), ("m7", "m8"), ("m9", "m10"))
    assert _bbs(r, n, "scm") == [(frozenset({"m1", "m2"}), frozenset({"m1"}))]
    assert len(_compounds(r, n)) == 1


def test_t13_a06_symmetric_cascode_mirrors():
    # a06_cascode_current_mirror_ota.sp = Eick Fig. 3 with cascode mirrors:
    # ccm A {ref m26/m21 (net16 diode), out m22/m20 → vbiasnd} and ccm B
    # {ref m27/m19 (net27), out m23/m18 → voutp} are symmetric building blocks
    # (net16→vbiasnd ↔ net27→voutp, Eick §III-C-2) → corresponding devices pair;
    # ccm C {ref m24/m11 (vbiasnd), out m25/m10 → voutp} carries the
    # self-symmetric edge vbiasnd→voutp (single-ended conversion, like scm3).
    # m14 (diode, id) + m16 (tail) = bias mirror: matching only.
    r, n = _detect_netlist("a06_cascode_current_mirror_ota")
    assert _pairs(r, n) == P(
        ("m17", "m15"), ("m26", "m27"), ("m21", "m19"), ("m22", "m23"), ("m20", "m18"),
        ("m24", "m25"), ("m11", "m10"),
    )
    ccm = _bbs(r, n, "ccm")
    assert len(ccm) == 3 and set(ccm) == {
        (frozenset({"m26", "m21", "m22", "m20"}), frozenset({"m26", "m21"})),
        (frozenset({"m27", "m19", "m23", "m18"}), frozenset({"m27", "m19"})),
        (frozenset({"m24", "m11", "m25", "m10"}), frozenset({"m24", "m11"})),
    }
    assert len(_compounds(r, n)) == 1


def test_t14_m02_cmfb_dps_do_not_seed():
    # m02_ota1.sp: main dp m0/m2 (inm/inp → intp/intm), loads mp1b/mp1a, second
    # stage m1/m3 (gates intp/intm → outm/outp), sinks m9/m6, Miller m25/m23 +
    # xc1/xc0. The CMFB dps m19/m18 (vref, outm) and m17/m15 (vref, outp) share the
    # reference gate vref: they stay matched dp blocks but are not symmetry seeds,
    # otherwise vref↔outm would block outm↔outp. Bias mirrors carry no role.
    r, n = _detect_netlist("m02_ota1")
    main = P(("m0", "m2"), ("mp1a", "mp1b"), ("m1", "m3"), ("m9", "m6"), ("m25", "m23"), ("xc1", "xc0"))
    assert _pairs(r, n) == main | P(("m19", "m18"), ("m17", "m15"))
    assert main in _compounds(r, n)


def test_t15_m01_latch_does_not_end_propagation():
    # m01_comp.sp (StrongARM-type comparator): dp m5/m6 (vip/vim → intern/interp),
    # latches m4/m3 and m14/m13 (crossn/crossp), output inverters m16/m8 → outm
    # (gate crossp) and m17/m15 → outp (gate crossn). The latch's gate→drain edges
    # crossn→crossp and crossp→crossn are a symmetric edge pair, not a single
    # self-symmetric edge (Eick Def. 4, S3), so propagation continues to (outm, outp).
    r, n = _detect_netlist("m01_comp")
    assert _pairs(r, n) == P(
        ("m5", "m6"), ("m4", "m3"), ("m14", "m13"), ("m0", "m22"), ("m18", "m19"), ("m10", "m12"),
        ("m16", "m17"), ("m8", "m15"),
    )
    assert len(_compounds(r, n)) == 1
