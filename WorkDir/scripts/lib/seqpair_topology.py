"""
Sequence Pair topology — supports both SA and GA optimizers.

Internal state: two permutations (r_plus, r_minus).
decode() builds H-DAG and V-DAG from permutation constraints, then runs
DAG longest-path to get block coordinates.
"""
from __future__ import annotations

import random
from collections import defaultdict, deque
from typing import Any, Callable

from topology_base import TopologyBase, SAMixin, GAMixin
from spacing import compute_block_spacing


class SequencePairTopology(TopologyBase, SAMixin, GAMixin):
    """
    Sequence-pair placement topology.

    Capabilities: SA (perturb/undo) and GA (mutate/crossover/random_init).
    """

    def __init__(self, blocks: dict, nets: list) -> None:
        self._blocks: dict       = blocks
        self._nets:   list       = nets
        self._r_plus:  list[str] = []
        self._r_minus: list[str] = []
        # variant_state: block_id → variant index
        self._variant: dict[str, int] = {}

    # ------------------------------------------------------------------
    # TopologyBase
    # ------------------------------------------------------------------

    def seed(self, blocks: dict, mode: str = "random") -> None:
        self._blocks = blocks
        ids = [bid for bid, b in blocks.items() if "error" not in b]
        self._r_plus  = list(ids)
        self._r_minus = list(ids)
        self._variant = {bid: self._default_variant_idx(bid) for bid in ids}

        if mode == "random":
            random.shuffle(self._r_plus)
            random.shuffle(self._r_minus)
        # mode="ordered": input order preserved in both permutations

    def decode(self) -> dict[str, tuple[float, float]]:
        """
        Build H-DAG and V-DAG from permutation constraints.
        Run DAG longest-path on each to get x and y coordinates.

        H-constraint (A left of B): A before B in both r_plus and r_minus.
        V-constraint (A below B):   A before B in r_plus, B before A in r_minus.
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

        # Build adjacency lists for H-DAG and V-DAG
        # Nodes: 0..n-1 (blocks by index in r_plus), n = source, n+1 = sink
        SRC, SNK = n, n + 1
        h_graph: dict[int, list[tuple[int, float]]] = defaultdict(list)
        v_graph: dict[int, list[tuple[int, float]]] = defaultdict(list)

        for i in range(n):
            a = bids[i]
            wa, ha, dta = _dims(a)
            for j in range(i + 1, n):
                b = bids[j]
                wb, hb, dtb = _dims(b)
                sp = compute_block_spacing({"device_type": dta}, {"device_type": dtb})

                pa_p, pa_m = pos_plus[a],  pos_minus[a]
                pb_p, pb_m = pos_plus[b],  pos_minus[b]

                if pa_p < pb_p and pa_m < pb_m:
                    # H-constraint: A left of B
                    # H-DAG: edge a→b with weight = A.width + x_spacing(A,B)
                    h_graph[pa_p].append((pb_p, wa + sp.x_spacing))
                    # V-DAG: edge b→a (critical invariant — not a→b)
                    v_graph[pb_p].append((pa_p, hb + sp.y_spacing))

                elif pa_p < pb_p and pa_m > pb_m:
                    # V-constraint: A below B
                    # V-DAG: edge a→b with weight = A.height + y_spacing(A,B)
                    v_graph[pa_p].append((pb_p, ha + sp.y_spacing))
                    # H-DAG: edge b→a
                    h_graph[pb_p].append((pa_p, wb + sp.x_spacing))

        # Source connects to all blocks; all blocks connect to sink
        for i in range(n):
            h_graph[SRC].append((i, 0.0))
            v_graph[SRC].append((i, 0.0))
            h_graph[i].append((SNK, _dims(bids[i])[0]))  # weight = block width
            v_graph[i].append((SNK, _dims(bids[i])[1]))  # weight = block height

        x_coords = _dag_longest_path(n + 2, h_graph, SRC)
        y_coords = _dag_longest_path(n + 2, v_graph, SRC)

        return {bids[i]: (x_coords[i], y_coords[i]) for i in range(n)}

    def copy_state(self) -> Any:
        return (list(self._r_plus), list(self._r_minus), dict(self._variant))

    def restore_state(self, saved: Any) -> None:
        rp, rm, vt = saved
        self._r_plus  = list(rp)
        self._r_minus = list(rm)
        self._variant = dict(vt)

    def capabilities(self) -> set[str]:
        return {"SA", "GA"}

    # ------------------------------------------------------------------
    # SAMixin
    # ------------------------------------------------------------------

    def perturb(self, temperature: float) -> Callable[[], None]:
        """Apply M1 (swap r_plus), M2 (swap r_minus), or M3 (variant change)."""
        if not self._r_plus:
            return lambda: None
        op = random.choices(
            [self._op_m1, self._op_m2, self._op_m3],
            weights=[0.40, 0.40, 0.20],
        )[0]
        return op()

    def _op_m1(self) -> Callable[[], None]:
        """Swap two elements in r_plus."""
        i, j = random.sample(range(len(self._r_plus)), 2)
        self._r_plus[i], self._r_plus[j] = self._r_plus[j], self._r_plus[i]
        def undo() -> None:
            self._r_plus[i], self._r_plus[j] = self._r_plus[j], self._r_plus[i]
        return undo

    def _op_m2(self) -> Callable[[], None]:
        """Swap two elements in r_minus."""
        i, j = random.sample(range(len(self._r_minus)), 2)
        self._r_minus[i], self._r_minus[j] = self._r_minus[j], self._r_minus[i]
        def undo() -> None:
            self._r_minus[i], self._r_minus[j] = self._r_minus[j], self._r_minus[i]
        return undo

    def _op_m3(self) -> Callable[[], None]:
        """Change the active size variant of a random block."""
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
        def undo() -> None:
            self._variant[bid] = old_vidx
        return undo

    # ------------------------------------------------------------------
    # GAMixin
    # ------------------------------------------------------------------

    def mutate(self) -> Callable[[], None]:
        return self.perturb(temperature=0.5)

    def crossover(self, other: "SequencePairTopology") -> "SequencePairTopology":
        """PMX crossover independently on r_plus and r_minus."""
        child = SequencePairTopology(self._blocks, self._nets)
        child._r_plus  = _pmx(self._r_plus,  other._r_plus)
        child._r_minus = _pmx(self._r_minus, other._r_minus)
        child._variant = dict(self._variant)   # inherit parent's variant state
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

    # Unreachable nodes default to 0.0
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

    # Copy segment from parent A
    for k in range(i, j + 1):
        offspring[k] = perm_a[k]

    # Build mapping: perm_a[k] ↔ perm_b[k] in segment
    mapping: dict[str, str] = {}
    for k in range(i, j + 1):
        mapping[perm_b[k]] = perm_a[k]

    # Fill remaining positions from parent B, resolving conflicts via mapping
    for k in range(n):
        if offspring[k] is not None:
            continue
        val = perm_b[k]
        # Follow the mapping chain until we find an unmapped value
        seen: set[str] = set()
        while val in mapping and val not in seen:
            seen.add(val)
            val = mapping[val]
        offspring[k] = val

    return offspring  # type: ignore[return-value]
