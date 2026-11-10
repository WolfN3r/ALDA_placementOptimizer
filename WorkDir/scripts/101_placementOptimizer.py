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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup      import get_logger
from ilp_optimizer     import GurobiParams
from pso_optimizer     import PSOConfig
from spacing           import GRID
from sa_optimizer      import SAConfig
from warmup_manager    import WarmupConfig
from reference_baseline import compute_contour_baseline

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG     = False
SEED_MODE = "random"      # "random" | "ordered" — initial topology seed strategy

# --- Cost-over-time tracing (opt-in, off by default) -------------------------
# When True, every optimizer/warmup run logs its shared-CostEvaluator
# breakdown (area/HPWL/AR/cost) vs. wall-clock time to
# WorkDir/traces/<session_id>/<run_id>.jsonl, plus one manifest.json per
# session listing every run. Driven by the viewer's Analysis tool; see
# lib/cost_trace.py. Zero overhead when False.
SAVE_COST_TRACE = False
_TRACES_DIR     = Path(__file__).parent.parent / "traces"

# --- Combination selector ---------------------------------------------------
# Set TOPOLOGY + OPTIMIZER to run exactly one combination.
# Leave both empty to fall back to RUN_MODE (exhaustive or random).
TOPOLOGY  = "ILPTopology"      # "" | "BStarTopology" | "SequencePairTopology" | "ILPTopology" | "PSOTopology"
OPTIMIZER = "ILPOptimizer"  # "" | "SimulatedAnnealingOptimizer" | "ILPOptimizer" | "PSOOptimizer"

# Used only when TOPOLOGY/OPTIMIZER are empty:
RUN_MODE  = ""  # "exhaustive" → all supported pairs | "random" → one random pair

# --- Cost-normalization reference baseline ----------------------------------
# Before any optimizer runs, a shared reference placement is computed via
# CONTOUR_BASELINE_N_RUNS parallel ContourWarmup sessions — the MEDIAN-cost
# one is kept (a "decent, unremarkable" yardstick, not a best-of-N target).
# Its raw area/HPWL become init_area/init_wl for every (topology, optimizer)
# pair run in this invocation — single combo, random, or exhaustive — so
# every run's final_cost shares the same denominator and is directly
# comparable, instead of each pair normalizing against its own random-seeded
# start. See .claude/plans/contour_reference_baseline.md.
# This is orthogonal to WARMUP_STRATEGY/WARMUP_N_RUNS below: that mechanism
# picks where the ILP optimizer starts its search; this one picks what "1.0"
# means for cost comparison across every optimizer.
USE_CONTOUR_BASELINE     = True
CONTOUR_BASELINE_N_RUNS  = 9   # odd → a true middle run; median = index n//2
CONTOUR_BASELINE_SEED    = 42

# --- SA tuning (0 → auto-computed from n_blocks) ----------------------------
SA_INITIAL_TEMP = 0.0    # auto-calibrated when 0.0
SA_FINAL_TEMP   = 1e-4
SA_MAX_ITER     = 0      # 0 → epoch_size × 200
SA_EPOCH_SIZE   = 0      # 0 → max(n_blocks × 8, 50)
SA_STAGNATION   = 15     # epochs without improvement before reheating

# --- Cost weights (must sum to 1.0) -----------------------------------------
W_AREA    = 1
W_WL      = 1
W_AR      = 1
TARGET_AR = 1        # target width/height ratio for the full placement

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

# --- Warmup multi-start (ILP only) ------------------------------------------
# WARMUP_STRATEGY selects which warm-start heuristic to run N times in parallel.
#   "corp"    — spring-embedding connectivity-ordered row placement
#   "contour" — greedy skyline placer with random block-ordering diversity
#   "spring"  — paper-faithful FDGD spring embedding
#   "spsa"    — SequencePairTopology+SA warm start
#   "pso"     — short PSOTopology+PSOOptimizer warm start
#   "bstar"   — short BStarTopology+SA warm start
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
# Note: RUN_MODE == "exhaustive" ignores WARMUP_STRATEGY/WARMUP_EXHAUSTIVE_ILP for
# the ILP pair and instead tries every strategy above once each, keeping the best
# (see WarmupConfig.all_strategies / WarmupManager.run_all_strategies()).
WARMUP_STRATEGY         = "spsa"  # "corp" | "contour" | "spring" | "spsa" | "pso" | "bstar"
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
        "trace_file":    result.trace_file,
    }


def _build_warmup_run_entries(result) -> list[dict]:
    """
    Expand one ILP PipelineResult's warmup_runs into one full run-entry dict
    per warmup-strategy candidate, so exhaustive mode shows every strategy
    (CORP+ILP, SPSA+ILP, PSO+ILP, ...) as its own tab instead of collapsing
    them into a single ambiguous 'ILPTopology+ILPOptimizer' entry.
    """
    strategies = [w.get("strategy", "") for w in result.warmup_runs]
    dup = {s for s in strategies if strategies.count(s) > 1}

    entries: list[dict] = []
    for w in result.warmup_runs:
        strategy = w.get("strategy", "?")
        suffix   = strategy if strategy not in dup else f"{strategy}_s{w.get('seed', 0)}"
        t_opt    = round(w.get("t_optimize_ms", 0.0), 2)
        entries.append({
            "run_id":          f"{result.topology}+{result.optimizer}::{suffix}",
            "topology":        result.topology,
            "optimizer":       result.optimizer,
            "warmup_strategy": strategy,
            "status":          "success",
            "is_best":         False,
            "final_cost":      round(w.get("cost", 0.0), 6),
            "area_um2":        round(w.get("area_um2", 0.0), 4),
            "hpwl_um":         round(w.get("hpwl_um", 0.0), 4),
            "aspect_ratio":    round(w.get("aspect_ratio", 1.0), 4),
            "n_iterations":    1,
            "t_seed_ms":       0.0,
            "t_optimize_ms":   t_opt,
            "t_total_ms":      t_opt,
            "placed_blocks":   w.get("placed_blocks", {}),
            "error":           None,
            "trace_file":      w.get("trace_file", ""),
        })
    return entries


def _write_trace_manifest(
    trace_dir:    str,
    session_id:   str,
    netlist_id:   str,
    symmetry_mode: str,
    all_results:  list,
    weights,
) -> None:
    """
    Write manifest.json for this session — the index the viewer's Analysis
    tool reads to discover which trace files exist and how to label them.

    Always expands each result's warmup_runs into one entry per warmup
    strategy (same as the exhaustive-mode run_entries construction) rather
    than only doing so when RUN_MODE == "exhaustive": a single fixed
    ILPTopology+ILPOptimizer combo can itself carry multiple warmup-strategy
    sub-results (WarmupConfig.all_strategies), each with its own trace file,
    and those must not collapse into the one merged entry.
    """
    full_entries: list[dict] = []
    for r in all_results:
        if r.optimizer == "ILPOptimizer" and r.warmup_runs:
            full_entries.extend(_build_warmup_run_entries(r))
        elif r.status == "success":
            full_entries.append(_build_run_entry(r))

    entries = [
        {
            "run_id":          e["run_id"],
            "warmup_strategy": e.get("warmup_strategy", ""),
            "topology":        e["topology"],
            "optimizer":       e["optimizer"],
            "trace_file":      e.get("trace_file", ""),
            "final_cost":      e["final_cost"],
            "area_um2":        e["area_um2"],
            "hpwl_um":         e["hpwl_um"],
            "aspect_ratio":    e["aspect_ratio"],
        }
        for e in full_entries
    ]

    manifest = {
        "session_id":    session_id,
        "netlist_id":    netlist_id,
        "symmetry_mode": symmetry_mode,
        "timestamp":     time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "weights": {
            "area_weight":         weights.area_weight,
            "wirelength_weight":   weights.wirelength_weight,
            "aspect_ratio_weight": weights.aspect_ratio_weight,
            "target_aspect_ratio": weights.target_aspect_ratio,
        },
        "runs":          entries,
    }
    manifest_path = Path(trace_dir) / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Cost trace manifest written: %s (%d runs)", manifest_path, len(entries))


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
        build_composite_blocks,
        SYM_MODE_LEVELS,
        LEGACY_SYM_MODES,
        remap_nets_for_composites,
        COMPOSITE_ID_BASE,
    )

    raw_blocks       = data.get("blocks", [])
    netlist          = data.get("netlist", {})
    gen_params       = data.get("generation_params", {})
    nets             = netlist.get("nets", [])
    placement_config = data.get("placement_config", {})
    sym_mode         = placement_config.get("symmetry_mode", "balanced")
    sym_mode         = LEGACY_SYM_MODES.get(sym_mode, sym_mode)
    if sym_mode not in SYM_MODE_LEVELS:
        raise KeyError(f"optimize: unknown symmetry_mode '{sym_mode}'")

    # Build composite blocks from hierarchy groups so each matched building
    # block (diff pair, current mirror, …) is placed as one atomic unit whose
    # variants are the pre-computed matching_variants from hierarchy_builder.
    raw_groups      = data.get("groups", [])

    block_by_id = {b["block_id"]: b for b in raw_blocks if "error" not in b}
    composite_list, excluded_ids = build_composite_blocks(raw_groups, block_by_id, nets)

    # Effective block set: composite blocks + ungrouped individual blocks
    effective_raw: list = list(composite_list)
    for blk in raw_blocks:
        if blk.get("block_id") not in excluded_ids and "error" not in blk:
            effective_raw.append(blk)
    blocks = _build_blocks_dict(effective_raw)

    # Remap net pin references so composite members are referenced via the
    # composite block's centre pin (used for HPWL estimation during optimisation).
    effective_nets = remap_nets_for_composites(nets, composite_list, block_by_id)

    # Axis constraints from the group symmetry annotations (hierarchy_builder):
    # a "self" group is centred on its axis, a "pair" group (side L) is mirrored
    # with its partner (side R), same variant on both sides. A group is one node —
    # its composite, or its single device; a self group without a composite falls
    # back to its member devices.
    levels = SYM_MODE_LEVELS[sym_mode]
    comp_of_group = {cb["group_id"]: cb["block_id"] for cb in composite_list}
    group_by_id = {g["group_id"]: g for g in raw_groups}

    def _node(g: dict):
        if g["group_id"] in comp_of_group:
            return comp_of_group[g["group_id"]]
        members = [b for b in g["block_ids"] if b in block_by_id]
        return members[0] if len(members) == 1 else None

    axis_self: dict = {}
    axis_pairs: dict = {}
    for g in raw_groups:
        sym = g.get("symmetry")
        if not sym or sym["level"] not in levels:
            continue
        if sym["role"] == "self":
            node = _node(g)
            nodes = [node] if node is not None else [b for b in g["block_ids"] if b in block_by_id]
            axis_self.setdefault(sym["axis_id"], []).extend(nodes)
        elif sym["side"] == "L":
            left, right = _node(g), _node(group_by_id[sym["partner"]])
            if left is None or right is None:
                logger.warning("Pair groups %d/%d have no single node — not mirrored",
                               g["group_id"], sym["partner"])
                continue
            axis_pairs.setdefault(sym["axis_id"], []).append([left, right])

    def _n_variants(node) -> int:
        return len(blocks[str(node)]["variants"])

    sym_groups: list = []
    for axis_id in sorted(set(axis_self) | set(axis_pairs)):
        pairs, selfs = axis_pairs.get(axis_id, []), axis_self.get(axis_id, [])
        if 2 * len(pairs) + len(selfs) < 2:
            continue
        sym_groups.append({
            "compound_id":               axis_id,
            "axis":                      "vertical",
            "pairs":                     pairs,
            "self_symmetric":            selfs,
            "enforce_matching_variants": bool(pairs) and all(
                _n_variants(a) == _n_variants(b) for a, b in pairs),
        })
    # Self nodes are centred on one axis (origin = axis - w/2): all origins are on the
    # grid only when every width has the same grid parity. Pad odd widths by one step;
    # the device then sits GRID/2 (2.5 nm) off its axis.
    for g in sym_groups:
        for node in g["self_symmetric"]:
            for v in blocks[str(node)]["variants"]:
                bb = v["main_bbox"]
                if round((bb["x_max"] - bb["x_min"]) / GRID) % 2:
                    bb["x_max"] = round(bb["x_max"] + GRID, 6)
                    logger.debug("Self node %s: width padded to %.4f (even grid count)",
                                 node, bb["x_max"] - bb["x_min"])

    logger.info(
        "Symmetry mode %s: %d axis group(s), %d self node(s), %d mirrored pair(s)",
        sym_mode, len(sym_groups), sum(len(g["self_symmetric"]) for g in sym_groups),
        sum(len(g["pairs"]) for g in sym_groups),
    )

    logger.info(
        "Symmetry mode: %s  →  %d group(s)  "
        "(%d composite + %d ungrouped = %d effective blocks)",
        sym_mode, len(raw_groups),
        len(composite_list), len(effective_raw) - len(composite_list), len(effective_raw),
    )

    n_blks     = gen_params.get("num_of_blocks", len(raw_blocks))
    seed       = gen_params.get("seed", 0)
    netlist_id = f"s{seed}_n{n_blks}"

    session_id = f"{netlist_id}_{time.strftime('%Y%m%dT%H%M%S')}"
    trace_dir  = str(_TRACES_DIR / session_id) if SAVE_COST_TRACE else None

    logger.info(
        "Starting optimizer: %d effective blocks, %d nets — topology=%s optimizer=%s mode=%s",
        len(blocks), len(effective_nets),
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
            all_strategies   = RUN_MODE == "exhaustive",  # try every warmup strategy, keep best
            spsa_timeout_sec = WARMUP_SPSA_TIMEOUT_SEC,
            sym_groups       = sym_groups,
        )
    if ilp_kwargs:
        per_opt_kwargs["ILPOptimizer"] = ilp_kwargs
    per_opt_kwargs["PSOOptimizer"]      = {"pso_config": PSO_CONFIG}

    # Shared, a-priori cost-normalization reference — computed once, before any
    # optimizer runs, so every (topology, optimizer) pair below (whether a
    # single fixed combo or the full picker) scores against the same
    # denominator. See USE_CONTOUR_BASELINE above and
    # .claude/plans/contour_reference_baseline.md.
    reference_baseline = None
    if USE_CONTOUR_BASELINE:
        reference_baseline = compute_contour_baseline(
            blocks, effective_nets,
            n_runs          = CONTOUR_BASELINE_N_RUNS,
            master_seed     = CONTOUR_BASELINE_SEED,
            use_power_rails = USE_POWER_RAILS,
        )
        logger.info(
            "Contour reference baseline: area=%.2f µm²  hpwl=%.2f µm  (median of %d)",
            reference_baseline.init_area, reference_baseline.init_wl, CONTOUR_BASELINE_N_RUNS,
        )

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
            save_trace       = SAVE_COST_TRACE,
            trace_dir        = trace_dir,
            reference_baseline = reference_baseline,
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
            save_trace           = SAVE_COST_TRACE,
            trace_dir            = trace_dir,
            reference_baseline   = reference_baseline,
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
            # Each warmup-strategy candidate carries its own placed_blocks — expand those too.
            for w in r.warmup_runs:
                if w.get("placed_blocks"):
                    exp_w = _expand_composite_placements(
                        composite_list, w["placed_blocks"], block_by_id, w.get("variant_map", {})
                    )
                    w["placed_blocks"].update(exp_w)

    placement_meta: dict = {}
    is_exhaustive = RUN_MODE == "exhaustive" and len(all_results) > 1

    if is_exhaustive:
        # --- Exhaustive mode: one full entry per run, all with placed_blocks ---
        # ILP results carrying warmup_runs are expanded into one entry per
        # warmup strategy (CORP+ILP, SPSA+ILP, ...) instead of one merged entry,
        # so every strategy that was actually run is visible, not just the winner.
        run_entries: list[dict] = []
        for r in all_results:
            if r.optimizer == "ILPOptimizer" and r.warmup_runs:
                run_entries.extend(_build_warmup_run_entries(r))
            else:
                run_entries.append(_build_run_entry(r))

        # final_cost is already directly comparable across runs — every pair
        # shares the same contour-baseline denominator (see USE_CONTOUR_BASELINE
        # above) — so no post-hoc rescaling is needed to rank them.
        successful = [e for e in run_entries if e["status"] == "success"]
        best_run_id = min(successful, key=lambda e: e["final_cost"])["run_id"] if successful else ""
        if not best_run_id and run_entries:
            best_run_id = run_entries[0]["run_id"]
        for e in run_entries:
            e["is_best"] = (e["run_id"] == best_run_id)
        placement_meta = {
            "mode":         "exhaustive",
            "seed_mode":    SEED_MODE,
            "best_run_id":  best_run_id,
            "runs":         run_entries,
        }
        if reference_baseline is not None:
            placement_meta["reference_baseline"] = {
                "area_um2": round(reference_baseline.init_area, 4),
                "hpwl_um":  round(reference_baseline.init_wl, 4),
                "n_runs":   CONTOUR_BASELINE_N_RUNS,
                "seed":     CONTOUR_BASELINE_SEED,
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
        if reference_baseline is not None:
            placement_meta["reference_baseline"] = {
                "area_um2": round(reference_baseline.init_area, 4),
                "hpwl_um":  round(reference_baseline.init_wl, 4),
                "n_runs":   CONTOUR_BASELINE_N_RUNS,
                "seed":     CONTOUR_BASELINE_SEED,
            }

    if SAVE_COST_TRACE and trace_dir:
        _write_trace_manifest(trace_dir, session_id, netlist_id, sym_mode, all_results, weights)

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
