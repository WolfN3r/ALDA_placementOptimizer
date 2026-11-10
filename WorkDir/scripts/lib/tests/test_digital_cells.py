"""
Digital gates (inv, nand2, nor2, tg) as stacked rows: structure_placer.digital_variant,
012 grouping and the device count through placement. Approved 2026-11-06.

Sources of expected values:
  [PDK]  WorkDir/pdk/sky130/pdk.json: nfet footprint w = 0.35 + 0.5 nf + nf*l, h = 0.75 + w,
         ring clearance l/r 0.145, bottom 0.07, top 0.135, x_routed 0.02; pfet footprint
         w = 0.71 + 0.5 nf + nf*l, h = 1.11 + w, clearance l/r -0.035, bottom -0.11, top -0.09,
         x_routed -0.34; ring bbox = opening + 2*grw + 0.25, grw 0.23, opening corner at
         grw + 0.125 = 0.355; n-ring nwell fill sticks out 0.18 - 0.125 = 0.055 per side
  [USER] ring-to-ring gap >= 0.02 µm (PDK p_ring|n_ring min is 0.005) (user, 2026-11-06)
  [NET]  device lines of the netlist text
  [HAND] hand calculation shown in the comment

Real sky02_comp inverter: xm17 nfet W 0.59 L 0.15 nf 1 -> 1.00 x 1.34 [PDK];
xm15 pfet w 0.97 L 0.15 nf 2 -> 2.01 x 2.08 [PDK].
N ring: opening 1.00 + 0.29 = 1.29 x 1.34 + 0.205 = 1.545 -> 2.00 x 2.255; content at (0.5, 0.425).
P ring: opening 2.01 - 0.07 = 1.94 x 2.08 - 0.20 = 1.88 -> 2.65 x 2.59 + 0.11 fill = 2.76 x 2.70;
        content at (0.055 + 0.355 - 0.035, 0.055 + 0.355 - 0.11) = (0.375, 0.30).
"""
import copy
import importlib.util
import random
import re
from pathlib import Path

import pytest

import pcell
import structure_placer as sp
from hierarchy_builder import COMPOSITE_ID_BASE

_SCRIPTS = Path(__file__).resolve().parents[2]
_NETLISTS = _SCRIPTS.parent / "#Netlists"
PDK = pcell.load_pdk("sky130")
NFET, PFET = "sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8"
TOL = 1e-6


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _n(bid):
    return {"block_id": bid, "copies": 1, "model": NFET,
            "pcell": pcell.pcell_params(PDK, NFET, {"W": 0.59, "L": 0.15, "nf": 1})}


def _p(bid):
    return {"block_id": bid, "copies": 1, "model": PFET,
            "pcell": pcell.pcell_params(PDK, PFET, {"W": 1.94, "L": 0.15, "nf": 2})}


def _box(o):
    return (o["x_min"], o["y_min"], o["x_max"], o["y_max"])


# ── D1-D3: inverter ───────────────────────────────────────────────────────────

def test_inverter_outline_slots_rings():
    v = sp.digital_variant(PDK, [[_n(17)], [_p(15)]])
    # D1 [HAND] W = max(2.00, 2.76); H = 2.255 + 0.02 [USER] + 2.70
    assert v["rows"] == 2
    assert (v["width_um"], v["height_um"]) == pytest.approx((2.76, 4.975), abs=TOL)
    # D2 [HAND] N ring shifted (2.76 - 2.00) / 2 = 0.38: x 0.38 + 0.5 + 0.5, y 0.425 + 0.67;
    #           P ring at y 2.275: x 0.375 + 1.005, y 2.275 + 0.30 + 1.04
    s = {x["block_id"]: x for x in v["slots"]}
    assert (s[17]["row"], s[15]["row"]) == (0, 1)
    assert (s[17]["x"], s[17]["y"]) == pytest.approx((1.38, 1.095), abs=TOL)
    assert (s[15]["x"], s[15]["y"]) == pytest.approx((1.38, 3.615), abs=TOL)
    assert s[17]["x"] == pytest.approx(v["width_um"] / 2, abs=TOL)
    assert all(x["orient"] == "R0" and not x["dummy"] for x in v["slots"])
    # D3 [HAND] openings: N (0.355 + 0.38, 0.355, +1.29, +1.545); P (0.41, 0.41 + 2.275, +1.94, +1.88)
    n_ring, p_ring = v["guard_rings"]
    assert (n_ring["ring"], p_ring["ring"]) == ("p_ring", "n_ring")
    assert _box(n_ring["opening"]) == pytest.approx((0.735, 0.355, 2.025, 1.90), abs=TOL)
    assert _box(p_ring["opening"]) == pytest.approx((0.41, 2.685, 2.35, 4.565), abs=TOL)


# ── D4: two devices per row (nand2 / nor2 shape) ─────────────────────────────

def test_two_device_rows_centred_in_member_order():
    v = sp.digital_variant(PDK, [[_n(1), _n(2)], [_p(3), _p(4)]])
    # [HAND] N opening 2*1.00 + 0.02 + 0.29 = 2.31 -> ring 3.02; P opening 2*2.01 - 0.34 - 0.07 = 3.61
    #        -> ring 3.61 + 0.71 + 0.11 = 4.43; N ring shifted (4.43 - 3.02) / 2 = 0.705
    assert v["width_um"] == pytest.approx(4.43, abs=TOL)
    s = {x["block_id"]: x for x in v["slots"]}
    # [HAND] N: 0.705 + 0.5 + 0.5 and + 1.02; P: 0.375 + 1.005 and + 2.01 - 0.34
    assert [s[b]["x"] for b in (1, 2)] == pytest.approx([1.705, 2.725], abs=TOL)
    assert [s[b]["x"] for b in (3, 4)] == pytest.approx([1.38, 3.05], abs=TOL)
    assert [s[b]["row"] for b in (1, 2, 3, 4)] == [0, 0, 1, 1]
    assert len(v["guard_rings"]) == 2


# ── D5: 012 grouping and device count through placement ──────────────────────

def _netlist_devices(path: Path) -> int:
    """[NET] instance lines of sky130 devices."""
    return sum(1 for line in path.read_text().splitlines()
               if re.match(r"\s*x", line, re.I) and "sky130_fd_pr__" in line)


@pytest.mark.parametrize("name", ["sky01_ota1", "sky02_comp"])
def test_every_netlist_device_placed_exactly_once(name):
    g012 = _load("012_pdkDeviceGenerator.py", "g012_digital")
    o101 = _load("101_placementOptimizer.py", "o101_digital")
    o101.WARMUP_N_RUNS = 0
    o101.USE_CONTOUR_BASELINE = False
    o101.SA_MAX_ITER = 3000
    o101.RUN_MODE = ""
    o101.TOPOLOGY, o101.OPTIMIZER = "SequencePairTopology", "SimulatedAnnealingOptimizer"

    netlist = _NETLISTS / f"{name}.sp"
    data = g012.run(str(netlist), 1, pdk_name="sky130", sym_mode="balanced")
    valid = [b["block_id"] for b in data["blocks"] if "error" not in b]
    assert len(valid) + len(data.get("netlist_dummies", [])) == _netlist_devices(netlist)

    # no device in two placement groups
    grouped = [b for g in data["groups"] if g.get("matching_variants") for b in g["block_ids"]]
    assert len(grouped) == len(set(grouped)), f"device in two groups: {sorted(grouped)}"
    for g in data["groups"]:
        if g["topology_type"] in ("inverter", "nand2", "nor2", "transmission_gate"):
            v = g["matching_variants"]
            assert len(v) == 1 and "slots" in v[0] and len(v[0]["guard_rings"]) == 2

    random.seed(0)
    out = o101.run(copy.deepcopy(data))
    groups = {g["group_id"]: g["block_ids"] for g in data["groups"]}
    placed = []
    for key in out["placement"]["placed_blocks"]:
        if key.startswith("__"):
            continue
        bid = int(key)
        placed += groups[bid - COMPOSITE_ID_BASE] if bid >= COMPOSITE_ID_BASE else [bid]
    assert sorted(placed) == sorted(valid)
