"""
Group roles [B][A|A][B'] and proximity (digital) blocks — tests written before
the implementation planned in .claude/plans/paired_groups_and_proximity_blocks.md (§5).

Circuits are inline SPICE run through 011 (parse → detect → blocks → build_groups).
Expected values are hand-derived from the plan's rules and Eick 2011:
  A  (role "self")  — pairs inside one building block (dp, latch, self-symmetric bank)
  B/B' (role "pair") — symmetric building blocks, passives, digital blocks, and
                       single transistors sharing gate + source on one side
  side "L"/"R"      — the first gate of the seeding dp is side L; derived pairs
                       inherit the orientation; a device takes the side of its drain.

Group contract assumed:
  group["symmetry"] = {"axis_id", "level", "role", "partner", "side"} or None
  detector groups' pairs are ordered [L member, R member].
"""
import importlib.util
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("g011_roles", _SCRIPTS / "011_netlisBlocksGenerator.py")
g011 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g011)
_spec = importlib.util.spec_from_file_location("g012_roles", _SCRIPTS / "012_pdkDeviceGenerator.py")
g012 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g012)

_NETLISTS = _SCRIPTS.parent / "#Netlists"


# ── helpers ───────────────────────────────────────────────────────────────────

def _generate(tmp_path, spice, mode="mirrored"):
    f = tmp_path / "c.sp"
    f.write_text(spice)
    return g011.run(str(f), 1, mode)


def _view(data):
    """(name map, {frozenset(member insts): group}) for groups with active members."""
    name = {b["block_id"]: b["inst"] for b in data["blocks"]}
    groups = {frozenset(name[b] for b in g["block_ids"]): g
              for g in data["groups"] if g["topology_type"] != "passive_free"}
    return name, groups


def _role(groups, members):
    g = groups[frozenset(members)]
    return g["symmetry"]


def _partner_members(data, name, group):
    pid = group["symmetry"]["partner"]
    other = next(g for g in data["groups"] if g["group_id"] == pid)
    return frozenset(name[b] for b in other["block_ids"])


def _group_of(data, name, inst):
    return next(g for g in data["groups"] if inst in {name[b] for b in g["block_ids"]})


# ── G1–G4: roles ──────────────────────────────────────────────────────────────

def test_g1_five_transistor_ota_groups_are_self(tmp_path):
    # Eick §III-C-2: dp and the single-ended-conversion mirror (scm3 analogue) are
    # self-symmetric building blocks → role A, centred on the axis.
    data = _generate(tmp_path, """
.subckt g1 inp inn x2 vb vdd vss
m1 x1 inp tail vss nmos w=2 l=0.2
m2 x2 inn tail vss nmos w=2 l=0.2
mt tail vb vss vss nmos w=2 l=0.2
m3 x1 x1 vdd vdd pmos w=2 l=0.2
m4 x2 x1 vdd vdd pmos w=2 l=0.2
.ends
""")
    _, groups = _view(data)
    for members in ({"m1", "m2"}, {"m3", "m4"}):
        sym = _role(groups, members)
        assert sym["role"] == "self" and sym["partner"] is None and sym["side"] is None


_FIG3 = """
.subckt fig3 inn inp out bias vdd vss
mn1 n1 inn n5 vss nmos w=2 l=0.2
mn2 n2 inp n5 vss nmos w=2 l=0.2
mp1 n1 n1 vdd vdd pmos w=2 l=0.2
mp3 n3 n1 vdd vdd pmos w=2 l=0.2
mp7 n7 n1 vdd vdd pmos w=2 l=0.2
mp2 n2 n2 vdd vdd pmos w=2 l=0.2
mp6 n6 n2 vdd vdd pmos w=2 l=0.2
mp4 n4 n2 vdd vdd pmos w=2 l=0.2
mn3 n3 n3 vss vss nmos w=2 l=0.2
mn4 n4 n3 vss vss nmos w=2 l=0.2
mp5 out n4 vdd vdd pmos w=2 l=0.2
mn5 bias bias vss vss nmos w=2 l=0.2
mn6 n5 bias vss vss nmos w=2 l=0.2
mn7 out bias vss vss nmos w=2 l=0.2
.ends
"""


def test_g2_eick_fig3_symmetric_mirrors_merge_into_one_group(tmp_path):
    # Eick §V, Fig. 13: symmetric building blocks scm1/scm7 {P1; P3, P7} and
    # scm2/scm6 {P2; P4, P6} form one matching group MG_B (analog pairs merge,
    # plan decision 2026-10-21, option 1) → one self-symmetric group A. dp and
    # scm3 are A as well.
    data = _generate(tmp_path, _FIG3)
    name, groups = _view(data)
    assert _role(groups, {"mp1", "mp3", "mp7", "mp2", "mp4", "mp6"})["role"] == "self"
    assert _role(groups, {"mn1", "mn2"})["role"] == "self"
    assert _role(groups, {"mn3", "mn4"})["role"] == "self"


def test_g3_reset_switches_one_block_per_side(tmp_path):
    # Hand analysis of m01_comp.sp (equal sizes here): reset switches share gate clk
    # and source vdd; m18 (intern) and m10 (crossn) lie on the vip side → B = {m18, m10},
    # m19 (interp) and m12 (crossp) → B'. dp and both latches are A.
    data = _generate(tmp_path, """
.subckt g3 vip vim clk vdd vss
m7 net050 clk vss vss nmos w=2 l=0.2
m5 intern vip net050 vss nmos w=2 l=0.2
m6 interp vim net050 vss nmos w=2 l=0.2
m4 crossn crossp intern vss nmos w=2 l=0.2
m3 crossp crossn interp vss nmos w=2 l=0.2
m14 crossn crossp vdd vdd pmos w=2 l=0.2
m13 crossp crossn vdd vdd pmos w=2 l=0.2
m18 intern clk vdd vdd pmos w=2 l=0.2
m19 interp clk vdd vdd pmos w=2 l=0.2
m10 crossn clk vdd vdd pmos w=2 l=0.2
m12 crossp clk vdd vdd pmos w=2 l=0.2
.ends
""")
    name, groups = _view(data)
    b = groups[frozenset({"m18", "m10"})]
    assert b["symmetry"]["role"] == "pair" and b["symmetry"]["side"] == "L"
    assert _partner_members(data, name, b) == frozenset({"m19", "m12"})
    assert groups[frozenset({"m19", "m12"})]["symmetry"]["side"] == "R"
    for members in ({"m5", "m6"}, {"m4", "m3"}, {"m14", "m13"}):
        assert _role(groups, members)["role"] == "self"


def test_g4_resistor_loads_are_mirrored_raw_blocks(tmp_path):
    # Plan §2: passives become B/B', each resistor its own group; r1 on x1 (inp side) = L.
    data = _generate(tmp_path, """
.subckt g4 inp inn x1 x2 vb vdd vss
m1 x1 inp tail vss nmos w=2 l=0.2
m2 x2 inn tail vss nmos w=2 l=0.2
mt tail vb vss vss nmos w=2 l=0.2
r1 vdd x1 res w=1 l=4
r2 vdd x2 res w=1 l=4
.ends
""")
    name, _ = _view(data)
    g1, g2 = _group_of(data, name, "r1"), _group_of(data, name, "r2")
    assert g1["group_id"] != g2["group_id"]
    assert g1["symmetry"]["role"] == g2["symmetry"]["role"] == "pair"
    assert g1["symmetry"]["partner"] == g2["group_id"] and g2["symmetry"]["partner"] == g1["group_id"]
    assert (g1["symmetry"]["side"], g2["symmetry"]["side"]) == ("L", "R")


# ── G5–G6: proximity (digital) blocks ─────────────────────────────────────────

def test_g5_output_inverters_are_paired_proximity_blocks(tmp_path):
    # Plan §3: inv = N + P with the same gate and drain, sources on the two rails.
    # Inverters on x1 → outm and x2 → outp are symmetric blocks → B (x1 = inp side, L) / B'.
    data = _generate(tmp_path, """
.subckt g5 inp inn outm outp vb vdd vss
m1 x1 inp tail vss nmos w=2 l=0.2
m2 x2 inn tail vss nmos w=2 l=0.2
mt tail vb vss vss nmos w=2 l=0.2
r1 vdd x1 res w=1 l=4
r2 vdd x2 res w=1 l=4
mna outm x1 vss vss nmos w=2 l=0.2
mpa outm x1 vdd vdd pmos w=4 l=0.2
mnb outp x2 vss vss nmos w=2 l=0.2
mpb outp x2 vdd vdd pmos w=4 l=0.2
.ends
""")
    name, groups = _view(data)
    inv = [bb for bb in data["symmetry_constraints"]["building_blocks"] if bb["type"] == "inv"]
    assert {frozenset(name[b] for b in bb["devices"]) for bb in inv} == {
        frozenset({"mna", "mpa"}), frozenset({"mnb", "mpb"})}
    a, b = groups[frozenset({"mna", "mpa"})], groups[frozenset({"mnb", "mpb"})]
    assert a["topology_type"] == b["topology_type"] == "inverter"
    assert a["symmetry"]["role"] == "pair" and a["symmetry"]["side"] == "L"
    assert a["symmetry"]["partner"] == b["group_id"]


def test_g6_nand2_is_one_proximity_block(tmp_path):
    # Plan §3: nand2 = two series N (gates a, b) to out + two parallel P on a, b.
    data = _generate(tmp_path, """
.subckt g6 a b out vdd vss
mna out a mid vss nmos w=2 l=0.2
mnb mid b vss vss nmos w=2 l=0.2
mpa out a vdd vdd pmos w=2 l=0.2
mpb out b vdd vdd pmos w=2 l=0.2
.ends
""")
    name, groups = _view(data)
    nand = [bb for bb in data["symmetry_constraints"]["building_blocks"] if bb["type"] == "nand2"]
    assert [frozenset(name[b] for b in bb["devices"]) for bb in nand] == [
        frozenset({"mna", "mnb", "mpa", "mpb"})]
    assert groups[frozenset({"mna", "mnb", "mpa", "mpb"})]["topology_type"] == "nand2"


# ── G7: orientation ───────────────────────────────────────────────────────────

def test_g7_pairs_are_ordered_left_first(tmp_path):
    # Plan §2 side labels: seed dp (inn, inp) → inn side L; every derived pair keeps the
    # orientation (Eick Fig. 9: n1/n2, n3/n4, n7/n6 from inn/inp).
    data = _generate(tmp_path, _FIG3)
    name, _ = _view(data)
    ordered = {(name[a], name[b]) for g in data["symmetry_constraints"]["groups"] for a, b in g["pairs"]}
    assert ordered == {("mn1", "mn2"), ("mp1", "mp2"), ("mp3", "mp4"), ("mn3", "mn4"), ("mp7", "mp6")}


# ── G8: invariant on the corpus ───────────────────────────────────────────────

@pytest.mark.parametrize("netlist", sorted(_NETLISTS.glob("*.sp")), ids=lambda p: p.stem)
def test_g8_corpus_group_roles_consistent(netlist):
    # Plan §1: each block in at most one group; a pair group's partner points back,
    # sits on the same axis and the opposite side; a self group has no partner/side.
    # sky130 netlists go through 012 (real PDK devices), all others through 011.
    try:
        if "sky130_fd_pr" in netlist.read_text(errors="ignore"):
            data = g012.run(str(netlist), 42, pdk_name="sky130", sym_mode="mirrored")
        else:
            data = g011.run(str(netlist), 42, "mirrored")
    except ValueError:
        pytest.skip("netlist has no devices")
    seen: set = set()
    by_id = {g["group_id"]: g for g in data["groups"]}
    for g in data["groups"]:
        assert not seen & set(g["block_ids"])
        seen |= set(g["block_ids"])
        sym = g.get("symmetry")
        if not sym:
            continue
        if sym["role"] == "self":
            assert sym["partner"] is None and sym["side"] is None
        else:
            p = by_id[sym["partner"]]["symmetry"]
            assert p["role"] == "pair" and p["partner"] == g["group_id"]
            assert p["axis_id"] == sym["axis_id"] and {p["side"], sym["side"]} == {"L", "R"}


# ── G9–G12: mode-dependent merging, switch rule, proximity geometry ───────────

def test_g9_passive_pair_merges_in_matched_mode(tmp_path):
    # Plan decision (option 1): passives merge into one self-symmetric group in
    # matched/balanced (interleaved resistors match best); B/B' only in mirrored (G4).
    spice = """
.subckt g9 inp inn x1 x2 vb vdd vss
m1 x1 inp tail vss nmos w=2 l=0.2
m2 x2 inn tail vss nmos w=2 l=0.2
mt tail vb vss vss nmos w=2 l=0.2
r1 vdd x1 res w=1 l=4
r2 vdd x2 res w=1 l=4
.ends
"""
    for mode in ("matched", "balanced"):
        data = _generate(tmp_path, spice, mode)
        _, groups = _view(data)
        assert _role(groups, {"r1", "r2"})["role"] == "self"


@pytest.mark.parametrize("mode", ["matched", "balanced"])
def test_g10_inverters_stay_paired_in_every_mode(tmp_path, mode):
    # Plan decision: digital blocks are never merged (coupling between outm/outp,
    # speed) — B/B' in every mode.
    data = _generate(tmp_path, """
.subckt g10 inp inn outm outp vb vdd vss
m1 x1 inp tail vss nmos w=2 l=0.2
m2 x2 inn tail vss nmos w=2 l=0.2
mt tail vb vss vss nmos w=2 l=0.2
r1 vdd x1 res w=1 l=4
r2 vdd x2 res w=1 l=4
mna outm x1 vss vss nmos w=2 l=0.2
mpa outm x1 vdd vdd pmos w=4 l=0.2
mnb outp x2 vss vss nmos w=2 l=0.2
mpb outp x2 vdd vdd pmos w=4 l=0.2
.ends
""", mode)
    _, groups = _view(data)
    a = groups[frozenset({"mna", "mpa"})]
    assert a["symmetry"]["role"] == "pair"
    assert a["symmetry"]["partner"] == groups[frozenset({"mnb", "mpb"})]["group_id"]


def test_g11_bias_driven_current_sources_merge():
    # a30_telescopic_ota.sp: m10/m9 (gate vbiasp2, drives PMOS only) are current
    # sources, not switches (switch = gate also drives the opposite polarity) → their
    # pair merges into one self-symmetric group, like the cascodes m5/m6.
    data = g011.run(str(_NETLISTS / "a30_telescopic_ota.sp"), 1, "mirrored")
    _, groups = _view(data)
    for members in ({"m9", "m10"}, {"m5", "m6"}, {"m7", "m8"}):
        assert _role(groups, members)["role"] == "self"


def test_g12_inverter_proximity_layout_is_p_over_n(tmp_path):
    # Plan §3, standard-cell style: one row per polarity, P row above N row.
    # width  = max(row widths); one device per row here → max(w_P, w_N)
    # height = h_P + gap + h_N, gap = gpdk090_device_rules.json between_topologies
    #          "different_bulks" WPE_poly = 3 µm (nmos bulk VSSA ≠ pmos bulk VDDA).
    data = _generate(tmp_path, """
.subckt g12 a y vdd vss
mn y a vss vss nmos w=2 l=0.2
mp y a vdd vdd pmos w=4 l=0.2
.ends
""")
    name, groups = _view(data)
    blk = {b["inst"]: b for b in data["blocks"]}

    def dims(inst):
        v = next((v for v in blk[inst]["variants"] if v.get("is_used")), blk[inst]["variants"][0])
        bb = v["main_bbox"]
        return bb["x_max"] - bb["x_min"], bb["y_max"] - bb["y_min"]

    (wn, hn), (wp, hp) = dims("mn"), dims("mp")
    [mv] = groups[frozenset({"mn", "mp"})]["matching_variants"]
    assert mv["width_um"] == pytest.approx(max(wn, wp), abs=1e-3)
    assert mv["height_um"] == pytest.approx(hp + 3.0 + hn, abs=1e-3)
