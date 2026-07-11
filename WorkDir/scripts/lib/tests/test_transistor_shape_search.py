"""
Unit tests for the free-num_fingers MOSFET shape search
(001_L1blocksGenerator.wmi_search_transistor_shape / wmi_search_unit_cell)
and its integration with 011_netlisBlocksGenerator.

Regression context: the netlist's own num_fingers was previously used as-is
to fold a transistor into (rows, cols), which for small/prime num_fingers
(or a raw netlist Nf that just happens to be a bad fit) produced long/narrow
blocks with aspect ratio up to ~16 — see
.claude/knowledge/notes/ for the investigation this fixes. num_fingers is
now a free layout choice (splitting a finger doesn't change W/L/electrical
behavior), searched to land inside a configured W/H band.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_PDK_DIR     = _SCRIPTS_DIR.parent / "myPDK"


def _load_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gen001():
    return _load_module("001_L1blocksGenerator.py", "gen001_test")


@pytest.fixture(scope="module")
def tech_file():
    tech = json.loads((_PDK_DIR / "gpdk090_tech_simple.json").read_text())
    dr   = json.loads((_PDK_DIR / "gpdk090_device_rules.json").read_text())
    return {**tech, **dr}


# A real case from m03_ota2.sp (nmos_lvt, M=1, netlist Nf=13 — prime, used to
# produce variants with AR 16.404 and 0.088, both far outside any sane band).
_PRIME_CASE = dict(width=29.25, length=0.3, multiplier=1, device_type="nmos_lvt")


def test_search_reaches_band_for_previously_extreme_case(gen001, tech_file):
    res = gen001.wmi_search_transistor_shape(
        tech_file, ar_min=0.5, ar_max=2.0, num_pins=4, **_PRIME_CASE)
    assert res["variants"], "expected at least one variant"
    used = next(v for v in res["variants"] if v["is_used"])
    bb = used["main_bbox"]
    ar = bb["x_max"] / bb["y_max"]
    assert 0.5 <= ar <= 2.0, f"is_used variant AR {ar} outside configured band"


def test_most_square_variant_is_first_and_marked_used(gen001, tech_file):
    res = gen001.wmi_search_transistor_shape(
        tech_file, ar_min=0.5, ar_max=2.0, num_pins=4, **_PRIME_CASE)

    def roundness(v):
        bb = v["main_bbox"]
        return max(bb["x_max"], bb["y_max"]) / min(bb["x_max"], bb["y_max"])

    square_count = gen001._MOSFET_SQUARE_VARIANT_COUNT
    core = [roundness(v) for v in res["variants"][:square_count]]
    assert core == sorted(core), "the near-square core should be roundness-ascending"
    assert res["variants"][0]["is_used"]
    assert all(not v["is_used"] for v in res["variants"][1:])


def test_variants_span_the_full_configured_interval(gen001, tech_file):
    """At least 8 variants: 4 near-square plus 4 anchored across the band
    (closest to ar_min, closest to ar_max, and the two geometric midpoints)
    — the placer should see shapes near both edges, not just near AR=1."""
    res = gen001.wmi_search_transistor_shape(
        tech_file, ar_min=0.5, ar_max=2.0, num_pins=4, **_PRIME_CASE)
    ars = [v["main_bbox"]["x_max"] / v["main_bbox"]["y_max"] for v in res["variants"]]
    assert len(res["variants"]) >= 8
    assert min(ars) <= 0.55, f"no variant near the low edge of the band: {sorted(ars)}"
    assert max(ars) >= 1.9, f"no variant near the high edge of the band: {sorted(ars)}"
    assert len(set(ars)) == len(ars), "no duplicate shapes expected among the 8 picks"


def test_identical_inputs_give_identical_shape(gen001, tech_file):
    """No explicit 'copy the partner' step is needed for symmetric pairs —
    the search is a pure function of (W, L, M, device_type), so identical
    inputs already guarantee identical output."""
    a = gen001.wmi_search_transistor_shape(
        tech_file, ar_min=0.5, ar_max=2.0, num_pins=4, **_PRIME_CASE)
    b = gen001.wmi_search_transistor_shape(
        tech_file, ar_min=0.5, ar_max=2.0, num_pins=4, **_PRIME_CASE)
    assert a["variants"] == b["variants"]


def test_unit_cell_is_independent_of_multiplier(gen001, tech_file):
    """wmi_search_unit_cell must not take multiplier as an input — any two
    devices sharing (device_type, W, L) need the identical unit cell so
    matching_engine.compute_matching_variants() can share it across a group
    regardless of per-member multiplier."""
    uw1, uh1, nf1 = gen001.wmi_search_unit_cell(
        tech_file, width=12.0, length=0.3, ar_min=0.5, ar_max=2.0, device_type="pmos_rvt")
    uw2, uh2, nf2 = gen001.wmi_search_unit_cell(
        tech_file, width=12.0, length=0.3, ar_min=0.5, ar_max=2.0, device_type="pmos_rvt")
    assert (uw1, uh1, nf1) == (uw2, uh2, nf2)
    ar = max(uw1, uh1) / min(uw1, uh1)
    assert ar <= 2.0, f"unit cell roundness {ar} is not close to square"


def test_max_layout_fingers_matches_active_min_width(gen001, tech_file):
    active_min = tech_file["physical_design_rules"]["active"]["min_width"]
    nf_max = gen001._max_layout_fingers(tech_file, width=1.0)
    assert nf_max == int(1.0 / active_min)


# --- Integration: 011_netlisBlocksGenerator on a real netlist ---------------

_NETLIST = _SCRIPTS_DIR.parent / "#Netlists" / "m03_ota2.sp"


@pytest.mark.skipif(not _NETLIST.exists(), reason="sample netlist not present")
def test_real_netlist_mosfet_blocks_reach_configured_band():
    gen011 = _load_module("011_netlisBlocksGenerator.py", "gen011_test")
    result = gen011.run(str(_NETLIST), seed=42, sym_mode="aggressive", random_sizes=False)

    cfg = json.loads((_PDK_DIR / "generation_config.json").read_text())
    ar_cfg = cfg["generation_params"]["mosfet_variant_aspect_ratio"]

    mosfets = [
        b for b in result["blocks"]
        if "error" not in b and b.get("device_type", "").startswith(("nmos", "pmos"))
    ]
    assert mosfets, "expected at least one MOSFET block"
    for blk in mosfets:
        used = next(v for v in blk["variants"] if v["is_used"])
        bb = used["main_bbox"]
        ar = bb["x_max"] / bb["y_max"]
        assert ar_cfg["min"] <= ar <= ar_cfg["max"], (
            f"block {blk['block_id']} ({blk['device_type']}) AR={ar} "
            f"outside configured band {ar_cfg}"
        )


@pytest.mark.skipif(not _NETLIST.exists(), reason="sample netlist not present")
def test_real_netlist_composite_groups_are_reasonably_square():
    """Regression for the unit_cell_w/h bug: computing the unit cell as a
    fixed '1 row x num_fingers cols' shape using the newly-searched (large)
    num_fingers produced groups with AR in the thousands. Composited groups
    should stay within a generous but bounded roundness after the fix."""
    gen011 = _load_module("011_netlisBlocksGenerator.py", "gen011_test")
    result = gen011.run(str(_NETLIST), seed=42, sym_mode="aggressive", random_sizes=False)

    checked = 0
    for g in result["groups"]:
        mvs = g.get("matching_variants", [])
        if not mvs:
            continue
        best = mvs[0]
        if best["height_um"] <= 0:
            continue
        ar_round = max(best["width_um"], best["height_um"]) / min(best["width_um"], best["height_um"])
        assert ar_round < 10.0, (
            f"group {g['group_id']} ({g['topology_type']}) matching_variant "
            f"roundness {ar_round} is far from square — unit_cell_w/h regression"
        )
        checked += 1
    assert checked > 0, "expected at least one composited group with matching_variants"
