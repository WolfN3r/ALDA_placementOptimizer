"""
B*-tree topology — supports both SA and GA optimizers.

Internal state: binary tree where left-child = x-neighbour, right-child = y-neighbour.
decode() uses DFS pre-order with a typed contour (skyline) to derive block coordinates.
"""
from __future__ import annotations

import copy
import random
from typing import Any, Callable

from topology_base import TopologyBase, SAMixin, GAMixin
from spacing import compute_block_spacing


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
    contour: list[tuple[float, float, float, str]],
    x_l: float,
    x_r: float,
    dt_new: str,
) -> float:
    """
    Return the effective height that blocks already in contour present to a new
    block of type dt_new placed in the x-range [x_l, x_r].
    effective_h = physical_top + y_spacing(placed_type, dt_new)
    """
    max_h = 0.0
    for (cx_l, cx_r, cy_top, cy_dt) in contour:
        if cx_r <= x_l or cx_l >= x_r:
            continue
        sp = compute_block_spacing({"device_type": cy_dt}, {"device_type": dt_new})
        effective = cy_top + sp.y_spacing
        if effective > max_h:
            max_h = effective
    return max_h


def _contour_update(
    contour: list[tuple[float, float, float, str]],
    x_l: float,
    x_r: float,
    y_top: float,
    dt: str,
) -> None:
    contour.append((x_l, x_r, y_top, dt))


# =============================================================================
# B*-TREE TOPOLOGY
# =============================================================================

class BStarTopology(TopologyBase, SAMixin, GAMixin):
    """
    B*-tree placement topology.

    Capabilities: SA (perturb/undo) and GA (mutate/crossover/random_init).
    Super-block symmetry constraints are detected during seed() — stub only,
    full implementation follows architecture step 13.
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
        Typed contour tracks effective height per device-type.
        """
        if self._root is None:
            return {}

        positions: dict[str, tuple[float, float]] = {}
        # contour entries: (x_left, x_right, y_top, device_type)
        contour: list[tuple[float, float, float, str]] = []

        # Stack entries: (node, parent_x, parent_y, parent_w, parent_h, parent_dt, is_left_child)
        stack = [(self._root, None)]
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
        _contour_update(contour, 0.0, rw, rh, rdt)

        # Iterative DFS pre-order
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

            sp = compute_block_spacing(
                {"device_type": p_dt}, {"device_type": c_dt}
            )

            if node is parent.left:
                # x-child: place to the right of parent
                cx = px + pw + sp.x_spacing
                cy = _contour_query(contour, cx, cx + cw, c_dt)
                # must not fall below parent baseline
                cy = max(cy, py)
            else:
                # y-child: place above parent (same x)
                cx = px
                cy = _contour_query(contour, px, px + pw, c_dt) + sp.y_spacing

            positions[node.block_id] = (cx, cy)
            node_geom[node.block_id] = (cx, cy, cw, ch)
            _contour_update(contour, cx, cx + cw, cy + ch, c_dt)

            # push children (right first so left is processed first)
            if node.right:
                dfs_stack.append(node.right)
            if node.left:
                dfs_stack.append(node.left)

        return positions

    def copy_state(self) -> Any:
        """Return a deep-copyable representation of the tree structure."""
        # Store as (block_id, variant_idx, left_index, right_index) with root index 0
        if not self._nodes:
            return ([], -1)
        idx = {id(n): i for i, n in enumerate(self._nodes)}
        rows = []
        for n in self._nodes:
            l = idx[id(n.left)]  if n.left  else -1
            r = idx[id(n.right)] if n.right else -1
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
        Choose and apply one SA operator. At high temperature, favour structural
        moves (swap, move); at low temperature, favour fine-tuning (rotate, variant).
        """
        if not self._nodes:
            return lambda: None

        # Operator weights: [rotate, swap, move, variant_change]
        # temp_fraction ∈ [0, 1]: 1 = hot, 0 = cold
        t_frac = min(1.0, temperature / 1.0)
        weights = [
            0.15 + 0.10 * (1 - t_frac),   # rotate: more at low T
            0.35 - 0.10 * (1 - t_frac),   # swap
            0.35 - 0.05 * (1 - t_frac),   # move
            0.15 + 0.05 * (1 - t_frac),   # variant change
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
        """Swap left and right children of a random node."""
        node = random.choice(self._nodes)
        old_l, old_r = node.left, node.right
        node.left, node.right = old_r, old_l
        def undo() -> None:
            node.left, node.right = old_l, old_r
        return undo

    def _op_swap(self) -> Callable[[], None]:
        """Exchange block assignment (block_id, variant_idx) of two nodes."""
        a, b = random.sample(self._nodes, 2)
        old_a_bid, old_a_vidx = a.block_id, a.variant_idx
        old_b_bid, old_b_vidx = b.block_id, b.variant_idx
        a.block_id, a.variant_idx = old_b_bid, old_b_vidx
        b.block_id, b.variant_idx = old_a_bid, old_a_vidx
        def undo() -> None:
            a.block_id, a.variant_idx = old_a_bid, old_a_vidx
            b.block_id, b.variant_idx = old_b_bid, old_b_vidx
        return undo

    def _op_move(self) -> Callable[[], None]:
        """
        Detach a random non-root node and re-insert it at a random free slot.
        If the detached node had two children, the left child is promoted and
        the right child is re-inserted into the promoted subtree.
        """
        non_root = [n for n in self._nodes if n.parent is not None]
        if not non_root:
            return lambda: None

        n        = random.choice(non_root)
        n_parent = n.parent
        n_is_left = (n_parent.left is n)

        # Save all affected node attributes by value (not reference)
        saved: list[tuple] = []
        def _save(node: _Node) -> None:
            saved.append((node, node.left, node.right, node.parent))

        _save(n)
        _save(n_parent)

        n_left  = n.left
        n_right = n.right

        demoted:          _Node | None = None
        demoted_old_par:  _Node | None = None
        demoted_is_left:  bool         = False
        promoted:         _Node | None = None

        if n_left is None and n_right is None:
            # Leaf: detach cleanly
            if n_is_left:
                n_parent.left = None
            else:
                n_parent.right = None

        elif n_left is not None and n_right is None:
            promoted = n_left
            _save(promoted)
            if n_is_left:
                n_parent.left = promoted
            else:
                n_parent.right = promoted
            promoted.parent = n_parent

        elif n_left is None and n_right is not None:
            promoted = n_right
            _save(promoted)
            if n_is_left:
                n_parent.left = promoted
            else:
                n_parent.right = promoted
            promoted.parent = n_parent

        else:
            # Two children: promote left, insert right into promoted subtree
            promoted = n_left
            demoted  = n_right
            _save(promoted)
            _save(demoted)
            if n_is_left:
                n_parent.left = promoted
            else:
                n_parent.right = promoted
            promoted.parent = n_parent

            # Find first free slot in promoted subtree (BFS)
            queue = [promoted]
            inserted = False
            while queue and not inserted:
                curr = queue.pop(0)
                if curr.left is None:
                    _save(curr)
                    demoted_old_par = curr
                    demoted_is_left = True
                    curr.left       = demoted
                    demoted.parent  = curr
                    inserted = True
                elif curr.right is None:
                    _save(curr)
                    demoted_old_par = curr
                    demoted_is_left = False
                    curr.right      = demoted
                    demoted.parent  = curr
                    inserted = True
                else:
                    queue.append(curr.left)
                    queue.append(curr.right)

        # Clear n's links before re-inserting
        n.left   = None
        n.right  = None
        n.parent = None

        # Find a free slot anywhere in the tree (excluding n itself)
        free_slots: list[tuple[_Node, bool]] = []
        stack = [self._root]
        while stack:
            curr = stack.pop()
            if curr is n:
                continue
            if curr.left is None:
                free_slots.append((curr, True))
            else:
                stack.append(curr.left)
            if curr.right is None:
                free_slots.append((curr, False))
            else:
                stack.append(curr.right)

        if not free_slots:
            # Undo partial changes and return no-op
            for (node, old_l, old_r, old_p) in reversed(saved):
                node.left, node.right, node.parent = old_l, old_r, old_p
            return lambda: None

        target, target_is_left = random.choice(free_slots)
        _save(target)
        if target_is_left:
            target.left = n
        else:
            target.right = n
        n.parent = target

        # Capture for undo closure
        n_new_parent  = target
        n_new_is_left = target_is_left
        saved_snapshot = list(saved)  # copy by value

        def undo() -> None:
            for (node, old_l, old_r, old_p) in reversed(saved_snapshot):
                node.left   = old_l
                node.right  = old_r
                node.parent = old_p

        return undo

    def _op_variant(self) -> Callable[[], None]:
        """Change the active size variant of a random block (includes rotation variants)."""
        node = random.choice(self._nodes)
        block = self._blocks.get(node.block_id, {})
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
        perm:  list[str] = []
        dirs:  list[int] = []   # 0 = x-child (left), 1 = y-child (right)
        stack  = [self._root]
        parent_seen: set[int] = set()

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
        Applies four-level slot-conflict fallback (see architecture §4).
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

            # Find insertion point with fallback
            inserted = False
            target_pool = [nodes[0]]   # start from root

            # Level 1+2: preferred and other slot on a random existing node
            candidates = [n for n in nodes if n is not node and n.parent is not None or n is nodes[0]]
            # More precisely: nodes that are already in the tree
            in_tree = [n for n in nodes if n is nodes[0] or n.parent is not None]
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
                # Level 3: walk right spine from root
                curr = nodes[0]
                while curr:
                    if curr.left is None:
                        curr.left  = node
                        node.parent = curr
                        inserted = True
                        break
                    if curr.right is None:
                        curr.right = node
                        node.parent = curr
                        inserted = True
                        break
                    curr = curr.right

            if not inserted:
                # Level 4: BFS scan of all tree nodes
                queue = [nodes[0]]
                while queue and not inserted:
                    curr = queue.pop(0)
                    if curr.left is None:
                        curr.left  = node
                        node.parent = curr
                        inserted = True
                    elif curr.right is None:
                        curr.right = node
                        node.parent = curr
                        inserted = True
                    else:
                        queue.append(curr.left)
                        queue.append(curr.right)

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
    segment = perm_a[i:j + 1]
    remaining = [x for x in perm_b if x not in segment]
    result = remaining[: i] + segment + remaining[i:]
    # Pad or trim to length n in case of rounding edge case
    return result[:n]
