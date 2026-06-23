"""
CORP placer — spring-embedding phase.

CORP (Connectivity-Ordered Row Placement) uses a spring-embedding simulation
to determine a connectivity-aware ordering of blocks.  The resulting centroids
are sorted by x-position and row-packed by _corp_row_pack() in ilp_optimizer.py
to produce a DRC-clean feasible starting layout for the ILP solver.

The simulation does NOT need to produce a DRC-clean layout — any coarse
arrangement that separates connected blocks is enough to guide the ordering.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spacing import compute_block_spacing
from log_setup import get_logger

# =============================================================================
# CONSTANTS  (tuned for analog blocks: 1–15 µm dims, 2–13 µm spacings)
# =============================================================================
DEBUG = False

_CANVAS_FACTOR = 2.0    # canvas side = sqrt(total_block_area) × factor
_K_ATTRACT     = 0.4    # attractive spring per unit distance per net weight
_K_REPEL       = 3.0    # repulsive force per µm of underspacing
_K_BOUNDARY    = 0.8    # restoring force per µm outside canvas
_K_ORIGIN      = 0.05   # origin force per µm from (0,0) — pulls blocks toward bottom-left
_DAMPING       = 0.80   # velocity damping factor applied every step
_N_ITER        = 400    # maximum simulation steps per run
_N_RUNS        = 3      # number of independent runs; best by connectivity cost is kept
_DT_INIT       = 0.60   # initial time step (µm)
_DT_COOL       = 0.995  # dt multiplied by this each step
_CONV_THRESH   = 5e-4   # stop early when max velocity falls below this

logger = get_logger(__name__, DEBUG)


# =============================================================================
# HELPERS
# =============================================================================

def _dims(block: dict) -> tuple[float, float]:
    """Width and height of the first variant (or 0,0 for error blocks)."""
    variants = block.get("variants", [])
    if not variants:
        return 0.0, 0.0
    bb = variants[0].get("main_bbox", {})
    return bb.get("x_max", 0.0), bb.get("y_max", 0.0)


def _connectivity_cost(
    cx: dict[str, float],
    cy: dict[str, float],
    conn: dict[tuple[str, str], float],
) -> float:
    """Sum of weight × centroid distance for all connected pairs (lower = better)."""
    cost = 0.0
    for (bi, bj), w in conn.items():
        dx = cx[bj] - cx[bi]
        dy = cy[bj] - cy[bi]
        cost += w * math.sqrt(dx * dx + dy * dy)
    return cost


def _run_once(
    bids:     list[str],
    bw:       dict[str, float],
    bh:       dict[str, float],
    conn:     dict[tuple[str, str], float],
    thresh_x: dict[tuple[str, str], float],
    thresh_y: dict[tuple[str, str], float],
    canvas:   float,
    seed:     int,
    n_iter:   int,
) -> tuple[dict[str, float], dict[str, float], float]:
    """
    One spring-embedding run.  Returns (cx, cy, connectivity_cost).
    Forces: attractive (connected pairs), repulsive (underspaced), boundary,
    and origin (attracts blocks toward (0,0) to minimise area spread).
    """
    rng = random.Random(seed)
    n   = len(bids)

    cx = {b: rng.uniform(bw[b] / 2.0, max(bw[b] / 2.0, canvas - bw[b] / 2.0)) for b in bids}
    cy = {b: rng.uniform(bh[b] / 2.0, max(bh[b] / 2.0, canvas - bh[b] / 2.0)) for b in bids}
    vx = {b: 0.0 for b in bids}
    vy = {b: 0.0 for b in bids}

    dt   = _DT_INIT
    step = 0
    for step in range(n_iter):
        fx = {b: 0.0 for b in bids}
        fy = {b: 0.0 for b in bids}

        # Attractive springs (connected pairs only)
        for (bi, bj), w in conn.items():
            ddx = cx[bj] - cx[bi]
            ddy = cy[bj] - cy[bi]
            f = _K_ATTRACT * w
            fx[bi] += f * ddx;  fy[bi] += f * ddy
            fx[bj] -= f * ddx;  fy[bj] -= f * ddy

        # Repulsive forces (all pairs that are underspaced in BOTH axes)
        for ai in range(n):
            for aj in range(ai + 1, n):
                bi, bj = bids[ai], bids[aj]
                ddx  = cx[bj] - cx[bi]
                ddy  = cy[bj] - cy[bi]
                tx   = thresh_x[(bi, bj)]
                ty   = thresh_y[(bi, bj)]
                viol_x = tx - abs(ddx)   # > 0 means underspaced in x
                viol_y = ty - abs(ddy)   # > 0 means underspaced in y
                if viol_x > 0.0 and viol_y > 0.0:
                    # Push along the axis with the smaller violation (min-correction)
                    sx = 1.0 if ddx >= 0.0 else -1.0
                    sy = 1.0 if ddy >= 0.0 else -1.0
                    if viol_x <= viol_y:
                        f = _K_REPEL * viol_x
                        fx[bi] -= f * sx;  fx[bj] += f * sx
                    else:
                        f = _K_REPEL * viol_y
                        fy[bi] -= f * sy;  fy[bj] += f * sy

        # Boundary restoring force (pull back toward canvas interior)
        for b in bids:
            hw = bw[b] / 2.0;  hh = bh[b] / 2.0
            lo_x = hw;  hi_x = canvas - hw
            lo_y = hh;  hi_y = canvas - hh
            if cx[b] < lo_x:
                fx[b] += _K_BOUNDARY * (lo_x - cx[b])
            elif cx[b] > hi_x:
                fx[b] -= _K_BOUNDARY * (cx[b] - hi_x)
            if cy[b] < lo_y:
                fy[b] += _K_BOUNDARY * (lo_y - cy[b])
            elif cy[b] > hi_y:
                fy[b] -= _K_BOUNDARY * (cy[b] - hi_y)

        # Origin force — attracts each block toward (0,0) to minimise area spread
        for b in bids:
            fx[b] -= _K_ORIGIN * cx[b]
            fy[b] -= _K_ORIGIN * cy[b]

        # Euler integration with velocity damping + step cooling
        max_v = 0.0
        for b in bids:
            vx[b] = (vx[b] + fx[b] * dt) * _DAMPING
            vy[b] = (vy[b] + fy[b] * dt) * _DAMPING
            cx[b] += vx[b] * dt
            cy[b] += vy[b] * dt
            if abs(vx[b]) > max_v:
                max_v = abs(vx[b])
            if abs(vy[b]) > max_v:
                max_v = abs(vy[b])

        dt *= _DT_COOL

        if step > 80 and max_v < _CONV_THRESH:
            logger.debug("CORP spring seed=%d: converged at step %d (max_v=%.2e)", seed, step, max_v)
            break

    cost = _connectivity_cost(cx, cy, conn)
    return cx, cy, cost


# =============================================================================
# PUBLIC API
# =============================================================================

def run_corp_spring(
    blocks: dict,
    nets:   list,
    seed:   int = 0,
    n_iter: int = _N_ITER,
    n_runs: int = _N_RUNS,
) -> dict[str, tuple[float, float]]:
    """
    Run spring-embedding (n_runs independent runs, keep best by connectivity cost)
    and return centroid positions {bid: (cx, cy)}.

    The x-ordering of centroids is used by _corp_row_pack() in ilp_optimizer.py
    to produce a connectivity-aware row layout as the ILP warm start.

    Forces applied each step:
      - Attractive  : connected blocks pulled together (spring, F ∝ distance)
      - Repulsive   : underspaced pairs pushed apart along the tighter axis
      - Boundary    : blocks outside the canvas pulled back in
      - Origin      : all blocks attracted toward (0,0) to minimise spread

    Returns centroid positions.  Convert to bottom-left corner with:
        bl_x = cx - w/2,  bl_y = cy - h/2
    before passing to _r_hints() or _solve_mip().
    """
    bids = [b for b in blocks if "error" not in blocks[b]]
    n    = len(bids)

    if n == 0:
        return {}
    if n == 1:
        w, h = _dims(blocks[bids[0]])
        return {bids[0]: (w / 2.0, h / 2.0)}

    # --- block geometry ---
    bw = {b: _dims(blocks[b])[0] for b in bids}
    bh = {b: _dims(blocks[b])[1] for b in bids}

    # --- canvas ---
    total_area = sum(bw[b] * bh[b] for b in bids)
    canvas     = math.sqrt(max(total_area, 1.0)) * _CANVAS_FACTOR

    # --- build net connectivity weights: (bi, bj) -> weight (bi < bj lex.) ---
    conn: dict[tuple[str, str], float] = {}
    bid_set = set(bids)
    for net in nets:
        net_bids: list[str] = []
        for pin in net.get("pins", []):
            if pin.startswith("B"):
                b = pin[1:].split("_", 1)[0]
                if b in bid_set and b not in net_bids:
                    net_bids.append(b)
        for i in range(len(net_bids)):
            for j in range(i + 1, len(net_bids)):
                key = (min(net_bids[i], net_bids[j]),
                       max(net_bids[i], net_bids[j]))
                conn[key] = conn.get(key, 0.0) + 1.0

    # --- pre-compute centroid-to-centroid separation thresholds ---
    thresh_x: dict[tuple[str, str], float] = {}
    thresh_y: dict[tuple[str, str], float] = {}
    for ai in range(n):
        for aj in range(ai + 1, n):
            bi, bj = bids[ai], bids[aj]
            sr = compute_block_spacing(blocks[bi], blocks[bj])
            thresh_x[(bi, bj)] = (bw[bi] + bw[bj]) / 2.0 + sr.x_spacing
            thresh_y[(bi, bj)] = (bh[bi] + bh[bj]) / 2.0 + sr.y_spacing

    # --- multiple runs: keep the best by connectivity cost ---
    best_cx: dict[str, float] | None = None
    best_cy: dict[str, float] | None = None
    best_cost = float("inf")

    for run_idx in range(n_runs):
        cx, cy, cost = _run_once(
            bids, bw, bh, conn, thresh_x, thresh_y, canvas,
            seed=seed + run_idx, n_iter=n_iter,
        )
        if cost < best_cost:
            best_cost = cost
            best_cx   = dict(cx)
            best_cy   = dict(cy)

    logger.debug(
        "CORP spring: %d runs  best_cost=%.2f  canvas=%.1f µm  n=%d  connections=%d",
        n_runs, best_cost, canvas, n, len(conn),
    )
    assert best_cx is not None and best_cy is not None
    return {b: (best_cx[b], best_cy[b]) for b in bids}
