"""
ILP placement optimizer — solves one MILP to place all blocks optimally.

Enforces non-overlap with PDK-aware DRC spacing (from spacing.py LUT),
multi-variant block selection, vertical symmetry groups, and HPWL connectivity.
Uses PuLP with the bundled CBC solver (open source, no license required).

Accepts SAConfig for pipeline interface parity; ignores all SA-specific fields.
Objective weights (area vs. HPWL) are read from CostEvaluator so results are
comparable with B*+SA and SP+SA runs on the same JSON.
"""
from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from spacing import compute_block_spacing
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG            = False
ILP_TIME_LIMIT_S = 200   # CBC solver wall-clock limit in seconds
ILP_LARGE_N_WARN = 20    # log warning when n_blocks exceeds this

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
    """Return conservative (M_x, M_y) — sum of all max variant widths/heights."""
    M_x = sum(max(d[0] for d in _variant_dims(blocks[bid])) for bid in bids)
    M_y = sum(max(d[1] for d in _variant_dims(blocks[bid])) for bid in bids)
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


def _lp_center_x(bid: str, x: dict, s: dict, dims: list[tuple[float, float]], pulp: Any) -> Any:
    """Linear expression for the x-centroid of block bid."""
    if not s[bid]:
        return x[bid] + dims[0][0] / 2.0
    return x[bid] + pulp.lpSum(dims[k][0] / 2.0 * s[bid][k] for k in range(len(dims)))


def _lp_center_y(bid: str, y: dict, s: dict, dims: list[tuple[float, float]], pulp: Any) -> Any:
    """Linear expression for the y-centroid of block bid."""
    if not s[bid]:
        return y[bid] + dims[0][1] / 2.0
    return y[bid] + pulp.lpSum(dims[k][1] / 2.0 * s[bid][k] for k in range(len(dims)))


def _solve_mip(
    bids:           list[str],
    blocks:         dict,
    nets:           list,
    sym_groups:     list,
    area_weight:    float,
    wl_weight:      float,
    warm_positions: dict[str, tuple[float, float]],
) -> tuple[dict[str, tuple[float, float]], dict[str, int], str]:
    """
    Build and solve the analog placement MILP.
    Returns (positions, variant_map, termination) where termination is
    "optimal", "feasible", or "infeasible".
    Falls back to warm_positions when the solver finds no feasible point.
    """
    import pulp

    n = len(bids)
    bid_set = set(bids)
    M_x, M_y = _big_m(bids, blocks)

    prob = pulp.LpProblem("analog_placement", pulp.LpMinimize)

    # Canvas bounding-box variables — upper bounds tighten LP relaxation for CBC
    W = pulp.LpVariable("W", lowBound=0.0, upBound=M_x)
    H = pulp.LpVariable("H", lowBound=0.0, upBound=M_y)

    # Block position variables
    x: dict[str, Any] = {bid: pulp.LpVariable(f"x_{bid}", lowBound=0.0, upBound=M_x) for bid in bids}
    y: dict[str, Any] = {bid: pulp.LpVariable(f"y_{bid}", lowBound=0.0, upBound=M_y) for bid in bids}

    # Variant selection — w/h are floats for single-variant blocks, LpAffineExpression for multi
    all_dims: dict[str, list[tuple[float, float]]] = {bid: _variant_dims(blocks[bid]) for bid in bids}
    w: dict[str, Any] = {}
    h: dict[str, Any] = {}
    s: dict[str, list] = {}   # binary selectors; empty list = single-variant block

    for bid in bids:
        dims = all_dims[bid]
        if len(dims) == 1:
            w[bid] = dims[0][0]
            h[bid] = dims[0][1]
            s[bid] = []
        else:
            s[bid] = [pulp.LpVariable(f"s_{bid}_{k}", cat="Binary") for k in range(len(dims))]
            prob += pulp.lpSum(s[bid]) == 1, f"var_sel_{bid}"
            w[bid] = pulp.lpSum(dims[k][0] * s[bid][k] for k in range(len(dims)))
            h[bid] = pulp.lpSum(dims[k][1] * s[bid][k] for k in range(len(dims)))

    # Boundary constraints
    for bid in bids:
        prob += x[bid] + w[bid] <= W, f"bnd_x_{bid}"
        prob += y[bid] + h[bid] <= H, f"bnd_y_{bid}"

    # Non-overlap constraints — one set of 4 big-M inequalities per ordered pair
    r_vars: dict[tuple[str, str], list] = {}
    for ai in range(n):
        for aj in range(ai + 1, n):
            bi, bj = bids[ai], bids[aj]
            sr = compute_block_spacing(blocks[bi], blocks[bj])
            ax, ay = sr.x_spacing, sr.y_spacing
            rv = [pulp.LpVariable(f"r_{bi}_{bj}_{k}", cat="Binary") for k in range(4)]
            r_vars[(bi, bj)] = rv
            # k=0: i is left of j
            prob += x[bi] + w[bi] + ax <= x[bj] + M_x * (1 - rv[0]), f"no_{bi}_{bj}_0"
            # k=1: i is below j
            prob += y[bi] + h[bi] + ay <= y[bj] + M_y * (1 - rv[1]), f"no_{bi}_{bj}_1"
            # k=2: j is left of i
            prob += x[bj] + w[bj] + ax <= x[bi] + M_x * (1 - rv[2]), f"no_{bi}_{bj}_2"
            # k=3: j is below i
            prob += y[bj] + h[bj] + ay <= y[bi] + M_y * (1 - rv[3]), f"no_{bi}_{bj}_3"
            prob += pulp.lpSum(rv) >= 1, f"no_sum_{bi}_{bj}"

    # Symmetry constraints — vertical axis only
    for gi, group in enumerate(sym_groups):
        axis = group.get("axis", "vertical")
        if axis != "vertical":
            logger.warning("ILP: group %d axis '%s' not supported — skipped", gi, axis)
            continue
        x_sym = pulp.LpVariable(f"x_sym_{gi}", lowBound=0.0)

        for pair in group.get("pairs", []):
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            a, b = str(pair[0]), str(pair[1])
            if a not in bid_set or b not in bid_set:
                continue
            # Pair mirrored across vertical axis: xs_a + xs_b + ws_a = 2*x_sym, ys_a = ys_b
            prob += x[a] + x[b] + w[a] == 2 * x_sym, f"sym_x_{gi}_{a}_{b}"
            prob += y[a] == y[b],                     f"sym_y_{gi}_{a}_{b}"
            # pair[0]='a' is designated left partner — its right edge must not cross the axis.
            # This prevents ABAB interleaving between pairs sharing the same axis.
            # It also eliminates the symmetric ABBA solution family, halving the search space.
            prob += x[a] + w[a] <= x_sym,             f"sym_left_{gi}_{a}"
            # Same variant for both partners
            if s[a] and s[b] and len(s[a]) == len(s[b]):
                for k in range(len(s[a])):
                    prob += s[a][k] == s[b][k], f"sym_var_{gi}_{a}_{b}_{k}"

        for ss in group.get("self_symmetric", []):
            ss_bid = str(ss)
            if ss_bid not in bid_set:
                continue
            prob += 2 * x[ss_bid] + w[ss_bid] == 2 * x_sym, f"sym_self_{gi}_{ss_bid}"

    # HPWL variables — one (dx, dy) pair per net that has ≥2 placed blocks
    dx: dict[int, Any] = {}
    dy: dict[int, Any] = {}

    for ei, net in enumerate(nets):
        net_bids: list[str] = []
        for pin in net.get("pins", []):
            # Pin key format: "B{bid}_{pin_name}"
            if pin.startswith("B"):
                parts = pin[1:].split("_", 1)
                nbid = parts[0] if parts else ""
                if nbid in bid_set and nbid not in net_bids:
                    net_bids.append(nbid)
        if len(net_bids) < 2:
            continue

        dx[ei] = pulp.LpVariable(f"dx_{ei}", lowBound=0.0)
        dy[ei] = pulp.LpVariable(f"dy_{ei}", lowBound=0.0)

        seen: set[tuple[str, str]] = set()
        for ai2 in range(len(net_bids)):
            for aj2 in range(ai2 + 1, len(net_bids)):
                bi2, bj2 = net_bids[ai2], net_bids[aj2]
                key = (bi2, bj2)
                if key in seen:
                    continue
                seen.add(key)
                xci = _lp_center_x(bi2, x, s, all_dims[bi2], pulp)
                xcj = _lp_center_x(bj2, x, s, all_dims[bj2], pulp)
                yci = _lp_center_y(bi2, y, s, all_dims[bi2], pulp)
                ycj = _lp_center_y(bj2, y, s, all_dims[bj2], pulp)
                prob += dx[ei] >= xci - xcj, f"hpwl_dx_{ei}_{bi2}_{bj2}_p"
                prob += dx[ei] >= xcj - xci, f"hpwl_dx_{ei}_{bi2}_{bj2}_n"
                prob += dy[ei] >= yci - ycj, f"hpwl_dy_{ei}_{bi2}_{bj2}_p"
                prob += dy[ei] >= ycj - yci, f"hpwl_dy_{ei}_{bi2}_{bj2}_n"

    # Objective — same area_weight / wl_weight ratio as SA evaluator
    n_nets_used = max(len(dx), 1)
    hpwl_term = pulp.lpSum(dx[ei] + dy[ei] for ei in dx) if dx else 0.0
    prob += area_weight * (W + H) + (wl_weight / n_nets_used) * hpwl_term

    # MIP warm start — fix dominant r-direction from seed layout
    hints = _r_hints(bids, warm_positions, blocks)
    for (bi, bj), k_best in hints.items():
        if (bi, bj) in r_vars:
            for k in range(4):
                r_vars[(bi, bj)][k].setInitialValue(1 if k == k_best else 0)

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=ILP_TIME_LIMIT_S)
    prob.solve(solver)

    status_label = pulp.LpStatus.get(prob.status, "Unknown")
    obj_val = pulp.value(prob.objective)
    logger.info("ILP solver: status=%s  obj=%.4f", status_label, obj_val or float("nan"))

    if obj_val is None:
        logger.warning("ILP: no feasible solution found — falling back to seed positions")
        return warm_positions, {bid: 0 for bid in bids}, "infeasible"

    # Extract block positions and chosen variant indices
    positions: dict[str, tuple[float, float]] = {}
    variant_map: dict[str, int] = {}
    for bid in bids:
        xv = pulp.value(x[bid]) or 0.0
        yv = pulp.value(y[bid]) or 0.0
        positions[bid] = (round(xv, 6), round(yv, 6))

        if s[bid]:
            vals = [pulp.value(s[bid][k]) or 0.0 for k in range(len(s[bid]))]
            variant_map[bid] = int(max(range(len(vals)), key=lambda k: vals[k]))
        else:
            variant_map[bid] = 0

    termination = "optimal" if status_label == "Optimal" else "feasible"
    return positions, variant_map, termination


class ILPOptimizer:
    """
    One-shot MILP optimizer. Replaces ILPTopology state with the MIP solution
    then returns an SAResult so the existing pipeline can handle the result.
    Accepts SAConfig for interface parity; ignores SA-specific fields.
    """

    def __init__(
        self,
        topology:  Any,
        evaluator: Any,
        config:    Any,
        observer:  Any = None,
    ) -> None:
        self._topo      = topology
        self._evaluator = evaluator
        # config (SAConfig) is stored but not used — ILP constants live in section 2 above

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

        warm_positions = self._topo.decode()
        c_area = self._evaluator._w.area_weight
        c_wl   = self._evaluator._w.wirelength_weight

        positions, variant_map, termination = _solve_mip(
            bids, blocks, nets, sym_groups, c_area, c_wl, warm_positions,
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
