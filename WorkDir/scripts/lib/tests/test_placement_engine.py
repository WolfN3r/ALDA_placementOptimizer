"""
Placement engine on small hand-built gpdk090 blocks — tests approved 2026-11-05.

  [INV]  invariant; no stored numbers, so tuning weights / SA parameters never makes these stale
  [7]    coding.md §7: perturb() returns an undo closure that reverses every mutation
  [DRC]  WorkDir/viewer/drc_checker._check_pair — the viewer's DRC (overlap, facing edges, WPE corner)
  [GRID] gpdk090_tech_simple.json manufacturing_grid 0.005 µm (sky130 pdk.json grid is the same)
  [BUG]  regression of a recorded bug (.claude/knowledge/notes/)

Topology / optimizer pairs: SP+SA, B*-tree+SA, PSO+PSO, ILP+ILP (skipped without gurobipy).
"""
import random
import sys
from pathlib import Path

import pytest

from bstar_topology import BStarTopology
from cost_evaluator import CostEvaluator
from pipeline import OptimizationPipeline, build_default_registry
from pso_optimizer import PSOConfig, PSOOptimizer
from pso_topology import PSOTopology
from sa_optimizer import SAConfig, SimulatedAnnealingOptimizer
from seqpair_topology import SequencePairTopology

_WORKDIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_WORKDIR / "viewer"))
import drc_checker  # noqa: E402

RULES = drc_checker.load_rules(_WORKDIR / "myPDK" / "gpdk090_device_rules.json")
GRID = 0.005
TOL = 2e-6          # placed_blocks coordinates are rounded to 1e-6

SA_TOPOLOGIES = [SequencePairTopology, BStarTopology]


# ── inputs ────────────────────────────────────────────────────────────────────

def _block(device_type, *sizes):
    return {"device_type": device_type, "variants": [
        {"main_bbox": {"x_min": 0.0, "y_min": 0.0, "x_max": w, "y_max": h}, "is_used": k == 0,
         "pin_positions": {"d": {"x": w / 2, "y": h / 2}}}
        for k, (w, h) in enumerate(sizes)]}


def _blocks():
    return {
        "1": _block("nmos_rvt", (2.0, 1.5), (1.5, 2.0)),
        "2": _block("nmos_rvt", (2.0, 1.5), (1.5, 2.0)),
        "3": _block("nmos_rvt", (3.0, 1.0), (1.0, 3.0)),
        "4": _block("pmos_rvt", (2.0, 2.0)),
        "5": _block("pmos_rvt", (2.0, 2.0)),
        "6": _block("res_poly", (1.0, 4.0), (4.0, 1.0)),
    }


NETS = [
    {"net_id": "n1", "net_type": "signal", "pins": ["B1_d", "B3_d"]},
    {"net_id": "n2", "net_type": "signal", "pins": ["B2_d", "B3_d"]},
    {"net_id": "n3", "net_type": "signal", "pins": ["B4_d", "B5_d", "B6_d"]},
]

# (a) one pair + one self-symmetric; (b) three self-symmetric on one axis
# [BUG 2026-07-08_ilp-shared-axis-bug]; (c) two pairs + one self-symmetric
# [BUG 2026-07-08_spsa-self-symmetric-axis-bug].
SYM_CASES = {
    "pair_self":   [{"pairs": [["1", "2"]], "self_symmetric": ["3"], "enforce_matching_variants": True}],
    "three_self":  [{"pairs": [], "self_symmetric": ["1", "2", "3"], "enforce_matching_variants": False}],
    "pairs_self":  [{"pairs": [["1", "2"], ["4", "5"]], "self_symmetric": ["3"], "enforce_matching_variants": True}],
}


# ── checks ────────────────────────────────────────────────────────────────────

def _rects(positions, blocks, variant_map):
    out = {}
    for bid, (x, y) in positions.items():
        bb = blocks[bid]["variants"][variant_map.get(bid, 0)]["main_bbox"]
        out[bid] = (x, y, x + bb["x_max"], y + bb["y_max"])
    return out


def _assert_legal(rects, blocks):
    # [INV] every block placed exactly once; [DRC] no overlap, gpdk090 spacing
    assert set(rects) == set(blocks)
    bids = sorted(rects)
    for i, a in enumerate(bids):
        for b in bids[i + 1:]:
            v = drc_checker._check_pair(a, b, rects[a], rects[b],
                                        blocks[a]["device_type"], blocks[b]["device_type"], 0, 0, RULES)
            assert not v, [x.display_str for x in v]


def _assert_symmetric(rects, sym_groups):
    # [INV] per group: pair centres mirror around one vertical axis at equal y,
    # self-symmetric centres lie on it
    for g in sym_groups:
        cx = {b: (r[0] + r[2]) / 2 for b, r in rects.items()}
        axes = [cx[s] for s in g["self_symmetric"]] + [(cx[a] + cx[b]) / 2 for a, b in g["pairs"]]
        assert max(axes) - min(axes) <= TOL, f"axes differ: {axes}"
        for a, b in g["pairs"]:
            assert rects[a][1] == pytest.approx(rects[b][1], abs=TOL)
            assert rects[a][2] - rects[a][0] == pytest.approx(rects[b][2] - rects[b][0], abs=TOL)


def _assert_on_grid(rects):
    # [GRID] every block origin on the manufacturing grid
    off = {b: r[:2] for b, r in rects.items()
           if any(abs(v / GRID - round(v / GRID)) > 1e-6 for v in r[:2])}
    assert not off, f"origins off the {GRID} µm grid: {off}"


# ── 1: perturb / undo and copy / restore (SP, B*-tree) ────────────────────────

@pytest.mark.parametrize("topo_cls", SA_TOPOLOGIES, ids=lambda c: c.__name__)
@pytest.mark.parametrize("case", SYM_CASES)
def test_perturb_undo_restores_exact_state(topo_cls, case):
    # [7] perturb + undo must leave decode() and the variant map unchanged, every time
    random.seed(1)
    blocks = _blocks()
    topo = topo_cls(blocks, NETS, sym_groups=SYM_CASES[case])
    topo.seed(blocks, mode="random")
    before = (topo.decode(), topo.get_variant_map())
    for i in range(300):
        undo = topo.perturb(1.0)
        undo()
        assert (topo.decode(), topo.get_variant_map()) == before, f"move {i}"


@pytest.mark.parametrize("topo_cls", SA_TOPOLOGIES, ids=lambda c: c.__name__)
def test_copy_restore_state_round_trip(topo_cls):
    # TopologyBase contract: restore_state(copy_state()) brings back the saved placement
    random.seed(2)
    blocks = _blocks()
    topo = topo_cls(blocks, NETS, sym_groups=SYM_CASES["pair_self"])
    topo.seed(blocks, mode="random")
    saved, expected = topo.copy_state(), (topo.decode(), topo.get_variant_map())
    for _ in range(50):
        topo.perturb(1.0)
    topo.restore_state(saved)
    assert (topo.decode(), topo.get_variant_map()) == expected


# ── 2 + 3: every reachable SP / B*-tree state is legal and symmetric ──────────

@pytest.mark.parametrize("topo_cls", SA_TOPOLOGIES, ids=lambda c: c.__name__)
@pytest.mark.parametrize("case", SYM_CASES)
def test_random_moves_stay_legal_and_symmetric(topo_cls, case):
    random.seed(3)
    blocks = _blocks()
    topo = topo_cls(blocks, NETS, sym_groups=SYM_CASES[case])
    topo.seed(blocks, mode="random")
    for i in range(300):
        topo.perturb(1.0)
        rects = _rects(topo.decode(), blocks, topo.get_variant_map())
        _assert_legal(rects, blocks)
        _assert_symmetric(rects, SYM_CASES[case])


# ── 7: SA optimizer ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("topo_cls", SA_TOPOLOGIES, ids=lambda c: c.__name__)
def test_sa_returns_its_best_state(topo_cls):
    # [INV] best_cost never exceeds the start cost, and best_state reproduces best_cost
    random.seed(4)
    blocks = _blocks()
    topo = topo_cls(blocks, NETS, sym_groups=SYM_CASES["pair_self"])
    topo.seed(blocks, mode="random")
    ev = CostEvaluator(blocks, NETS, init_area=1.0, init_wl=1.0, use_power_rails=False)
    start = ev.evaluate(topo.decode(), topo.get_variant_map())
    res = SimulatedAnnealingOptimizer(topo, ev, SAConfig(initial_temp=1.0, max_iterations=3000)).run()
    assert res.best_cost <= start + 1e-12
    topo.restore_state(res.best_state)
    assert ev.evaluate(topo.decode(), topo.get_variant_map()) == pytest.approx(res.best_cost, abs=1e-9)


# ── 2 + 3 + 6 + grid: full pipeline result of every topology / optimizer pair ─

def _optimizer_kwargs(opt_cls):
    if opt_cls is PSOOptimizer:
        return {"pso_config": PSOConfig(max_iter=300)}
    if opt_cls.__name__ == "ILPOptimizer":
        pytest.importorskip("gurobipy")
        from ilp_optimizer import GurobiParams
        return {"gurobi_params": GurobiParams(verbose=False)}
    return {}


PAIRS = build_default_registry().supported_pairs()


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f"{p[0].__name__}+{p[1].__name__}")
@pytest.mark.parametrize("case", SYM_CASES)
def test_pipeline_result_is_legal_symmetric_on_grid(pair, case):
    topo_cls, opt_cls = pair
    random.seed(5)
    blocks = _blocks()
    res = OptimizationPipeline(
        topo_cls, opt_cls, sa_config=SAConfig(max_iterations=3000), sym_groups=SYM_CASES[case],
        optimizer_kwargs=_optimizer_kwargs(opt_cls),
    ).run(blocks, NETS)
    assert res.status == "success", res.error_message
    rects = {b: (p["main_bbox"]["x_min"], p["main_bbox"]["y_min"], p["main_bbox"]["x_max"], p["main_bbox"]["y_max"])
             for b, p in res.placed_blocks.items() if not b.startswith("__")}
    _assert_legal(rects, blocks)
    _assert_symmetric(rects, SYM_CASES[case])
    _assert_on_grid(rects)
