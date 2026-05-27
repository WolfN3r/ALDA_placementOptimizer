"""
ILP placement optimizer — solves one MILP to place all blocks optimally.

Enforces non-overlap with PDK-aware DRC spacing (from spacing.py LUT),
multi-variant block selection, vertical symmetry groups, and HPWL connectivity.
Uses gurobipy directly (academic or commercial license required).

Accepts SAConfig for pipeline interface parity; ignores all SA-specific fields.
Objective weights (area vs. HPWL) are read from CostEvaluator so results are
comparable with B*+SA and SP+SA runs on the same JSON.

ML parameter injection: set ILP_GUROBI_PARAMS in 101_placementOptimizer.py to a
GurobiParams instance before calling optimize() to override solver parameters.
"""
from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import dataclasses
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from spacing import compute_block_spacing
from fdgd    import run_fdgd
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG            = False
ILP_LARGE_N_WARN = 20   # log warning when n_blocks exceeds this


@dataclasses.dataclass
class GurobiParams:
    """
    Gurobi solver parameters. All fields are ML-tunable.
    Defaults give a good general baseline; ML can override per netlist.

    Fields that depend most on netlist structure (high ML-tuning priority):
      mip_focus, symmetry, cuts, heuristics
    """

    threads: int = 16
    # Parallel B&B threads. Scales well to physical core count.
    # More threads → faster wall-clock; no benefit beyond physical cores.

    time_limit: float = 500.0
    # Hard wall-clock limit in seconds. Solver returns best incumbent found so far.

    mip_gap: float = 0.03
    # Stop when gap between best incumbent and LP bound ≤ this fraction.
    # Tighter → longer solve; 1% is negligible for layout quality.

    mip_focus: int = 1
    # 0=balanced, 1=feasibility first, 2=optimality, 3=best-bound.
    # Small/easy netlists: use 2 (prove optimum fast).
    # Large/hard netlists: use 1 (find any feasible solution first).

    cuts: int = 2
    # Global cut aggressiveness: -1=auto, 0=none, 1=moderate, 2=aggressive, 3=very.
    # Big-M non-overlap constraints benefit from 2–3; sparse netlists often 0–1.

    mir_cuts: int = 2
    # Mixed-Integer Rounding cuts. Especially effective with big-M formulations.
    # -1=auto, 0=off, 1=moderate, 2=aggressive.

    implied_cuts: int = 2
    # Implied-bound cuts derived from constraint structure.
    # Tightens LP relaxation without adding new constraints. -1=auto, 0–2.

    symmetry: int = 2
    # Symmetry detection aggressiveness: 0=none, 1=conservative, 2=aggressive.
    # Strongly correlated with number of symmetry groups in the netlist.

    heuristics: float = 0.2
    # Fraction of B&B time spent on MIP heuristics (0.0–1.0).
    # Tightly-coupled netlists: higher value finds a good incumbent earlier.

    no_rel_heur_time: int = 30
    # Seconds of NoRel heuristic run before B&B starts.
    # Useful when problem is highly integer-feasible (tight netlists with warm start).

    improve_start_gap: float = 0.5
    # Switch from heuristic improvement to B&B when gap falls below this fraction.

    verbose: bool = False
    # True → print Gurobi B&B log to console. Use for diagnostics.
    # Key lines to read: "Root relaxation" (LP gap), "MIP gap" at time limit,
    # "Explored N nodes" (large N = loose LP relaxation, not a thread problem).

    log_file: str = ""
    # Write full Gurobi log to this path (e.g. "logs/gurobi_ilp.log").
    # Non-empty value also sets verbose=True automatically inside Gurobi.
    # Use m.write("model.lp") (add temporarily in _solve_mip_gurobi) to export
    # the LP for inspection in Gurobi's interactive shell.

    use_fdgd_start: bool = True
    # True → run FDGD before solving, sort blocks by FDGD x-centroid, row-pack to
    # produce a DRC-clean feasible layout, and inject it as a complete MIP start
    # (all binary AND continuous variables set).  This gives Gurobi a verified
    # initial incumbent at node 0, tightening pruning from the first B&B split.
    # False → use plain row-pack as warm start (faster pre-solve, worse initial bound).


# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _variant_dims(block: dict) -> list[tuple[float, float]]:
    """Return [(w, h), ...] for every variant of block."""
    dims = []
    for v in block.get("variants", []):
        bb = v.get("main_bbox", {})
        dims.append((bb.get("x_max", 0.0), bb.get("y_max", 0.0)))
    return dims if dims else [(0.0, 0.0)]


def _big_m(bids: list[str], blocks: dict) -> tuple[float, float]:
    """
    Return (M_x, M_y) = sum-of-all-widths/heights + max pairwise spacing.

    The +max_spacing term is required for correctness: without it, the
    big-M constraints for an inactive r-flag (rv=0) can become binding,
    letting the LP relaxation place blocks at overlapping positions with
    fractional r-vars.
    """
    M_x = sum(max(d[0] for d in _variant_dims(blocks[bid])) for bid in bids)
    M_y = sum(max(d[1] for d in _variant_dims(blocks[bid])) for bid in bids)
    if len(bids) >= 2:
        max_ax = max_ay = 0.0
        for bi in bids:
            for bj in bids:
                if bi != bj:
                    sr = compute_block_spacing(blocks[bi], blocks[bj])
                    if sr.x_spacing > max_ax:
                        max_ax = sr.x_spacing
                    if sr.y_spacing > max_ay:
                        max_ay = sr.y_spacing
        M_x += max_ax
        M_y += max_ay
    return max(M_x, 1.0), max(M_y, 1.0)


def _r_hints(
    bids:      list[str],
    positions: dict[str, tuple[float, float]],
    blocks:    dict,
) -> dict[tuple[str, str], int]:
    """
    Return {(bi, bj): k} where k ∈ {0,1,2,3} is the best-satisfied direction
    for the seed positions. Used as MIP start hint for the r-flag variables.
    """
    hints: dict[tuple[str, str], int] = {}
    n = len(bids)
    for ai in range(n):
        for aj in range(ai + 1, n):
            bi, bj = bids[ai], bids[aj]
            xi, yi = positions.get(bi, (0.0, 0.0))
            xj, yj = positions.get(bj, (0.0, 0.0))
            wi = _variant_dims(blocks[bi])[0][0]
            hi = _variant_dims(blocks[bi])[0][1]
            wj = _variant_dims(blocks[bj])[0][0]
            hj = _variant_dims(blocks[bj])[0][1]
            gaps = [
                xj - (xi + wi),   # k=0: i left of j
                yj - (yi + hi),   # k=1: i below j
                xi - (xj + wj),   # k=2: j left of i
                yi - (yj + hj),   # k=3: j below i
            ]
            hints[(bi, bj)] = int(max(range(4), key=lambda k: gaps[k]))
    return hints


def _fdgd_row_pack(
    bids:           list[str],
    blocks:         dict,
    fdgd_centroids: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """
    Convert FDGD centroids to a DRC-clean feasible layout.
    Sorts blocks by FDGD x-centroid (connectivity-aware ordering), then
    row-packs left-to-right with correct DRC spacing between each pair.
    Returns bottom-left corner positions. Always overlap-free.
    """
    sorted_bids = sorted(bids, key=lambda b: fdgd_centroids.get(b, (0.0, 0.0))[0])
    positions: dict[str, tuple[float, float]] = {}
    x_cursor = 0.0
    prev: str | None = None
    for bid in sorted_bids:
        w = _variant_dims(blocks[bid])[0][0]
        if prev is not None:
            x_cursor += compute_block_spacing(blocks[prev], blocks[bid]).x_spacing
        positions[bid] = (round(x_cursor, 6), 0.0)
        x_cursor += w
        prev = bid
    return positions


def _solve_mip_gurobi(
    bids:           list[str],
    blocks:         dict,
    nets:           list,
    sym_groups:     list,
    area_weight:    float,
    wl_weight:      float,
    warm_positions: dict[str, tuple[float, float]],
    params:         GurobiParams,
    hint_positions: dict[str, tuple[float, float]] | None = None,
) -> tuple[dict[str, tuple[float, float]], dict[str, int], str]:
    """
    Build and solve the analog placement MILP with gurobipy.
    Returns (positions, variant_map, termination) where termination is
    "optimal", "feasible", or "infeasible".
    Falls back to warm_positions when the solver finds no feasible point.
    """
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise ImportError(
            "gurobipy is not installed. Obtain a free academic license at "
            "https://www.gurobi.com/academia/academic-program-and-licenses/ "
            "then: pip install gurobipy"
        ) from exc

    n = len(bids)
    bid_set = set(bids)
    M_x, M_y = _big_m(bids, blocks)

    m = gp.Model("analog_placement")
    m.Params.OutputFlag       = 1 if (params.verbose or params.log_file) else 0
    if params.log_file:
        m.Params.LogFile      = params.log_file
    m.Params.Threads          = params.threads
    m.Params.TimeLimit        = params.time_limit
    m.Params.MIPGap           = params.mip_gap
    m.Params.MIPFocus         = params.mip_focus
    m.Params.Cuts             = params.cuts
    m.Params.MIRCuts          = params.mir_cuts
    m.Params.ImpliedCuts      = params.implied_cuts
    m.Params.Symmetry         = params.symmetry
    m.Params.Heuristics       = params.heuristics
    m.Params.NoRelHeurTime    = params.no_rel_heur_time
    m.Params.ImproveStartGap  = params.improve_start_gap

    # Canvas bounding-box variables
    W = m.addVar(lb=0.0, ub=M_x, name="W")
    H = m.addVar(lb=0.0, ub=M_y, name="H")

    # Block position variables
    x: dict[str, Any] = {bid: m.addVar(lb=0.0, ub=M_x, name=f"x_{bid}") for bid in bids}
    y: dict[str, Any] = {bid: m.addVar(lb=0.0, ub=M_y, name=f"y_{bid}") for bid in bids}

    # Variant selection
    all_dims: dict[str, list[tuple[float, float]]] = {bid: _variant_dims(blocks[bid]) for bid in bids}
    w: dict[str, Any] = {}
    h: dict[str, Any] = {}
    s: dict[str, list] = {}

    for bid in bids:
        dims = all_dims[bid]
        if len(dims) == 1:
            w[bid] = dims[0][0]
            h[bid] = dims[0][1]
            s[bid] = []
        else:
            s[bid] = [m.addVar(vtype=GRB.BINARY, name=f"s_{bid}_{k}") for k in range(len(dims))]
            m.addConstr(gp.quicksum(s[bid]) == 1, name=f"var_sel_{bid}")
            w[bid] = gp.quicksum(dims[k][0] * s[bid][k] for k in range(len(dims)))
            h[bid] = gp.quicksum(dims[k][1] * s[bid][k] for k in range(len(dims)))

    # Boundary constraints
    for bid in bids:
        m.addConstr(x[bid] + w[bid] <= W, name=f"bnd_x_{bid}")
        m.addConstr(y[bid] + h[bid] <= H, name=f"bnd_y_{bid}")

    # Valid inequality: W*H >= total_block_area, and by AM-GM W+H >= 2*sqrt(area).
    # Lifts the LP lower bound on the area objective term by ~6 µm for n=10,
    # reducing the root LP gap from ~14% toward ~5%.
    total_area_lb = sum(min(wd * ht for wd, ht in all_dims[bid]) for bid in bids)
    if total_area_lb > 0.0:
        m.addConstr(W + H >= 2.0 * math.sqrt(total_area_lb), name="bbox_area_lb")

    # Non-overlap — 4 big-M inequalities per ordered pair, sum >= 1
    r_vars: dict[tuple[str, str], list] = {}
    for ai in range(n):
        for aj in range(ai + 1, n):
            bi, bj = bids[ai], bids[aj]
            sr = compute_block_spacing(blocks[bi], blocks[bj])
            ax, ay = sr.x_spacing, sr.y_spacing
            rv = [m.addVar(vtype=GRB.BINARY, name=f"r_{bi}_{bj}_{k}") for k in range(4)]
            r_vars[(bi, bj)] = rv
            # k=0: i is left of j
            m.addConstr(x[bi] + w[bi] + ax <= x[bj] + M_x * (1 - rv[0]), name=f"no_{bi}_{bj}_0")
            # k=1: i is below j
            m.addConstr(y[bi] + h[bi] + ay <= y[bj] + M_y * (1 - rv[1]), name=f"no_{bi}_{bj}_1")
            # k=2: j is left of i
            m.addConstr(x[bj] + w[bj] + ax <= x[bi] + M_x * (1 - rv[2]), name=f"no_{bi}_{bj}_2")
            # k=3: j is below i
            m.addConstr(y[bj] + h[bj] + ay <= y[bi] + M_y * (1 - rv[3]), name=f"no_{bi}_{bj}_3")
            m.addConstr(gp.quicksum(rv) >= 1, name=f"no_sum_{bi}_{bj}")

    # Symmetry constraints — vertical axis only
    for gi, group in enumerate(sym_groups):
        axis = group.get("axis", "vertical")
        if axis != "vertical":
            logger.warning("ILP: group %d axis '%s' not supported — skipped", gi, axis)
            continue
        x_sym = m.addVar(lb=0.0, name=f"x_sym_{gi}")

        for pair in group.get("pairs", []):
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            a, b = str(pair[0]), str(pair[1])
            if a not in bid_set or b not in bid_set:
                continue
            m.addConstr(x[a] + x[b] + w[a] == 2 * x_sym, name=f"sym_x_{gi}_{a}_{b}")
            m.addConstr(y[a] == y[b],                      name=f"sym_y_{gi}_{a}_{b}")
            # pair[0] is designated left partner — prevents ABAB interleaving and
            # eliminates the symmetric ABBA solution family, halving the search space.
            m.addConstr(x[a] + w[a] <= x_sym,             name=f"sym_left_{gi}_{a}")
            if s[a] and s[b] and len(s[a]) == len(s[b]):
                for k in range(len(s[a])):
                    m.addConstr(s[a][k] == s[b][k], name=f"sym_var_{gi}_{a}_{b}_{k}")

        for ss in group.get("self_symmetric", []):
            ss_bid = str(ss)
            if ss_bid not in bid_set:
                continue
            m.addConstr(2 * x[ss_bid] + w[ss_bid] == 2 * x_sym, name=f"sym_self_{gi}_{ss_bid}")

    # HPWL — O(m·deg) per-net min/max formulation.
    # 4 variables per net (x_lo, x_hi, y_lo, y_hi) + 4 constraints per block in net.
    # Correct for k>2-pin nets; replaces the previous O(m²) pairwise bounds.
    # Power nets (VDD/VSS) are excluded: they connect to most blocks and are served
    # by the power grid, not individual wires. Including them creates a very loose LP
    # relaxation (LP can pull all k=7 blocks to the same fractional point → ~40% gap).
    x_lo: dict[int, Any] = {}
    x_hi: dict[int, Any] = {}
    y_lo: dict[int, Any] = {}
    y_hi: dict[int, Any] = {}
    hpwl_bids: dict[int, list[str]] = {}   # ei → bids for warm-start computation

    for ei, net in enumerate(nets):
        if net.get("net_type") == "power":
            continue
        net_bids: list[str] = []
        for pin in net.get("pins", []):
            if pin.startswith("B"):
                parts = pin[1:].split("_", 1)
                nbid = parts[0] if parts else ""
                if nbid in bid_set and nbid not in net_bids:
                    net_bids.append(nbid)
        if len(net_bids) < 2:
            continue

        hpwl_bids[ei] = net_bids
        x_lo[ei] = m.addVar(lb=0.0,         name=f"xlo_{ei}")
        x_hi[ei] = m.addVar(lb=0.0, ub=M_x, name=f"xhi_{ei}")
        y_lo[ei] = m.addVar(lb=0.0,         name=f"ylo_{ei}")
        y_hi[ei] = m.addVar(lb=0.0, ub=M_y, name=f"yhi_{ei}")

        for nbid in net_bids:
            dims = all_dims[nbid]
            if not s[nbid]:
                xc = x[nbid] + dims[0][0] / 2.0
                yc = y[nbid] + dims[0][1] / 2.0
            else:
                xc = x[nbid] + gp.quicksum(dims[k][0] / 2.0 * s[nbid][k] for k in range(len(dims)))
                yc = y[nbid] + gp.quicksum(dims[k][1] / 2.0 * s[nbid][k] for k in range(len(dims)))
            m.addConstr(x_lo[ei] <= xc, name=f"hpwl_xlo_{ei}_{nbid}")
            m.addConstr(x_hi[ei] >= xc, name=f"hpwl_xhi_{ei}_{nbid}")
            m.addConstr(y_lo[ei] <= yc, name=f"hpwl_ylo_{ei}_{nbid}")
            m.addConstr(y_hi[ei] >= yc, name=f"hpwl_yhi_{ei}_{nbid}")

    # Objective
    n_nets_used = max(len(x_lo), 1)
    hpwl_expr = gp.quicksum(
        (x_hi[ei] - x_lo[ei]) + (y_hi[ei] - y_lo[ei]) for ei in x_lo
    ) if x_lo else 0.0
    m.setObjective(
        area_weight * (W + H) + (wl_weight / n_nets_used) * hpwl_expr,
        GRB.MINIMIZE,
    )

    # Complete MIP warm start from warm_positions (a DRC-clean feasible layout).
    # Setting ALL variables (binary + continuous) lets Gurobi accept the start as a
    # verified incumbent at node 0, tightening pruning from the first B&B split.
    # Incomplete starts (missing s-vars, W, H, HPWL) are silently ignored by Gurobi.
    for bid in bids:
        x[bid].Start = warm_positions[bid][0]
        y[bid].Start = warm_positions[bid][1]

    # Use hint_positions for r-var direction inference when provided (e.g. PSO 2D layout).
    # warm_positions (DRC-clean row-pack) gives Gurobi a valid incumbent;
    # hint_positions (PSO 2D) gives better directional hints without corrupting the incumbent.
    hints = _r_hints(bids, hint_positions if hint_positions is not None else warm_positions, blocks)
    for (bi, bj), k_best in hints.items():
        if (bi, bj) in r_vars:
            for k in range(4):
                r_vars[(bi, bj)][k].Start = 1 if k == k_best else 0

    for bid in bids:
        for k, sv in enumerate(s[bid]):
            sv.Start = 1.0 if k == 0 else 0.0   # default: variant 0

    W_start = max(warm_positions[bid][0] + all_dims[bid][0][0] for bid in bids)
    H_start = max(warm_positions[bid][1] + all_dims[bid][0][1] for bid in bids)
    W.Start = W_start
    H.Start = H_start

    for ei, nbids in hpwl_bids.items():
        cxs = [warm_positions[nb][0] + all_dims[nb][0][0] / 2.0 for nb in nbids]
        cys = [warm_positions[nb][1] + all_dims[nb][0][1] / 2.0 for nb in nbids]
        x_lo[ei].Start = min(cxs);  x_hi[ei].Start = max(cxs)
        y_lo[ei].Start = min(cys);  y_hi[ei].Start = max(cys)

    logger.debug("ILP: model has %d vars, %d constrs", m.NumVars, m.NumConstrs)
    m.optimize()

    status = m.Status
    logger.info(
        "ILP solver: gurobi_status=%d  SolCount=%d  ObjVal=%.4f",
        status, m.SolCount, m.ObjVal if m.SolCount > 0 else float("nan"),
    )

    if m.SolCount == 0:
        logger.warning(
            "ILP: no feasible integer solution (gurobi_status=%d) — falling back to seed",
            status,
        )
        return warm_positions, {bid: 0 for bid in bids}, "infeasible"

    positions: dict[str, tuple[float, float]] = {}
    variant_map: dict[str, int] = {}
    for bid in bids:
        xv = x[bid].X
        yv = y[bid].X
        positions[bid] = (round(xv, 6), round(yv, 6))

        if s[bid]:
            vals = [sv.X for sv in s[bid]]
            variant_map[bid] = int(max(range(len(vals)), key=lambda k: vals[k]))
        else:
            variant_map[bid] = 0

    # Status 2 = OPTIMAL, 9 = TIME_LIMIT (but has incumbent)
    termination = "optimal" if status == GRB.OPTIMAL else "feasible"
    return positions, variant_map, termination


def _solve_mip(
    bids:           list[str],
    blocks:         dict,
    nets:           list,
    sym_groups:     list,
    area_weight:    float,
    wl_weight:      float,
    warm_positions: dict[str, tuple[float, float]],
    gurobi_params:  GurobiParams | None = None,
    hint_positions: dict[str, tuple[float, float]] | None = None,
) -> tuple[dict[str, tuple[float, float]], dict[str, int], str]:
    """Dispatch to _solve_mip_gurobi with the given (or default) parameters."""
    return _solve_mip_gurobi(
        bids, blocks, nets, sym_groups,
        area_weight, wl_weight, warm_positions,
        gurobi_params or GurobiParams(),
        hint_positions=hint_positions,
    )


class ILPOptimizer:
    """
    One-shot MILP optimizer. Replaces ILPTopology state with the MIP solution
    then returns an SAResult so the existing pipeline can handle the result.
    Accepts SAConfig for interface parity; ignores SA-specific fields.
    """

    def __init__(
        self,
        topology:       Any,
        evaluator:      Any,
        config:         Any,
        observer:       Any           = None,
        gurobi_params:  GurobiParams | None = None,
    ) -> None:
        self._topo          = topology
        self._evaluator     = evaluator
        self._gurobi_params = gurobi_params

    def run(self) -> Any:
        from sa_optimizer import SAResult

        blocks     = self._topo._blocks
        nets       = self._topo._nets
        sym_groups = self._topo._sym_groups
        bids       = list(blocks.keys())

        if not bids:
            logger.error("ILPOptimizer: no valid blocks to place")
            return SAResult(
                best_state    = self._topo.copy_state(),
                best_cost     = float("inf"),
                n_iterations  = 0,
                termination   = "infeasible",
            )

        if len(bids) > ILP_LARGE_N_WARN:
            logger.warning(
                "ILP: %d blocks exceeds recommended limit of %d — MIP may be slow",
                len(bids), ILP_LARGE_N_WARN,
            )

        row_pack_positions = self._topo.decode()
        c_area = self._evaluator._w.area_weight
        c_wl   = self._evaluator._w.wirelength_weight

        params = self._gurobi_params or GurobiParams()
        warm_positions = row_pack_positions
        if params.use_fdgd_start:
            try:
                fdgd_centroids = run_fdgd(blocks, nets, seed=0)
                if len(fdgd_centroids) == len(bids):
                    # Sort blocks by FDGD x-centroid → row-pack → DRC-clean positions.
                    # DRC-clean positions let Gurobi accept the start as a complete
                    # feasible incumbent rather than just positional hints.
                    warm_positions = _fdgd_row_pack(bids, blocks, fdgd_centroids)
                    logger.debug("FDGD row-pack warm start applied (%d blocks)", len(bids))
            except Exception as exc:
                logger.warning("FDGD failed (%s) — using plain row-pack for warm start", exc)

        positions, variant_map, termination = _solve_mip(
            bids, blocks, nets, sym_groups, c_area, c_wl, warm_positions,
            params,
        )

        self._topo.set_solution(positions, variant_map)
        cost = self._evaluator.evaluate(positions)
        best_state = self._topo.copy_state()

        logger.info(
            "ILP finished: termination=%s  cost=%.4f  n_blocks=%d",
            termination, cost, len(bids),
        )
        return SAResult(
            best_state     = best_state,
            best_cost      = cost,
            n_iterations   = 1,
            accept_history = [],
            termination    = termination,
        )
