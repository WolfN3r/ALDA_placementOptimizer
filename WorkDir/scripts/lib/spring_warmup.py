"""
Spring-embedding (FDGD) warm-start placer — faithful implementation of Grus et al. (ICORES 2023).

Places blocks via force-directed graph drawing to produce connectivity-aware centroid
positions that are used as r-variable hints and variant hints for the ILP solver.
Registered under strategy names "spring" and "fdgd".
"""
from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from spacing        import compute_block_spacing
from warmup_manager import WarmupStrategy, register_strategy
from log_setup      import get_logger

# =============================================================================
# 2. CONSTANTS  (paper §4 — all tuning values live here)
# =============================================================================
DEBUG = False

CANVAS_FACTOR = math.sqrt(1.25)  # canvas side = sqrt(1.25 × total_block_area) — paper §4
K_ATTRACT     = 0.3              # attractive spring coefficient per unit distance per net weight
K_REPEL       = 5.0              # repulsive coefficient per µm of underspacing
K_BOUNDARY    = 1.0              # restoring force per µm outside canvas
K_ORIGIN      = 0.03             # origin pull per µm from (0, 0) — minimises area spread
DT_INIT       = 1.0              # initial simulation step δ
DT_COOL       = 0.992            # δ multiplied each step (geometric cooling)
N_ITER        = 600              # maximum iterations per run
N_RUNS        = 5                # independent runs; best by connectivity cost is kept
CONV_THRESH   = 1e-4             # stop early when max |Q| falls below this
ROT_PROB      = 0.5              # probability of selecting the "rotated" variant — paper §4

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _best_variant(block: dict, rng: random.Random) -> tuple[int, float, float]:
    """
    Return (variant_idx, w, h) for the variant closest to square aspect ratio.
    With probability ROT_PROB, the alternative (transposed-dims) variant is chosen instead.
    Implements paper §4: "best aspect-ratio-wise variant; with prob 0.5 rotated variant."
    """
    variants = block.get("variants", [])
    if not variants:
        return 0, 0.0, 0.0

    scored: list[tuple[float, int, float, float]] = []
    for k, v in enumerate(variants):
        bb = v.get("main_bbox", {})
        w  = bb.get("x_max", 0.0)
        h  = bb.get("y_max", 0.0)
        if w > 0.0 and h > 0.0:
            ar = min(w, h) / max(w, h)   # 1.0 = square (best)
            scored.append((ar, k, w, h))

    if not scored:
        return 0, 0.0, 0.0

    scored.sort(reverse=True)   # best (most square) first
    _, k_best, w_best, h_best = scored[0]

    if rng.random() < ROT_PROB and len(scored) >= 2:
        # Look for the variant with dimensions closest to (h_best, w_best) — transposed
        target_w, target_h = h_best, w_best
        best_dist = float("inf")
        k_rot, w_rot, h_rot = k_best, w_best, h_best
        for _, k, w, h in scored[1:]:
            dist = (w - target_w) ** 2 + (h - target_h) ** 2
            if dist < best_dist:
                best_dist = dist
                k_rot, w_rot, h_rot = k, w, h
        return k_rot, w_rot, h_rot

    return k_best, w_best, h_best


def _connectivity_cost(
    cx:   dict[str, float],
    cy:   dict[str, float],
    conn: dict[tuple[str, str], float],
) -> float:
    """Sum of weight × Euclidean centroid distance for all connected pairs."""
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
) -> tuple[dict[str, float], dict[str, float]]:
    """
    One spring-embedding run (first-order integration, no velocity).
    Matches paper Algorithm 1: p_c ← p_c + δ·Q_c at each step.
    Returns (cx, cy) — centroid coordinates per block.
    """
    rng = random.Random(seed)
    n   = len(bids)

    # Initialise centroids uniformly over the canvas
    cx = {b: rng.uniform(bw[b] / 2.0, max(bw[b] / 2.0, canvas - bw[b] / 2.0)) for b in bids}
    cy = {b: rng.uniform(bh[b] / 2.0, max(bh[b] / 2.0, canvas - bh[b] / 2.0)) for b in bids}

    for step in range(n_iter):
        qx = {b: 0.0 for b in bids}
        qy = {b: 0.0 for b in bids}

        # --- Attractive force Gc (connected pairs only) ---
        for (bi, bj), w in conn.items():
            ddx = cx[bj] - cx[bi]
            ddy = cy[bj] - cy[bi]
            f   = K_ATTRACT * w
            qx[bi] += f * ddx;  qy[bi] += f * ddy
            qx[bj] -= f * ddx;  qy[bj] -= f * ddy

        # --- Repulsive force Fc (ALL pairs — fires on EITHER axis underspaced) ---
        for ai in range(n):
            for aj in range(ai + 1, n):
                bi, bj = bids[ai], bids[aj]
                ddx = cx[bj] - cx[bi]
                ddy = cy[bj] - cy[bi]
                viol_x = thresh_x[(bi, bj)] - abs(ddx)
                viol_y = thresh_y[(bi, bj)] - abs(ddy)
                if viol_x > 0.0 or viol_y > 0.0:
                    # Push along the centroid-to-centroid vector
                    d = math.sqrt(ddx * ddx + ddy * ddy)
                    if d < 1e-6:
                        # Degenerate: push along a random direction
                        angle  = rng.uniform(0.0, 2.0 * math.pi)
                        nx, ny = math.cos(angle), math.sin(angle)
                    else:
                        nx, ny = ddx / d, ddy / d
                    f = K_REPEL * max(viol_x, viol_y)
                    qx[bi] -= f * nx;  qy[bi] -= f * ny
                    qx[bj] += f * nx;  qy[bj] += f * ny

        # --- Boundary force Bc ---
        for b in bids:
            hw = bw[b] / 2.0
            hh = bh[b] / 2.0
            if cx[b] - hw < 0.0:
                qx[b] += K_BOUNDARY * (hw - cx[b])
            elif cx[b] + hw > canvas:
                qx[b] -= K_BOUNDARY * (cx[b] + hw - canvas)
            if cy[b] - hh < 0.0:
                qy[b] += K_BOUNDARY * (hh - cy[b])
            elif cy[b] + hh > canvas:
                qy[b] -= K_BOUNDARY * (cy[b] + hh - canvas)

        # --- Origin force Oc (attracts each block toward (0,0)) ---
        for b in bids:
            qx[b] -= K_ORIGIN * cx[b]
            qy[b] -= K_ORIGIN * cy[b]

        # --- Position update (no velocity — paper Algorithm 1) ---
        dt    = DT_INIT * (DT_COOL ** step)
        max_q = 0.0
        for b in bids:
            dx = dt * qx[b]
            dy = dt * qy[b]
            # Clamp displacement: never move more than one canvas width per step
            # to prevent numerical divergence when blocks start highly overlapping.
            disp = math.sqrt(dx * dx + dy * dy)
            if disp > canvas:
                scale = canvas / disp
                dx *= scale
                dy *= scale
            cx[b] += dx
            cy[b] += dy
            q_mag = math.sqrt(qx[b] * qx[b] + qy[b] * qy[b])
            if q_mag > max_q:
                max_q = q_mag

        if step > 100 and max_q < CONV_THRESH:
            logger.debug("SpringWarmup: converged at step %d (seed=%d, max_q=%.2e)", step, seed, max_q)
            break

    return cx, cy


class SpringWarmup(WarmupStrategy):
    """
    Paper-faithful FDGD warm start (Grus et al., ICORES 2023).
    Selects one variant per block (best aspect ratio ± rotation), runs N_RUNS independent
    spring simulations, keeps the best by connectivity cost, converts centroids to
    bottom-left corners, and exposes the chosen variant indices via get_variant_map().
    """

    def __init__(self) -> None:
        self._variant_map: dict[str, int] = {}

    def get_variant_map(self) -> dict[str, int]:
        return self._variant_map

    def run_single(
        self,
        blocks: dict,
        nets:   list,
        seed:   int,
    ) -> dict[str, tuple[float, float, float, float]]:
        bids = [b for b in blocks if "error" not in blocks[b]]
        if not bids:
            self._variant_map = {}
            return {}

        rng = random.Random(seed)

        # --- Step 1: select one variant per block (fixed before simulation) ---
        v_idx: dict[str, int]   = {}
        bw:    dict[str, float] = {}
        bh:    dict[str, float] = {}
        for bid in sorted(bids):   # sorted for stable RNG consumption order
            k, w, h = _best_variant(blocks[bid], rng)
            v_idx[bid] = k
            bw[bid]    = w
            bh[bid]    = h

        # --- Step 2: build connectivity weights ---
        bid_set = set(bids)
        conn: dict[tuple[str, str], float] = {}
        for net in nets:
            net_bids: list[str] = []
            for pin in net.get("pins", []):
                if pin.startswith("B"):
                    b = pin[1:].split("_", 1)[0]
                    if b in bid_set and b not in net_bids:
                        net_bids.append(b)
            for i in range(len(net_bids)):
                for j in range(i + 1, len(net_bids)):
                    key = (min(net_bids[i], net_bids[j]), max(net_bids[i], net_bids[j]))
                    conn[key] = conn.get(key, 0.0) + 1.0

        # --- Step 3: pre-compute centroid separation thresholds ---
        n = len(bids)
        thresh_x: dict[tuple[str, str], float] = {}
        thresh_y: dict[tuple[str, str], float] = {}
        for ai in range(n):
            for aj in range(ai + 1, n):
                bi, bj = bids[ai], bids[aj]
                sr = compute_block_spacing(blocks[bi], blocks[bj])
                thresh_x[(bi, bj)] = (bw[bi] + bw[bj]) / 2.0 + sr.x_spacing
                thresh_y[(bi, bj)] = (bh[bi] + bh[bj]) / 2.0 + sr.y_spacing

        # --- Step 4: canvas (paper §4: 125% of total block area) ---
        total_area = sum(bw[b] * bh[b] for b in bids)
        canvas     = math.sqrt(max(total_area, 1.0)) * CANVAS_FACTOR

        # --- Step 5: N_RUNS independent simulations; keep best by connectivity cost ---
        best_cx:   dict[str, float] | None = None
        best_cy:   dict[str, float] | None = None
        best_cost  = float("inf")

        for run_idx in range(N_RUNS):
            cx, cy = _run_once(
                bids, bw, bh, conn, thresh_x, thresh_y,
                canvas, seed=seed + run_idx, n_iter=N_ITER,
            )
            cost = _connectivity_cost(cx, cy, conn)
            if cost < best_cost:
                best_cost = cost
                best_cx   = dict(cx)
                best_cy   = dict(cy)

        assert best_cx is not None and best_cy is not None

        logger.info(
            "SpringWarmup: %d runs  best_cost=%.2f  canvas=%.1f µm  n=%d  connections=%d",
            N_RUNS, best_cost, canvas, n, len(conn),
        )

        # --- Step 6: convert centroids → bottom-left corners ---
        positions: dict[str, tuple[float, float, float, float]] = {}
        for bid in bids:
            x_bl = best_cx[bid] - bw[bid] / 2.0
            y_bl = best_cy[bid] - bh[bid] / 2.0
            positions[bid] = (x_bl, y_bl, bw[bid], bh[bid])

        # --- Step 7: store variant map for ILP hint ---
        self._variant_map = dict(v_idx)

        logger.debug("SpringWarmup: placed %d blocks (seed=%d)", len(positions), seed)
        return positions


register_strategy("spring", SpringWarmup)
