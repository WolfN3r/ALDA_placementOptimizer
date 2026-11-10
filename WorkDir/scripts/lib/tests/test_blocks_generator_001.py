"""
001_L1blocksGenerator.run (random blocks + symmetry-aware netlist) — approved 2026-11-05.
Invariants [INV]: reproducible per seed, and every reference points to a generated block.
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("g001_test", _SCRIPTS / "001_L1blocksGenerator.py")
g001 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g001)


def test_same_seed_same_output_other_seed_differs():
    a, b, c = g001.run(6, 7), g001.run(6, 7), g001.run(6, 8)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert json.dumps(a, sort_keys=True) != json.dumps(c, sort_keys=True)


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_references_point_to_generated_blocks(seed):
    out = g001.run(6, seed)
    ids = {b["block_id"] for b in out["blocks"]}
    assert len(ids) == len(out["blocks"]) == 6
    for net in out["netlist"]["nets"]:
        for pin in net["pins"]:
            assert int(re.match(r"B(\d+)_", pin).group(1)) in ids, f"{net['net_id']}: {pin}"
    sc = out["symmetry_constraints"]
    for g in sc["groups"]:
        assert {b for p in g["pairs"] for b in p} | set(g["self_symmetric"]) <= ids
    for p in sc.get("symmetric_net_pairs", []):
        assert set(p["block_pair"]) <= ids
