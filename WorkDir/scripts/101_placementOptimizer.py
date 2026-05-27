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
from log_setup      import get_logger
from ilp_optimizer     import GurobiParams
from pso_optimizer     import PSOConfig
from sa_optimizer      import SAConfig

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG     = False
SEED_MODE = "random"      # "random" | "ordered" — initial topology seed strategy

# --- Combination selector ---------------------------------------------------
# Set TOPOLOGY + OPTIMIZER to run exactly one combination.
# Leave both empty to fall back to RUN_MODE (exhaustive or random).
TOPOLOGY  = ""      # "" | "BStarTopology" | "SequencePairTopology" | "ILPTopology" | "PSOTopology"
OPTIMIZER = ""  # "" | "SimulatedAnnealingOptimizer" | "ILPOptimizer" | "PSOOptimizer" | "PSOILPOptimizer" | "BStarILPOptimizer"

# Used only when TOPOLOGY/OPTIMIZER are empty:
RUN_MODE  = "exhaustive"  # "exhaustive" → all supported pairs | "random" → one random pair

# --- Exhaustive mode output options -----------------------------------------
# RENORMALIZE: recalculates cost for all exhaustive runs using the best run's
# area and hpwl as shared references so costs are directly comparable.
# Best run = 1.0, all others >= 1.0 (higher is worse).
RENORMALIZE = True

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

# --- Power rails -------------------------------------------------------------
USE_POWER_RAILS = True   # VDD net pulled to canvas top, VSS net pulled to canvas bottom via HPWL

# --- Gurobi ML parameter injection hook -------------------------------------
# A future ML model reads netlist features externally, predicts the best
# parameter values, constructs a GurobiParams instance, and assigns it here
# before calling optimize().  None → solver uses GurobiParams() defaults.
#
# Fields most worth ML-tuning (depend on netlist structure):
#   mip_focus  — small/easy netlists: 2 (prove optimum); large: 1 (feasibility first)
#   symmetry   — correlates with number of symmetry groups in the netlist
#   cuts       — dense big-M netlists: 2–3; sparse netlists: 0–1
#   heuristics — tightly-coupled netlists: higher → finds incumbent faster
ILP_GUROBI_PARAMS= GurobiParams(verbose=False) #| None = None

# --- PSO tuning -------------------------------------------------------------
# Tuning signals for ~15 analog blocks with tight DRC spacing:
#   Residual DRC overlaps in result → raise overlap_penalty_w (try 5–10)
#   Particles cluster too early     → raise inertia_w to 0.5–0.7
#   Slow / no improvement           → lower c1, c2 to 0.25 each
#   Canvas too crowded              → raise canvas_factor to 2.2
PSO_CONFIG = PSOConfig(
    swarm_size        = 30,
    max_iter          = 5000,
    inertia_w         = 0.5,
    c1                = 0.4,
    c2                = 0.3,
    canvas_factor     = 1.8,
    overlap_penalty_w = 200.0,
    use_fdgd_init     = True,
)

# --- B*-tree+ILP hybrid tuning ----------------------------------------------
# BSTAR_ILP_SA_CONFIG:    controls the B*-tree SA warm-start inside BStarILPOptimizer.
#   max_iterations=0 → auto-computed as epoch_size × 60 (~30 % of a full SA budget);
#   epoch_size=0      → auto-computed as max(n_blocks × 8, 50).
#   Pass explicit values here to override.  initial_temp is always auto-calibrated.
# BSTAR_ILP_GUROBI_PARAMS: same fields as ILP_GUROBI_PARAMS.
#   use_fdgd_start is False: B*-tree SA already provides a 2D warm start, so FDGD
#   row-pack would overwrite it with a less informative 1D layout.
BSTAR_ILP_SA_CONFIG = SAConfig(
    max_iterations    = 0,       # 0 → epoch_size × 60 (set in BStarILPOptimizer)
    epoch_size        = 0,       # 0 → max(n_blocks × 8, 50)
)
BSTAR_ILP_GUROBI_PARAMS = GurobiParams(
    verbose           = False,
    use_fdgd_start    = False,   # B*-tree SA provides the ordering; no FDGD needed
    time_limit        = 120.0,
    mip_gap           = 0.03,
    no_rel_heur_time  = 5,
)

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
    from bstar_topology    import BStarTopology
    from seqpair_topology  import SequencePairTopology
    from sa_optimizer      import SimulatedAnnealingOptimizer
    from ilp_topology      import ILPTopology
    from ilp_optimizer     import ILPOptimizer
    from pso_topology      import PSOTopology
    from pso_optimizer     import PSOOptimizer
    from pso_ilp_optimizer   import PSOILPOptimizer
    from bstar_ilp_optimizer import BStarILPOptimizer

    topo_map = {
        "BStarTopology":        BStarTopology,
        "SequencePairTopology": SequencePairTopology,
        "ILPTopology":          ILPTopology,
        "PSOTopology":          PSOTopology,
    }
    opt_map = {
        "SimulatedAnnealingOptimizer": SimulatedAnnealingOptimizer,
        "ILPOptimizer":               ILPOptimizer,
        "PSOOptimizer":               PSOOptimizer,
        "PSOILPOptimizer":            PSOILPOptimizer,
        "BStarILPOptimizer":          BStarILPOptimizer,
    }
    t_cls = topo_map.get(TOPOLOGY)
    o_cls = opt_map.get(OPTIMIZER)
    if t_cls is None:
        raise ValueError(f"Unknown TOPOLOGY '{TOPOLOGY}'. Valid: {list(topo_map)}")
    if o_cls is None:
        raise ValueError(f"Unknown OPTIMIZER '{OPTIMIZER}'. Valid: {list(opt_map)}")
    return t_cls, o_cls


def _build_run_entry(result) -> dict:
    """Full per-run dict for exhaustive mode output, including placed_blocks."""
    return {
        "run_id":        result.run_id,
        "topology":      result.topology,
        "optimizer":     result.optimizer,
        "status":        result.status,
        "is_best":       False,
        "final_cost":    round(result.final_cost, 6),
        "area_um2":      round(result.area_um2, 4),
        "hpwl_um":       round(result.hpwl_um, 4),
        "aspect_ratio":  round(result.aspect_ratio, 4),
        "n_iterations":  result.n_iterations,
        "t_seed_ms":     round(result.t_seed_ms, 2),
        "t_optimize_ms": round(result.t_optimize_ms, 2),
        "t_total_ms":    round(result.t_total_ms, 2),
        "placed_blocks": result.placed_blocks,
        "error":         result.error_message or None,
    }


def _renormalize_costs(entries: list, weights) -> None:
    """
    Add renorm_cost to each entry using element-wise best metrics as shared
    normalization references so every ratio is guaranteed >= 1.0.

    ref_area = min(area) across successful runs  → all area ratios >= 1.0
    ref_hpwl = min(hpwl) across successful runs  → all hpwl ratios >= 1.0

    shared_cost(R) = W_A*(R.area/ref_area) + W_WL*(R.hpwl/ref_hpwl) + W_AR*(R.ar-target)²

    renorm_cost(R) = shared_cost(R) / min(shared_cost)   → best = 1.0, others >= 1.0
    Failed runs get None.
    """
    success = [e for e in entries if e["status"] == "success"]
    if not success:
        for e in entries:
            e["renorm_cost"] = None
        return

    ref_area = min(e["area_um2"] for e in success)
    ref_hpwl = min(e["hpwl_um"]  for e in success)

    w_a  = weights.area_weight
    w_wl = weights.wirelength_weight
    w_ar = weights.aspect_ratio_weight
    target_ar = weights.target_aspect_ratio

    def _shared_cost(e: dict) -> float:
        area_term = w_a  * (e["area_um2"] / ref_area) if ref_area > 0.0 else 0.0
        hpwl_term = w_wl * (e["hpwl_um"]  / ref_hpwl) if ref_hpwl > 0.0 else 0.0
        ar_term   = w_ar * (e["aspect_ratio"] - target_ar) ** 2
        return area_term + hpwl_term + ar_term

    shared_costs = {id(e): _shared_cost(e) for e in success}
    min_shared   = min(shared_costs.values())
    denom        = min_shared if min_shared > 0.0 else 1.0

    for e in entries:
        if e["status"] == "success":
            e["renorm_cost"] = round(_shared_cost(e) / denom, 6)
        else:
            e["renorm_cost"] = None


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

    raw_blocks      = data.get("blocks", [])
    netlist         = data.get("netlist", {})
    gen_params      = data.get("generation_params", {})
    blocks          = _build_blocks_dict(raw_blocks)
    nets            = netlist.get("nets", [])
    sym_constraints = data.get("symmetry_constraints", {})
    sym_groups      = sym_constraints.get("groups", []) if sym_constraints else []

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

    # Per-optimizer kwargs — each optimizer only receives its own params.
    # Used in exhaustive/random mode so ILP kwargs don't pollute SA/PSO runs.
    per_opt_kwargs: dict = {}
    if ILP_GUROBI_PARAMS is not None:
        per_opt_kwargs["ILPOptimizer"] = {"gurobi_params": ILP_GUROBI_PARAMS}
    per_opt_kwargs["PSOOptimizer"]      = {"pso_config": PSO_CONFIG}
    per_opt_kwargs["BStarILPOptimizer"] = {
        "bstar_sa_config": BSTAR_ILP_SA_CONFIG,
        "gurobi_params":   BSTAR_ILP_GUROBI_PARAMS,
    }

    if fixed_combo is not None:
        # Single combination selected via TOPOLOGY + OPTIMIZER constants
        t_cls, o_cls = fixed_combo
        single_kwargs = per_opt_kwargs.get(o_cls.__name__, {})
        pipeline = OptimizationPipeline(
            topology_cls     = t_cls,
            optimizer_cls    = o_cls,
            sa_config        = sa_cfg,
            weights          = weights,
            auto_calibrate   = True,
            sym_groups       = sym_groups,
            optimizer_kwargs = single_kwargs,
            use_power_rails  = USE_POWER_RAILS,
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
            sa_config            = sa_cfg,
            weights              = weights,
            auto_calibrate       = True,
            sym_groups           = sym_groups,
            per_optimizer_kwargs = per_opt_kwargs,
            use_power_rails      = USE_POWER_RAILS,
        )
        if RUN_MODE == "exhaustive":
            doc = picker.run_exhaustive(
                blocks, nets, seed_mode=SEED_MODE, netlist_id=netlist_id
            )
            all_results = picker._last_results
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
    is_exhaustive = RUN_MODE == "exhaustive" and len(all_results) > 1

    if is_exhaustive:
        # --- Exhaustive mode: one full entry per run, all with placed_blocks ---
        run_entries = [_build_run_entry(r) for r in all_results]
        if RENORMALIZE:
            _renormalize_costs(run_entries, weights)
            # After renorm the winner is the entry with renorm_cost == 1.0
            best_run_id = next(
                (e["run_id"] for e in run_entries if e.get("renorm_cost") == 1.0),
                best.run_id if best else "",
            )
        else:
            best_run_id = best.run_id if best else ""
        for e in run_entries:
            e["is_best"] = (e["run_id"] == best_run_id)
        placement_meta = {
            "mode":         "exhaustive",
            "seed_mode":    SEED_MODE,
            "best_run_id":  best_run_id,
            "renormalized": RENORMALIZE,
            "runs":         run_entries,
        }
    elif best:
        # --- Single / random mode: flat structure (backward compatible) ---
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
