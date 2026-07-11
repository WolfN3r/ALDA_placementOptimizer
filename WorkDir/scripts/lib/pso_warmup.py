"""
PSO warm-start placer.

Runs a short PSOOptimizer swarm on a throwaway PSOTopology to produce a 2D
approximate layout {bid: (x, y)}. The swarm is intentionally short
(max_iter=500 default) — it only needs to hand ILP a reasonable 2D
arrangement, not a fully converged result.

The raw PSO output is returned as-is (no row-packing / post-processing):
ILP's own MILP solve already enforces hard DRC non-overlap, so any residual
PSO overlap is resolved by the solver itself, not by this warm-start stage.
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

PSO_WARMUP_SWARM_SIZE = 20     # smaller swarm than a full standalone PSO run
PSO_WARMUP_MAX_ITER   = 500    # short budget — approximate 2D arrangement only
PSO_WARMUP_USE_CORP_INIT = True

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

class PSOWarmup(WarmupStrategy):
    """
    Short PSO run used purely as an ILP warm start.
    Operates on the merged blocks dict (composite group blocks + ungrouped
    individual blocks) — same schema as a standalone PSO run.
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
        from pso_topology  import PSOTopology
        from pso_optimizer import PSOOptimizer, PSOConfig
        from cost_evaluator import CostEvaluator
        from sa_optimizer   import SAConfig
        from ilp_optimizer  import _variant_dims

        random.seed(seed)

        valid_blocks = {bid: b for bid, b in blocks.items() if "error" not in b}
        if not valid_blocks:
            return {}

        topo = PSOTopology(valid_blocks, nets, sym_groups=self._sym_groups or None)
        topo.seed(valid_blocks, mode="random")

        # Scale-neutral evaluator: PSO only needs relative cost deltas to rank
        # particles, not absolute normalization.
        evaluator = CostEvaluator(valid_blocks, nets, 1.0, 1.0)

        pso_cfg = PSOConfig(
            swarm_size    = PSO_WARMUP_SWARM_SIZE,
            max_iter      = PSO_WARMUP_MAX_ITER,
            use_corp_init = PSO_WARMUP_USE_CORP_INIT,
        )
        PSOOptimizer(topo, evaluator, SAConfig(), pso_config=pso_cfg).run()

        self._variant_map = topo.get_variant_map()
        final_pos = topo.decode()   # {bid: (x, y)} — used as-is, no row-pack

        out: dict[str, tuple[float, float, float, float]] = {}
        for bid, (x, y) in final_pos.items():
            dims = _variant_dims(valid_blocks[bid])
            vidx = self._variant_map.get(bid, 0)
            w, h = dims[vidx] if vidx < len(dims) else dims[0]
            out[bid] = (x, y, w, h)

        logger.debug("PSOWarmup: placed %d blocks (seed=%d)", len(out), seed)
        return out


register_strategy("pso", PSOWarmup)
