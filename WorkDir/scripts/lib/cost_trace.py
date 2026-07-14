"""
Cost-over-time tracing — opt-in, off unless a caller explicitly attaches one.

TraceObserver satisfies the same duck-typed observer protocol SA/PSO already
use (on_improvement/on_termination) plus one new callback, on_iteration,
called every loop pass regardless of accept/reject. Samples are held in
memory and written to disk only once, at the end of a run — the optimizer
inner loop must never perform I/O.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cost_evaluator import CostBreakdown


# =============================================================================
# TRACE FILE I/O
# =============================================================================

def write_trace_jsonl(path: str | Path, samples: list[dict]) -> None:
    """Write one JSON object per line. Creates parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")


# =============================================================================
# OBSERVER
# =============================================================================

class TraceObserver:
    """
    Records (t_rel, iteration, area/HPWL/AR/cost) samples for one run and
    flushes them to `path` on termination.

    t0 must be the same time.perf_counter() reference used across every
    phase of a run (warmup construction + the optimizer loop that follows
    it), so the clock never resets between phases.
    """

    def __init__(
        self, run_id: str, t0: float, path: str | Path, auto_flush: bool = True
    ) -> None:
        """
        auto_flush=False is for warmup strategies whose samples are only an
        intermediate result — the parent process collects `.samples` after
        run_single() returns and appends them to the ILP run's own trace
        file, rather than writing a separate warmup-only file here.
        """
        self.run_id     = run_id
        self.path       = Path(path)
        self._t0        = t0
        self._auto_flush = auto_flush
        self.samples: list[dict] = []

    def record(self, iteration: int, breakdown: "CostBreakdown") -> None:
        self.samples.append({
            "iteration":    iteration,
            "t_rel":        time.perf_counter() - self._t0,
            "area_um2":     breakdown.area_um2,
            "hpwl_um":      breakdown.hpwl_um,
            "aspect_ratio": breakdown.aspect_ratio,
            "cost":         breakdown.cost,
        })

    def flush(self) -> None:
        write_trace_jsonl(self.path, self.samples)

    # ------------------------------------------------------------------
    # Duck-typed observer protocol shim (matches sa_optimizer.NullObserver /
    # pso_optimizer's observer usage) so SA/PSO can use this directly as
    # their `observer=` argument with no extra glue code.
    # ------------------------------------------------------------------
    def on_iteration(self, iteration: int, breakdown: "CostBreakdown") -> None:
        self.record(iteration, breakdown)

    def on_improvement(self, iteration: int, cost: float, positions: dict) -> None:
        pass  # the trace only cares about on_iteration; every-iteration data already covers this

    def on_termination(
        self, reason: str, n_iterations: int, best_cost: float, best_positions: dict
    ) -> None:
        if self._auto_flush:
            self.flush()
