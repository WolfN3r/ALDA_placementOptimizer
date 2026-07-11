"""
B*-tree SA warm-start placer.

Runs a short SimulatedAnnealingOptimizer on a throwaway BStarTopology to
produce a 2D approximate layout {bid: (x, y)}. The SA run is intentionally
short (~30% of a full SA budget) — it only needs to hand ILP a reasonable
2D arrangement, not a fully converged result.

B*-tree decode is DRC-clean by construction (the contour placement enforces
spacing), so the output is returned as-is — no additional row-packing.
"""
from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from warmup_manager import WarmupStrategy, register_strategy
from log_setup      import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

BSTAR_WARMUP_ITER_FRACTION = 60   # max_iterations = epoch_size * this (~30% of a full run)
BSTAR_WARMUP_MIN_EPOCH     = 50   # epoch_size floor for very small netlists

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

class BStarWarmup(WarmupStrategy):
    """
    Short B*-tree SA run used purely as an ILP warm start.
    Operates on the merged blocks dict (composite group blocks + ungrouped
    individual blocks) — same schema as a standalone B*-tree run.
    """

    def __init__(self, sym_groups: list | None = None) -> None:
        self._sym_groups  = sym_groups or []
        self._variant_map: dict[str, int] = {}

    def get_variant_map(self) -> dict[str, int]:
        return self._variant_map

    def run_single(
        self,
        blocks: dict,
        nets:   list,
        seed:   int,
    ) -> dict[str, tuple[float, float, float, float]]:
        import random
        from bstar_topology import BStarTopology
        from cost_evaluator import CostEvaluator
        from sa_optimizer   import (
            SimulatedAnnealingOptimizer, SAConfig,
            calibrate_initial_temperature,
        )
        from ilp_optimizer  import _variant_dims

        random.seed(seed)

        valid_blocks = {bid: b for bid, b in blocks.items() if "error" not in b}
        if not valid_blocks:
            return {}

        topo = BStarTopology(valid_blocks, nets, sym_groups=self._sym_groups or None)
        topo.seed(valid_blocks, mode="random")

        # Scale-neutral evaluator: SA only needs relative cost deltas to
        # accept/reject moves, not absolute normalization.
        evaluator = CostEvaluator(valid_blocks, nets, 1.0, 1.0)

        epoch_size = max(len(valid_blocks) * 8, BSTAR_WARMUP_MIN_EPOCH)
        sa_cfg = SAConfig(
            max_iterations = epoch_size * BSTAR_WARMUP_ITER_FRACTION,
            epoch_size     = epoch_size,
        )
        sa_cfg.initial_temp = calibrate_initial_temperature(topo, evaluator)

        result = SimulatedAnnealingOptimizer(topo, evaluator, sa_cfg).run()
        topo.restore_state(result.best_state)

        self._variant_map = topo.get_variant_map()
        final_pos = topo.decode()   # {bid: (x, y)} — DRC-clean, used as-is

        out: dict[str, tuple[float, float, float, float]] = {}
        for bid, (x, y) in final_pos.items():
            dims = _variant_dims(valid_blocks[bid])
            vidx = self._variant_map.get(bid, 0)
            w, h = dims[vidx] if vidx < len(dims) else dims[0]
            out[bid] = (x, y, w, h)

        logger.debug(
            "BStarWarmup: placed %d blocks (seed=%d) cost=%.4f",
            len(out), seed, result.best_cost,
        )
        return out


register_strategy("bstar", BStarWarmup)
