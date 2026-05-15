#!/usr/bin/env python3
"""
Run the decoupled placement-optimization framework on a block+netlist JSON.

Standalone:  python 101_placementOptimizer.py s42_n10_py001_v01.json
             Writes s42_n10_py101_v01.json with placement coordinates merged
             into the blocks list and a "placement" metadata section.
n8n mode:    reads JSON from stdin, writes JSON to stdout.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG     = False
SEED_MODE = "random"      # "random" | "ordered" — initial topology seed strategy

# --- Combination selector ---------------------------------------------------
# Set TOPOLOGY + OPTIMIZER to run exactly one combination.
# Leave both empty to fall back to RUN_MODE (exhaustive or random).
TOPOLOGY  = ""   # "" | "BStarTopology" | "SequencePairTopology"
OPTIMIZER = "SimulatedAnnealingOptimizer"   # "" | "SimulatedAnnealingOptimizer"

# Used only when TOPOLOGY/OPTIMIZER are empty:
RUN_MODE  = "exhaustive"  # "exhaustive" → all supported pairs | "random" → one random pair

# --- SA tuning (0 → auto-computed from n_blocks) ----------------------------
SA_INITIAL_TEMP = 0.0    # auto-calibrated when 0.0
SA_FINAL_TEMP   = 1e-4
SA_MAX_ITER     = 0      # 0 → epoch_size × 200
SA_EPOCH_SIZE   = 0      # 0 → max(n_blocks × 8, 50)
SA_STAGNATION   = 15     # epochs without improvement before reheating

# --- Cost weights (must sum to 1.0) -----------------------------------------
W_AREA    = 0.6
W_WL      = 0.1
W_AR      = 0.3
TARGET_AR = 1.0          # target width/height ratio for the full placement

# --- Output ------------------------------------------------------------------
_OUTPUT_DIR = Path(__file__).parent.parent / "json_files"
_VERSION    = "v01"

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _build_blocks_dict(raw_blocks: list) -> dict:
    """Convert the blocks list (from py001 JSON) to a block_id-keyed dict."""
    return {str(b["block_id"]): b for b in raw_blocks}


def _resolve_combination():
    """
    Return (topology_cls, optimizer_cls) when TOPOLOGY + OPTIMIZER are set,
    or None when the picker should decide via RUN_MODE.
    """
    if not TOPOLOGY or not OPTIMIZER:
        return None
    from bstar_topology   import BStarTopology
    from seqpair_topology import SequencePairTopology
    from sa_optimizer     import SimulatedAnnealingOptimizer

    topo_map = {
        "BStarTopology":        BStarTopology,
        "SequencePairTopology": SequencePairTopology,
    }
    opt_map = {
        "SimulatedAnnealingOptimizer": SimulatedAnnealingOptimizer,
    }
    t_cls = topo_map.get(TOPOLOGY)
    o_cls = opt_map.get(OPTIMIZER)
    if t_cls is None:
        raise ValueError(f"Unknown TOPOLOGY '{TOPOLOGY}'. Valid: {list(topo_map)}")
    if o_cls is None:
        raise ValueError(f"Unknown OPTIMIZER '{OPTIMIZER}'. Valid: {list(opt_map)}")
    return t_cls, o_cls


def _run_summary(result) -> dict:
    """Compact per-run dict for the all_runs comparison list."""
    return {
        "topology":    result.topology,
        "optimizer":   result.optimizer,
        "status":      result.status,
        "final_cost":  result.final_cost,
        "area_um2":    round(result.area_um2, 4),
        "hpwl_um":     round(result.hpwl_um, 4),
        "aspect_ratio": round(result.aspect_ratio, 4),
        "n_iterations": result.n_iterations,
        "t_seed_ms":   round(result.t_seed_ms, 2),
        "t_optimize_ms": round(result.t_optimize_ms, 2),
        "t_total_ms":  round(result.t_total_ms, 2),
        "error":       result.error_message or None,
    }


def optimize(data: dict) -> dict:
    """
    Run the optimizer on the py001 input JSON.

    Output structure (py101):
      generation_params   — unchanged from input
      technology          — unchanged
      blocks[]            — same as input + placed_x, placed_y on every block
      netlist             — unchanged
      symmetry_constraints — unchanged
      placement{}         — optimizer metadata + per-run comparison
    """
    from cost_evaluator import CostWeights
    from sa_optimizer   import SAConfig
    from solver_picker  import SolverPicker, _build_exhaustive_doc
    from pipeline       import OptimizationPipeline, build_default_registry

    raw_blocks = data.get("blocks", [])
    netlist    = data.get("netlist", {})
    gen_params = data.get("generation_params", {})
    blocks     = _build_blocks_dict(raw_blocks)
    nets       = netlist.get("nets", [])

    n_blks     = gen_params.get("num_of_blocks", len(blocks))
    seed       = gen_params.get("seed", 0)
    netlist_id = f"s{seed}_n{n_blks}"

    logger.info(
        "Starting optimizer: %d blocks, %d nets — topology=%s optimizer=%s mode=%s",
        len(blocks), len(nets),
        TOPOLOGY or f"({RUN_MODE})", OPTIMIZER or "auto", RUN_MODE,
    )

    weights = CostWeights(
        area_weight         = W_AREA,
        wirelength_weight   = W_WL,
        aspect_ratio_weight = W_AR,
        target_aspect_ratio = TARGET_AR,
    )
    sa_cfg = SAConfig(
        initial_temp     = SA_INITIAL_TEMP,
        final_temp       = SA_FINAL_TEMP,
        max_iterations   = SA_MAX_ITER,
        stagnation_limit = SA_STAGNATION,
        epoch_size       = SA_EPOCH_SIZE,
    )

    fixed_combo = _resolve_combination()
    all_results = []

    if fixed_combo is not None:
        # Single combination selected via TOPOLOGY + OPTIMIZER constants
        t_cls, o_cls = fixed_combo
        pipeline = OptimizationPipeline(
            topology_cls   = t_cls,
            optimizer_cls  = o_cls,
            sa_config      = sa_cfg,
            weights        = weights,
            auto_calibrate = True,
        )
        run_id = f"{t_cls.__name__}+{o_cls.__name__}"
        result = pipeline.run(blocks, nets, seed_mode=SEED_MODE, run_id=run_id)
        all_results = [result]
        logger.info(
            "Single run %s: status=%s cost=%.4f t=%.0fms",
            run_id, result.status, result.final_cost, result.t_total_ms,
        )
        if result.error_message:
            logger.error("  error: %s", result.error_message)

    else:
        picker = SolverPicker(
            sa_config      = sa_cfg,
            weights        = weights,
            auto_calibrate = True,
        )
        if RUN_MODE == "exhaustive":
            doc = picker.run_exhaustive(
                blocks, nets, seed_mode=SEED_MODE, netlist_id=netlist_id
            )
            # Reconstruct PipelineResult list from the doc for uniform handling below
            # (SolverPicker already logged the exhaustive doc)
            all_results = picker._last_results  # set in run_exhaustive below
        else:
            all_results = picker.run_random(blocks, nets, seed_mode=SEED_MODE)

    # Pick the best successful run
    success = [r for r in all_results if r.status == "success"]
    if not success:
        logger.error("All runs failed. Check logs for details.")
        for r in all_results:
            if r.error_message:
                logger.error("  %s: %s", r.run_id, r.error_message)
        best = all_results[0] if all_results else None
    else:
        best = min(success, key=lambda r: r.final_cost)
        logger.info(
            "Best run: %s  cost=%.4f  area=%.2f µm²  AR=%.3f",
            best.run_id, best.final_cost, best.area_um2, best.aspect_ratio,
        )

    placement_meta: dict = {}
    if best:
        placement_meta = {
            "run_id":        best.run_id,
            "topology":      best.topology,
            "optimizer":     best.optimizer,
            "seed_mode":     SEED_MODE,
            "final_cost":    round(best.final_cost, 6),
            "area_um2":      round(best.area_um2, 4),
            "hpwl_um":       round(best.hpwl_um, 4),
            "aspect_ratio":  round(best.aspect_ratio, 4),
            "n_iterations":  best.n_iterations,
            "t_seed_ms":     round(best.t_seed_ms, 2),
            "t_optimize_ms": round(best.t_optimize_ms, 2),
            "t_total_ms":    round(best.t_total_ms, 2),
            "placed_blocks": best.placed_blocks,
        }
        if len(all_results) > 1:
            placement_meta["all_runs"] = [_run_summary(r) for r in all_results]

    return {
        "generation_params":    gen_params,
        "technology":           data.get("technology", ""),
        "blocks":               raw_blocks,
        "netlist":              netlist,
        "symmetry_constraints": data.get("symmetry_constraints", {}),
        "placement":            placement_meta,
    }


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(data: dict) -> dict:
    """Called by main.py pipeline. Validates input then runs optimizer."""
    if "blocks" not in data:
        raise KeyError("run: input JSON missing 'blocks'")
    if "netlist" not in data:
        raise KeyError("run: input JSON missing 'netlist'")
    return optimize(data)


def main_standalone(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    result = run(data)

    gp  = result["generation_params"]
    n   = gp.get("num_of_blocks", 0)
    s   = gp.get("seed", 0)
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = _OUTPUT_DIR / f"s{s}_n{n}_py101_{_VERSION}.json"

    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Saved → %s", out)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main_standalone(sys.argv[1])
    else:
        logger.error("Usage: 101_placementOptimizer.py <s##_n##_py001_v01.json>")
        sys.exit(1)
