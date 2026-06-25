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
from warmup_manager    import WarmupConfig

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG     = False
SEED_MODE = "random"      # "random" | "ordered" — initial topology seed strategy

# --- Combination selector ---------------------------------------------------
# Set TOPOLOGY + OPTIMIZER to run exactly one combination.
# Leave both empty to fall back to RUN_MODE (exhaustive or random).
TOPOLOGY  = "ILPTopology"      # "" | "BStarTopology" | "SequencePairTopology" | "ILPTopology" | "PSOTopology"
OPTIMIZER = "ILPOptimizer"  # "" | "SimulatedAnnealingOptimizer" | "ILPOptimizer" | "PSOOptimizer" | "PSOILPOptimizer" | "BStarILPOptimizer"

# Used only when TOPOLOGY/OPTIMIZER are empty:
RUN_MODE  = ""  # "exhaustive" → all supported pairs | "random" → one random pair

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
W_AREA    = 0.55
W_WL      = 0.3
W_AR      = 0.05
W_CLUSTER = 0.10         # device-type bounding-box clustering (nmos_lvt, pmos_rvt, …)
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
    use_corp_init     = True,
)

# --- B*-tree+ILP hybrid tuning ----------------------------------------------
# BSTAR_ILP_SA_CONFIG:    controls the B*-tree SA warm-start inside BStarILPOptimizer.
#   max_iterations=0 → auto-computed as epoch_size × 60 (~30 % of a full SA budget);
#   epoch_size=0      → auto-computed as max(n_blocks × 8, 50).
#   Pass explicit values here to override.  initial_temp is always auto-calibrated.
# BSTAR_ILP_GUROBI_PARAMS: same fields as ILP_GUROBI_PARAMS.
#   use_corp_start is False: B*-tree SA already provides a 2D warm start, so CORP
#   row-pack would overwrite it with a less informative 1D layout.
BSTAR_ILP_SA_CONFIG = SAConfig(
    max_iterations    = 0,       # 0 → epoch_size × 60 (set in BStarILPOptimizer)
    epoch_size        = 0,       # 0 → max(n_blocks × 8, 50)
)
BSTAR_ILP_GUROBI_PARAMS = GurobiParams(
    verbose           = False,
    use_corp_start    = False,   # B*-tree SA provides the ordering; no CORP needed
    time_limit        = 120.0,
    mip_gap           = 0.03,
    no_rel_heur_time  = 5,
)

# --- Warmup multi-start (ILP only) ------------------------------------------
# WARMUP_STRATEGY selects which warm-start heuristic to run N times in parallel.
#   "corp"    — spring-embedding connectivity-ordered row placement
#   "contour" — greedy skyline placer with random block-ordering diversity
#   "spsa"    — SequencePairTopology+SA warm start
# WARMUP_N_RUNS: number of parallel warmup sessions; 0 disables the system
#   and falls back to the single-run CORP inside ILPOptimizer.
# WARMUP_MASTER_SEED: base seed; child seeds are master_seed × 10000 + run_index.
#   Same master_seed always produces exactly the same warmup results.
# WARMUP_VISUALIZE: when True, all warmup placements are saved in the output
#   JSON under placement.warmup_runs so the viewer can display them.
# WARMUP_EXHAUSTIVE_ILP: when True, a full ILP pass is run for each warmup
#   result and N ILP placements are stored for comparison (serial — one Gurobi
#   instance at a time due to license constraints).
# WARMUP_SPSA_TIMEOUT_SEC: wall-clock budget per SPSA run (ignored for other strategies).
WARMUP_STRATEGY         = "spsa"  # "corp" | "contour" | "spsa"
WARMUP_N_RUNS           = 8       # 0 → disabled (use single-run CORP inside ILPOptimizer)
WARMUP_MASTER_SEED      = 42
WARMUP_VISUALIZE        = False
WARMUP_EXHAUSTIVE_ILP   = False
WARMUP_SPSA_TIMEOUT_SEC = 10.0    # wall-clock seconds per SPSA warmup run

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


def _expand_composite_placements(
    composite_list: list,
    placed_blocks:  dict,
    block_by_id:    dict,
    variant_map:    dict | None = None,
) -> dict:
    """
    Enrich placed composite block entries with group metadata and nested sub_blocks.

    For each composite block in placed_blocks, identifies the selected matching
    variant (via variant_map or bbox matching), computes each member device's
    absolute position, and returns an enriched dict keyed by the composite block_id.

    The composite entry keeps the same top-level fields as a regular placed block
    (main_bbox, pins) but gains: group_id, topology_type, matching_variant,
    and sub_blocks — one entry per member device with their absolute main_bbox and
    absolute pin positions.

    Returns {str(comp_id): enriched_composite_dict} — merge into placed_blocks
    in-place; individual member IDs are NOT added to the top-level placed_blocks.
    """
    enriched: dict = {}

    for cb in composite_list:
        comp_id  = cb["block_id"]
        comp_key = str(comp_id)
        if comp_key not in placed_blocks:
            continue

        pb = placed_blocks[comp_key]
        cx = pb["main_bbox"]["x_min"]
        cy = pb["main_bbox"]["y_min"]
        pw = pb["main_bbox"]["x_max"] - cx
        ph = pb["main_bbox"]["y_max"] - cy

        # Select which matching variant was used — prefer explicit variant_map.
        variants  = cb.get("variants", [])
        vidx      = (variant_map or {}).get(comp_key)
        if vidx is not None and 0 <= vidx < len(variants):
            sel_v = variants[vidx]
        else:
            sel_v = None
            for v in variants:
                vw = v["main_bbox"].get("x_max", 0.0)
                vh = v["main_bbox"].get("y_max", 0.0)
                if abs(vw - pw) < 1e-3 and abs(vh - ph) < 1e-3:
                    sel_v = v
                    break
            if sel_v is None:
                sel_v = next((v for v in variants if v.get("is_used")), variants[0] if variants else {})

        rows            = sel_v.get("rows", 1)
        cols_per_device = sel_v.get("cols_per_device", 1)
        dummy_cols      = sel_v.get("dummy_cols_per_side", 0)
        dummy_rows      = sel_v.get("dummy_rows_top_bottom", 0)

        member_bids = cb.get("group_block_ids", [])
        n_devices   = len(member_bids)
        if n_devices == 0:
            continue

        # Sub_blocks: equal contiguous strips of the composite bbox.
        # Horizontal (side by side) when composite is wider than tall; vertical otherwise.
        sub_blocks: dict = {}
        if pw >= ph:
            strip = pw / n_devices
            for i, mbid in enumerate(member_bids):
                sub_blocks[str(mbid)] = {
                    "main_bbox": {
                        "x_min": round(cx + i * strip,         6),
                        "y_min": round(cy,                      6),
                        "x_max": round(cx + (i + 1) * strip,   6),
                        "y_max": round(cy + ph,                 6),
                    },
                    "pins": {"center": {
                        "x": round(cx + (i + 0.5) * strip, 6),
                        "y": round(cy + ph / 2.0,           6),
                    }},
                }
        else:
            strip = ph / n_devices
            for i, mbid in enumerate(member_bids):
                sub_blocks[str(mbid)] = {
                    "main_bbox": {
                        "x_min": round(cx,                      6),
                        "y_min": round(cy + i * strip,         6),
                        "x_max": round(cx + pw,                 6),
                        "y_max": round(cy + (i + 1) * strip,   6),
                    },
                    "pins": {"center": {
                        "x": round(cx + pw / 2.0,           6),
                        "y": round(cy + (i + 0.5) * strip,  6),
                    }},
                }

        # Build the matching_variant summary for the output (metadata only).
        mv_summary = {
            "rows":                  rows,
            "cols_per_device":       cols_per_device,
            "matching_type":         sel_v.get("matching_type") or "",
            "dummy_cols_per_side":   dummy_cols,
            "dummy_rows_top_bottom": dummy_rows,
            "width_um":              sel_v.get("width_um",  round(pw, 6)),
            "height_um":             sel_v.get("height_um", round(ph, 6)),
        }

        enriched[comp_key] = {
            **pb,  # keeps main_bbox and pins from _compute_placed_blocks
            "block_id":        comp_id,
            "device_type":     cb.get("device_type", ""),
            "group_id":        cb.get("group_id", comp_id - 10_000),
            "topology_type":   cb.get("topology_type", ""),
            "matching_variant": mv_summary,
            "sub_blocks":      sub_blocks,
        }

    return enriched


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

    from hierarchy_builder import (
        filter_groups_for_sym_mode,
        build_composite_blocks,
        remap_nets_for_composites,
        COMPOSITE_ID_BASE,
    )

    raw_blocks       = data.get("blocks", [])
    netlist          = data.get("netlist", {})
    gen_params       = data.get("generation_params", {})
    nets             = netlist.get("nets", [])
    placement_config = data.get("placement_config", {})
    sym_mode         = placement_config.get("symmetry_mode", "aggressive")

    # Build composite blocks from hierarchy groups so each matched building
    # block (diff pair, current mirror, …) is placed as one atomic unit whose
    # variants are the pre-computed matching_variants from hierarchy_builder.
    raw_groups      = data.get("groups", [])
    filtered_groups = filter_groups_for_sym_mode(raw_groups, sym_mode)

    block_by_id = {b["block_id"]: b for b in raw_blocks if "error" not in b}
    composite_list, excluded_ids = build_composite_blocks(filtered_groups, block_by_id, nets)

    # Effective block set: composite blocks + ungrouped individual blocks
    effective_raw: list = list(composite_list)
    for blk in raw_blocks:
        if blk.get("block_id") not in excluded_ids and "error" not in blk:
            effective_raw.append(blk)
    blocks = _build_blocks_dict(effective_raw)

    # Remap net pin references so composite members are referenced via the
    # composite block's centre pin (used for HPWL estimation during optimisation).
    effective_nets = remap_nets_for_composites(nets, composite_list, block_by_id)

    # For moderate mode: symmetry is encoded inside each composite block's
    # matching_variants — no inter-composite axis constraints needed.
    # For aggressive mode: additionally enforce global vertical axis constraints
    # between composite pairs that the circuit analyzer placed on the same axis.
    sym_constraints_raw = data.get("symmetry_constraints", {})
    sym_groups: list = []

    if sym_mode == "aggressive":
        # Build mapping: original block_id → composite_id (COMPOSITE_ID_BASE + group_id)
        bid_to_comp: dict = {
            int(mbid): cb["block_id"]
            for cb in composite_list
            for mbid in cb.get("group_block_ids", [])
        }
        for cg in sym_constraints_raw.get("groups", []):
            # Pass 1: classify pairs.
            # Two blocks mapping to different composites → inter-composite pair (axis-mirrored).
            # Two blocks mapping to the SAME composite → that composite is self-symmetric.
            comp_pairs: list = []
            seen_pairs: set = set()
            intra_ss_candidates: list = []
            seen_intra: set = set()

            for a, b in cg.get("pairs", []):
                ca  = bid_to_comp.get(a, a)
                cb_ = bid_to_comp.get(b, b)
                if ca == cb_:
                    if ca not in seen_intra:
                        intra_ss_candidates.append(ca)
                        seen_intra.add(ca)
                else:
                    key = (min(ca, cb_), max(ca, cb_))
                    if key not in seen_pairs:
                        comp_pairs.append([ca, cb_])
                        seen_pairs.add(key)

            # Composites in comp_pairs already have a defined role (left/right of axis).
            # They cannot simultaneously be self-symmetric (would make the ILP infeasible).
            in_pairs: set = {e for pair in comp_pairs for e in pair}

            # Pass 2: build comp_ss, skipping anything already in a pair role.
            comp_ss: list = []
            seen_ss: set = set()

            for ca in intra_ss_candidates:
                if ca not in in_pairs and ca not in seen_ss:
                    comp_ss.append(ca)
                    seen_ss.add(ca)

            for ss in cg.get("self_symmetric", []):
                cid = bid_to_comp.get(ss, ss)
                if cid not in in_pairs and cid not in seen_ss:
                    comp_ss.append(cid)
                    seen_ss.add(cid)

            if comp_pairs or comp_ss:
                sym_groups.append({
                    "compound_id": cg.get("compound_id", 0),
                    "axis": "vertical",
                    "pairs": comp_pairs,
                    "self_symmetric": comp_ss,
                })
        logger.info(
            "Aggressive sym_groups: %d axis group(s) with %d composite pair(s)",
            len(sym_groups),
            sum(len(g["pairs"]) for g in sym_groups),
        )

    logger.info(
        "Symmetry mode: %s  →  %d group(s)  "
        "(%d composite + %d ungrouped = %d effective blocks)",
        sym_mode, len(filtered_groups),
        len(composite_list), len(effective_raw) - len(composite_list), len(effective_raw),
    )

    n_blks     = gen_params.get("num_of_blocks", len(raw_blocks))
    seed       = gen_params.get("seed", 0)
    netlist_id = f"s{seed}_n{n_blks}"

    logger.info(
        "Starting optimizer: %d effective blocks, %d nets — topology=%s optimizer=%s mode=%s",
        len(blocks), len(effective_nets),
        TOPOLOGY or f"({RUN_MODE})", OPTIMIZER or "auto", RUN_MODE,
    )

    weights = CostWeights(
        area_weight              = W_AREA,
        wirelength_weight        = W_WL,
        aspect_ratio_weight      = W_AR,
        target_aspect_ratio      = TARGET_AR,
        device_clustering_weight = W_CLUSTER,
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
    ilp_kwargs: dict = {}
    if ILP_GUROBI_PARAMS is not None:
        ilp_kwargs["gurobi_params"] = ILP_GUROBI_PARAMS
    if WARMUP_N_RUNS > 0:
        ilp_kwargs["warmup_config"] = WarmupConfig(
            strategy         = WARMUP_STRATEGY,
            n_runs           = WARMUP_N_RUNS,
            master_seed      = WARMUP_MASTER_SEED,
            visualize        = WARMUP_VISUALIZE,
            exhaustive_ilp   = WARMUP_EXHAUSTIVE_ILP,
            spsa_timeout_sec = WARMUP_SPSA_TIMEOUT_SEC,
        )
    if ilp_kwargs:
        per_opt_kwargs["ILPOptimizer"] = ilp_kwargs
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
        result = pipeline.run(blocks, effective_nets, seed_mode=SEED_MODE, run_id=run_id)
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
                blocks, effective_nets, seed_mode=SEED_MODE, netlist_id=netlist_id
            )
            all_results = picker._last_results
        else:
            all_results = picker.run_random(blocks, effective_nets, seed_mode=SEED_MODE)

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

    # Enrich composite block entries with group metadata and nested sub_blocks.
    # Composite IDs (≥ 10_000) are kept as top-level keys in placed_blocks so
    # DRC operates on the composite bounding box; individual member positions
    # are nested inside each composite's sub_blocks dict.
    if best is not None and composite_list:
        expanded = _expand_composite_placements(
            composite_list, best.placed_blocks, block_by_id, best.variant_map
        )
        best.placed_blocks.update(expanded)
        logger.info(
            "Composite expansion: enriched %d group block(s) with sub_blocks", len(expanded)
        )

    # Same enrichment for every exhaustive run result so all placed_blocks are consistent.
    if RUN_MODE == "exhaustive" and composite_list:
        for r in all_results:
            if r.status == "success" and r.placed_blocks:
                exp = _expand_composite_placements(
                    composite_list, r.placed_blocks, block_by_id, r.variant_map
                )
                r.placed_blocks.update(exp)

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
        if best.warmup_runs:
            placement_meta["warmup_runs"] = best.warmup_runs

    return {
        "generation_params":    gen_params,
        "technology":           data.get("technology", ""),
        "placement_config":     placement_config,
        "blocks":               raw_blocks,
        "netlist":              netlist,
        "symmetry_constraints": data.get("symmetry_constraints", {}),
        "groups":               data.get("groups", []),
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
