"""
#Netlists circuits (a*, m*, sky*) through the real chain (011 or 012 -> 101) with each
topology / optimizer pair; the placed result must be legal, symmetric and on grid.
Approved 2026-11-05.

  [INV]  invariant; no stored numbers
  [DRC]  WorkDir/viewer/drc_checker._check_pair with gpdk090_device_rules.json — only for
         the gpdk090 netlists (a*, m*); sky130 spacing rules are not written yet (user, 2026-11-05)
  [GRID] manufacturing grid 0.005 µm (gpdk090_tech_simple.json, pdk/sky130/pdk.json)

Nothing is written to json_files/: 011/012/101 run() return dicts only.
SA and PSO run shortened (3000 iterations / 300 PSO iterations); ILP warmups and the
contour baseline are off — they only change the start point, not the constraints.
"""
import copy
import functools
import importlib.util
import random
import sys
from pathlib import Path

import pytest

from hierarchy_builder import COMPOSITE_ID_BASE, SYM_MODE_LEVELS
from spacing import MIXED_TYPE_SEP

_SCRIPTS = Path(__file__).resolve().parents[2]
_WORKDIR = _SCRIPTS.parent
_NETLISTS = _WORKDIR / "#Netlists"
sys.path.insert(0, str(_WORKDIR / "viewer"))
import drc_checker  # noqa: E402

RULES = drc_checker.load_rules(_WORKDIR / "myPDK" / "gpdk090_device_rules.json")
GRID = 0.005
TOL = 2e-6
SYM_MODE = "balanced"

# Run by default (user, 2026-11-06); every other netlist only with `-m corpus`
# (~41 min, a22_mimo_bulk alone ~34 min).
DEFAULT_NETLISTS = {"a01_adder", "a06_cascode_current_mirror_ota", "a30_telescopic_ota",
                    "m01_comp", "m02_ota1", "sky01_ota1"}

PAIRS = [("SequencePairTopology", "SimulatedAnnealingOptimizer"),
         ("BStarTopology", "SimulatedAnnealingOptimizer"),
         ("PSOTopology", "PSOOptimizer"),
         ("ILPTopology", "ILPOptimizer")]


def _load(filename, name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g011 = _load("011_netlisBlocksGenerator.py", "g011_corpus")
g012 = _load("012_pdkDeviceGenerator.py", "g012_corpus")
o101 = _load("101_placementOptimizer.py", "o101_corpus")
o101.WARMUP_N_RUNS = 0
o101.USE_CONTOUR_BASELINE = False
o101.SA_MAX_ITER = 3000
o101.PSO_CONFIG = o101.PSOConfig(max_iter=300)
o101.RUN_MODE = ""


def _is_sky(netlist: Path) -> bool:
    return "sky130_fd_pr" in netlist.read_text(errors="ignore")


@functools.lru_cache(maxsize=None)
def _generate(netlist: Path) -> dict:
    if _is_sky(netlist):
        return g012.run(str(netlist), 1, pdk_name="sky130", sym_mode=SYM_MODE)
    return g011.run(str(netlist), 1, SYM_MODE)


def _netlists():
    return [pytest.param(p, id=p.stem, marks=() if p.stem in DEFAULT_NETLISTS else pytest.mark.corpus)
            for p in sorted(_NETLISTS.glob("*.sp")) if p.stem[0] in "am" or p.stem.startswith("sky")]


def _expected_nodes(data):
    """Top-level placement nodes the way 101 builds them: one composite per group with
    matching_variants, every other valid block on its own; plus the symmetry axes."""
    blocks = {b["block_id"]: b for b in data["blocks"] if "error" not in b}
    comp = {g["group_id"]: COMPOSITE_ID_BASE + g["group_id"]
            for g in data["groups"] if g.get("block_ids") and g.get("matching_variants")}
    members = {b for g in data["groups"] if g["group_id"] in comp for b in g["block_ids"]}
    nodes = {str(c) for c in comp.values()} | {str(b) for b in blocks if b not in members}

    def node(g):
        if g["group_id"] in comp:
            return str(comp[g["group_id"]])
        m = [b for b in g["block_ids"] if b in blocks]
        return str(m[0]) if len(m) == 1 else None

    by_id = {g["group_id"]: g for g in data["groups"]}
    axes: dict = {}
    for g in data["groups"]:
        sym = g.get("symmetry")
        if not sym or sym["level"] not in SYM_MODE_LEVELS[SYM_MODE]:
            continue
        ax = axes.setdefault(sym["axis_id"], {"self": [], "pairs": []})
        if sym["role"] == "self":
            n = node(g)
            ax["self"] += [n] if n else [str(b) for b in g["block_ids"] if b in blocks]
        elif sym["side"] == "L":
            a, b = node(g), node(by_id[sym["partner"]])
            if a and b:
                ax["pairs"].append((a, b))
    axes = [a for a in axes.values() if 2 * len(a["pairs"]) + len(a["self"]) >= 2]
    return nodes, axes


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: p[0].replace("Topology", ""))
@pytest.mark.parametrize("netlist", _netlists())
def test_corpus_placement_is_legal_symmetric_on_grid(netlist, pair):
    if pair[1] == "ILPOptimizer":
        pytest.importorskip("gurobipy")
    try:
        data = _generate(netlist)
    except ValueError:              # no devices (e.g. a14_fixed_height)
        pytest.skip("netlist has no devices")
    o101.TOPOLOGY, o101.OPTIMIZER = pair
    random.seed(0)
    out = o101.run(copy.deepcopy(data))
    placed = {b: p for b, p in out["placement"]["placed_blocks"].items() if not b.startswith("__")}
    rects = {b: (p["main_bbox"]["x_min"], p["main_bbox"]["y_min"], p["main_bbox"]["x_max"], p["main_bbox"]["y_max"])
             for b, p in placed.items()}
    nodes, axes = _expected_nodes(data)

    # [INV] every placement node exactly once
    assert set(rects) == nodes

    # [DRC] no overlap; gpdk090 spacing only for gpdk090 netlists. A composite's type is
    # its member types joined, as hierarchy_builder.build_composite_blocks names it.
    dtype = {str(b["block_id"]): b.get("device_type", "") for b in data["blocks"]}
    for g in data["groups"]:
        types = sorted({dtype[str(m)] for m in g["block_ids"] if dtype.get(str(m))})
        dtype[str(COMPOSITE_ID_BASE + g["group_id"])] = MIXED_TYPE_SEP.join(types) or "unknown"
    bids = sorted(rects)
    for i, a in enumerate(bids):
        for b in bids[i + 1:]:
            ra, rb = rects[a], rects[b]
            overlap = min(ra[2], rb[2]) - max(ra[0], rb[0]) > TOL and min(ra[3], rb[3]) - max(ra[1], rb[1]) > TOL
            assert not overlap, f"{a} overlaps {b}: {ra} {rb}"
            if not _is_sky(netlist):
                v = drc_checker._check_pair(a, b, ra, rb, dtype[a], dtype[b], 0, 0, RULES)
                assert not v, [x.display_str for x in v]

    # [INV] symmetry: one vertical axis per group, pairs mirrored at equal y
    cx = {b: (r[0] + r[2]) / 2 for b, r in rects.items()}
    for ax in axes:
        centres = [cx[s] for s in ax["self"]] + [(cx[a] + cx[b]) / 2 for a, b in ax["pairs"]]
        assert max(centres) - min(centres) <= TOL, f"axis centres differ: {centres}"
        for a, b in ax["pairs"]:
            assert rects[a][1] == pytest.approx(rects[b][1], abs=TOL), f"pair {a}/{b} not at equal y"

    # [GRID] block origins on the manufacturing grid
    off = {b: r[:2] for b, r in rects.items() if any(abs(v / GRID - round(v / GRID)) > 1e-6 for v in r[:2])}
    assert not off, f"origins off the {GRID} µm grid: {off}"
