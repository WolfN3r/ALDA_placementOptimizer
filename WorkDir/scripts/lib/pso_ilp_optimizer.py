"""
PSO+ILP two-stage placement optimizer.

Stage 1 — PSO warm-start:
  Runs a PSOOptimizer swarm on a temporary PSOTopology to produce a 2D approximate
  layout {bid: (x, y)}.  The swarm is intentionally short (max_iter=500 default) —
  we need a good 2D arrangement, not a fully converged result.

Stage 2 — ILP fine-tuning:
  Passes the PSO layout as warm_positions to _solve_mip().  _r_hints() derives
  r-flag direction binaries from the 2D PSO positions, which are far more
  informative than the flat row-pack (all y=0) used by the standalone ILPOptimizer.
  ILP then enforces hard DRC constraints, exact symmetry, and multi-variant
  selection on top of the PSO approximate placement.

Pipeline interface is identical to ILPOptimizer:
  - Constructor: (topology, evaluator, cfg, observer=None, pso_config=None,
                  gurobi_params=None)
  - run() → SAResult
  - Topology: ILPTopology  (state is updated via topology.set_solution)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from ilp_optimizer import _solve_mip, _fdgd_row_pack, GurobiParams, ILP_LARGE_N_WARN
from log_setup import get_logger

DEBUG = False
logger = get_logger(__name__, DEBUG)


class PSOILPOptimizer:
    """
    Two-stage optimizer: PSO global search → ILP local fine-tuning.

    Uses ILPTopology as its topology (same state structure as PSOTopology).
    The PSO stage runs on a throwaway PSOTopology so the final ILPTopology
    state is set once, atomically, after the ILP stage completes.
    """

    def __init__(
        self,
        topology:      Any,
        evaluator:     Any,
        cfg:           Any,               # SAConfig — required by pipeline, not used
        observer:      Any           = None,
        pso_config:    Any | None    = None,   # PSOConfig — lazy import
        gurobi_params: GurobiParams | None = None,
    ) -> None:
        self._topo          = topology
        self._evaluator     = evaluator
        self._pso_config    = pso_config
        self._gurobi_params = gurobi_params

    def run(self) -> Any:
        from sa_optimizer import SAResult
        try:
            return self._run_two_stage()
        except Exception as exc:
            logger.error("PSOILPOptimizer failed: %s", exc, exc_info=True)
            return SAResult(
                best_state   = self._topo.copy_state(),
                best_cost    = float("inf"),
                n_iterations = 0,
                termination  = "failed",
            )

    def _run_two_stage(self) -> Any:
        from sa_optimizer import SAResult

        blocks     = self._topo._blocks
        nets       = self._topo._nets
        sym_groups = self._topo._sym_groups
        bids       = list(blocks.keys())

        if not bids:
            logger.error("PSOILPOptimizer: no valid blocks to place")
            return SAResult(
                best_state   = self._topo.copy_state(),
                best_cost    = float("inf"),
                n_iterations = 0,
                termination  = "infeasible",
            )

        if len(bids) > ILP_LARGE_N_WARN:
            logger.warning(
                "PSO+ILP: %d blocks exceeds recommended limit of %d — ILP stage may be slow",
                len(bids), ILP_LARGE_N_WARN,
            )

        # Stage 1: PSO warm-start
        pso_positions = self._run_pso_stage(blocks, nets, sym_groups)

        # Stage 2: ILP fine-tuning.
        # PSO output may have residual overlaps — Gurobi cannot accept an infeasible
        # layout as an incumbent, and wrong r-flag hints from overlapping blocks slow
        # B&B down.  Fix: row-pack blocks in PSO x-order to produce a DRC-clean
        # incumbent, but keep raw PSO positions for r-var direction hints.
        # Gurobi gets a tight initial upper bound (from the DRC-clean row-pack) AND
        # better directional hints (from the 2D PSO layout).
        pso_ordered_warm = _fdgd_row_pack(bids, blocks, pso_positions)

        c_area = self._evaluator._w.area_weight
        c_wl   = self._evaluator._w.wirelength_weight
        params = self._gurobi_params or GurobiParams()

        positions, variant_map, termination = _solve_mip(
            bids, blocks, nets, sym_groups,
            c_area, c_wl,
            pso_ordered_warm,            # DRC-clean PSO-ordered row-pack → Gurobi incumbent
            params,
            hint_positions=pso_positions,  # raw PSO 2D layout → r-var direction hints
        )

        self._topo.set_solution(positions, variant_map)
        cost = self._evaluator.evaluate(positions)
        best_state = self._topo.copy_state()

        logger.info(
            "PSO+ILP finished: termination=%s  cost=%.4f  n_blocks=%d",
            termination, cost, len(bids),
        )
        return SAResult(
            best_state     = best_state,
            best_cost      = cost,
            n_iterations   = 1,
            accept_history = [],
            termination    = termination,
        )

    def _run_pso_stage(
        self,
        blocks:     dict,
        nets:       list,
        sym_groups: list,
    ) -> dict[str, tuple[float, float]]:
        """Run PSO on a temporary topology; return decoded positions."""
        from pso_topology import PSOTopology
        from pso_optimizer import PSOOptimizer, PSOConfig
        from sa_optimizer  import SAConfig

        # Reduced iteration count: PSO only needs an approximate 2D arrangement,
        # not a fully converged result.  The ILP stage fixes remaining violations.
        pso_cfg = self._pso_config or PSOConfig(max_iter=500, swarm_size=20, use_fdgd_init=True)

        topo = PSOTopology(blocks, nets, sym_groups)
        topo.seed(blocks, mode="random")
        PSOOptimizer(topo, self._evaluator, SAConfig(), pso_config=pso_cfg).run()
        positions = topo.decode()

        logger.info("PSO warm start complete: %d blocks placed", len(positions))
        return positions
