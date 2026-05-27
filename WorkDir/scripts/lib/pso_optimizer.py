"""
PSO placement optimizer — works directly in (x, y) position space.

Based on: Hsieh et al., "Placement Constraints and Macrocell Overlap Removal
Using Particle Swarm Optimization", ANTS 2006, LNCS 4150, pp. 235–246.

Key differences from the paper to fit analog IC placement:
  - Soft DRC-aware overlap penalty instead of reject-and-regenerate.
    Uses compute_block_spacing() thresholds so DRC spacing is approximated,
    though final layouts may still have residual violations (expected limitation).
  - Symmetry via master-slave model (paper Section 4.1): master blocks move
    freely; slave x-coordinates are mirrored about a shared symmetry axis.
    Self-symmetric blocks are placed at axis - w/2 (x fixed, y free).
  - FDGD warm-start (paper does not use; reuses existing lib/fdgd.py) for
    particle 0 to give a connectivity-aware starting position.
  - Turn-around factor T (paper Section 4.2) triggers when overlap penalty
    exceeds turn_around_thresh fraction of total cost.
  - All blocks use variant 0; multi-variant selection is not implemented.
"""
from __future__ import annotations

import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from spacing import compute_block_spacing
from log_setup import get_logger

DEBUG = False
logger = get_logger(__name__, DEBUG)

_COST_ZERO_GUARD = 1e-9   # prevents /0 in turn-around overlap-ratio check
_FLOAT_EPS       = 1e-6   # floating-point tolerance for gap comparisons in repair
_REPAIR_GAP      = 0.001  # minimum clearance added when y-nudging a block in repair


# =============================================================================
# CONFIG
# =============================================================================

@dataclass
class PSOConfig:
    """
    Tunable PSO parameters.

    Recommended starting point for ~15 analog blocks with DRC spacing:
      swarm_size=20, inertia_w=0.4, c1=0.4, c2=0.3, max_iter=1000

    Tuning signals:
      Residual DRC overlaps       → raise overlap_penalty_w (try 5–10)
      Premature convergence       → raise inertia_w (0.5–0.7)
      Slow / no improvement       → lower c1, c2 to 0.25 each
      Canvas too crowded          → raise canvas_factor to 2.2
    """
    swarm_size:          int   = 20
    max_iter:            int   = 5000
    inertia_w:           float = 0.4    # w  — momentum / inertia weight
    c1:                  float = 0.4    # personal-best acceleration
    c2:                  float = 0.3    # global-best  acceleration
    canvas_factor:       float = 1.8    # canvas_side = factor × sqrt(total_block_area)
    overlap_penalty_w:   float = 200.0  # weight on the soft DRC-overlap penalty term
    use_fdgd_init:       bool  = True   # seed particle 0 with FDGD connectivity positions
    v_max_factor:        float = 0.2    # v_max = canvas_side × factor (velocity clamp)
    turn_around_thresh:  float = 0.5    # trigger T=−1 when overlap/total_cost > this
    seed:                int   = 0      # random seed for swarm initialisation


# =============================================================================
# HELPERS
# =============================================================================

def _block_dims(block: dict) -> tuple[float, float]:
    v  = (block.get("variants") or [{}])[0]
    bb = v.get("main_bbox", {})
    return bb.get("x_max", 0.0), bb.get("y_max", 0.0)


# =============================================================================
# OPTIMIZER
# =============================================================================

class PSOOptimizer:
    """
    Standalone PSO-based placement optimizer.

    Pipeline interface mirrors ILPOptimizer:
      - Constructor: (topology, evaluator, cfg, observer=None, pso_config=None)
      - run() → SAResult  (topology state is updated via topology.set_solution)

    Each particle is a complete layout {bid: (x, y)} for all blocks.
    The swarm collectively searches the continuous (x, y) placement space.
    """

    def __init__(
        self,
        topology,                          # PSOTopology
        evaluator,                         # CostEvaluator
        cfg,                               # SAConfig — required by pipeline, not used by PSO
        observer:   Any          = None,
        pso_config: PSOConfig | None = None,
    ) -> None:
        self._topo      = topology
        self._evaluator = evaluator
        self._observer  = observer
        self._pso       = pso_config or PSOConfig()

    def run(self) -> Any:
        from sa_optimizer import SAResult
        try:
            return self._run_pso()
        except Exception as exc:
            logger.error("PSOOptimizer failed: %s", exc, exc_info=True)
            return SAResult(
                best_state   = self._topo.copy_state(),
                best_cost    = float("inf"),
                n_iterations = 0,
                termination  = "failed",
            )

    def _run_pso(self) -> Any:
        from sa_optimizer import SAResult

        blocks     = self._topo._blocks
        nets       = self._topo._nets
        sym_groups = self._topo._sym_groups
        cfg        = self._pso
        rng        = random.Random(cfg.seed)

        bids = list(blocks.keys())
        if not bids:
            return SAResult(
                best_state   = self._topo.copy_state(),
                best_cost    = 0.0,
                n_iterations = 0,
                termination  = "trivial",
            )

        block_dims:  dict[str, tuple[float, float]] = {bid: _block_dims(blocks[bid]) for bid in bids}
        variant_map: dict[str, int]                 = {bid: 0 for bid in bids}

        total_area = sum(w * h for w, h in block_dims.values())
        canvas     = math.sqrt(max(total_area, 1.0)) * cfg.canvas_factor
        v_max      = canvas * cfg.v_max_factor
        # All symmetry groups share one vertical axis at the canvas midpoint.
        # A floating per-group axis (axis = master's own center) is wrong:
        # it makes slave_cx = master_cx, collapsing the slave onto the master.
        sym_axis = canvas / 2.0

        # slave_set:    blocks whose (x, y) is derived from a master
        # master_set:   pair-master blocks — PSO restricts them to the left half
        # master_x_max: per-master hard x-limit that guarantees DRC x-spacing to slave
        # pso_bids:     all non-slave blocks (masters + free blocks)
        slave_set:    set[str]         = set()
        master_set:   set[str]         = set()
        master_x_max: dict[str, float] = {}

        # Collect self-symmetric blocks from all groups upfront — their x is
        # pinned to sym_axis ± w/2, so masters from every group must clear them.
        all_self_syms: list[str] = []
        for g in sym_groups:
            for s in g.get("self_symmetric", []):
                s_id = str(s)
                if s_id in blocks:
                    all_self_syms.append(s_id)

        for group in sym_groups:
            for pair in group.get("pairs", []):
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    a, b = str(pair[0]), str(pair[1])
                    if a in blocks and b in blocks:
                        slave_set.add(b)
                        master_set.add(a)
                        w_a, _ = block_dims[a]
                        w_b, _ = block_dims[b]
                        sr     = compute_block_spacing(blocks[a], blocks[b])
                        # Constraint 1: master right edge + x_spacing + slave width
                        # must not cross sym_axis when master is at x_max.
                        x_max = sym_axis - sr.x_spacing / 2.0 - (3.0 * w_a + w_b) / 4.0
                        # Constraint 2+3: master and slave must clear every
                        # self-symmetric block (same group and cross-group).
                        # Self-sym blocks sit at a fixed x = sym_axis ± w_s/2.
                        for s_id in all_self_syms:
                            w_s, _ = block_dims[s_id]
                            sr_as  = compute_block_spacing(blocks[a], blocks[s_id])
                            sr_bs  = compute_block_spacing(blocks[b], blocks[s_id])
                            c_master = sym_axis - w_s / 2.0 - w_a - sr_as.x_spacing
                            c_slave  = (sym_axis - w_a / 2.0 - w_b / 2.0
                                        - w_s / 2.0 - sr_bs.x_spacing)
                            x_max = min(x_max, c_master, c_slave)
                        master_x_max[a] = max(0.0, x_max)

        pso_bids = [bid for bid in bids if bid not in slave_set]

        thresh: dict[tuple[str, str], tuple[float, float]] = {}
        n = len(bids)
        for i in range(n):
            for j in range(i + 1, n):
                bi, bj = bids[i], bids[j]
                sr     = compute_block_spacing(blocks[bi], blocks[bj])
                wi, hi = block_dims[bi]
                wj, hj = block_dims[bj]
                thresh[(bi, bj)] = (
                    (wi + wj) / 2.0 + sr.x_spacing,
                    (hi + hj) / 2.0 + sr.y_spacing,
                )

        fdgd_positions: dict[str, tuple[float, float]] = {}
        if cfg.use_fdgd_init:
            try:
                from fdgd import run_fdgd
                centroids = run_fdgd(blocks, nets, seed=0)
                for bid, (cx, cy) in centroids.items():
                    w, h = block_dims[bid]
                    fdgd_positions[bid] = (max(0.0, cx - w / 2.0), max(0.0, cy - h / 2.0))
            except Exception as exc:
                logger.debug("FDGD skipped (%s), using random init for particle 0", exc)

        def _clamp(bid: str, x: float, y: float) -> tuple[float, float]:
            w, h = block_dims[bid]
            return (
                max(0.0, min(canvas - w, x)),
                max(0.0, min(canvas - h, y)),
            )

        def _clamp_master(bid: str, x: float, y: float) -> tuple[float, float]:
            # x bounded by master_x_max so the mirrored slave clears DRC spacing
            w, h  = block_dims[bid]
            x_max = master_x_max.get(bid, sym_axis - w)
            return (
                max(0.0, min(x_max, x)),
                max(0.0, min(canvas - h, y)),
            )

        def _enforce_symmetry(positions: dict) -> None:
            for group in sym_groups:
                for pair in group.get("pairs", []):
                    if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                        continue
                    a, b = str(pair[0]), str(pair[1])
                    if a not in positions or b not in blocks:
                        continue
                    x_a, y_a = positions[a]
                    w_a, _   = block_dims[a]
                    w_b, _   = block_dims[b]
                    cx_b     = 2.0 * sym_axis - (x_a + w_a / 2.0)
                    positions[b] = _clamp(b, cx_b - w_b / 2.0, y_a)

                for s in group.get("self_symmetric", []):
                    s_id = str(s)
                    if s_id not in positions:
                        continue
                    _, y_s = positions[s_id]
                    w_s, _ = block_dims[s_id]
                    positions[s_id] = _clamp(s_id, sym_axis - w_s / 2.0, y_s)

        def _overlap_penalty(positions: dict) -> float:
            total = 0.0
            for i in range(n):
                for j in range(i + 1, n):
                    bi, bj = bids[i], bids[j]
                    xi, yi = positions[bi]
                    xj, yj = positions[bj]
                    wi, hi = block_dims[bi]
                    wj, hj = block_dims[bj]
                    dx     = abs((xi + wi / 2.0) - (xj + wj / 2.0))
                    dy     = abs((yi + hi / 2.0) - (yj + hj / 2.0))
                    tx, ty = thresh[(bi, bj)]
                    viol_x = max(0.0, tx - dx)
                    viol_y = max(0.0, ty - dy)
                    if viol_x > 0.0 and viol_y > 0.0:
                        total += viol_x * viol_y
            return cfg.overlap_penalty_w * total

        def _total_cost(positions: dict) -> tuple[float, float]:
            base    = self._evaluator.evaluate(positions)
            overlap = _overlap_penalty(positions)
            return base + overlap, overlap

        def _init_particle(particle_idx: int) -> dict[str, tuple[float, float]]:
            pos: dict[str, tuple[float, float]] = {}
            if particle_idx == 0 and fdgd_positions:
                pos = dict(fdgd_positions)
                for bid in bids:
                    if bid not in pos:
                        w, h = block_dims[bid]
                        pos[bid] = (rng.uniform(0.0, canvas - w), rng.uniform(0.0, canvas - h))
            else:
                for bid in bids:
                    w, h = block_dims[bid]
                    pos[bid] = (rng.uniform(0.0, canvas - w), rng.uniform(0.0, canvas - h))

            # Clamp masters to left half; clamp free blocks to canvas.
            # FDGD may place either type outside valid bounds — clamp before
            # symmetry derivation. Slaves are skipped here; _enforce_symmetry derives them.
            for bid in bids:
                if bid in master_set:
                    pos[bid] = _clamp_master(bid, pos[bid][0], pos[bid][1])
                elif bid not in slave_set:
                    pos[bid] = _clamp(bid, pos[bid][0], pos[bid][1])

            _enforce_symmetry(pos)
            return pos

        swarm_pos: list[dict] = [_init_particle(i) for i in range(cfg.swarm_size)]
        swarm_vel: list[dict] = [
            {bid: (0.0, 0.0) for bid in pso_bids} for _ in range(cfg.swarm_size)
        ]

        pb_pos:  list[dict]  = [dict(p) for p in swarm_pos]
        pb_cost: list[float] = [_total_cost(p)[0] for p in swarm_pos]

        gb_idx  = min(range(cfg.swarm_size), key=lambda i: pb_cost[i])
        gb_pos  = dict(pb_pos[gb_idx])
        gb_cost = pb_cost[gb_idx]

        logger.debug(
            "PSO start: swarm=%d  n_blocks=%d  canvas=%.1f µm  gb_cost=%.4f",
            cfg.swarm_size, len(bids), canvas, gb_cost,
        )

        # Turn-around factor T per particle (paper Eq. 5): +1 normal, −1 when the
        # overlap fraction of total cost exceeds the threshold (escape from dense region).
        turn_around = [1] * cfg.swarm_size

        t_start = time.perf_counter()

        for it in range(cfg.max_iter):
            for i in range(cfg.swarm_size):
                T   = turn_around[i]
                pos = swarm_pos[i]
                vel = swarm_vel[i]

                new_vel: dict[str, tuple[float, float]] = {}
                new_pos: dict[str, tuple[float, float]] = dict(pos)

                for bid in pso_bids:
                    r1 = rng.random()
                    r2 = rng.random()
                    vx, vy = vel[bid]
                    px, py = pb_pos[i][bid]
                    gx, gy = gb_pos[bid]
                    x,  y  = pos[bid]

                    nvx = T * (cfg.inertia_w * vx
                               + cfg.c1 * r1 * (px - x)
                               + cfg.c2 * r2 * (gx - x))
                    nvy = T * (cfg.inertia_w * vy
                               + cfg.c1 * r1 * (py - y)
                               + cfg.c2 * r2 * (gy - y))

                    nvx = max(-v_max, min(v_max, nvx))
                    nvy = max(-v_max, min(v_max, nvy))
                    new_vel[bid] = (nvx, nvy)
                    nx, ny = x + nvx, y + nvy
                    new_pos[bid] = _clamp_master(bid, nx, ny) if bid in master_set else _clamp(bid, nx, ny)

                _enforce_symmetry(new_pos)

                cost, overlap = _total_cost(new_pos)

                if cost > _COST_ZERO_GUARD and (overlap / cost) > cfg.turn_around_thresh:
                    turn_around[i] = -1
                else:
                    turn_around[i] = 1

                swarm_vel[i] = new_vel
                swarm_pos[i] = new_pos

                if cost < pb_cost[i]:
                    pb_pos[i]  = dict(new_pos)
                    pb_cost[i] = cost

                if cost < gb_cost:
                    gb_pos  = dict(new_pos)
                    gb_cost = cost
                    logger.debug("PSO iter %4d  new gb_cost=%.5f", it, gb_cost)
                    if self._observer:
                        self._observer.on_improvement(it, gb_cost, gb_pos)

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "PSO done: %d iter  %.0f ms  gb_cost=%.4f  n_blocks=%d",
            cfg.max_iter, elapsed_ms, gb_cost, len(bids),
        )

        # Resolve residual x-spacing/geometric-overlap violations caused by y-adjacency:
        # if two blocks are too close in x only because their y-ranges overlap, nudging
        # a movable block's y breaks the adjacency without changing symmetry constraints.
        #
        # y_movable includes masters: masters are x-constrained (via _clamp_master) but
        # free in y. Slaves are excluded — their y is derived from their master.
        # _enforce_symmetry is called after each pass so slave positions stay consistent
        # with any master that was moved.
        y_movable = set(bids) - slave_set
        repaired = dict(gb_pos)

        def _valid_y(tgt_bid: str, y_cand: float, exclude_bid: str) -> bool:
            # Return True if placing tgt_bid at y_cand creates no geometric overlap
            # with any block other than exclude_bid (the pair we are resolving).
            xt2, _   = repaired[tgt_bid]
            wt2, ht2 = block_dims[tgt_bid]
            for k in bids:
                if k == tgt_bid or k == exclude_bid:
                    continue
                xk, yk   = repaired[k]
                wk, hk   = block_dims[k]
                gx_k     = max(xk - (xt2 + wt2), xt2 - (xk + wk))
                gy_k     = max(yk - (y_cand + ht2), y_cand - (yk + hk))
                if gx_k < 0 and gy_k < 0:
                    return False
            return True

        for _ in range(10):
            changed = False
            moved_this_pass: set[str] = set()
            for i in range(n):
                for j in range(i + 1, n):
                    bi, bj = bids[i], bids[j]
                    xi, yi = repaired[bi]; xj, yj = repaired[bj]
                    wi, hi = block_dims[bi]; wj, hj = block_dims[bj]
                    gx = max(xj - (xi + wi), xi - (xj + wj))
                    gy = max(yj - (yi + hi), yi - (yj + hj))
                    if gy >= 0:
                        continue
                    sr_ij = compute_block_spacing(blocks[bi], blocks[bj])
                    if gx >= sr_ij.x_spacing - _FLOAT_EPS:
                        continue
                    # each block may only be moved once per pass to prevent oscillation
                    tgt = (bi if bi in y_movable and bi not in moved_this_pass
                           else bj if bj in y_movable and bj not in moved_this_pass
                           else None)
                    if tgt is None:
                        continue
                    oth   = bj if tgt == bi else bi
                    _, yo = repaired[oth];  _, ho = block_dims[oth]
                    xt, _ = repaired[tgt];  _, ht = block_dims[tgt]
                    y_above = max(0.0, min(canvas - ht, yo + ho + sr_ij.y_spacing + _REPAIR_GAP))
                    y_below = max(0.0, min(canvas - ht, yo - ht - sr_ij.y_spacing - _REPAIR_GAP))
                    sep_above    = y_above - (yo + ho)
                    sep_below    = yo - (y_below + ht)
                    above_ok     = _valid_y(tgt, y_above, oth)
                    below_ok     = _valid_y(tgt, y_below, oth)
                    if above_ok and below_ok:
                        chosen_y = y_above if sep_above >= sep_below else y_below
                    elif above_ok:
                        chosen_y = y_above
                    elif below_ok:
                        chosen_y = y_below
                    else:
                        continue  # no clean nudge; PSO penalty handles the residual
                    repaired[tgt] = (xt, chosen_y)
                    moved_this_pass.add(tgt)
                    changed = True
            _enforce_symmetry(repaired)
            if not changed:
                break
        gb_pos = repaired

        self._topo.set_solution(gb_pos, variant_map)
        best_state = self._topo.copy_state()

        return SAResult(
            best_state   = best_state,
            best_cost    = gb_cost,
            n_iterations = cfg.max_iter,
            termination  = "max_iter",
        )
