"""
SolverPicker — selects (topology, optimizer) combinations and runs them.
ResultLog    — appends exhaustive result documents to a JSONL file.
NetlistFeatures + extract_netlist_features — ML decider input (data collection only).
"""
from __future__ import annotations

import hashlib
import json
import random
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Type

from pipeline import (
    OptimizationPipeline, PipelineResult, build_default_registry,
    CompatibilityRegistry,
)
from cost_evaluator import CostWeights
from sa_optimizer import SAConfig


# =============================================================================
# CONSTANTS
# =============================================================================
_RESULT_LOG_PATH = Path(__file__).parent.parent.parent / "logs" / "result_log.jsonl"
_TRACES_DIR      = Path(__file__).parent.parent.parent / "traces"


# =============================================================================
# NETLIST FEATURES
# =============================================================================

@dataclass
class NetlistFeatures:
    n_blocks:                  int
    n_nets:                    int
    n_symmetric_pairs:         int
    block_area_variance:       float
    net_density:               float
    has_self_symmetric_blocks: bool
    target_aspect_ratio:       float
    max_block_to_min_block_ratio: float


def extract_netlist_features(blocks: dict, nets: list, weights: CostWeights) -> NetlistFeatures:
    """Pure function — no optimizer dependency."""
    valid  = [b for b in blocks.values() if "error" not in b]
    n_blks = len(valid)
    n_nets = len(nets)

    def _area(block: dict) -> float:
        for v in block.get("variants", []):
            if v.get("is_used"):
                bb = v.get("main_bbox", {})
                return bb.get("x_max", 0.0) * bb.get("y_max", 0.0)
        if block.get("variants"):
            bb = block["variants"][0].get("main_bbox", {})
            return bb.get("x_max", 0.0) * bb.get("y_max", 0.0)
        return 0.0

    areas   = [_area(b) for b in valid]
    mean_a  = sum(areas) / len(areas) if areas else 0.0
    var_a   = sum((a - mean_a) ** 2 for a in areas) / len(areas) if areas else 0.0
    min_a   = min(areas) if areas else 1.0
    max_a   = max(areas) if areas else 1.0
    size_ratio = max_a / min_a if min_a > 0.0 else 1.0

    sym = blocks.get("__symmetry__", {})
    n_pairs   = 0
    has_self  = False
    # Symmetry data is attached separately via the netlist JSON
    # Caller should populate via netlist["symmetry_constraints"] if available

    density = n_nets / (n_blks ** 2) if n_blks > 1 else 0.0

    return NetlistFeatures(
        n_blocks                  = n_blks,
        n_nets                    = n_nets,
        n_symmetric_pairs         = n_pairs,
        block_area_variance       = var_a,
        net_density               = density,
        has_self_symmetric_blocks = has_self,
        target_aspect_ratio       = weights.target_aspect_ratio,
        max_block_to_min_block_ratio = size_ratio,
    )


# =============================================================================
# SOLVER PICKER
# =============================================================================

class SolverPicker:
    """
    Three modes, all producing the same output type: list[PipelineResult].

    random     — picks one SUPPORTED pair at random.
    exhaustive — runs all SUPPORTED pairs and returns all results.
    ml         — stub; raises NotImplementedError until a trained model exists.
    """

    def __init__(
        self,
        registry:              CompatibilityRegistry | None = None,
        sa_config:             SAConfig | None              = None,
        weights:               CostWeights | None           = None,
        result_log:            "ResultLog | None"           = None,
        auto_calibrate:        bool                         = True,
        sym_groups:            list | None                  = None,
        optimizer_kwargs:      dict | None                  = None,
        per_optimizer_kwargs:  dict | None                  = None,
        use_power_rails:       bool                         = False,
    ) -> None:
        self._registry        = registry      or build_default_registry()
        self._sa_config       = sa_config     or SAConfig()
        self._weights         = weights       or CostWeights()
        self._result_log      = result_log    or ResultLog()
        self._auto_calibrate  = auto_calibrate
        self._sym_groups      = sym_groups or []
        # per_optimizer_kwargs takes priority; optimizer_kwargs is a fallback for
        # single-combo callers that pass a flat dict.
        self._per_optimizer_kwargs: dict = per_optimizer_kwargs or {}
        self._optimizer_kwargs:     dict = optimizer_kwargs or {}
        self._use_power_rails       = use_power_rails
        self._last_results: list = []

    def run_random(
        self,
        blocks: dict,
        nets:   list,
        seed_mode: str = "random",
    ) -> list[PipelineResult]:
        """Pick one SUPPORTED pair at random and run it."""
        pairs = self._registry.supported_pairs()
        if not pairs:
            return []
        t_cls, o_cls = random.choice(pairs)
        return [self._run_one(t_cls, o_cls, blocks, nets, seed_mode)]

    def run_exhaustive(
        self,
        blocks:    dict,
        nets:      list,
        seed_mode: str = "random",
        netlist_id: str = "",
    ) -> dict:
        """Run all SUPPORTED pairs. Returns exhaustive result document."""
        pairs   = self._registry.supported_pairs()
        results = []
        for t_cls, o_cls in pairs:
            r = self._run_one(t_cls, o_cls, blocks, nets, seed_mode)
            results.append(r)

        # Store results list so callers can retrieve PipelineResult objects
        self._last_results = results

        doc = _build_exhaustive_doc(results, blocks, nets, netlist_id, seed_mode, self._sa_config)
        self._result_log.record(doc)
        return doc

    def run_ml(
        self, blocks: dict, nets: list, seed_mode: str = "random"
    ) -> list[PipelineResult]:
        raise NotImplementedError(
            "ML solver picker requires a trained model. Collect training data first."
        )

    def _run_one(
        self,
        topology_cls:  Type,
        optimizer_cls: Type,
        blocks: dict,
        nets:   list,
        seed_mode: str,
    ) -> PipelineResult:
        # Per-optimizer kwargs take priority over the shared fallback dict.
        kwargs = self._per_optimizer_kwargs.get(optimizer_cls.__name__,
                                                self._optimizer_kwargs)
        pipeline = OptimizationPipeline(
            topology_cls     = topology_cls,
            optimizer_cls    = optimizer_cls,
            sa_config        = self._sa_config,
            weights          = self._weights,
            registry         = self._registry,
            auto_calibrate   = self._auto_calibrate,
            sym_groups       = self._sym_groups,
            optimizer_kwargs = kwargs,
            use_power_rails  = self._use_power_rails,
        )
        run_id = f"{topology_cls.__name__}+{optimizer_cls.__name__}"
        return pipeline.run(blocks, nets, seed_mode=seed_mode, run_id=run_id)


# =============================================================================
# RESULT LOG
# =============================================================================

class ResultLog:
    """
    Appends one exhaustive-result document per run to a JSONL file.
    Every run is logged — including failures — to avoid biasing training data.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _RESULT_LOG_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, doc: dict) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


# =============================================================================
# EXHAUSTIVE DOCUMENT BUILDER
# =============================================================================

def _config_hash(cfg: SAConfig) -> str:
    payload = json.dumps(cfg.__dict__, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()[:6]


def _build_exhaustive_doc(
    results:    list[PipelineResult],
    blocks:     dict,
    nets:       list,
    netlist_id: str,
    seed_mode:  str,
    cfg:        SAConfig,
) -> dict:
    n_blocks = len([b for b in blocks.values() if "error" not in b])
    runs     = [r.to_dict() for r in results]

    success = [r for r in results if r.status == "success"]
    failed  = [r.run_id for r in results if r.status != "success"]

    ranked_cost    = sorted(success, key=lambda r: r.final_cost)
    ranked_runtime = sorted(success, key=lambda r: r.t_optimize_ms)

    summary = {
        "best_cost_run":  ranked_cost[0].run_id    if ranked_cost    else "",
        "fastest_run":    ranked_runtime[0].run_id  if ranked_runtime else "",
        "rank_by_cost":   [r.run_id for r in ranked_cost],
        "rank_by_runtime":[r.run_id for r in ranked_runtime],
        "failed_runs":    failed,
    }

    return {
        "netlist_id":  netlist_id,
        "timestamp":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_blocks":    n_blocks,
        "seed_mode":   seed_mode,
        "config_hash": _config_hash(cfg),
        "runs":        runs,
        "summary":     summary,
    }
