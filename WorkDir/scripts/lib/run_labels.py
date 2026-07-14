"""
Run-id / warmup-strategy display labels — shared between the viewer's tab
bar/compare table and the cost-trace plotting library, so legend text always
matches what the viewer already shows. No PyQt dependency, so headless
plotting code can import this too.
"""
from __future__ import annotations


# =============================================================================
# CONSTANTS
# =============================================================================
_RUN_ID_OVERRIDES: dict[str, str] = {
    "BStarTopology+SimulatedAnnealingOptimizer": "B* SA",
}

_WARMUP_STRATEGY_LABELS: dict[str, str] = {
    "corp":    "CORP",
    "spsa":    "SPSA",
    "contour": "CONTOUR",
    "spring":  "SPRING",
    "pso":     "PSO",
    "bstar":   "BTSA",
}


def abbrev_run_id(run_id: str) -> str:
    """Shorten a run_id like 'SequencePairTopology+SimulatedAnnealingOptimizer' → 'SP+SA'."""
    if run_id in _RUN_ID_OVERRIDES:
        return _RUN_ID_OVERRIDES[run_id]
    subs = [
        ("SimulatedAnnealing", "SA"),
        ("SequencePair", "SP"),
        ("Topology", ""),
        ("Optimizer", ""),
    ]
    result = run_id
    for old, new in subs:
        result = result.replace(old, new)
    parts = [p for p in result.split("+") if p]
    dedup: list[str] = []
    for p in parts:
        if not dedup or p != dedup[-1]:
            dedup.append(p)
    return "+".join(dedup)


def display_label(run_id: str, warmup_strategy: str | None) -> str:
    """
    Legend/tab label for one placement run.

    Exhaustive-mode ILP runs are exploded into one entry per warmup strategy
    (see 101_placementOptimizer.py::_build_warmup_run_entries) — label those
    as e.g. 'BTSA+ILP' / 'SPSA+ILP' instead of the generic abbrev_run_id
    output, which would collapse every strategy to the same ambiguous 'ILP'.
    """
    if warmup_strategy:
        base = _WARMUP_STRATEGY_LABELS.get(warmup_strategy, warmup_strategy.upper())
        return f"{base}+ILP"
    return abbrev_run_id(run_id)
