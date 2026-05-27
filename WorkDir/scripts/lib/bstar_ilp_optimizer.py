"""
B*-tree SA + ILP two-stage placement optimizer.

Stage 1 — B*-tree SA warm-start:
  Runs a SimulatedAnnealingOptimizer on a temporary BStarTopology to produce a
  2D approximate layout {bid: (x, y)}.  The SA run is intentionally short
  (default max_iter ≈ epoch_size × 60) — we need a good 2D arrangement, not a
  fully converged result.  The ILP stage resolves remaining violations.

Stage 2 — ILP fine-tuning:
  Passes the B*-tree layout as warm_positions to _solve_mip().  _r_hints()
  derives r-flag direction binaries from the 2D B*-tree positions, which are
  far more informative than the flat row-pack (all y=0) used by the standalone
  ILPOptimizer.  ILP then enforces hard DRC constraints, exact symmetry, and
  multi-variant selection on top of the B*-tree approximate placement.

Pipeline interface is identical to ILPOptimizer:
  - Constructor: (topology, evaluator, cfg, observer=None,
                  bstar_sa_config=None, gurobi_params=None)
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


class BStarILPOptimizer:
    """
    Two-stage optimizer: B*-tree SA global search → ILP local fine-tuning.

    Uses ILPTopology as its topology (same state structure).
    The B*-tree SA stage runs on a throwaway BStarTopology so the final
    ILPTopology state is set once, atomically, after the ILP stage completes.
    """

    def __init__(
        self,
        topology:        Any,
        evaluator:       Any,
        cfg:             Any,                        # SAConfig — required by pipeline, not used
        observer:        Any            = None,
        bstar_sa_config: Any | None     = None,      # SAConfig for B*-tree warm-start
        gurobi_params:   GurobiParams | None = None,
    ) -> None:
        self._topo            = topology
        self._evaluator       = evaluator
        self._bstar_sa_config = bstar_sa_config
        self._gurobi_params   = gurobi_params

    def run(self) -> Any:
        from sa_optimizer import SAResult
        try:
            return self._run_two_stage()
        except Exception as exc:
            logger.error("BStarILPOptimizer failed: %s", exc, exc_info=True)
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
            logger.error("BStarILPOptimizer: no valid blocks to place")
            return SAResult(
                best_state   = self._topo.copy_state(),
                best_cost    = float("inf"),
                n_iterations = 0,
                termination  = "infeasible",
            )

        if len(bids) > ILP_LARGE_N_WARN:
            logger.warning(
                "B*-tree+ILP: %d blocks exceeds recommended limit of %d — ILP stage may be slow",
                len(bids), ILP_LARGE_N_WARN,
            )

        # Stage 1: B*-tree SA warm-start
        bstar_positions = self._run_bstar_stage(blocks, nets, sym_groups)

        # Stage 2: ILP fine-tuning.
        # B*-tree output is DRC-clean (the contour already enforces spacing), but
        # _fdgd_row_pack gives Gurobi a tight 1D incumbent with a known feasible
        # cost bound, while the raw 2D positions feed the r-var direction hints.
        bstar_ordered_warm = _fdgd_row_pack(bids, blocks, bstar_positions)

        c_area = self._evaluator._w.area_weight
        c_wl   = self._evaluator._w.wirelength_weight
        params = self._gurobi_params or GurobiParams()

        positions, variant_map, termination = _solve_mip(
            bids, blocks, nets, sym_groups,
            c_area, c_wl,
            bstar_ordered_warm,               # B*-tree-ordered row-pack → Gurobi incumbent
            params,
            hint_positions=bstar_positions,   # raw B*-tree 2D layout → r-var direction hints
        )

        self._topo.set_solution(positions, variant_map)
        cost = self._evaluator.evaluate(positions)
        best_state = self._topo.copy_state()

        logger.info(
            "B*-tree+ILP finished: termination=%s  cost=%.4f  n_blocks=%d",
            termination, cost, len(bids),
        )
        return SAResult(
            best_state     = best_state,
            best_cost      = cost,
            n_iterations   = 1,
            accept_history = [],
            termination    = termination,
        )

    def _run_bstar_stage(
        self,
        blocks:     dict,
        nets:       list,
        sym_groups: list,
    ) -> dict[str, tuple[float, float]]:
        """Run B*-tree SA on a throwaway topology; return best decoded positions."""
        from bstar_topology import BStarTopology
        from sa_optimizer import (
            SimulatedAnnealingOptimizer, SAConfig,
            calibrate_initial_temperature,
        )

        n_blocks   = len(blocks)
        epoch_size = max(n_blocks * 8, 50)

        sa_cfg = self._bstar_sa_config
        if sa_cfg is None:
            # ~30 % of a full SA budget: enough for a good 2D seed, not full convergence
            sa_cfg = SAConfig(
                max_iterations = epoch_size * 60,
                epoch_size     = epoch_size,
            )

        topo = BStarTopology(blocks, nets, sym_groups)
        topo.seed(blocks, mode="random")

        sa_cfg.initial_temp = calibrate_initial_temperature(topo, self._evaluator)

        result = SimulatedAnnealingOptimizer(topo, self._evaluator, sa_cfg).run()
        topo.restore_state(result.best_state)
        positions = topo.decode()

        logger.info(
            "B*-tree SA warm start complete: %d blocks placed  cost=%.4f",
            len(positions), result.best_cost,
        )
        return positions
