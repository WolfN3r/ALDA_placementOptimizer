"""
B*-tree topology — supports both SA and GA optimizers.

Internal state: binary tree where left-child = x-neighbour, right-child = y-neighbour.
decode() uses DFS pre-order with a typed contour (skyline) to derive block coordinates.

SA operators follow Lin, Yi & Chang (2001):
  Op1 (_op_variant) — change active variant (size/rotation) of one block.
  Op2 (_op_swap)    — exchange block assignments of two nodes.
  Op3 (_op_move)    — detach one node, re-insert via push-down.
  Extra (_op_rotate) — flip left/right children of one node (project addition).

perturb(temperature) expects temperature in [0, 1] (normalised fraction,
  1 = hot start, 0 = cold end).  The SA optimiser is responsible for
  mapping its internal schedule to this range before calling perturb().
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable

from topology_base import TopologyBase, SAMixin, GAMixin
from spacing import compute_block_spacing, is_wpe_pair


# =============================================================================
# INTERNAL DATA STRUCTURES
# =============================================================================

class _Node:
    """One node in the B*-tree. Holds block assignment and tree links."""
    __slots__ = ("block_id", "variant_idx", "left", "right", "parent")

    def __init__(self, block_id: str, variant_idx: int) -> None:
        self.block_id:    str          = block_id
        self.variant_idx: int          = variant_idx
        self.left:   "_Node | None"   = None   # x-child (placed to the right)
        self.right:  "_Node | None"   = None   # y-child (placed above)
        self.parent: "_Node | None"   = None


# =============================================================================
# CONTOUR HELPERS
# =============================================================================

def _contour_query(
    contour: list[tuple[float, float, float, float, str]],
    x_l: float,
    x_r: float,
    dt_new: str,
    ch: float,
) -> float:
    """
    2-D contour query — return the y-floor for a new block (type dt_new,
    x-range [x_l, x_r], height ch) that satisfies *all* pairwise DRC spacing.

    Each contour segment is a 5-tuple (x_l, x_r, y_bot, y_top, dt).
    Three cases per segment:

    x-overlap (x_gap == 0):
        Standard 1-D skyline — y_floor = y_top + y_spacing.

    x-gap (x_gap > 0), WPE pair (different_bulks / different_deviceGroups):
        Well boundary requires Euclidean corner clearance:
            sqrt(x_gap² + y_gap²) ≥ req = max(WPE_active, WPE_poly)
        Solved for y_gap:
            y_floor = y_top + sqrt(req² - x_gap²) + 1e-6
        The +1e-6 guards against IEEE rounding where the computed sqrt is
        fractionally below req, which would cause the DRC checker to flag a
        spurious violation at exactly the limit.

    x-gap (x_gap > 0), non-WPE pair:
        The DRC checker has no diagonal constraint for non-WPE pairs, BUT it
        does fire an "active" (x-direction) violation when x_gap < req_active
        AND the blocks share a y-band.  To prevent sharing a y-band we push
        the new block above the segment: y_floor = y_top + 1e-6.
        y_bot is checked against the running max_h to avoid pushing when the
        new block's y-range cannot actually overlap the segment.
    """
    max_h = 0.0
    blk_new = {"device_type": dt_new}
    for (cx_l, cx_r, cy_bot, cy_top, cy_dt) in contour:
        blk_seg = {"device_type": cy_dt}
        sp      = compute_block_spacing(blk_seg, blk_new)
        x_gap   = max(0.0, max(x_l - cx_r, cx_l - x_r))

        if x_gap < 1e-9:
            # Standard y-spacing (1-D skyline)
            effective = cy_top + sp.y_spacing

        elif is_wpe_pair(blk_seg, blk_new):
            # WPE corner clearance for diagonal pairs
            req_corner = max(sp.x_spacing, sp.y_spacing)
            if x_gap < req_corner:
                effective = (
                    cy_top
                    + math.sqrt(max(0.0, req_corner ** 2 - x_gap ** 2))
                    + 1e-6   # IEEE rounding guard
                )
            else:
                effective = 0.0  # x-gap already satisfies corner distance

        elif x_gap < sp.x_spacing:
            # Non-WPE with insufficient x-gap: DRC fires only when y-bands
            # overlap.  Using max_h as the running y-floor estimate, check
            # whether [max_h, max_h+ch] and [cy_bot, cy_top] intersect.
            y_overlap = min(max_h + ch, cy_top) - max(max_h, cy_bot)
            if y_overlap > 1e-9:
                effective = cy_top + 1e-6  # push above → diagonal → no DRC
            else:
                effective = 0.0

        else:
            effective = 0.0  # non-WPE, x-gap already sufficient

        if effective > max_h:
            max_h = effective
    return max_h


def _contour_update(
    contour: list[tuple[float, float, float, float, str]],
    x_l: float,
    x_r: float,
    y_bot: float,
    y_top: float,
    dt: str,
) -> None:
    contour.append((x_l, x_r, y_bot, y_top, dt))


# =============================================================================
# TREE HELPERS
# =============================================================================

def _bfs_subtree(root: _Node) -> list[_Node]:
    """Return all nodes reachable from root (root included) in BFS order."""
    result: list[_Node] = []
    queue = [root]
    while queue:
        curr = queue.pop(0)
        result.append(curr)
        if curr.left:
            queue.append(curr.left)
        if curr.right:
            queue.append(curr.right)
    return result


# =============================================================================
# B*-TREE TOPOLOGY
# =============================================================================

class BStarTopology(TopologyBase, SAMixin, GAMixin):
    """
    B*-tree placement topology.

    Capabilities: SA (perturb/undo) and GA (mutate/crossover/random_init).
    """

    def __init__(self, blocks: dict, nets: list) -> None:
        # block_id → block definition dict (read-only after construction)
        self._blocks: dict = blocks
        self._nets:   list = nets
        self._root:  _Node | None = None
        self._nodes: list[_Node]  = []   # all nodes, positionally stable

    # ------------------------------------------------------------------
    # TopologyBase
    # ------------------------------------------------------------------

    def seed(self, blocks: dict, mode: str = "random") -> None:
        """Build a valid binary tree from the block list."""
        self._blocks = blocks
        ids = [bid for bid, b in blocks.items() if "error" not in b]
        if not ids:
            self._root  = None
            self._nodes = []
            return

        # Each block gets one node; pick default (first valid) variant
        nodes = [_Node(bid, self._default_variant_idx(bid)) for bid in ids]

        if mode == "random":
            random.shuffle(nodes)

        self._root = nodes[0]
        self._root.parent = None

        for node in nodes[1:]:
            # Find a node with at least one free slot
            candidates = [
                n for n in nodes[:nodes.index(node)]
                if n.left is None or n.right is None
            ]
            parent = random.choice(candidates) if mode == "random" else candidates[0]

            free_left  = parent.left  is None
            free_right = parent.right is None
            if free_left and free_right:
                go_left = random.random() < 0.5 if mode == "random" else True
            else:
                go_left = free_left

            if go_left:
                parent.left = node
            else:
                parent.right = node
            node.parent = parent

        self._nodes = nodes

    def decode(self) -> dict[str, tuple[float, float]]:
        """
        DFS pre-order traversal → block (x, y) positions.
        Typed contour tracks effective height per device-type pair.

        x-child: cx = parent.x + parent.w + x_spacing(parent→child)
                 cy = max(parent.y, contour_query(child_x_range, child_dt))
        y-child: cx = parent.x
                 cy = contour_query(child_x_range, child_dt)
                 [contour_query already includes y_spacing — do NOT add it again]
        """
        if self._root is None:
            return {}

        positions: dict[str, tuple[float, float]] = {}
        # contour entries: (x_left, x_right, y_bot, y_top, device_type)
        contour: list[tuple[float, float, float, float, str]] = []
        node_geom: dict[str, tuple[float, float, float, float]] = {}  # block_id → (x,y,w,h)

        def _get_block_dims(node: _Node) -> tuple[float, float, str]:
            block   = self._blocks[node.block_id]
            variant = block["variants"][node.variant_idx]
            bb      = variant["main_bbox"]
            return bb["x_max"], bb["y_max"], block.get("device_type", "")

        # Root placed at origin
        rw, rh, rdt = _get_block_dims(self._root)
        positions[self._root.block_id] = (0.0, 0.0)
        node_geom[self._root.block_id] = (0.0, 0.0, rw, rh)
        _contour_update(contour, 0.0, rw, 0.0, rh, rdt)

        # Iterative DFS pre-order (right pushed first → left processed first)
        dfs_stack: list[_Node] = []
        if self._root.right:
            dfs_stack.append(self._root.right)
        if self._root.left:
            dfs_stack.append(self._root.left)

        while dfs_stack:
            node = dfs_stack.pop()
            parent = node.parent
            px, py, pw, ph = node_geom[parent.block_id]
            _, _, p_dt = _get_block_dims(parent)
            cw, ch, c_dt = _get_block_dims(node)

            if node is parent.left:
                # x-child: placed to the right of parent
                sp = compute_block_spacing({"device_type": p_dt}, {"device_type": c_dt})
                cx = px + pw + sp.x_spacing
                cy = _contour_query(contour, cx, cx + cw, c_dt, ch)
                cy = max(cy, py)   # x-child must not fall below parent's baseline
            else:
                # y-child: same x-column as parent.
                # Query uses child width (not parent width) so child's full footprint
                # is checked.  _contour_query already adds y_spacing — never add again.
                cx = px
                cy = _contour_query(contour, cx, cx + cw, c_dt, ch)

            positions[node.block_id] = (cx, cy)
            node_geom[node.block_id] = (cx, cy, cw, ch)
            _contour_update(contour, cx, cx + cw, cy, cy + ch, c_dt)

            if node.right:
                dfs_stack.append(node.right)
            if node.left:
                dfs_stack.append(node.left)

        return positions

    def copy_state(self) -> Any:
        """Return a deep-copyable representation of the tree structure."""
        if not self._nodes:
            return ([], -1)
        idx = {id(n): i for i, n in enumerate(self._nodes)}
        rows = []
        for n in self._nodes:
            l = idx[id(n.left)]   if n.left   else -1
            r = idx[id(n.right)]  if n.right  else -1
            p = idx[id(n.parent)] if n.parent else -1
            rows.append((n.block_id, n.variant_idx, l, r, p))
        root_idx = idx[id(self._root)]
        return (rows, root_idx)

    def restore_state(self, saved: Any) -> None:
        rows, root_idx = saved
        if not rows:
            self._nodes = []
            self._root  = None
            return
        nodes = [_Node(r[0], r[1]) for r in rows]
        for i, (bid, vidx, l, r, p) in enumerate(rows):
            nodes[i].left   = nodes[l] if l >= 0 else None
            nodes[i].right  = nodes[r] if r >= 0 else None
            nodes[i].parent = nodes[p] if p >= 0 else None
        self._nodes = nodes
        self._root  = nodes[root_idx]

    def capabilities(self) -> set[str]:
        return {"SA", "GA"}

    # ------------------------------------------------------------------
    # SAMixin
    # ------------------------------------------------------------------

    def perturb(self, temperature: float) -> Callable[[], None]:
        """
        Choose and apply one SA operator and return its undo closure.

        temperature — normalised fraction in [0, 1].  1 = hot (start of run),
          0 = cold (end of run).  The SA optimiser maps its internal schedule
          to this range before calling.  Operator weights shift from structural
          (swap, move) at high T to fine-grained (rotate, variant) at low T.
        """
        if not self._nodes:
            return lambda: None

        t = min(1.0, max(0.0, temperature))
        weights = [
            0.15 + 0.10 * (1 - t),   # _op_rotate:  more at low T
            0.35 - 0.10 * (1 - t),   # _op_swap
            0.35 - 0.05 * (1 - t),   # _op_move
            0.15 + 0.05 * (1 - t),   # _op_variant
        ]
        r = random.random() * sum(weights)
        cumulative = 0.0
        ops = [self._op_rotate, self._op_swap, self._op_move, self._op_variant]
        chosen = ops[-1]
        for op, w in zip(ops, weights):
            cumulative += w
            if r <= cumulative:
                chosen = op
                break
        return chosen()

    def _op_rotate(self) -> Callable[[], None]:
        """Flip left and right children of a random node (structural perturbation)."""
        node = random.choice(self._nodes)
        old_l, old_r = node.left, node.right
        node.left, node.right = old_r, old_l
        def undo() -> None:
            node.left, node.right = old_l, old_r
        return undo

    def _op_swap(self) -> Callable[[], None]:
        """
        Exchange block assignment (block_id, variant_idx) of two random nodes.
        Clamps variant_idx to the destination block's variant count to prevent
        out-of-range access when blocks have different numbers of variants.
        """
        a, b = random.sample(self._nodes, 2)
        old_a_bid,  old_a_vidx = a.block_id, a.variant_idx
        old_b_bid,  old_b_vidx = b.block_id, b.variant_idx

        n_vars_b = len(self._blocks.get(old_b_bid, {}).get("variants", [1]))
        n_vars_a = len(self._blocks.get(old_a_bid, {}).get("variants", [1]))

        a.block_id    = old_b_bid
        a.variant_idx = min(old_b_vidx, max(0, n_vars_b - 1))
        b.block_id    = old_a_bid
        b.variant_idx = min(old_a_vidx, max(0, n_vars_a - 1))

        def undo() -> None:
            a.block_id, a.variant_idx = old_a_bid, old_a_vidx
            b.block_id, b.variant_idx = old_b_bid, old_b_vidx
        return undo

    def _op_move(self) -> Callable[[], None]:
        """
        Detach a random non-root node and re-insert it via push-down (paper Op3).

        Detach cases:
          A. Leaf             → clean removal.
          B. One child C      → C takes n's slot in parent.
          C. Two children L,R → promote L to n's slot; re-insert R via push-down
                                on a node outside R's subtree (prevents cycles).

        Insert: push-down at a random target node (any node except n itself).
        Push-down: n becomes target's child; target's old child becomes n's child.

        All mutations are preceded by a save; undo replays in reverse order.
        Because the first (chronological) save for any node captures the true
        original state, reversed replay always restores correctly even if a node
        is saved more than once.
        """
        # Exclude orphaned nodes: a node is valid only if its parent still
        # forward-links back to it.  Stale parent pointers (from prior
        # Bug-1-style corruption) would cause n_is_left to be evaluated
        # incorrectly, detaching the wrong child and deepening corruption.
        non_root = [
            nd for nd in self._nodes
            if nd.parent is not None
            and (nd.parent.left is nd or nd.parent.right is nd)
        ]
        if not non_root:
            return lambda: None

        n         = random.choice(non_root)
        n_parent  = n.parent
        n_is_left = (n_parent.left is n)
        n_left    = n.left
        n_right   = n.right

        saved: list[tuple] = []

        def _save(node: _Node) -> None:
            saved.append((node, node.left, node.right, node.parent))

        def _push_down(target: _Node, node: _Node) -> None:
            """
            Insert node as a child of target, pushing target's existing child
            down as node's child.  node must be a leaf before calling.
            """
            go_left = random.random() < 0.5
            _save(target)
            _save(node)
            if go_left:
                old_child   = target.left
                target.left = node
                node.parent = target
                node.left   = old_child
                if old_child:
                    _save(old_child)
                    old_child.parent = node
            else:
                old_child    = target.right
                target.right = node
                node.parent  = target
                node.right   = old_child
                if old_child:
                    _save(old_child)
                    old_child.parent = node

        def _abort() -> Callable[[], None]:
            for (nd, ol, or_, op) in reversed(saved):
                nd.left, nd.right, nd.parent = ol, or_, op
            return lambda: None

        # --- Save initial states ---
        _save(n)
        _save(n_parent)

        # --- Detach n from the tree ---
        if n_left is None and n_right is None:
            # Case A: leaf — clean removal
            if n_is_left:
                n_parent.left  = None
            else:
                n_parent.right = None

        elif n_right is None:
            # Case B: left child only
            _save(n_left)
            if n_is_left:
                n_parent.left  = n_left
            else:
                n_parent.right = n_left
            n_left.parent = n_parent

        elif n_left is None:
            # Case B: right child only
            _save(n_right)
            if n_is_left:
                n_parent.left  = n_right
            else:
                n_parent.right = n_right
            n_right.parent = n_parent

        else:
            # Case C: two children — promote left, re-attach right subtree.
            # n_right is a subtree root with its own children; _push_down must
            # NOT be used here because it does `node.left = old_child`, which
            # overwrites one of n_right's existing children and orphans it.
            # Instead, find a node outside n_right's subtree that has an empty
            # slot and attach n_right there, preserving its subtree intact.
            _save(n_left)
            if n_is_left:
                n_parent.left  = n_left
            else:
                n_parent.right = n_left
            n_left.parent = n_parent

            r_ids   = {id(nd) for nd in _bfs_subtree(n_right)}
            valid_r = [
                nd for nd in self._nodes
                if nd is not n
                and id(nd) not in r_ids
                and (nd.left is None or nd.right is None)
            ]
            if not valid_r:
                return _abort()
            ins = random.choice(valid_r)
            _save(ins)
            _save(n_right)
            if ins.left is None:
                ins.left = n_right
            else:
                ins.right = n_right
            n_right.parent = ins

        # n is now detached — clear all its links before re-inserting
        n.left   = None
        n.right  = None
        n.parent = None

        # --- Re-insert n via push-down ---
        valid = [nd for nd in self._nodes if nd is not n]
        if not valid:
            return _abort()

        _push_down(random.choice(valid), n)

        saved_snap = list(saved)

        def undo() -> None:
            for (nd, old_l, old_r, old_p) in reversed(saved_snap):
                nd.left   = old_l
                nd.right  = old_r
                nd.parent = old_p

        return undo

    def _op_variant(self) -> Callable[[], None]:
        """
        Change the active variant of a random block.
        Rotation is represented as a separate variant entry — no special
        rotate operator is needed.
        """
        node = random.choice(self._nodes)
        block    = self._blocks.get(node.block_id, {})
        variants = block.get("variants", [])
        if len(variants) <= 1:
            return lambda: None
        old_vidx = node.variant_idx
        new_vidx = random.choice(
            [i for i in range(len(variants)) if i != old_vidx]
        )
        node.variant_idx = new_vidx
        def undo() -> None:
            node.variant_idx = old_vidx
        return undo

    # ------------------------------------------------------------------
    # GAMixin
    # ------------------------------------------------------------------

    def mutate(self) -> Callable[[], None]:
        return self.perturb(temperature=0.5)

    def crossover(self, other: "BStarTopology") -> "BStarTopology":
        """
        B*-tree crossover via DFS+binary encoding.
        1. Encode both trees as (permutation, direction_vector).
        2. Apply OX crossover to permutations, single-point to direction vectors.
        3. Reconstruct a new valid tree.
        """
        perm_a, dirs_a = self._encode()
        perm_b, dirs_b = other._encode()

        offspring_perm = _ox_crossover(perm_a, perm_b)
        cut = random.randint(1, max(1, len(dirs_a) - 1))
        offspring_dirs = dirs_a[:cut] + dirs_b[cut:]

        child = BStarTopology(self._blocks, self._nets)
        child._nodes = [_Node(bid, self._default_variant_idx(bid)) for bid in offspring_perm]
        child._root  = child._nodes[0]
        child._root.parent = None
        child._reconstruct_from_dirs(offspring_dirs)
        return child

    def random_init(self) -> None:
        self.seed(self._blocks, mode="random")

    # ------------------------------------------------------------------
    # Encoding helpers for GA crossover
    # ------------------------------------------------------------------

    def _encode(self) -> tuple[list[str], list[int]]:
        """DFS pre-order → (block_id permutation, x/y direction bits)."""
        if self._root is None:
            return [], []
        perm: list[str] = []
        dirs: list[int] = []   # 0 = x-child (left), 1 = y-child (right)

        def _dfs(node: _Node) -> None:
            perm.append(node.block_id)
            if node.left:
                dirs.append(0)
                _dfs(node.left)
            if node.right:
                dirs.append(1)
                _dfs(node.right)

        _dfs(self._root)
        return perm, dirs

    def _reconstruct_from_dirs(self, dirs: list[int]) -> None:
        """
        Attach self._nodes[1:] as children in order, using dirs as preferred slot.
        Applies four-level slot-conflict fallback.
        """
        nodes = self._nodes
        if len(nodes) <= 1:
            return

        dir_idx = 0
        for node in nodes[1:]:
            node.left   = None
            node.right  = None
            node.parent = None

            preferred_left = (dir_idx < len(dirs) and dirs[dir_idx] == 0)
            dir_idx += 1

            inserted = False
            in_tree  = [n for n in nodes if n is nodes[0] or n.parent is not None]
            random.shuffle(in_tree)

            for candidate in in_tree:
                if preferred_left and candidate.left is None:
                    candidate.left = node
                    node.parent    = candidate
                    inserted = True
                    break
                if not preferred_left and candidate.right is None:
                    candidate.right = node
                    node.parent     = candidate
                    inserted = True
                    break

            if not inserted:
                # Walk right spine from root
                curr = nodes[0]
                while curr:
                    if curr.left is None:
                        curr.left   = node
                        node.parent = curr
                        inserted = True
                        break
                    if curr.right is None:
                        curr.right  = node
                        node.parent = curr
                        inserted = True
                        break
                    curr = curr.right

            if not inserted:
                # BFS scan of all tree nodes
                queue = [nodes[0]]
                while queue and not inserted:
                    curr = queue.pop(0)
                    if curr.left is None:
                        curr.left   = node
                        node.parent = curr
                        inserted = True
                    elif curr.right is None:
                        curr.right  = node
                        node.parent = curr
                        inserted = True
                    else:
                        queue.append(curr.left)
                        queue.append(curr.right)

    def get_variant_map(self) -> dict[str, int]:
        return {node.block_id: node.variant_idx for node in self._nodes}

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _default_variant_idx(self, block_id: str) -> int:
        block = self._blocks.get(block_id, {})
        variants = block.get("variants", [])
        for i, v in enumerate(variants):
            if v.get("is_used"):
                return i
        return 0


# =============================================================================
# CROSSOVER HELPERS
# =============================================================================

def _ox_crossover(perm_a: list[str], perm_b: list[str]) -> list[str]:
    """Order Crossover (OX) producing one offspring permutation."""
    n = len(perm_a)
    if n == 0:
        return []
    i, j = sorted(random.sample(range(n), 2))
    segment   = perm_a[i:j + 1]
    remaining = [x for x in perm_b if x not in segment]
    result    = remaining[:i] + segment + remaining[i:]
    return result[:n]
