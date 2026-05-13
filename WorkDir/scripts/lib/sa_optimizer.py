"""
Simulated Annealing optimizer — topology-agnostic.

Operates on any topology that implements TopologyBase + SAMixin.
Temperature schedule follows Huang 1986 adaptive cooling.
"""
from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cost_evaluator import CostEvaluator
    from topology_base import TopologyBase, SAMixin

# =============================================================================
# CONSTANTS
# =============================================================================
_CALIBRATION_RUNS    = 100    # random perturbations for auto-calibration
_CALIBRATION_TARGET  = 0.80   # target acceptance rate at initial temperature

_ACCEPT_HOT    = 0.90   # acceptance rate above which cooling is fast
_ACCEPT_LOW    = 0.10   # acceptance rate threshold for slow fine-tuning phase
_REHEAT_THRESH = 0.03   # acceptance rate below which reheating triggers

_ALPHA_HOT     = 0.95   # cooling factor — exploration phase
_ALPHA_NORMAL  = 0.97   # cooling factor — moderate phase
_ALPHA_COOL    = 0.99   # cooling factor — fine-tuning phase

_REHEAT_FACTOR = 1.30   # multiply T by this on reheat
_REHEAT_CAP    = 0.30   # reheat ceiling as fraction of initial_temp
_MAX_REHEATS   = 5


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SAConfig:
    initial_temp:     float = 0.0      # 0.0 → auto-calibrated by SolverPicker
    final_temp:       float = 1e-4
    max_iterations:   int   = 0        # 0 → computed from epoch_size at run time
    stagnation_limit: int   = 15       # epochs without improvement before reheat
    epoch_size:       int   = 0        # 0 → computed as max(n_blocks × 8, 50)
    alpha_hot:        float = _ALPHA_HOT
    alpha_normal:     float = _ALPHA_NORMAL
    alpha_cool:       float = _ALPHA_COOL
    high_accept:      float = _ACCEPT_HOT
    low_accept:       float = _ACCEPT_LOW
    reheat_thresh:    float = _REHEAT_THRESH
    reheat_factor:    float = _REHEAT_FACTOR
    max_reheats:      int   = _MAX_REHEATS


@dataclass
class SAResult:
    best_state:     Any
    best_cost:      float
    n_iterations:   int
    accept_history: list[float] = field(default_factory=list)
    termination:    str = "max_iter"


# =============================================================================
# OBSERVERS
# =============================================================================

class NullObserver:
    """Default observer — zero overhead, no I/O."""
    def on_improvement(self, iteration: int, cost: float, positions: dict) -> None:
        pass

    def on_termination(
        self, reason: str, n_iterations: int, best_cost: float, best_positions: dict
    ) -> None:
        pass


class ConsoleObserver:
    """Writes epoch summaries to stderr only — never stdout."""
    def __init__(self, report_interval: int = 5000) -> None:
        self._interval = report_interval

    def on_improvement(self, iteration: int, cost: float, positions: dict) -> None:
        if iteration % self._interval == 0:
            print(f"[SA] iter={iteration:7d}  cost={cost:.5f}", file=sys.stderr)

    def on_termination(
        self, reason: str, n_iterations: int, best_cost: float, best_positions: dict
    ) -> None:
        print(
            f"[SA] done  reason={reason}  iters={n_iterations}  best={best_cost:.5f}",
            file=sys.stderr,
        )


# =============================================================================
# OPTIMIZER
# =============================================================================

class SimulatedAnnealingOptimizer:
    """
    SA optimizer loop. Requires topology to implement TopologyBase + SAMixin.
    No topology-specific logic lives here — only the Metropolis loop.
    """

    def __init__(
        self,
        topology: Any,
        evaluator: "CostEvaluator",
        config: SAConfig,
        observer: Any = None,
    ) -> None:
        self._topo     = topology
        self._eval     = evaluator
        self._cfg      = config
        self._observer = observer or NullObserver()

    # ------------------------------------------------------------------
    def run(self) -> SAResult:
        cfg   = self._cfg
        topo  = self._topo
        n_blocks = len(getattr(topo, "_blocks", {}))

        epoch_size = cfg.epoch_size or max(n_blocks * 8, 50)
        max_iter   = cfg.max_iterations or epoch_size * 200

        temp  = cfg.initial_temp
        if temp <= 0.0:
            raise ValueError("SAConfig.initial_temp must be > 0. Run calibration first.")

        positions     = topo.decode()
        current_cost  = self._eval.evaluate(positions)
        best_cost     = current_cost
        best_state    = topo.copy_state()
        best_positions = positions

        accept_hist:   list[float] = []
        accepted       = 0
        attempted      = 0
        stagnant_epochs = 0
        n_reheats      = 0
        iteration      = 0

        while iteration < max_iter and temp > cfg.final_temp:
            # Generate pre-computed random values for the epoch to cut Python overhead
            randoms = [random.random() for _ in range(epoch_size)]

            for r in randoms:
                undo = topo.perturb(temp)
                new_positions = topo.decode()
                new_cost = self._eval.evaluate(new_positions)

                delta = new_cost - current_cost
                if delta < 0 or r < math.exp(-delta / temp):
                    current_cost = new_cost
                    accepted += 1
                    if new_cost < best_cost:
                        best_cost      = new_cost
                        best_state     = topo.copy_state()
                        best_positions = new_positions
                        if self._observer:
                            self._observer.on_improvement(iteration, best_cost, best_positions)
                else:
                    undo()

                attempted += 1
                iteration += 1

            # --- epoch boundary: update temperature ---
            rate = accepted / attempted if attempted > 0 else 0.0
            accept_hist.append(rate)
            accepted  = 0
            attempted = 0

            if rate > cfg.high_accept:
                temp *= cfg.alpha_hot
                stagnant_epochs = 0
            elif rate >= cfg.low_accept:
                temp *= cfg.alpha_normal
                stagnant_epochs = 0
            elif rate >= cfg.reheat_thresh:
                temp *= cfg.alpha_cool
                stagnant_epochs += 1
            else:
                stagnant_epochs += 1

            if stagnant_epochs >= cfg.stagnation_limit and n_reheats < cfg.max_reheats:
                temp = min(temp * cfg.reheat_factor, cfg.initial_temp * _REHEAT_CAP)
                n_reheats      += 1
                stagnant_epochs = 0

        reason = (
            "temp_floor" if temp <= cfg.final_temp
            else "stagnation" if stagnant_epochs >= cfg.stagnation_limit
            else "max_iter"
        )
        if self._observer:
            self._observer.on_termination(reason, iteration, best_cost, best_positions)

        return SAResult(
            best_state     = best_state,
            best_cost      = best_cost,
            n_iterations   = iteration,
            accept_history = accept_hist,
            termination    = reason,
        )


# =============================================================================
# CALIBRATION (called by SolverPicker, not by the optimizer itself)
# =============================================================================

def calibrate_initial_temperature(
    topology: Any,
    evaluator: "CostEvaluator",
) -> float:
    """
    Run _CALIBRATION_RUNS random perturbations and derive initial_temp such
    that the acceptance rate at that temperature is _CALIBRATION_TARGET.
    The survey does not count toward the optimization iteration budget.
    """
    ref_positions = topology.decode()
    ref_cost      = evaluator.evaluate(ref_positions)

    deltas: list[float] = []
    for _ in range(_CALIBRATION_RUNS):
        undo         = topology.perturb(temperature=1e9)
        new_pos      = topology.decode()
        new_cost     = evaluator.evaluate(new_pos)
        deltas.append(abs(new_cost - ref_cost))
        undo()

    mean_delta = sum(deltas) / len(deltas) if deltas else 1.0
    if mean_delta == 0.0:
        return 1.0
    return -mean_delta / math.log(_CALIBRATION_TARGET)
