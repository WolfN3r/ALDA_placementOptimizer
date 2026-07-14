"""
Shared, a-priori cost-normalization reference for CostEvaluator.

compute_contour_baseline() runs ContourWarmup N times in parallel (reusing
WarmupManager's ProcessPoolExecutor fan-out), keeps the median-cost
placement, and reports its true (unnormalized) area/HPWL as init_area/init_wl.
Callers (pipeline.py, solver_picker.py) pass the resulting ReferenceBaseline
into every optimizer run in a given invocation, so every (topology, optimizer)
pair is scored against the same denominator instead of its own random-seeded
start — see .claude/plans/contour_reference_baseline.md.

Median (not best) is deliberate: this reference is a "decent, unremarkable
placement" yardstick, not a target to beat by construction — using the best
of N would bias every optimizer's cost slightly worse purely by picking a
stronger denominator. WarmupManager's own best-of-N selection (used for ILP
warm-starts elsewhere) is untouched; this module implements its own median
pick directly on WarmupManager's sorted results instead.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from warmup_manager import WarmupConfig, WarmupManager
from pipeline        import _bbox_area, _hpwl
from log_setup       import get_logger

DEBUG = False
logger = get_logger(__name__, DEBUG)


# =============================================================================
# CONSTANTS
# =============================================================================
_NEUTRAL_AREA = 1.0   # scale-neutral evaluator divisor — ranks contour seeds by raw physical cost
_NEUTRAL_WL   = 1.0


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ReferenceBaseline:
    init_area:   float
    init_wl:     float
    positions:   dict[str, tuple[float, float]] = field(default_factory=dict)
    variant_map: dict[str, int]                 = field(default_factory=dict)


# =============================================================================
# BASELINE COMPUTATION
# =============================================================================

def compute_contour_baseline(
    blocks:          dict,
    nets:            list,
    n_runs:          int   = 9,
    master_seed:     int   = 42,
    use_power_rails: bool  = False,
) -> ReferenceBaseline:
    """Median-of-N parallel ContourWarmup placements, used as the shared cost reference.

    The N seeds are ranked on raw physical merit (scale-neutral evaluator,
    init_area = init_wl = 1.0) rather than against each other's normalization,
    then the true middle one is picked directly from the ascending-sorted
    list (index n//2 — for n_runs=9, that's the 5th of 9 runs), bypassing
    WarmupManager's own best-of-N selection (index 0), which exists for a
    different purpose (ILP warm-start seeding elsewhere).
    """
    cfg = WarmupConfig(strategy="contour", n_runs=n_runs, master_seed=master_seed)
    mgr = WarmupManager(cfg)
    _, sorted_results, _ = mgr.run(blocks, nets, _NEUTRAL_AREA, _NEUTRAL_WL)

    median = sorted_results[len(sorted_results) // 2]
    positions_2d = {bid: (v[0], v[1]) for bid, v in median.positions.items()}
    variant_map  = median.variant_map

    init_area = _bbox_area(positions_2d, blocks, variant_map)
    init_wl   = _hpwl(
        positions_2d, blocks, nets,
        use_power_rails=use_power_rails, variant_map=variant_map,
    )

    logger.info(
        "compute_contour_baseline: median of %d seeds (run %d, seed %d) → area=%.2f  hpwl=%.2f",
        n_runs, median.run_index, median.seed, init_area, init_wl,
    )

    return ReferenceBaseline(
        init_area   = max(init_area, 1e-9),
        init_wl     = max(init_wl, 0.0),
        positions   = positions_2d,
        variant_map = variant_map,
    )
