"""
B*-tree topology — supports both SA and GA optimizers.

Two-level structure, following Chang et al. (2000) B*-trees and Lin, Chang &
Lin (2009) ASF-/HB*-trees:

  outer tree   — plain B*-tree over free (non-symmetric) blocks, plus at most
                 one HIERARCHY NODE when the netlist has a shared-axis
                 symmetry group (aggressive mode). left-child = x-neighbour,
                 right-child = y-neighbour, same as any other node.
  inner tree   — only inside the hierarchy node: an ASF-B*-tree over
                 REPRESENTATIVE nodes of the shared symmetry axis (one pair
                 member, or one self-symmetric block). Mirrors are never
                 given tree nodes — their position is derived by mirroring
                 after the representative tree is packed (_pack_island()).

decode() packs the inner tree once (_pack_island), then runs one ordinary
DFS+contour pass over the outer tree; wherever it reaches the hierarchy
node it stamps every island member's position and pushes each member's own
bbox into the shared contour (instead of one padded bounding box), so free
blocks placed afterwards see the island's true rectilinear top silhouette —
this is the "contour node" mechanism from Lin 2009, reused directly through
the existing typed-contour machinery rather than reified as its own tree
nodes (this project only ever has one shared axis per run — see
.claude/plans/bstar_symmetry_island_reimplementation.md §5.2 for why the
paper's general multi-segment contour-node bookkeeping isn't needed here).

SA operators:
  Outer tree (Chang 2000 Op1-3):
    _op_variant     — change active variant (size/rotation) of one block.
    _op_swap_outer  — exchange block assignments of two free-tree nodes.
    _op_move_outer  — detach one node, re-insert via push-down.
  Inner tree (Lin 2009 Op2-4, restricted to the representative sub-tree):
    _op_swap_inner  — exchange two pair reps, or reorder two self-sym reps
                       along the spine (Property 1 preserved by construction).
    _op_move_inner  — detach/reinsert a pair rep; self-sym reps never move
                       via this operator (spine reordering is a swap, not a
                       move — see plan §4b/§5.3) and reinsertion never
                       splices a node between two spine members.
    _op_change_rep  — swap which side of a pair/self-sym has the tree node.
  Symmetry-type conversion (paper Op5) is intentionally not implemented:
  every axis in this project is vertical by construction.

perturb(temperature) expects temperature in [0, 1] (normalised fraction,
  1 = hot start, 0 = cold end).  The SA optimiser is responsible for
  mapping its internal schedule to this range before calling perturb().
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable

from topology_base import TopologyBase, SAMixin, GAMixin
from spacing import compute_block_spacing, is_wpe_pair, SpacingResult


# =============================================================================
# CONSTANTS
# =============================================================================
_HIERARCHY_MOVE_WEIGHT = 0.2   # Lin 2009 §V-A: moving/swapping a whole island
                                # is "a big jump" — down-weight its selection.


# =============================================================================
# INTERNAL DATA STRUCTURES
# =============================================================================

class _Node:
    """One node in a B*-tree (outer or inner). Holds block assignment and tree links.

    is_hierarchy=True marks the (at most one) outer node that wraps the
    shared-axis symmetry island; its block_id is the sentinel
    BStarTopology._ISLAND_ID and does not index into self._blocks.
    """
    __slots__ = ("block_id", "variant_idx", "left", "right", "parent", "is_hierarchy")

    def __init__(self, block_id: str, variant_idx: int) -> None:
        self.block_id:    str          = block_id
        self.variant_idx: int          = variant_idx
        self.left:   "_Node | None"   = None   # x-child (placed to the right)
        self.right:  "_Node | None"   = None   # y-child (placed above)
        self.parent: "_Node | None"   = None
        self.is_hierarchy: bool        = False


# =============================================================================
# CONTOUR HELPERS
# =============================================================================

def _contour_query(
    contour: list[tuple[float, float, float, float, str]],
    x_l: float,
    x_r: float,
    dts_new: frozenset[str],
    ch: float,
) -> float:
    """
    2-D contour query — return the y-floor for a new node (candidate device
    types dts_new — a single-element set for a regular block, or the full
    set of device types present in the symmetry island when the incoming
    node is the hierarchy node) whose x-range is [x_l, x_r] and height ch,
    satisfying *all* pairwise DRC spacing against every existing segment.

    Each contour segment is a 5-tuple (x_l, x_r, y_bot, y_top, dt). For
    dts_new with more than one member (island case), the effective height is
    the max over all candidate device types — the safe (never-too-tight)
    choice, since the exact island member nearest a given outer segment can
    vary by SA perturbation and isn't worth tracking precisely (see plan
    §5.2). For a single-block query this degenerates to the original
    single-device-type computation.

    Three cases per (segment, dt_new) pair:

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
    for (cx_l, cx_r, cy_bot, cy_top, cy_dt) in contour:
        blk_seg = {"device_type": cy_dt}
        x_gap   = max(0.0, max(x_l - cx_r, cx_l - x_r))

        for dt_new in dts_new:
            blk_new = {"device_type": dt_new}
            sp      = compute_block_spacing(blk_seg, blk_new)

            if x_gap < 1e-9:
                effective = cy_top + sp.y_spacing

            elif is_wpe_pair(blk_seg, blk_new):
                req_corner = max(sp.x_spacing, sp.y_spacing)
                if x_gap < req_corner:
                    effective = (
                        cy_top
                        + math.sqrt(max(0.0, req_corner ** 2 - x_gap ** 2))
                        + 1e-6
                    )
                else:
                    effective = 0.0

            elif x_gap < sp.x_spacing:
                y_overlap = min(max_h + ch, cy_top) - max(max_h, cy_bot)
                if y_overlap > 1e-9:
                    effective = cy_top + 1e-6
                else:
                    effective = 0.0

            else:
                effective = 0.0

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


def _spacing_multi(dts_a: frozenset[str], dts_b: frozenset[str]) -> SpacingResult:
    """Componentwise-max SpacingResult over every (dt_a, dt_b) pair — the
    safe generalisation of compute_block_spacing() used whenever one side
    is the symmetry island (multiple device types) rather than one block."""
    x = 0.0
    y = 0.0
    for dt_a in dts_a:
        for dt_b in dts_b:
            sp = compute_block_spacing({"device_type": dt_a}, {"device_type": dt_b})
            x = max(x, sp.x_spacing)
            y = max(y, sp.y_spacing)
    return SpacingResult(x_spacing=x, y_spacing=y)


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

    _ISLAND_ID = "__ISLAND__"   # sentinel outer block_id for the hierarchy node

    def __init__(self, blocks: dict, nets: list, sym_groups: list | None = None) -> None:
        self._blocks: dict = blocks
        self._nets:   list = nets
        self._root:  _Node | None = None
        self._nodes: list[_Node]  = []          # outer tree: free blocks + hierarchy node
        self._inner_root: _Node | None = None
        self._inner_nodes: list[_Node] = []     # inner ASF-tree: representative nodes only
        self._sym_groups: list    = sym_groups or []
        # Symmetry lookups — populated by _build_sym_lookups()
        #   _partner[bid]     : partner block_id, or None for non-symmetric blocks
        #   _is_rep[bid]      : True → block currently has the inner tree node
        #   _is_self_sym[bid] : True → self-symmetric (block maps to itself across the axis)
        self._partner:     dict[str, str | None] = {}
        self._is_rep:      dict[str, bool]        = {}
        self._is_self_sym: dict[str, bool]        = {}
        self._build_sym_lookups()

    # ------------------------------------------------------------------
    # Symmetry helpers
    # ------------------------------------------------------------------

    def _build_sym_lookups(self) -> None:
        """Populate _partner / _is_rep / _is_self_sym from self._sym_groups.

        Convention: for each pair (a, b), the *first* listed index (a) is the
        representative that gets a tree node; b is the mirror and has no node.
        _op_change_rep() can swap this assignment at SA-perturbation time.

        All entries across every group in self._sym_groups are merged into
        one flat set of lookups — this project's aggressive mode always
        means "share one common axis," never several independently-aligned
        axes (confirmed: symmetry_detector.py's Union-Find already merges
        everything on one axis into a single compound), so one shared
        representative tree per run is sufficient (see plan §3).
        """
        for bid in self._blocks:
            self._partner.setdefault(bid, None)
            self._is_rep.setdefault(bid, True)
            self._is_self_sym.setdefault(bid, False)
        for group in self._sym_groups:
            for pair in group.get("pairs", []):
                id_a = str(pair[0])
                id_b = str(pair[1])
                if id_a in self._blocks and id_b in self._blocks:
                    self._partner[id_a] = id_b
                    self._partner[id_b] = id_a
                    self._is_rep[id_a]  = True   # default representative
                    self._is_rep[id_b]  = False  # mirror — no tree node
            for ss_idx in group.get("self_symmetric", []):
                bid = str(ss_idx)
                if bid in self._blocks:
                    self._partner[bid]     = bid   # maps to itself
                    self._is_self_sym[bid] = True
                    self._is_rep[bid]      = True  # self-sym IS in the tree

    def _block_dims(self, bid: str, variant_idx: int) -> tuple[float, float, str]:
        block   = self._blocks[bid]
        variant = block["variants"][variant_idx]
        bb      = variant["main_bbox"]
        return bb["x_max"], bb["y_max"], block.get("device_type", "")

    def _rep_variant_idx(self, bid: str, rep_node_map: dict[str, _Node]) -> int:
        """Variant index to use for block `bid` inside the island: its own
        node's variant if it has one (a rep), else its rep partner's."""
        node = rep_node_map.get(bid)
        if node is not None:
            return node.variant_idx
        rep_bid = self._partner.get(bid)
        node = rep_node_map.get(rep_bid) if rep_bid else None
        return node.variant_idx if node is not None else 0

    def _pack_island(
        self,
    ) -> tuple[dict[str, tuple[float, float]], list[tuple[float, float, float, float, str]], float, float, frozenset[str]]:
        """
        Pack the shared-axis symmetry island (Lin 2009 §III, ASF-B*-tree):
        DFS+contour over representative nodes only, then derive mirror and
        self-symmetric positions via the mirror formula. Returns:
          - local (x, y) position of every island member (reps + mirrors),
          - that member's own bbox as an (x_l, x_r, y_bot, y_top, dt) segment
            — collectively these segments ARE the island's true silhouette,
            reused directly as extra outer-contour entries by decode(),
          - island width/height,
          - the set of device types present in the island.
        All positions/segments are in the island's own local space, shifted
        so its own bottom-left corner is (0, 0) — consistent with how the
        outer DFS treats every node's (cx, cy) as its own bottom-left corner.
        """
        if self._inner_root is None:
            return {}, [], 0.0, 0.0, frozenset()

        rep_node_map = {n.block_id: n for n in self._inner_nodes}

        # 1. Standard B*-tree DFS+contour over representative nodes.
        rep_pos:  dict[str, tuple[float, float]] = {}
        node_geom: dict[str, tuple[float, float, float, float]] = {}
        contour:  list[tuple[float, float, float, float, str]] = []

        root = self._inner_root
        rw, rh, rdt = self._block_dims(root.block_id, root.variant_idx)
        rep_pos[root.block_id]  = (0.0, 0.0)
        node_geom[root.block_id] = (0.0, 0.0, rw, rh)
        _contour_update(contour, 0.0, rw, 0.0, rh, rdt)

        stack: list[_Node] = []
        if root.right: stack.append(root.right)
        if root.left:  stack.append(root.left)
        while stack:
            node   = stack.pop()
            parent = node.parent
            px, py, pw, ph = node_geom[parent.block_id]
            _, _, p_dt = self._block_dims(parent.block_id, parent.variant_idx)
            cw, ch, c_dt = self._block_dims(node.block_id, node.variant_idx)

            if node is parent.left:
                sp = compute_block_spacing({"device_type": p_dt}, {"device_type": c_dt})
                cx = px + pw + sp.x_spacing
                cy = _contour_query(contour, cx, cx + cw, frozenset({c_dt}), ch)
                cy = max(cy, py)
            else:
                cx = px
                cy = _contour_query(contour, cx, cx + cw, frozenset({c_dt}), ch)

            rep_pos[node.block_id]  = (cx, cy)
            node_geom[node.block_id] = (cx, cy, cw, ch)
            _contour_update(contour, cx, cx + cw, cy, cy + ch, c_dt)

            if node.right: stack.append(node.right)
            if node.left:  stack.append(node.left)

        # 2. Axis geometry (mirrors bstar_topology.md's Bug-1/Bug-2 fixes,
        #    now scoped to the single merged island instead of per-group).
        axis_x = 0.0
        gap_x  = 0.0
        for bid, (x, _y) in rep_pos.items():
            w, _h, _dt = self._block_dims(bid, self._rep_variant_idx(bid, rep_node_map))
            axis_x = max(axis_x, x + w)
            if not self._is_self_sym.get(bid, False):
                sp = compute_block_spacing(self._blocks[bid], self._blocks[bid])
                gap_x = max(gap_x, sp.x_spacing)
        axis_mid = axis_x + gap_x / 2.0

        # 3. Final local positions for every island member.
        all_pos: dict[str, tuple[float, float]] = {}
        for bid, (x, y) in rep_pos.items():
            w, _h, _dt = self._block_dims(bid, self._rep_variant_idx(bid, rep_node_map))
            if self._is_self_sym.get(bid, False):
                all_pos[bid] = (axis_mid - w / 2.0, y)
                continue
            all_pos[bid] = (x + axis_x + gap_x, y)
            partner = self._partner.get(bid)
            if partner and partner != bid:
                all_pos[partner] = (axis_x - (x + w), y)

        # 4. Normalize to the island's own bottom-left corner and build the
        #    per-member segment list (root is always at local y=0, so
        #    min_y is trivially 0; min_x may not be).
        min_x = min(x for x, _y in all_pos.values())
        segments: list[tuple[float, float, float, float, str]] = []
        dts: set[str] = set()
        max_x = 0.0
        max_y = 0.0
        norm_pos: dict[str, tuple[float, float]] = {}
        for bid, (x, y) in all_pos.items():
            nx, ny = x - min_x, y
            w, h, dt = self._block_dims(bid, self._rep_variant_idx(bid, rep_node_map))
            norm_pos[bid] = (nx, ny)
            segments.append((nx, nx + w, ny, ny + h, dt))
            dts.add(dt)
            max_x = max(max_x, nx + w)
            max_y = max(max_y, ny + h)

        return norm_pos, segments, max_x, max_y, frozenset(dts)

    # ------------------------------------------------------------------
    # TopologyBase
    # ------------------------------------------------------------------

    def _random_binary_tree(self, nodes: list[_Node], mode: str) -> _Node:
        """Plain Chang-2000 random B*-tree build over `nodes` (nodes[0] becomes root)."""
        if mode == "random":
            random.shuffle(nodes)
        root = nodes[0]
        root.parent = None
        for i, node in enumerate(nodes[1:], start=1):
            candidates = [n for n in nodes[:i] if n.left is None or n.right is None]
            parent = random.choice(candidates) if mode == "random" else candidates[0]
            free_left, free_right = parent.left is None, parent.right is None
            if free_left and free_right:
                go_left = random.random() < 0.5 if mode == "random" else True
            else:
                go_left = free_left
            if go_left:
                parent.left = node
            else:
                parent.right = node
            node.parent = parent
        return root

    def _seed_inner(self, rep_ids: list[str], mode: str) -> None:
        """Build the ASF-B*-tree over representative nodes (Property 1:
        self-symmetric reps chained onto the rightmost branch first)."""
        if not rep_ids:
            self._inner_root  = None
            self._inner_nodes = []
            return

        ss_ids  = [bid for bid in rep_ids if self._is_self_sym.get(bid)]
        reg_ids = [bid for bid in rep_ids if not self._is_self_sym.get(bid)]
        if mode == "random":
            random.shuffle(reg_ids)
        ordered_ids = ss_ids + reg_ids

        nodes = [_Node(bid, self._default_variant_idx(bid)) for bid in ordered_ids]
        root = nodes[0]
        root.parent = None
        rightmost_tail = root

        for i, node in enumerate(nodes[1:], start=1):
            if self._is_self_sym.get(node.block_id, False):
                while rightmost_tail.right is not None:
                    rightmost_tail = rightmost_tail.right
                rightmost_tail.right = node
                node.parent = rightmost_tail
                rightmost_tail = node
            else:
                candidates = [n for n in nodes[:i] if n.left is None or n.right is None]
                parent = random.choice(candidates) if mode == "random" else candidates[0]
                free_left, free_right = parent.left is None, parent.right is None
                if free_left and free_right:
                    go_left = random.random() < 0.5 if mode == "random" else True
                else:
                    go_left = free_left
                if go_left:
                    parent.left = node
                else:
                    parent.right = node
                node.parent = parent

        self._inner_root  = root
        self._inner_nodes = nodes

    def seed(self, blocks: dict, mode: str = "random") -> None:
        """Build a valid outer tree (free blocks + at most one hierarchy
        node) and, if any symmetry pairs/self-symmetric blocks exist, an
        inner ASF-B*-tree of their representatives."""
        self._blocks = blocks
        self._build_sym_lookups()   # rebuild after blocks update

        valid_ids = [bid for bid, b in blocks.items() if "error" not in b]
        sym_ids   = {bid for bid in valid_ids if self._partner.get(bid) is not None}
        rep_ids   = [bid for bid in valid_ids if bid in sym_ids and self._is_rep.get(bid, True)]
        free_ids  = [bid for bid in valid_ids if bid not in sym_ids]

        self._seed_inner(rep_ids, mode)

        outer_nodes: list[_Node] = []
        if rep_ids:
            island_node = _Node(self._ISLAND_ID, 0)
            island_node.is_hierarchy = True
            outer_nodes.append(island_node)
        outer_nodes += [_Node(bid, self._default_variant_idx(bid)) for bid in free_ids]

        if not outer_nodes:
            self._root  = None
            self._nodes = []
            return

        self._nodes = outer_nodes
        self._root  = self._random_binary_tree(outer_nodes, mode)

    def decode(self) -> dict[str, tuple[float, float]]:
        """
        DFS pre-order traversal over the outer tree → block (x, y) positions.
        The hierarchy node (if any) is packed once via _pack_island() before
        the traversal starts; wherever the traversal reaches it, every
        island member's absolute position is stamped and each member's own
        bbox is pushed into the shared contour, so later nodes see the
        island's true rectilinear top silhouette rather than a padded
        bounding box (Lin 2009's contour-node mechanism, folded directly
        into the existing typed contour — see module docstring).
        """
        if self._root is None:
            return {}

        island_pos, island_segments, island_w, island_h, island_dts = self._pack_island()

        positions: dict[str, tuple[float, float]] = {}
        contour: list[tuple[float, float, float, float, str]] = []
        node_geom: dict[str, tuple[float, float, float, float]] = {}

        def _dims(node: _Node) -> tuple[float, float, frozenset[str]]:
            if node.is_hierarchy:
                return island_w, island_h, island_dts
            w, h, dt = self._block_dims(node.block_id, node.variant_idx)
            return w, h, frozenset({dt})

        def _place(node: _Node, cx: float, cy: float, w: float, h: float) -> None:
            if node.is_hierarchy:
                for bid, (lx, ly) in island_pos.items():
                    positions[bid] = (cx + lx, cy + ly)
                for (sx_l, sx_r, sy_b, sy_t, sdt) in island_segments:
                    _contour_update(contour, cx + sx_l, cx + sx_r, cy + sy_b, cy + sy_t, sdt)
            else:
                positions[node.block_id] = (cx, cy)
                _, _, dt = self._block_dims(node.block_id, node.variant_idx)
                _contour_update(contour, cx, cx + w, cy, cy + h, dt)

        def _key(node: _Node) -> str:
            return self._ISLAND_ID if node.is_hierarchy else node.block_id

        rw, rh, _r_dts = _dims(self._root)
        _place(self._root, 0.0, 0.0, rw, rh)
        node_geom[_key(self._root)] = (0.0, 0.0, rw, rh)

        dfs_stack: list[_Node] = []
        if self._root.right: dfs_stack.append(self._root.right)
        if self._root.left:  dfs_stack.append(self._root.left)

        while dfs_stack:
            node   = dfs_stack.pop()
            parent = node.parent
            px, py, pw, ph = node_geom[_key(parent)]
            _, _, p_dts = _dims(parent)
            cw, ch, c_dts = _dims(node)

            if node is parent.left:
                sp = _spacing_multi(p_dts, c_dts)
                cx = px + pw + sp.x_spacing
                cy = _contour_query(contour, cx, cx + cw, c_dts, ch)
                cy = max(cy, py)   # x-child must not fall below parent's baseline
            else:
                cx = px
                cy = _contour_query(contour, cx, cx + cw, c_dts, ch)

            _place(node, cx, cy, cw, ch)
            node_geom[_key(node)] = (cx, cy, cw, ch)

            if node.right: dfs_stack.append(node.right)
            if node.left:  dfs_stack.append(node.left)

        return positions

    def copy_state(self) -> Any:
        """Return a deep-copyable representation of both tree structures."""
        outer = self._serialize_tree(self._nodes, self._root)
        inner = self._serialize_tree(self._inner_nodes, self._inner_root)
        return (outer, inner, dict(self._is_rep))

    @staticmethod
    def _serialize_tree(nodes: list[_Node], root: _Node | None) -> tuple[list[tuple], int]:
        if not nodes:
            return ([], -1)
        idx = {id(n): i for i, n in enumerate(nodes)}
        rows = []
        for n in nodes:
            l = idx[id(n.left)]   if n.left   else -1
            r = idx[id(n.right)]  if n.right  else -1
            p = idx[id(n.parent)] if n.parent else -1
            rows.append((n.block_id, n.variant_idx, l, r, p, n.is_hierarchy))
        return (rows, idx[id(root)])

    @staticmethod
    def _deserialize_tree(saved: tuple[list[tuple], int]) -> tuple[list[_Node], _Node | None]:
        rows, root_idx = saved
        if not rows:
            return [], None
        nodes = []
        for (bid, vidx, _l, _r, _p, is_h) in rows:
            n = _Node(bid, vidx)
            n.is_hierarchy = is_h
            nodes.append(n)
        for i, (_bid, _vidx, l, r, p, _is_h) in enumerate(rows):
            nodes[i].left   = nodes[l] if l >= 0 else None
            nodes[i].right  = nodes[r] if r >= 0 else None
            nodes[i].parent = nodes[p] if p >= 0 else None
        return nodes, nodes[root_idx]

    def restore_state(self, saved: Any) -> None:
        outer, inner, is_rep_snap = saved
        self._nodes, self._root             = self._deserialize_tree(outer)
        self._inner_nodes, self._inner_root = self._deserialize_tree(inner)
        self._is_rep = dict(is_rep_snap)

    def capabilities(self) -> set[str]:
        return {"SA", "GA"}

    # ------------------------------------------------------------------
    # SAMixin
    # ------------------------------------------------------------------

    def perturb(self, temperature: float) -> Callable[[], None]:
        """
        Choose and apply one SA operator and return its undo closure.

        temperature — normalised fraction in [0, 1].  1 = hot (start of run),
          0 = cold (end of run).  Operator weights shift from structural
          (swap, move) at high T to fine-grained (variant) at low T, same as
          before; the inner (island) pool only exists when a hierarchy node
          is present, and change-rep only when the island has real pairs.
        """
        if not self._nodes:
            return lambda: None

        t = min(1.0, max(0.0, temperature))
        has_island = self._inner_root is not None
        has_pairs  = any(
            self._partner.get(bid) is not None and not self._is_self_sym.get(bid, False)
            for bid in self._partner
        )

        ops:     list[Callable[[], Callable[[], None]]] = [self._op_variant, self._op_swap_outer, self._op_move_outer]
        weights: list[float] = [
            0.15 + 0.05 * (1 - t),
            0.30 - 0.07 * (1 - t),
            0.30 - 0.07 * (1 - t),
        ]
        if has_island:
            ops     += [self._op_swap_inner, self._op_move_inner]
            weights += [0.10 + 0.05 * (1 - t), 0.10 + 0.05 * (1 - t)]
        if has_pairs:
            ops.append(self._op_change_rep)
            weights.append(0.05)

        r = random.random() * sum(weights)
        cumulative = 0.0
        chosen = ops[-1]
        for op, w in zip(ops, weights):
            cumulative += w
            if r <= cumulative:
                chosen = op
                break
        return chosen()

    def _op_variant(self) -> Callable[[], None]:
        """Change the active variant of a random block — free or representative.
        Rotation is represented as a separate variant entry — no dedicated
        rotate operator is needed (Chang 2000 Op1)."""
        candidates = [n for n in self._nodes if not n.is_hierarchy] + self._inner_nodes
        if not candidates:
            return lambda: None
        node = random.choice(candidates)
        block    = self._blocks.get(node.block_id, {})
        variants = block.get("variants", [])
        if len(variants) <= 1:
            return lambda: None
        old_vidx = node.variant_idx
        new_vidx = random.choice([i for i in range(len(variants)) if i != old_vidx])
        node.variant_idx = new_vidx
        def undo() -> None:
            node.variant_idx = old_vidx
        return undo

    @staticmethod
    def _swap_content(a: _Node, b: _Node, blocks: dict) -> Callable[[], None]:
        """Exchange (block_id, variant_idx) between two node objects,
        clamping variant_idx to the destination's variant count."""
        old_a_bid, old_a_vidx = a.block_id, a.variant_idx
        old_b_bid, old_b_vidx = b.block_id, b.variant_idx
        n_vars_b = len(blocks.get(old_b_bid, {}).get("variants", [1]))
        n_vars_a = len(blocks.get(old_a_bid, {}).get("variants", [1]))
        a.block_id, a.variant_idx = old_b_bid, min(old_b_vidx, max(0, n_vars_b - 1))
        b.block_id, b.variant_idx = old_a_bid, min(old_a_vidx, max(0, n_vars_a - 1))
        def undo() -> None:
            a.block_id, a.variant_idx = old_a_bid, old_a_vidx
            b.block_id, b.variant_idx = old_b_bid, old_b_vidx
        return undo

    def _op_swap_outer(self) -> Callable[[], None]:
        """Exchange block assignment of two free (non-hierarchy) outer nodes."""
        swappable = [n for n in self._nodes if not n.is_hierarchy]
        if len(swappable) < 2:
            return lambda: None
        a, b = random.sample(swappable, 2)
        return self._swap_content(a, b, self._blocks)

    def _op_swap_inner(self) -> Callable[[], None]:
        """Exchange two pair representatives freely (Lin 2009 §V-B Case 1),
        or reorder two self-symmetric representatives along the spine
        (Case 2) — never mix the two pools, which would move a self-sym
        node off the rightmost branch or a pair rep onto it."""
        ss  = [n for n in self._inner_nodes if self._is_self_sym.get(n.block_id, False)]
        reg = [n for n in self._inner_nodes if not self._is_self_sym.get(n.block_id, False)]
        pools = [p for p in (ss, reg) if len(p) >= 2]
        if not pools:
            return lambda: None
        pool = random.choice(pools)
        a, b = random.sample(pool, 2)
        return self._swap_content(a, b, self._blocks)

    def _move_node(
        self,
        n: _Node,
        pool: list[_Node],
        forbid_right: Callable[[_Node], bool] | None = None,
    ) -> Callable[[], None]:
        """
        Detach node `n` and re-insert it via push-down at a random target in
        `pool` (paper Op2/Op3-move). Shared by the outer and inner trees;
        `forbid_right` lets the inner tree veto inserting `n` as a target's
        right child when that would splice a non-spine node between two
        self-symmetric representatives (breaking Property 1) — see the
        module docstring and plan §5.3.

        Detach cases:
          A. Leaf             → clean removal.
          B. One child C      → C takes n's slot in parent.
          C. Two children L,R → promote L to n's slot; re-insert R via push-down
                                on a node outside R's subtree (prevents cycles).

        All mutations are preceded by a save; undo replays in reverse order.
        Because the first (chronological) save for any node captures the true
        original state, reversed replay always restores correctly even if a
        node is saved more than once.
        """
        forbid_right = forbid_right or (lambda _target: False)

        n_parent  = n.parent
        n_is_left = (n_parent.left is n)
        n_left    = n.left
        n_right   = n.right

        saved: list[tuple] = []

        def _save(node: _Node) -> None:
            saved.append((node, node.left, node.right, node.parent))

        def _push_down(target: _Node, node: _Node) -> None:
            """Insert node as a child of target, pushing target's existing
            child down as node's child. node must be a leaf before calling."""
            go_left = random.random() < 0.5
            if forbid_right(target):
                go_left = True
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

        _save(n)
        _save(n_parent)

        if n_left is None and n_right is None:
            if n_is_left:
                n_parent.left  = None
            else:
                n_parent.right = None

        elif n_right is None:
            _save(n_left)
            if n_is_left:
                n_parent.left  = n_left
            else:
                n_parent.right = n_left
            n_left.parent = n_parent

        elif n_left is None:
            _save(n_right)
            if n_is_left:
                n_parent.left  = n_right
            else:
                n_parent.right = n_right
            n_right.parent = n_parent

        else:
            _save(n_left)
            if n_is_left:
                n_parent.left  = n_left
            else:
                n_parent.right = n_left
            n_left.parent = n_parent

            r_ids   = {id(nd) for nd in _bfs_subtree(n_right)}
            valid_r = [
                nd for nd in pool
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

        n.left   = None
        n.right  = None
        n.parent = None

        valid = [nd for nd in pool if nd is not n]
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

    def _op_move_outer(self) -> Callable[[], None]:
        """Move a random outer node (free block, or the whole island as one
        atomic unit — down-weighted per Lin 2009 §V-A)."""
        non_root = [
            nd for nd in self._nodes
            if nd.parent is not None and (nd.parent.left is nd or nd.parent.right is nd)
        ]
        if not non_root:
            return lambda: None
        weights = [_HIERARCHY_MOVE_WEIGHT if nd.is_hierarchy else 1.0 for nd in non_root]
        n = random.choices(non_root, weights=weights, k=1)[0]
        return self._move_node(n, self._nodes)

    def _op_move_inner(self) -> Callable[[], None]:
        """Move a random pair-representative node within the island.
        Self-symmetric reps are excluded (their only legal reordering is the
        spine-restricted swap, _op_swap_inner — see module docstring)."""
        non_root = [
            nd for nd in self._inner_nodes
            if nd.parent is not None and (nd.parent.left is nd or nd.parent.right is nd)
            and not self._is_self_sym.get(nd.block_id, False)
        ]
        if not non_root:
            return lambda: None
        n = random.choice(non_root)

        def forbid_right(target: _Node) -> bool:
            # Never splice a node between two self-symmetric spine members.
            return target.right is not None and self._is_self_sym.get(target.right.block_id, False)

        return self._move_node(n, self._inner_nodes, forbid_right)

    def _op_change_rep(self) -> Callable[[], None]:
        """Op4 from the ASF-B*-tree paper: swap which side of a symmetric
        pair is the representative (the block stored in the inner tree
        node). Structure is unchanged; only the block_id in one randomly
        chosen pair-node flips from one side of the pair to the other.
        Excluded for self-symmetric nodes (no "other side" to swap to)."""
        pair_nodes = [
            n for n in self._inner_nodes
            if self._partner.get(n.block_id) is not None
            and not self._is_self_sym.get(n.block_id, False)
        ]
        if not pair_nodes:
            return lambda: None

        node    = random.choice(pair_nodes)
        old_bid = node.block_id
        new_bid = self._partner[old_bid]

        node.block_id          = new_bid
        self._is_rep[old_bid]  = False
        self._is_rep[new_bid]  = True

        def undo() -> None:
            node.block_id          = old_bid
            self._is_rep[old_bid]  = True
            self._is_rep[new_bid]  = False
        return undo

    # ------------------------------------------------------------------
    # GAMixin
    # ------------------------------------------------------------------
    # BStarTopology's GA path currently has no caller in this project (no
    # GeneticAlgorithmOptimizer exists) — kept minimal and correct rather
    # than elaborated, per YAGNI: crossover reuses the same DFS-encode +
    # OX-crossover + reconstruct machinery independently for the outer and
    # inner trees, no new algorithm.

    def mutate(self) -> Callable[[], None]:
        return self.perturb(temperature=0.5)

    def crossover(self, other: "BStarTopology") -> "BStarTopology":
        outer_perm_a, outer_dirs_a = self._encode_tree(self._root)
        outer_perm_b, outer_dirs_b = other._encode_tree(other._root)
        inner_perm_a, inner_dirs_a = self._encode_tree(self._inner_root)
        inner_perm_b, inner_dirs_b = other._encode_tree(other._inner_root)

        child = BStarTopology(self._blocks, self._nets, self._sym_groups)
        child._is_rep = dict(self._is_rep)

        if outer_perm_a:
            offspring_perm = _ox_crossover(outer_perm_a, outer_perm_b)
            cut = random.randint(1, max(1, len(outer_dirs_a) - 1))
            offspring_dirs = outer_dirs_a[:cut] + outer_dirs_b[cut:]
            child._nodes = [self._make_outer_node(bid) for bid in offspring_perm]
            child._root  = child._nodes[0]
            child._root.parent = None
            self._reconstruct_from_dirs(child._nodes, offspring_dirs)
        else:
            child._nodes, child._root = [], None

        if inner_perm_a:
            offspring_perm = _ox_crossover(inner_perm_a, inner_perm_b)
            cut = random.randint(1, max(1, len(inner_dirs_a) - 1))
            offspring_dirs = inner_dirs_a[:cut] + inner_dirs_b[cut:]
            child._inner_nodes = [_Node(bid, self._default_variant_idx(bid)) for bid in offspring_perm]
            child._inner_root  = child._inner_nodes[0]
            child._inner_root.parent = None
            self._reconstruct_from_dirs(child._inner_nodes, offspring_dirs)
        else:
            child._inner_nodes, child._inner_root = [], None

        return child

    def random_init(self) -> None:
        self.seed(self._blocks, mode="random")

    def _make_outer_node(self, bid: str) -> _Node:
        if bid == self._ISLAND_ID:
            n = _Node(bid, 0)
            n.is_hierarchy = True
            return n
        return _Node(bid, self._default_variant_idx(bid))

    # ------------------------------------------------------------------
    # Encoding helpers for GA crossover
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_tree(root: _Node | None) -> tuple[list[str], list[int]]:
        """DFS pre-order → (block_id permutation, x/y direction bits)."""
        if root is None:
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

        _dfs(root)
        return perm, dirs

    @staticmethod
    def _reconstruct_from_dirs(nodes: list[_Node], dirs: list[int]) -> None:
        """
        Attach nodes[1:] as children in order, using dirs as preferred slot.
        Applies four-level slot-conflict fallback.
        """
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
        result: dict[str, int] = {}
        for node in self._inner_nodes:
            result[node.block_id] = node.variant_idx
            partner = self._partner.get(node.block_id)
            if partner and partner != node.block_id and partner not in result:
                result[partner] = node.variant_idx
        for node in self._nodes:
            if not node.is_hierarchy:
                result[node.block_id] = node.variant_idx
        return result

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
