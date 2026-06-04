"""
Sequence Pair topology — supports both SA and GA optimizers.

Internal state: two permutations (r_plus, r_minus).
decode() builds H-DAG and V-DAG from permutation constraints, then runs
DAG longest-path to get block coordinates.

When sym_groups are provided the topology enforces symmetric-feasibility
(Balasa & Lampaert 2000, IEEE TCAD 19(7)) throughout:
  - seed() inserts each group's nested-brackets block at a random position so
    pairs are not frozen at the front of both sequences.
  - M1/M2 are group-aware: picking a symmetric cell relocates the ENTIRE group
    as an indivisible unit in one sequence, preserving condition S by construction.
  - decode() applies the two-pass x-sweep and forces y-equality on symmetric pairs.
  - capabilities() returns {"SA"} only (PMX crossover breaks condition S).
"""
from __future__ import annotations

import random
from collections import defaultdict, deque
from typing import Any, Callable

from topology_base import TopologyBase, SAMixin, GAMixin
from spacing import compute_block_spacing, is_wpe_pair

_WEIGHTS_SYM   = [0.40, 0.40, 0.20]   # M1 M2 M3
_WEIGHTS_NOSYM = [0.40, 0.40, 0.20]   # M1 M2 M3 — kept separate for future tuning


class SequencePairTopology(TopologyBase, SAMixin, GAMixin):

    def __init__(
        self,
        blocks: dict,
        nets: list,
        sym_groups: list | None = None,
    ) -> None:
        self._blocks: dict        = blocks
        self._nets:   list        = nets
        self._r_plus:  list[str]  = []
        self._r_minus: list[str]  = []
        self._variant: dict[str, int] = {}

        self._sym_groups: list              = sym_groups or []
        self._sym_partner: dict[str, str]   = {}   # bid → partner (self→self for self-sym)
        self._sym_group_idx: dict[str, int] = {}   # bid → group index  (-1 = asymmetric)
        self._enforce_matching: list[bool]  = []   # per-group variant-match flag
        self._build_sym_lookups()

    # ------------------------------------------------------------------
    # Symmetry lookup tables (built once, never mutated)
    # ------------------------------------------------------------------

    def _build_sym_lookups(self) -> None:
        for g_idx, group in enumerate(self._sym_groups):
            for pair in group.get("pairs", []):
                # Accept new format [[a, b]] only; skip old {"block_a":…} dicts
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                a_id, b_id = str(pair[0]), str(pair[1])
                self._sym_partner[a_id]   = b_id
                self._sym_partner[b_id]   = a_id
                self._sym_group_idx[a_id] = g_idx
                self._sym_group_idx[b_id] = g_idx
            for s_idx in group.get("self_symmetric", []):
                s_id = str(s_idx)
                self._sym_partner[s_id]   = s_id   # self-referential
                self._sym_group_idx[s_id] = g_idx
            self._enforce_matching.append(group.get("enforce_matching_variants", True))

    # ------------------------------------------------------------------
    # TopologyBase
    # ------------------------------------------------------------------

    def seed(self, blocks: dict, mode: str = "random") -> None:
        self._blocks = blocks
        ids = [bid for bid, b in blocks.items() if "error" not in b]
        self._variant = {bid: self._default_variant_idx(bid) for bid in ids}

        if not self._sym_groups:
            self._r_plus  = list(ids)
            self._r_minus = list(ids)
            if mode == "random":
                random.shuffle(self._r_plus)
                random.shuffle(self._r_minus)
            return

        # Symmetric-feasible initial SP.
        # Pass 1: collect all symmetric block IDs so asym list is correct.
        id_set   = set(ids)
        assigned: set[str] = set()
        for group in self._sym_groups:
            for pair in group.get("pairs", []):
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    a_id, b_id = str(pair[0]), str(pair[1])
                    if a_id in id_set and b_id in id_set:
                        assigned.add(a_id); assigned.add(b_id)
            for s in group.get("self_symmetric", []):
                s_id = str(s)
                if s_id in id_set:
                    assigned.add(s_id)

        asym  = [bid for bid in ids if bid not in assigned]
        asym2 = list(asym)
        if mode == "random":
            random.shuffle(asym); random.shuffle(asym2)
        alpha: list[str] = list(asym)
        beta:  list[str] = list(asym2)

        # Pass 2: insert each group's nested-brackets block at a random position.
        for group in self._sym_groups:
            a_list: list[str] = []
            b_list: list[str] = []
            c_list: list[str] = []
            for pair in group.get("pairs", []):
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                a_id, b_id = str(pair[0]), str(pair[1])
                if a_id in id_set and b_id in id_set:
                    a_list.append(a_id); b_list.append(b_id)
            for s in group.get("self_symmetric", []):
                s_id = str(s)
                if s_id in id_set:
                    c_list.append(s_id)
            if not a_list and not c_list:
                continue
            blk_a = a_list + c_list + list(reversed(b_list))
            blk_b = a_list + list(reversed(c_list)) + list(reversed(b_list))
            k_a = random.randint(0, len(alpha))
            k_b = random.randint(0, len(beta))
            for bid in reversed(blk_a): alpha.insert(k_a, bid)
            for bid in reversed(blk_b): beta.insert(k_b, bid)

        self._r_plus  = alpha
        self._r_minus = beta

    def decode(self) -> dict[str, tuple[float, float]]:
        """
        Build H-DAG and V-DAG; run DAG longest-path for coordinates.
        With symmetry groups: apply x-sweeps after H-DAG and y-force after V-DAG.
        """
        if not self._r_plus:
            return {}

        bids = self._r_plus
        n    = len(bids)

        pos_plus  = {bid: i for i, bid in enumerate(self._r_plus)}
        pos_minus = {bid: i for i, bid in enumerate(self._r_minus)}

        def _dims(bid: str) -> tuple[float, float, str]:
            block   = self._blocks[bid]
            variant = block["variants"][self._variant[bid]]
            bb      = variant["main_bbox"]
            return bb["x_max"], bb["y_max"], block.get("device_type", "")

        SRC, SNK = n, n + 1
        h_graph: dict[int, list[tuple[int, float]]] = defaultdict(list)
        v_graph: dict[int, list[tuple[int, float]]] = defaultdict(list)

        for i in range(n):
            a = bids[i]
            wa, ha, dta = _dims(a)
            for j in range(i + 1, n):
                b = bids[j]
                _, _, dtb = _dims(b)
                sp = compute_block_spacing({"device_type": dta}, {"device_type": dtb})

                pa_p, pa_m = pos_plus[a],  pos_minus[a]
                pb_p, pb_m = pos_plus[b],  pos_minus[b]

                wpe = is_wpe_pair({"device_type": dta}, {"device_type": dtb})
                req = max(sp.x_spacing, sp.y_spacing) if wpe else None

                if pa_p < pb_p and pa_m < pb_m:
                    eff_x = req if wpe else sp.x_spacing
                    h_graph[pa_p].append((pb_p, wa + eff_x))
                elif pa_p < pb_p and pa_m > pb_m:
                    eff_y = req if wpe else sp.y_spacing
                    v_graph[pa_p].append((pb_p, ha + eff_y))

        for i in range(n):
            h_graph[SRC].append((i, 0.0))
            v_graph[SRC].append((i, 0.0))
            h_graph[i].append((SNK, _dims(bids[i])[0]))
            v_graph[i].append((SNK, _dims(bids[i])[1]))

        x_coords = _dag_longest_path(n + 2, h_graph, SRC)

        if self._sym_groups:
            x_coords = self._sym_sweep_x(x_coords, bids, pos_plus, pos_minus)

        y_coords = _dag_longest_path(n + 2, v_graph, SRC)

        if self._sym_groups:
            self._enforce_y_symmetry(y_coords, bids, v_graph, n)

        return {bids[i]: (x_coords[i], y_coords[i]) for i in range(n)}

    # ------------------------------------------------------------------
    # Symmetry coordinate post-processing
    # ------------------------------------------------------------------

    def _sym_sweep_x(
        self,
        x_coords:  list[float],
        bids:      list[str],
        pos_plus:  dict[str, int],
        pos_minus: dict[str, int],
    ) -> list[float]:
        """
        Balasa-Lampaert two-pass x-sweep (§IV).
        Operates on x_coords[0..n-1]; SRC/SNK entries are preserved unchanged.
        """
        x = list(x_coords)
        n = len(bids)
        idx = {bid: i for i, bid in enumerate(bids)}

        def _w(bid: str) -> float:
            v = self._blocks[bid]["variants"][self._variant[bid]]
            return v["main_bbox"]["x_max"]

        for group in self._sym_groups:
            members: set[str] = set()
            for pair in group.get("pairs", []):
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                a_id, b_id = str(pair[0]), str(pair[1])
                if a_id in idx and b_id in idx:
                    members.add(a_id)
                    members.add(b_id)
            for s in group.get("self_symmetric", []):
                s_id = str(s)
                if s_id in idx:
                    members.add(s_id)
            if not members:
                continue

            sym_axis = 0.0

            # Pass 1 — sweep right (α order)
            for rp_i in range(n):
                j = self._r_plus[rp_i]
                if j not in members:
                    continue
                k = self._sym_partner.get(j)
                if k is None:
                    continue

                if k == j:
                    # Self-symmetric: centre on current axis estimate
                    j_i = idx[j]
                    w_j = _w(j)
                    d   = sym_axis - x[j_i] - w_j / 2
                    if d > 0:
                        x[j_i] += d / 2
                        for m_i in range(n):
                            m = self._r_plus[m_i]
                            if (pos_plus[j] < pos_plus[m]
                                    and pos_minus[j] < pos_minus[m]):
                                x[idx[m]] += d / 2

                elif k in idx and pos_plus[k] < pos_plus[j]:
                    # j is the right partner, k is the left partner already placed
                    j_i     = idx[j]
                    k_i     = idx[k]
                    w_k     = _w(k)
                    x_j_pre = x[j_i]          # capture before push
                    d       = 2 * sym_axis - (x[k_i] + w_k) - x_j_pre
                    if d > 0:
                        x[j_i] += d
                        for m_i in range(n):
                            m = self._r_plus[m_i]
                            if (pos_plus[j] < pos_plus[m]
                                    and pos_minus[j] < pos_minus[m]):
                                x[idx[m]] += d
                    # Axis update always uses PRE-push x_j
                    sym_axis = max(sym_axis, (x[k_i] + w_k + x_j_pre) / 2)

            # Pass 2 — sweep left (reverse α order)
            for rp_i in range(n - 1, -1, -1):
                j = self._r_plus[rp_i]
                if j not in members:
                    continue
                k = self._sym_partner.get(j)
                if k is None or k == j or k not in idx:
                    continue
                if pos_plus[k] > pos_plus[j]:
                    # j is the left partner, k is to its right
                    j_i = idx[j]
                    k_i = idx[k]
                    w_j = _w(j)
                    d   = 2 * sym_axis - (x[j_i] + w_j) - x[k_i]
                    if d < 0:
                        x[j_i] += d
                        for m_i in range(n):
                            m = self._r_plus[m_i]
                            if (pos_plus[m] < pos_plus[j]
                                    and pos_minus[m] < pos_minus[j]):
                                x[idx[m]] += d

        return x

    def _enforce_y_symmetry(
        self,
        y_coords: list[float],
        bids: list[str],
        v_graph: dict,
        n: int,
    ) -> None:
        """Force each symmetric pair to share the same y-coordinate (in-place).

        Takes max(y_A, y_B) so neither block is pulled below its V-DAG lower
        bound, then re-propagates V-constraints forward (r_plus topological
        order) to repair any blocks above that were pushed up.
        """
        idx = {bid: i for i, bid in enumerate(bids)}

        # Step 1: equalise y for each pair using the higher of the two DAG values.
        for group in self._sym_groups:
            for pair in group.get("pairs", []):
                if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                    continue
                a_id, b_id = str(pair[0]), str(pair[1])
                if a_id in idx and b_id in idx:
                    a_i, b_i = idx[a_id], idx[b_id]
                    y_both = max(y_coords[a_i], y_coords[b_i])
                    y_coords[a_i] = y_both
                    y_coords[b_i] = y_both

        # Step 2: forward propagation — re-apply all V-constraints so blocks
        # above a raised pair are pushed up to maintain their spacing.
        # V-graph edges always go from lower to higher r_plus index, so r_plus
        # order is a valid topological order for one-pass propagation.
        for u in range(n):
            for v, w in v_graph.get(u, []):
                if v < n and y_coords[u] + w > y_coords[v]:
                    y_coords[v] = y_coords[u] + w

    def copy_state(self) -> Any:
        return (list(self._r_plus), list(self._r_minus), dict(self._variant))

    def restore_state(self, saved: Any) -> None:
        rp, rm, vt = saved
        self._r_plus  = list(rp)
        self._r_minus = list(rm)
        self._variant = dict(vt)

    def capabilities(self) -> set[str]:
        # PMX crossover does not preserve symmetric-feasibility — disable GA
        return {"SA"} if self._sym_groups else {"SA", "GA"}

    # ------------------------------------------------------------------
    # SAMixin
    # ------------------------------------------------------------------

    def perturb(self, temperature: float) -> Callable[[], None]:
        if not self._r_plus:
            return lambda: None
        w = _WEIGHTS_SYM if self._sym_groups else _WEIGHTS_NOSYM
        return random.choices([self._op_m1, self._op_m2, self._op_m3], weights=w)[0]()

    def _op_m1(self) -> Callable[[], None]:
        """
        For asymmetric blocks: relocate one block in r_plus.
        For symmetric group members (paper §IV): swap two group cells in r_plus
        and simultaneously swap their symmetric partners in r_minus, preserving
        condition (S) (Balasa & Lampaert 2000).
        """
        if len(self._r_plus) < 2:
            return lambda: None
        bid   = random.choice(self._r_plus)
        g_idx = self._sym_group_idx.get(bid, -1)

        if g_idx == -1:
            # Asymmetric cell: relocate in r_plus only.
            old_rp = list(self._r_plus)
            rp = [x for x in self._r_plus if x != bid]
            rp.insert(random.randint(0, len(rp)), bid)
            self._r_plus = rp
            def _undo_asym(old_rp=old_rp) -> None:
                self._r_plus = list(old_rp)
            return _undo_asym

        # Symmetric cell: pick a second group member and swap the pair in r_plus,
        # then swap their sym-partners in r_minus to maintain condition (S).
        group_members = [x for x in self._r_plus
                         if self._sym_group_idx.get(x, -1) == g_idx]
        if len(group_members) < 2:
            return lambda: None
        other = random.choice([x for x in group_members if x != bid])
        old_rp = list(self._r_plus)
        old_rm = list(self._r_minus)

        i, j = self._r_plus.index(bid), self._r_plus.index(other)
        self._r_plus[i], self._r_plus[j] = self._r_plus[j], self._r_plus[i]

        pa = self._sym_partner.get(bid,   bid)
        pb = self._sym_partner.get(other, other)
        if pa != pb and pa in self._r_minus and pb in self._r_minus:
            ki = self._r_minus.index(pa)
            kj = self._r_minus.index(pb)
            self._r_minus[ki], self._r_minus[kj] = self._r_minus[kj], self._r_minus[ki]

        def _undo_sym(old_rp=old_rp, old_rm=old_rm) -> None:
            self._r_plus  = list(old_rp)
            self._r_minus = list(old_rm)
        return _undo_sym

    def _op_m2(self) -> Callable[[], None]:
        """
        For asymmetric blocks: relocate one block in r_minus.
        For symmetric group members: swap two group cells in r_minus and
        simultaneously swap their symmetric partners in r_plus (condition S).
        """
        if len(self._r_minus) < 2:
            return lambda: None
        bid   = random.choice(self._r_minus)
        g_idx = self._sym_group_idx.get(bid, -1)

        if g_idx == -1:
            # Asymmetric cell: relocate in r_minus only.
            old_rm = list(self._r_minus)
            rm = [x for x in self._r_minus if x != bid]
            rm.insert(random.randint(0, len(rm)), bid)
            self._r_minus = rm
            def _undo_asym(old_rm=old_rm) -> None:
                self._r_minus = list(old_rm)
            return _undo_asym

        # Symmetric cell: pick a second group member and swap the pair in r_minus,
        # then swap their sym-partners in r_plus to maintain condition (S).
        group_members = [x for x in self._r_minus
                         if self._sym_group_idx.get(x, -1) == g_idx]
        if len(group_members) < 2:
            return lambda: None
        other = random.choice([x for x in group_members if x != bid])
        old_rp = list(self._r_plus)
        old_rm = list(self._r_minus)

        i, j = self._r_minus.index(bid), self._r_minus.index(other)
        self._r_minus[i], self._r_minus[j] = self._r_minus[j], self._r_minus[i]

        pa = self._sym_partner.get(bid,   bid)
        pb = self._sym_partner.get(other, other)
        if pa != pb and pa in self._r_plus and pb in self._r_plus:
            ki = self._r_plus.index(pa)
            kj = self._r_plus.index(pb)
            self._r_plus[ki], self._r_plus[kj] = self._r_plus[kj], self._r_plus[ki]

        def _undo_sym(old_rp=old_rp, old_rm=old_rm) -> None:
            self._r_plus  = list(old_rp)
            self._r_minus = list(old_rm)
        return _undo_sym

    def _op_m3(self) -> Callable[[], None]:
        """Change the active size variant; match partner's variant for symmetric pairs."""
        if not self._variant:
            return lambda: None
        bid = random.choice(list(self._variant.keys()))
        block    = self._blocks.get(bid, {})
        variants = block.get("variants", [])
        if len(variants) <= 1:
            return lambda: None
        old_vidx = self._variant[bid]
        new_vidx = random.choice([i for i in range(len(variants)) if i != old_vidx])
        self._variant[bid] = new_vidx

        partner = self._sym_partner.get(bid)
        g_idx   = self._sym_group_idx.get(bid, -1)
        enforce = (
            partner and partner != bid
            and g_idx >= 0 and g_idx < len(self._enforce_matching)
            and self._enforce_matching[g_idx]
        )
        if enforce and partner in self._variant:
            old_pvidx  = self._variant[partner]
            p_variants = self._blocks.get(partner, {}).get("variants", [])
            if len(p_variants) > new_vidx:
                self._variant[partner] = new_vidx
                def _undo_m3p(bid=bid, ov=old_vidx, p=partner, opv=old_pvidx) -> None:
                    self._variant[bid] = ov
                    self._variant[p]   = opv
                return _undo_m3p

        def _undo_m3(bid=bid, ov=old_vidx) -> None:
            self._variant[bid] = ov
        return _undo_m3

    # ------------------------------------------------------------------
    # GAMixin
    # ------------------------------------------------------------------

    def mutate(self) -> Callable[[], None]:
        return self.perturb(temperature=0.5)

    def crossover(self, other: "SequencePairTopology") -> "SequencePairTopology":
        """PMX crossover on r_plus and r_minus independently.
        Safe only when no symmetry groups are active (PMX breaks condition S)."""
        child = SequencePairTopology(self._blocks, self._nets,
                                     self._sym_groups or None)
        child._r_plus  = _pmx(self._r_plus,  other._r_plus)
        child._r_minus = _pmx(self._r_minus, other._r_minus)
        child._variant = dict(self._variant)
        return child

    def random_init(self) -> None:
        self.seed(self._blocks, mode="random")

    def get_variant_map(self) -> dict[str, int]:
        return dict(self._variant)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _default_variant_idx(self, block_id: str) -> int:
        block    = self._blocks.get(block_id, {})
        variants = block.get("variants", [])
        for i, v in enumerate(variants):
            if v.get("is_used"):
                return i
        return 0


# =============================================================================
# DAG LONGEST-PATH (topological sort + relaxation)
# =============================================================================

def _dag_longest_path(
    n_nodes: int,
    graph:   dict[int, list[tuple[int, float]]],
    source:  int,
) -> list[float]:
    """
    Returns longest-path distance from source to each node in a DAG.
    graph[u] = [(v, weight), ...]. Uses Kahn's algorithm for topological sort.
    """
    in_deg = [0] * n_nodes
    for u, edges in graph.items():
        for v, _ in edges:
            in_deg[v] += 1

    dist = [-1.0] * n_nodes
    dist[source] = 0.0

    queue = deque([i for i in range(n_nodes) if in_deg[i] == 0])
    while queue:
        u = queue.popleft()
        for v, w in graph.get(u, []):
            if dist[u] >= 0 and dist[u] + w > dist[v]:
                dist[v] = dist[u] + w
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)

    return [max(0.0, d) for d in dist]


# =============================================================================
# PMX CROSSOVER
# =============================================================================

def _pmx(perm_a: list[str], perm_b: list[str]) -> list[str]:
    """
    Partially Mapped Crossover (PMX).
    Guarantees a valid permutation (no duplicates, no missing elements).
    """
    n = len(perm_a)
    if n == 0:
        return []
    if n == 1:
        return list(perm_a)

    i, j = sorted(random.sample(range(n), 2))
    offspring = [None] * n

    for k in range(i, j + 1):
        offspring[k] = perm_a[k]

    mapping: dict[str, str] = {}
    for k in range(i, j + 1):
        mapping[perm_b[k]] = perm_a[k]

    for k in range(n):
        if offspring[k] is not None:
            continue
        val = perm_b[k]
        seen: set[str] = set()
        while val in mapping and val not in seen:
            seen.add(val)
            val = mapping[val]
        offspring[k] = val

    return offspring  # type: ignore[return-value]
