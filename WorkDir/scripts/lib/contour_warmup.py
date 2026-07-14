"""
Greedy skyline (contour-line) warm-start placer.

Adapted from ALDA_placementAnalyzer/scripts/03_initial_placer.py.
Places blocks in random order onto a growing skyline contour, using
DRC-aware spacing from spacing.py for clearance checks.

Each call with the same seed produces exactly the same placement.
Different seeds produce different block orderings and variant choices,
giving the WarmupManager diversity across N parallel runs.

Composite / grouped blocks are already atomic units entering this stage;
they carry their own device_type and variants and are treated like any
other block.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spacing        import compute_block_spacing
from warmup_manager import WarmupStrategy, register_strategy
from log_setup      import get_logger

DEBUG = False
logger = get_logger(__name__, DEBUG)


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _get_block_dims(block: dict, variant_idx: int) -> tuple[float, float]:
    variants = block.get("variants", [])
    if not variants:
        return 0.0, 0.0
    v  = variants[variant_idx]
    bb = v.get("main_bbox", {})
    return bb.get("x_max", 0.0), bb.get("y_max", 0.0)


def _y_floor(
    bid:     str,
    w:       float,
    x_try:   float,
    blocks:  dict,
    placed:  list[tuple[str, float, float, float, float]],
) -> float:
    """
    Minimum y such that block bid (width=w) placed at x=x_try does not
    violate DRC spacing against any already-placed block.

    placed entries: (p_bid, xp, yp, wp, hp)
    """
    y_min = 0.0
    new_block = blocks[bid]
    for (p_bid, xp, yp, wp, hp) in placed:
        sp = compute_block_spacing(blocks[p_bid], new_block)
        sx, sy = sp.x_spacing, sp.y_spacing
        # Check whether new block and placed block are within x-spacing of each
        # other (i.e. they would overlap or violate x clearance if stacked).
        x_overlap = x_try < xp + wp + sx and x_try + w + sx > xp
        if x_overlap:
            y_min = max(y_min, yp + hp + sy)
    return y_min


def _candidate_xs(
    bid:    str,
    w:      float,
    blocks: dict,
    placed: list[tuple[str, float, float, float, float]],
) -> list[float]:
    """
    Candidate x-positions to try for the new block: origin plus one position
    flush to the right of each placed block (with DRC x-spacing).
    """
    candidates = [0.0]
    new_block = blocks[bid]
    for (p_bid, xp, yp, wp, hp) in placed:
        sx = compute_block_spacing(blocks[p_bid], new_block).x_spacing
        candidates.append(xp + wp + sx)
    return candidates


def _score(x: float, y: float, w: float, h: float) -> float:
    """Bounding-box area proxy: penalises large or non-square placements."""
    return (x + w) * (y + h)


# =============================================================================
# CONTOUR WARMUP STRATEGY
# =============================================================================

class ContourWarmup(WarmupStrategy):
    """
    Greedy skyline placer.

    For each block (in random order):
      1. Try a set of candidate x-positions (origin + right-edge of each placed block).
      2. For each candidate x, find the minimum DRC-clean y using _y_floor().
      3. Place at the (x, y) that minimises the bounding-box area score.
    """

    def __init__(self) -> None:
        self._trace_samples: list[dict] = []

    def get_trace_samples(self) -> list[dict]:
        return self._trace_samples

    def run_single(
        self,
        blocks: dict,
        nets:   list,
        seed:   int,
        t0:     float | None = None,
        trace:  bool = False,
        init_area: float = 1.0,
        init_wl:   float = 1.0,
    ) -> dict[str, tuple[float, float, float, float]]:
        bids = [b for b in blocks if "error" not in blocks[b]]
        if not bids:
            return {}

        rng = random.Random(seed)

        # Randomly pick one variant per block (or composite group)
        variant_choices: dict[str, int] = {}
        block_dims:      dict[str, tuple[float, float]] = {}
        for bid in sorted(bids):   # sorted for stable RNG consumption order
            variants = blocks[bid].get("variants", [])
            n_v = len(variants) if variants else 1
            idx = rng.randrange(n_v) if n_v > 1 else 0
            variant_choices[bid] = idx
            block_dims[bid] = _get_block_dims(blocks[bid], idx)

        # Shuffle determines placement order; this is the source of diversity
        rng.shuffle(bids)

        # Tracing (when enabled): log the shared-CostEvaluator breakdown on
        # the *partial* placement after each block is placed. CostEvaluator's
        # bbox/AR terms tolerate a partial positions dict directly, and HPWL
        # skips any net with fewer than 2 placed pins — so this gives a real
        # N-block-point curve, not just a start/end pair.
        #
        # Normalized against the pipeline's real init_area/init_wl (not 1.0/1.0)
        # so the "cost" field stays on the same scale as the ILP-optimizer
        # samples appended after this warmup phase in the merged trace file —
        # this evaluator only feeds the trace, never a placement decision, so
        # rescaling it has no effect on ContourWarmup's actual behavior.
        evaluator = None
        trace_obs = None
        if trace and t0 is not None:
            from cost_evaluator import CostEvaluator
            from cost_trace import TraceObserver
            evaluator = CostEvaluator(blocks, nets, init_area, init_wl)
            trace_obs = TraceObserver("contour_warmup", t0, path="", auto_flush=False)

        placed: list[tuple[str, float, float, float, float]] = []
        positions: dict[str, tuple[float, float, float, float]] = {}
        step = 0

        for bid in bids:
            w, h = block_dims[bid]
            if w == 0.0 or h == 0.0:
                logger.warning("ContourWarmup: block %s has zero dimension, skipping", bid)
                continue

            if not placed:
                # First block always goes to the origin
                positions[bid] = (0.0, 0.0, w, h)
                placed.append((bid, 0.0, 0.0, w, h))
            else:
                best_x    = 0.0
                best_y    = _y_floor(bid, w, 0.0, blocks, placed)
                best_score = _score(best_x, best_y, w, h)

                for x_try in _candidate_xs(bid, w, blocks, placed):
                    y_try = _y_floor(bid, w, x_try, blocks, placed)
                    s     = _score(x_try, y_try, w, h)
                    if s < best_score:
                        best_score = s
                        best_x     = x_try
                        best_y     = y_try

                positions[bid] = (best_x, best_y, w, h)
                placed.append((bid, best_x, best_y, w, h))

            if trace_obs is not None:
                positions_2d = {b: (v[0], v[1]) for b, v in positions.items()}
                trace_obs.record(step, evaluator.evaluate_breakdown(positions_2d, variant_choices))
                step += 1

        self._trace_samples = trace_obs.samples if trace_obs is not None else []

        logger.debug(
            "ContourWarmup: placed %d blocks (seed=%d)", len(positions), seed
        )
        return positions


# Register this strategy so WarmupManager._resolve_strategy("contour") works
register_strategy("contour", ContourWarmup)
