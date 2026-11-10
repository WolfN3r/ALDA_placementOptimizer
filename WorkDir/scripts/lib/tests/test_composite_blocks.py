"""
Composite (grouped) blocks: hierarchy_builder.build_composite_blocks /
remap_nets_for_composites and 101's _expand_composite_placements — approved 2026-11-05.
All checks are invariants [INV] on an inline circuit run through 011 (balanced mode):
5T-OTA input stage with resistor loads and two output inverters.
"""
import importlib.util
import re
from pathlib import Path

import pytest

import pipeline
from hierarchy_builder import build_composite_blocks, remap_nets_for_composites

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g011 = _load("011_netlisBlocksGenerator.py", "g011_composite")
o101 = _load("101_placementOptimizer.py", "o101_composite")

SPICE = """
.subckt comp inp inn outm outp vb vdd vss
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
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    f = tmp_path_factory.mktemp("comp") / "c.sp"
    f.write_text(SPICE)
    data = g011.run(str(f), 1, "balanced")
    block_by_id = {b["block_id"]: b for b in data["blocks"] if "error" not in b}
    nets = data["netlist"]["nets"]
    comps, excluded = build_composite_blocks(data["groups"], block_by_id, nets)
    effective = {c["block_id"]: c for c in comps} | {b: x for b, x in block_by_id.items() if b not in excluded}
    return data, block_by_id, nets, comps, excluded, effective


def test_composites_replace_their_members(built):
    data, _, _, comps, excluded, _ = built
    assert comps, "expected at least one composite"
    groups = {g["group_id"]: g for g in data["groups"]}
    for c in comps:
        assert c["group_block_ids"] == groups[c["group_id"]]["block_ids"]
        assert set(c["group_block_ids"]) <= excluded
    assert len(excluded) == sum(len(c["group_block_ids"]) for c in comps)   # no block in two composites


def test_remapped_pins_resolve_to_placed_block_pins(built):
    # HPWL silently skips a pin it cannot find, so every pin must name a placement
    # node (composite or ungrouped block) and one of that node's pin_positions
    _, block_by_id, nets, comps, excluded, effective = built
    for net in remap_nets_for_composites(nets, comps, block_by_id):
        for pin in net["pins"]:
            bid, name = re.fullmatch(r"B(\d+)_(.+)", pin).groups()
            bid = int(bid)
            assert bid not in excluded, f"{net['net_id']}: {pin} points inside a composite"
            assert bid in effective, f"{net['net_id']}: {pin} has no block"
            used = next(v for v in effective[bid]["variants"] if v.get("is_used", True))
            assert name in used["pin_positions"], f"{net['net_id']}: {pin} has no pin position"


def test_nets_internal_to_one_composite_get_no_pin(built):
    # remap_nets_for_composites docstring: a signal net between >= 2 members of one
    # composite and nothing else is local to it -> no composite pin
    _, block_by_id, nets, comps, _, _ = built
    remapped = {n["net_id"]: n for n in remap_nets_for_composites(nets, comps, block_by_id)}
    for c in comps:
        members = set(c["group_block_ids"])
        for net in nets:
            bids = {int(re.match(r"B(\d+)_", p).group(1)) for p in net["pins"]}
            if net.get("net_type", "signal") != "power" and len(bids) >= 2 and bids <= members:
                assert not [p for p in remapped[net["net_id"]]["pins"] if p.startswith(f"B{c['block_id']}_")]


def test_expanded_members_lie_inside_their_composite(built):
    _, block_by_id, _, comps, _, effective = built
    blocks = {str(b): x for b, x in effective.items()}
    positions = {b: (10.0 * i, 5.0 * i) for i, b in enumerate(sorted(blocks))}
    vm = {str(c["block_id"]): len(c["variants"]) - 1 for c in comps}      # not variant 0 on purpose
    placed = pipeline._compute_placed_blocks(positions, blocks, vm)
    expanded = o101._expand_composite_placements(comps, placed, block_by_id, vm)
    for c in comps:
        e = expanded[str(c["block_id"])]
        bb = e["main_bbox"]
        subs = e["sub_blocks"]
        assert set(subs) == {str(m) for m in c["group_block_ids"]}
        rects = []
        for s in subs.values():
            r = s["main_bbox"]
            assert bb["x_min"] - 1e-6 <= r["x_min"] < r["x_max"] <= bb["x_max"] + 1e-6
            assert bb["y_min"] - 1e-6 <= r["y_min"] < r["y_max"] <= bb["y_max"] + 1e-6
            rects.append((r["x_min"], r["y_min"], r["x_max"], r["y_max"]))
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert min(a[2], b[2]) - max(a[0], b[0]) <= 1e-6 or min(a[3], b[3]) - max(a[1], b[1]) <= 1e-6
