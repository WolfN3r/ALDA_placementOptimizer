"""
012_pdkDeviceGenerator + lib/spice_parser + lib/pcell (sky130 via WorkDir/pdk/sky130/pdk.json).

Sources of expected values:
  [GDS]  bboxes measured in 05_miller_ota_tutorial/layout_klayout/miller_ota.gds
         (KLayout, PCell instances M1, M3, M6, M8, R1A, C1; DRC-clean layout)
  [PATCH] MOS PCell patched 2026-11-06 (characterize.json _comment_pcell_patch): npc encloses
         every poly licon by 0.10 instead of 0.09 (licon.15) -> every MOS 0.01 taller than [GDS]
  [NET]  the netlist text itself (data/miller_ota_sized.spice, data/ota1.spice)
  [PAR]  data/ota1_params.json = 06_ota1_magical/result.json + definitions.py
         layoutParams (NF1=10, NF2=16, NFCM=4)
  [HAND] hand calculation shown in the comment
"""
import importlib.util
import json
from pathlib import Path

import pytest

import hierarchy_builder
import pcell
from spice_parser import eval_expr

_SCRIPTS = Path(__file__).resolve().parents[2]
_DATA = Path(__file__).resolve().parent / "data"
_spec = importlib.util.spec_from_file_location("g012", _SCRIPTS / "012_pdkDeviceGenerator.py")
g012 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g012)

PDK = pcell.load_pdk("sky130")
NFET, PFET = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"
RES, CAP = "sky130_fd_pr__res_xhigh_po_0p35", "sky130_fd_pr__cap_mim_m3_1"
TOL = 1e-6


def _ota1_params():
    return json.loads((_DATA / "ota1_params.json").read_text())


def _by_inst(devs):
    return {d["inst"]: d for d in devs}


# ── T1: SPICE expressions ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text, env, expected", [
    ("{nint(MP1_M)}",       {"MP1_M": 4.817},  5),        # [HAND] 4.817 -> 5
    ("{2*nint(M6_M/2)}",    {"M6_M": 21.263},  22),       # [HAND] 10.63 -> 11 -> 22
    ("{2*nint(MP1_M)-4}",   {"MP1_M": 4.817},  6),        # [HAND] 2*5-4
    ("'int((4 + 1)/2)'",    {},                2),        # [HAND] int() truncates 2.5 -> 2
    ("2.5u",                {},                2.5e-6),   # [HAND] SPICE suffix u
    ("1meg",                {},                1e6),      # [HAND] meg before m
    ("{w1/nf1}",            {"W1": 131.3, "NF1": 10}, 13.13),  # [HAND] names are case-insensitive
])
def test_eval_expr(text, env, expected):
    assert eval_expr(text, env) == pytest.approx(expected, abs=1e-12)


# ── T2: parsing a real sky130 netlist ─────────────────────────────────────────

def test_parse_miller_sized_netlist():
    # [NET] 18 device lines; xschem writes both mult= and m= (same value).
    _, devs, _ = g012.netlist_devices(_DATA / "miller_ota_sized.spice", PDK, {})
    d = _by_inst(devs)
    assert len(devs) == 18
    m1 = d["xm1"]
    assert m1["pdk_type"] == NFET and m1["device_class"] == "nmos"
    assert (m1["parsed"]["W"], m1["parsed"]["L"], m1["parsed"]["nf"], m1["copies"]) == (2.17, 0.585, 1, 2)
    assert m1["terminals"] == {"drain": "n1", "gate": "inm", "source": "tail", "bulk": "vss"}
    assert (d["xm6"]["pdk_type"], d["xm6"]["parsed"]["W"], d["xm6"]["parsed"]["nf"], d["xm6"]["copies"]) \
        == (PFET, 11.42, 4, 1)
    assert d["xm7"]["copies"] == 12
    assert d["xr1a"]["device_class"] == "res" and d["xr1a"]["parsed"]["L"] == 1.27
    assert d["xr1a"]["terminals"] == {"n1": "n2", "n2": "nr1", "substrate": "vss"}
    assert (d["xc1"]["device_class"], d["xc1"]["parsed"]["W"], d["xc1"]["parsed"]["L"], d["xc1"]["copies"]) \
        == ("cap", 8.0, 12.67, 1)


def test_parse_ota1_with_params_file():
    # [NET]+[PAR] 25 device lines (21 FETs, 2 res_high_po_0p69, 2 MIM caps);
    # copies are expressions of result.json values.
    _, devs, _ = g012.netlist_devices(_DATA / "ota1.spice", PDK, _ota1_params())
    d = _by_inst(devs)
    assert len(devs) == 25
    assert d["xm9"]["copies"] == 22                  # 2*nint(21.263/2)
    assert d["xm10"]["copies"] == 6                  # 2*nint(4.817)-4
    assert d["xmp1a"]["copies"] == 5                 # nint(4.817)
    assert d["xm11"]["copies"] == 4                  # literal m=4
    assert d["xm0"]["parsed"]["W"] == pytest.approx(131.26673805422675, abs=TOL)
    assert d["xm0"]["parsed"]["nf"] == 10
    assert d["xm1"]["pdk_type"] == "sky130_fd_pr__pfet_01v8_lvt"
    assert d["xc1"]["parsed"]["W"] == pytest.approx(20.88000744043268, abs=TOL)
    assert d["xr25"]["pdk_type"] == "sky130_fd_pr__res_high_po_0p69"
    assert d["xr25"]["parsed"]["L"] == pytest.approx(2.9972030887418635, abs=TOL)   # RZ_L


def test_parse_subckt_hierarchy_multiplier(tmp_path):
    # [HAND] .param WN=2 -> WU = 2*2 = 4; copies = inner m=3 x instance m=2 = 6;
    # inner nets map to the top-level nets of the instance line.
    f = tmp_path / "h.spice"
    f.write_text("""
.param WN=2
.subckt unit d g s b WU=1
XM1 d g s b sky130_fd_pr__nfet_01v8 W={WU} L=0.5 nf=1 m=3
.ends
.subckt top a b c VSS
X1 a b c VSS unit WU={WN*2} m=2
.ends
""")
    _, devs, hier = g012.netlist_devices(f, PDK, {})
    assert len(devs) == 1
    dev = devs[0]
    assert dev["inst"] == "x1.xm1"
    assert dev["parsed"]["W"] == 4.0 and dev["copies"] == 6
    assert dev["terminals"] == {"drain": "a", "gate": "b", "source": "c", "bulk": "vss"}
    assert hier["x1.xm1"] == "unit"


# ── T3: footprints from pdk.json vs. the real GDS ─────────────────────────────

@pytest.mark.parametrize("model, values, w, h", [
    (NFET, {"W": 2.17,  "L": 0.585, "nf": 1}, 1.435, 2.92),    # [GDS] M1 2.91 + [PATCH]
    (NFET, {"W": 2.125, "L": 0.525, "nf": 1}, 1.375, 2.875),   # [GDS] M8 2.865 + [PATCH]
    (PFET, {"W": 1.61,  "L": 0.86,  "nf": 1}, 2.07,  2.72),    # [GDS] M3 2.71 + [PATCH]
    (PFET, {"W": 11.42, "L": 0.38,  "nf": 4}, 4.23,  3.965),   # [GDS] M6 3.955 + [PATCH] (4 fingers of 2.855)
    (RES,  {"L": 1.27},                       1.27,  5.87),    # [GDS] R1A (PCell len = 1.27 - 0.12)
    (CAP,  {"W": 8.0,   "L": 12.67},          9.86,  13.07),   # [GDS] C1
])
def test_footprint_matches_miller_gds(model, values, w, h):
    fw, fh = pcell.footprint(PDK, model, pcell.pcell_params(PDK, model, values))
    assert (fw, fh) == (pytest.approx(w, abs=TOL), pytest.approx(h, abs=TOL))


def test_pcell_params_snap_to_grid():
    # [PAR]+[HAND] ota1 XM0: W/nf = 131.26674/10 = 13.126674 -> 13.125 (5 nm grid),
    # L = 0.610489 -> 0.61. Footprint = 0.35 + 10*(0.61 + 0.5) = 11.45 by
    # 0.75 + 13.125 = 13.875 (nfet coefficients, checked against the GDS above; 0.74 + [PATCH]).
    p = pcell.pcell_params(PDK, NFET, {"W": 131.26673805422675, "L": 0.610488987657381, "nf": 10})
    assert p["w"] == pytest.approx(13.125, abs=TOL) and p["l"] == pytest.approx(0.61, abs=TOL)
    assert p["nf"] == 10
    fw, fh = pcell.footprint(PDK, NFET, p)
    assert (fw, fh) == (pytest.approx(11.45, abs=TOL), pytest.approx(13.875, abs=TOL))


# ── T4: copy arrays (pure geometry, gaps passed in) ───────────────────────────

def test_copy_array_footprint():
    # [HAND] 12 copies of M7 (1.375 x 2.865) as 2 rows x 6 cols, gap x 0.02, y 0.2:
    # W = 6*1.375 + 5*0.02 = 8.35, H = 2*2.865 + 1*0.2 = 5.93
    assert g012.copy_array(1.375, 2.865, 2, 6, 0.02, 0.2) == (pytest.approx(8.35), pytest.approx(5.93))


def test_copy_variants_factorizations():
    # [HAND] 12 copies, unit 1.375 x 2.865, gaps 0.02 / 0.2, aspect band [0.25, 4]:
    #   rows 1: 16.72 x 2.865 (AR 5.84, out)   rows 2: 8.35 x 5.93 (AR 1.41)
    #   rows 3: 5.56 x 8.995 (AR 0.62)          rows 4: 4.165 x 12.06 (AR 0.345)
    #   rows 6: 2.77 x 18.19 (AR 0.15, out)     rows 12: AR 0.04 (out)
    # Closest to square (max/min): rows 2 (1.41) < rows 3 (1.62) < rows 4 (2.90).
    v = g012.copy_variants(1.375, 2.865, 12, 0.02, 0.2)
    assert [x["layout"]["rows"] for x in v] == [2, 3, 4]
    assert [x["is_used"] for x in v] == [True, False, False]
    assert v[0]["main_bbox"]["x_max"] == pytest.approx(8.35) and v[0]["main_bbox"]["y_max"] == pytest.approx(5.93)


def test_copy_variants_prime_and_single():
    # [HAND] 7 copies: rows 1 -> 9.745 x 2.865 (AR 3.40, in), rows 7 -> 1.375 x 21.255
    # (AR 0.065, out). 1 copy -> the unit itself.
    v7 = g012.copy_variants(1.375, 2.865, 7, 0.02, 0.2)
    assert [(x["layout"]["rows"], x["layout"]["cols"]) for x in v7] == [(1, 7)]
    v1 = g012.copy_variants(1.375, 2.865, 1, 0.02, 0.2)
    assert len(v1) == 1 and v1[0]["main_bbox"]["x_max"] == pytest.approx(1.375)


# ── T5: polarity / passive from device_class (gpdk090 names keep working) ─────

def test_polarity_and_passive_from_device_class():
    assert hierarchy_builder._polarity({"device_type": PFET, "device_class": "pmos"}) == "p"
    assert hierarchy_builder._polarity({"device_type": NFET, "device_class": "nmos"}) == "n"
    assert hierarchy_builder._polarity({"device_type": "pmos_rvt"}) == "p"          # gpdk090 path
    assert hierarchy_builder._is_passive_block({"device_type": RES, "device_class": "res"})
    assert not hierarchy_builder._is_passive_block({"device_type": NFET, "device_class": "nmos"})
    assert hierarchy_builder._is_passive_block({"device_type": "res_poly"})         # gpdk090 path


def test_symmetry_detector_sees_sky130_inverter(tmp_path):
    # symmetry_detector docstring: "inv — N + P, same gate and drain, sources on the
    # rails". Needs the pfet recognised as P although its name has no "pmos".
    from symmetry_detector import detect_symmetries
    f = tmp_path / "inv.spice"
    f.write_text("""
.subckt inv in out vdd vss
XMN out in vss vss sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1
XMP out in vdd vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1
.ends
""")
    ports, devs, _ = g012.netlist_devices(f, PDK, {})
    devs = [dict(d, block_id=i) for i, d in enumerate(devs)]
    r = detect_symmetries(devs, {"in", "out"}, {"vdd", "vss"})
    name = {d["block_id"]: d["inst"] for d in devs}
    invs = [[name[b] for b in bb["devices"]] for bb in r["building_blocks"] if bb["type"] == "inv"]
    assert invs == [["xmn", "xmp"]]


# ── T6: end to end ────────────────────────────────────────────────────────────

def test_run_miller_end_to_end():
    # [NET] 18 devices; XRD1, XRD2, XMD1, XMD3, XMD8 have every terminal on a
    # supply -> netlist dummies, dropped (placement dummies are added after
    # placement) -> 13 blocks. find_passive_arrays lists every remaining
    # passive as a cluster: C1, R1A..R1D, each alone.
    out = g012.run(str(_DATA / "miller_ota_sized.spice"), 1, pdk_name="sky130")
    blocks = out["blocks"]
    assert out["technology"] == "sky130A"
    assert len(blocks) == 13
    assert not [b for b in blocks if "error" in b]
    for b in blocks:
        assert b["variants"] and sum(v["is_used"] for v in b["variants"]) == 1
    m7 = next(b for b in blocks if b["inst"] == "xm7")
    assert m7["parameters"]["multiplier"] == 12
    assert (m7["unit_cell_w"], m7["unit_cell_h"]) == (pytest.approx(1.375), pytest.approx(2.875))   # [GDS] M7 + [PATCH]
    assert sorted(c["original_count"] for c in out["symmetry_constraints"]["passive_clusters"]) \
        == [1, 1, 1, 1, 1]


def test_run_ota1_end_to_end():
    # [NET]+[PAR] 25 devices; the two caps and the two resistors each sit on
    # different nets -> nothing collapses.
    out = g012.run(str(_DATA / "ota1.spice"), 1, pdk_name="sky130",
                   params_paths=[str(_DATA / "ota1_params.json")])
    blocks = out["blocks"]
    assert len(blocks) == 25
    assert not [b for b in blocks if "error" in b]
    assert next(b for b in blocks if b["inst"] == "xm9")["parameters"]["multiplier"] == 22
