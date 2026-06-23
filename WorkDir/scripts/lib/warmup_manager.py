"""
WarmupManager — pluggable multi-run warm-start system for ILP placement.

A WarmupStrategy runs N times in parallel (ProcessPoolExecutor, one core each)
with child seeds derived from a master seed.  A selection layer picks the
median result by cost function value as the warm start for the ILP solver.

Usage (from pipeline.py):
    from warmup_manager import WarmupConfig, WarmupManager
    cfg = WarmupConfig(strategy="corp", n_runs=3, master_seed=42)
    mgr = WarmupManager(cfg)
    selected_positions, all_results = mgr.run(blocks, nets, init_area, init_wl)
    # selected_positions: {bid: (x, y)} — pass to ILPOptimizer as initial_warm_positions
"""
from __future__ import annotations

import dataclasses
import sys
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

DEBUG = False
logger = get_logger(__name__, DEBUG)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclasses.dataclass
class WarmupResult:
    run_index:   int
    positions:   dict   # {bid: (x_bl, y_bl, w, h)} — 4-tuple, w/h for viewer use
    cost:        float
    strategy:    str
    seed:        int
    is_selected: bool = False
    variant_map: dict = dataclasses.field(default_factory=dict)  # {bid: variant_idx}


@dataclasses.dataclass
class WarmupConfig:
    strategy:         str   = "corp"   # "corp" | "contour" | "spsa"
    n_runs:           int   = 3
    master_seed:      int   = 42
    visualize:        bool  = False    # if True, warmup_runs saved to output JSON
    exhaustive_ilp:   bool  = False    # if True, run ILP for each warmup result
    spsa_timeout_sec: float = 10.0     # wall-clock budget per SPSA run


# =============================================================================
# STRATEGY ABSTRACT BASE
# =============================================================================

class WarmupStrategy(ABC):
    """
    One seeded warm-start placement run.
    Returns {bid: (x_bl, y_bl, w, h)} — bottom-left corner plus block dimensions.
    Dimensions are stored so the viewer can draw blocks without needing blocks dict.
    """

    @abstractmethod
    def run_single(
        self,
        blocks: dict,
        nets:   list,
        seed:   int,
    ) -> dict[str, tuple[float, float, float, float]]:
        ...

    def get_variant_map(self) -> dict[str, int]:
        """Return {bid: variant_idx} chosen during run_single(). Default: empty (use variant 0)."""
        return {}


# =============================================================================
# CORP WARM-START STRATEGY
# =============================================================================

class CORPWarmup(WarmupStrategy):
    """
    CORP (Connectivity-Ordered Row Placement) warm start.
    Runs the spring-embedding phase via corp_placer.run_corp_spring() to get
    connectivity-aware centroids, then row-packs them into a DRC-clean layout
    via _corp_row_pack() from ilp_optimizer.py.
    Uses the provided seed so N parallel runs explore different orderings.
    """

    def run_single(
        self,
        blocks: dict,
        nets:   list,
        seed:   int,
    ) -> dict[str, tuple[float, float, float, float]]:
        from corp_placer   import run_corp_spring
        from ilp_optimizer import _corp_row_pack, _variant_dims

        bids = [b for b in blocks if "error" not in blocks[b]]
        if not bids:
            return {}

        centroids    = run_corp_spring(blocks, nets, seed=seed)
        positions_2d = _corp_row_pack(bids, blocks, centroids)

        result: dict[str, tuple[float, float, float, float]] = {}
        for bid, (x, y) in positions_2d.items():
            dims = _variant_dims(blocks[bid])
            w, h = (dims[0][0], dims[0][1]) if dims else (0.0, 0.0)
            result[bid] = (x, y, w, h)
        return result


# =============================================================================
# SP+SA WARM-START STRATEGY
# =============================================================================

class SPSAWarmup(WarmupStrategy):
    """
    Sequence Pair + SA warm start, time-bounded to timeout_sec wall-clock
    seconds. Operates on the merged blocks dict (composite group blocks +
    ungrouped individual blocks) — composite blocks share the same
    variants/main_bbox schema as regular blocks, so no pre-processing is needed.
    SA exits naturally when temperature converges; timeout_sec is the hard ceiling.
    """

    def __init__(self, timeout_sec: float = 10.0) -> None:
        self._timeout_sec  = timeout_sec
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
        from seqpair_topology import SequencePairTopology
        from cost_evaluator   import CostEvaluator
        from sa_optimizer     import (
            SimulatedAnnealingOptimizer, SAConfig,
            calibrate_initial_temperature,
        )
        from ilp_optimizer import _variant_dims

        # Seed global random — SequencePairTopology.seed() and SA move operators
        # both draw from random.* internally; seed ensures reproducibility.
        random.seed(seed)

        valid_blocks = {bid: b for bid, b in blocks.items() if "error" not in b}
        if not valid_blocks:
            return {}

        topo = SequencePairTopology(valid_blocks, nets)
        topo.seed(valid_blocks, mode="random")

        # Use scale-neutral evaluator: calibration only needs relative cost deltas,
        # not absolute normalization, so init_area=1.0 / init_wl=1.0 is correct.
        evaluator = CostEvaluator(valid_blocks, nets, 1.0, 1.0)

        initial_temp = calibrate_initial_temperature(topo, evaluator)

        cfg = SAConfig(
            initial_temp   = initial_temp,
            timeout_sec    = self._timeout_sec,
            max_iterations = 0,   # 0 → epoch_size × 200; SA exits when converged
        )
        result = SimulatedAnnealingOptimizer(topo, evaluator, cfg).run()

        topo.restore_state(result.best_state)
        self._variant_map = topo.get_variant_map()
        final_pos = topo.decode()   # {bid: (x, y)}

        # Enrich to 4-tuples (x, y, w, h) as required by WarmupStrategy contract
        out: dict[str, tuple[float, float, float, float]] = {}
        for bid, (x, y) in final_pos.items():
            dims = _variant_dims(valid_blocks[bid])
            vidx = self._variant_map.get(bid, 0)
            w, h = dims[vidx] if vidx < len(dims) else dims[0]
            out[bid] = (x, y, w, h)
        return out


# =============================================================================
# STRATEGY REGISTRY
# =============================================================================

_STRATEGY_MAP: dict[str, type] = {
    "corp": CORPWarmup,
    "spsa": SPSAWarmup,
    # "contour" is registered lazily by contour_warmup.py via register_strategy()
}


def register_strategy(name: str, cls: type) -> None:
    """Allow external modules (contour_warmup.py) to register additional strategies."""
    _STRATEGY_MAP[name] = cls


# =============================================================================
# MODULE-LEVEL WORKER  (must be top-level for ProcessPoolExecutor on Windows)
# =============================================================================

def _worker(
    strategy_cls:    type,
    strategy_kwargs: dict,
    blocks:          dict,
    nets:            list,
    seed:            int,
    init_area:       float,
    init_wl:         float,
) -> tuple[dict, float]:
    """
    Executed in a subprocess.  Imports are done inside to keep the pickling
    boundary clean — only JSON-native data crosses between processes.
    Returns (positions_with_dims, cost) where
        positions_with_dims: {bid: (x_bl, y_bl, w, h)}
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))

    from cost_evaluator import CostEvaluator

    strategy = strategy_cls(**strategy_kwargs)
    positions_with_dims = strategy.run_single(blocks, nets, seed)
    variant_map         = strategy.get_variant_map()

    # Strip to (x, y) for CostEvaluator — it expects 2-tuples
    positions_2d = {bid: (v[0], v[1]) for bid, v in positions_with_dims.items()}

    evaluator = CostEvaluator(
        blocks, nets,
        max(init_area, 1e-9),
        max(init_wl, 0.0),
    )
    cost = evaluator.evaluate(positions_2d)
    return positions_with_dims, cost, variant_map


# =============================================================================
# WARMUP MANAGER
# =============================================================================

class WarmupManager:
    """Runs N warmup sessions in parallel and returns the median-cost result."""

    def __init__(self, config: WarmupConfig) -> None:
        self._cfg          = config
        self._strategy_cls = self._resolve_strategy(config.strategy)

    @staticmethod
    def _resolve_strategy(name: str) -> type:
        if name == "contour":
            # Lazy import — contour_warmup registers itself on import
            from contour_warmup import ContourWarmup  # noqa: F401
        if name == "spring":
            # Lazy import — spring_warmup registers itself on import
            from spring_warmup import SpringWarmup  # noqa: F401
        cls = _STRATEGY_MAP.get(name)
        if cls is None:
            raise ValueError(
                f"Unknown warmup strategy: {name!r}. "
                f"Available: {sorted(_STRATEGY_MAP)}"
            )
        return cls

    def run(
        self,
        blocks:    dict,
        nets:      list,
        init_area: float,
        init_wl:   float,
    ) -> tuple[dict[str, tuple[float, float]], list[WarmupResult], dict[str, int]]:
        """
        Run N warmup sessions in parallel.
        Returns (selected_positions_2d, all_results_sorted_by_cost, selected_variant_map).
        selected_positions_2d: {bid: (x, y)} ready for ILPOptimizer.
        all_results is sorted ascending by cost; the selected entry has is_selected=True.
        selected_variant_map: {bid: variant_idx} from the selected run (empty for strategies
        that do not expose variant choices).
        """
        cfg             = self._cfg
        seeds           = [cfg.master_seed * 10_000 + i for i in range(cfg.n_runs)]
        strategy_kwargs: dict = {}
        if cfg.strategy == "spsa":
            strategy_kwargs = {"timeout_sec": cfg.spsa_timeout_sec}

        logger.info(
            "WarmupManager: strategy=%s  n_runs=%d  master_seed=%d",
            cfg.strategy, cfg.n_runs, cfg.master_seed,
        )

        raw: list[tuple[int, dict, float, int, dict]] = []  # (run_idx, positions, cost, seed, variant_map)

        with ProcessPoolExecutor(max_workers=cfg.n_runs) as pool:
            futures = {
                pool.submit(
                    _worker,
                    self._strategy_cls,
                    strategy_kwargs,
                    blocks,
                    nets,
                    seed,
                    init_area,
                    init_wl,
                ): (i, seed)
                for i, seed in enumerate(seeds)
            }
            for future in as_completed(futures):
                run_idx, seed = futures[future]
                try:
                    positions_with_dims, cost, variant_map = future.result(timeout=120.0)
                    raw.append((run_idx, positions_with_dims, cost, seed, variant_map))
                    logger.debug(
                        "Warmup run %d (seed=%d) done: cost=%.4f", run_idx, seed, cost
                    )
                except Exception as exc:
                    logger.warning(
                        "Warmup run %d (seed=%d) failed: %s", run_idx, seed, exc
                    )

        if not raw:
            raise RuntimeError(
                "All warmup runs failed — cannot provide warm start to ILP"
            )

        results = [
            WarmupResult(
                run_index   = idx,
                positions   = pos,
                cost        = cost,
                strategy    = cfg.strategy,
                seed        = seed,
                variant_map = vm,
            )
            for idx, pos, cost, seed, vm in raw
        ]

        sorted_results = sorted(results, key=lambda r: r.cost)
        selected       = self._select_median(sorted_results)
        selected.is_selected = True

        logger.info(
            "WarmupManager: selected run %d (seed=%d, cost=%.4f) from %d runs",
            selected.run_index, selected.seed, selected.cost, len(sorted_results),
        )

        selected_positions_2d: dict[str, tuple[float, float]] = {
            bid: (v[0], v[1]) for bid, v in selected.positions.items()
        }
        return selected_positions_2d, sorted_results, selected.variant_map

    @staticmethod
    def _select_median(results: list[WarmupResult]) -> WarmupResult:
        """
        Lower-biased median: sort ascending by cost, pick the index just below
        the midpoint so ties favour the cheaper solution.
          n odd  → index n//2     (true middle)
          n even → index n//2 - 1 (left of centre, lower cost)
        """
        n   = len(results)
        idx = 0 #n // 2 if n % 2 == 1 else n // 2 - 1
        return results[idx]
