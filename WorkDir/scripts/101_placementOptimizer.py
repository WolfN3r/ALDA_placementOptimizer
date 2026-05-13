#!/usr/bin/env python3
"""
Run the decoupled placement-optimization framework on a block+netlist JSON.

Standalone:  python 101_placementOptimizer.py s42_n10_py001_v01.json
             Writes s42_n10_py101_v01.json with placement results.
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
DEBUG        = False
SEED_MODE    = "random"      # "random" | "ordered"
RUN_MODE     = "exhaustive"  # "random" | "exhaustive"

# SA tuning overrides (0 → auto-calibrated / auto-computed from n_blocks)
SA_INITIAL_TEMP  = 0.0
SA_FINAL_TEMP    = 1e-4
SA_MAX_ITER      = 0
SA_EPOCH_SIZE    = 0
SA_STAGNATION    = 15

# Cost weights (must sum to 1.0)
W_AREA    = 0.6
W_WL      = 0.1
W_AR      = 0.3
TARGET_AR = 1.0

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _build_blocks_dict(raw_blocks: list) -> dict:
    """Convert the blocks list from JSON to a block_id-keyed dict."""
    return {str(b["block_id"]): b for b in raw_blocks}


def _build_nets_list(netlist: dict) -> list:
    return netlist.get("nets", [])


def optimize(data: dict) -> dict:
    """
    Run the optimizer on the input JSON produced by 001_L1blocksGenerator.
    Returns an exhaustive result document augmented with input metadata.
    """
    from cost_evaluator import CostWeights
    from sa_optimizer   import SAConfig
    from solver_picker  import SolverPicker, _build_exhaustive_doc

    blocks_raw = data.get("blocks", [])
    netlist    = data.get("netlist", {})
    gen_params = data.get("generation_params", {})

    blocks = _build_blocks_dict(blocks_raw)
    nets   = _build_nets_list(netlist)

    n_blks     = gen_params.get("num_of_blocks", len(blocks))
    seed       = gen_params.get("seed", 0)
    netlist_id = f"s{seed}_n{n_blks}"

    logger.info("Starting optimizer: %d blocks, %d nets, mode=%s", len(blocks), len(nets), RUN_MODE)

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

    picker = SolverPicker(
        sa_config      = sa_cfg,
        weights        = weights,
        auto_calibrate = True,
    )

    if RUN_MODE == "exhaustive":
        doc = picker.run_exhaustive(blocks, nets, seed_mode=SEED_MODE, netlist_id=netlist_id)
    else:
        results = picker.run_random(blocks, nets, seed_mode=SEED_MODE)
        doc = _build_exhaustive_doc(results, blocks, nets, netlist_id, SEED_MODE, sa_cfg)

    success_costs = [r["metrics"]["final_cost"] for r in doc["runs"] if r["status"] == "success"]
    logger.info(
        "Optimizer complete. Best run: %s  cost=%.4f",
        doc["summary"].get("best_cost_run", "n/a"),
        min(success_costs) if success_costs else float("nan"),
    )

    return {
        "generation_params":    gen_params,
        "technology":           data.get("technology", ""),
        "netlist":              netlist,
        "symmetry_constraints": data.get("symmetry_constraints", {}),
        "placement_results":    doc,
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
    stem = Path(path).stem.replace("py001", "py101")
    out  = Path(path).with_stem(stem)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Saved placement result to %s", out)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main_standalone(sys.argv[1])
    else:
        logger.error("Usage: 101_placementOptimizer.py <input.json>")
        sys.exit(1)
