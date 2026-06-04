#!/usr/bin/env python3
"""
Graph-based symmetry detection for analog netlists using the SSFG approach.

Based on: Eick et al., "Comprehensive Generation of Hierarchical Placement Rules
for Analog Integrated Circuits", IEEE TCAD 2011.

Pipeline:
  1. Building block recognition  — diff pairs, current mirrors, cascode mirrors
  2. SSFG construction           — directed net graph with (bb_type, pin_a, pin_b) edge attrs
  3. Symmetry assignment         — BFS from diff-pair input seeds
  3b. Reverse SSFG scan          — finds self-symmetric source nets (e.g. tail transistors)
  4. Device pair extraction      — map symmetric nets → device pairs (cross-block MS pairs)
  5. Residual mirror pairing     — sequential MB pairing for unclaimed mirror-group devices
  5b. Enhanced passive pairing   — cross-group and within-group passive symmetry via net registry
  6. Compound assembly           — Union-Find merges all pairs sharing symmetric terminal nets
  7. Output assembly             — one group entry per compound (mixed pdk_type)

Public API (called from 011_netlisBlocksGenerator.py):
  detect_symmetries(devices, port_nets, power_nets) -> dict
  find_passive_arrays(devices)                      -> list  (legacy, no registry)
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from collections import defaultdict, namedtuple
from typing import Dict, List, Set, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG  = False

_MOSFET_GROUPS  = frozenset({"LV", "HV"})
_PASSIVE_GROUPS = frozenset({"passive"})

_SsfgEdge = namedtuple("_SsfgEdge", ["src", "dst", "attr"])
# attr = (bb_type_str, pin_a, pin_b)

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

# ── Device accessors ──────────────────────────────────────────────────────────

def _is_mosfet(dev: dict) -> bool:
    return dev.get("device_group") in _MOSFET_GROUPS


def _is_passive(dev: dict) -> bool:
    return dev.get("device_group") in _PASSIVE_GROUPS


def _gate(dev: dict) -> str:
    return dev["terminals"].get("gate", "")


def _drain(dev: dict) -> str:
    return dev["terminals"].get("drain", "")


def _source(dev: dict) -> str:
    return dev["terminals"].get("source", "")


def _passive_nets(dev: dict) -> frozenset:
    return frozenset(
        v for k, v in dev["terminals"].items()
        if k not in ("substrate", "bulk")
    )


def _polarity(dev: dict) -> str:
    return "p" if "pmos" in dev.get("pdk_type", "").lower() else "n"


def _terminal_nets(dev: dict) -> Dict[str, str]:
    return {k: v for k, v in dev["terminals"].items()
            if k not in ("bulk", "substrate") and v}


# ── Phase 1 — Building block recognition ──────────────────────────────────────

def _recognize_building_blocks(devices: list, power_nets: set) -> dict:
    mosfets: list = [d for d in devices if _is_mosfet(d)]
    by_type: Dict[str, list] = defaultdict(list)
    for d in mosfets:
        by_type[d["pdk_type"]].append(d)

    diff_pairs:     List[Tuple[dict, dict]]             = []
    mirror_groups:  List[List[dict]]                    = []
    cascode_groups: List[Tuple[dict, dict, dict, dict]] = []
    used: Set[int] = set()

    # Cascodes first (consume 4 devices each)
    for pdk_type, group in by_type.items():
        by_gate: Dict[str, list] = defaultdict(list)
        for d in group:
            g = _gate(d)
            if g and g not in power_nets:
                by_gate[g].append(d)
        gate_nets = list(by_gate.keys())

        changed = True
        while changed:
            changed = False
            for gn_u in gate_nets:
                upper_free = [d for d in by_gate[gn_u] if d["block_id"] not in used]
                if len(upper_free) < 2:
                    continue
                for gn_l in gate_nets:
                    if gn_u == gn_l:
                        continue
                    lower_free = [d for d in by_gate[gn_l] if d["block_id"] not in used]
                    if len(lower_free) < 2:
                        continue
                    matched: List[Tuple[dict, dict]] = []
                    lower_ids_used: Set[int] = set()
                    for u in upper_free:
                        us = _source(u)
                        if not us or us in power_nets:
                            continue
                        for l in lower_free:
                            if _drain(l) == us and l["block_id"] not in lower_ids_used:
                                matched.append((u, l))
                                lower_ids_used.add(l["block_id"])
                                break
                    if len(matched) >= 2:
                        (u0, l0), (u1, l1) = matched[0], matched[1]
                        ids4 = {u0["block_id"], u1["block_id"], l0["block_id"], l1["block_id"]}
                        if not ids4 & used:
                            cascode_groups.append((u0, u1, l0, l1))
                            used |= ids4
                            changed = True
                            logger.info(
                                "Cascode: upper(%s,%s) lower(%s,%s)",
                                u0["inst"], u1["inst"], l0["inst"], l1["inst"],
                            )
                            break
                if changed:
                    break

    # Diff pairs
    for pdk_type, group in by_type.items():
        by_source: Dict[str, list] = defaultdict(list)
        for d in group:
            if d["block_id"] in used:
                continue
            src = _source(d)
            if src and src not in power_nets:
                by_source[src].append(d)

        for src_net, members in by_source.items():
            by_g: Dict[str, list] = defaultdict(list)
            for d in members:
                if d["block_id"] not in used:
                    g = _gate(d)
                    if g:
                        by_g[g].append(d)
            gate_list = list(by_g.keys())
            if len(gate_list) < 2:
                continue
            for gi in range(len(gate_list)):
                for gj in range(gi + 1, len(gate_list)):
                    free_i = [d for d in by_g[gate_list[gi]] if d["block_id"] not in used]
                    free_j = [d for d in by_g[gate_list[gj]] if d["block_id"] not in used]
                    for da, db in zip(free_i, free_j):
                        diff_pairs.append((da, db))
                        used.update((da["block_id"], db["block_id"]))
                        logger.info(
                            "Diff pair: %s/%s (source=%s)",
                            da["inst"], db["inst"], src_net,
                        )

    # Current mirrors (remaining)
    for pdk_type, group in by_type.items():
        by_gate: Dict[str, list] = defaultdict(list)
        for d in group:
            if d["block_id"] in used:
                continue
            g = _gate(d)
            if g and g not in power_nets:
                by_gate[g].append(d)
        for gate_net, members in by_gate.items():
            free = [d for d in members if d["block_id"] not in used]
            if len(free) < 2:
                continue
            mirror_groups.append(free)
            for d in free:
                used.add(d["block_id"])
            logger.info("Mirror group: gate=%s, n=%d", gate_net, len(free))

    return {
        "diff_pairs":     diff_pairs,
        "mirror_groups":  mirror_groups,
        "cascode_groups": cascode_groups,
    }


# ── Phase 2 — SSFG construction ───────────────────────────────────────────────

def _build_ssfg(building_blocks: dict) -> Tuple[set, List[_SsfgEdge]]:
    nodes: Set[str] = set()
    seen:  Set[tuple] = set()
    edges: List[_SsfgEdge] = []

    def _add(src: str, dst: str, attr: tuple) -> None:
        if not src or not dst:
            return
        k = (src, dst, attr)
        if k in seen:
            return
        seen.add(k)
        nodes.update((src, dst))
        edges.append(_SsfgEdge(src, dst, attr))

    for da, db in building_blocks["diff_pairs"]:
        bbt = f"{_polarity(da)}-dp"
        _add(_gate(da),   _drain(da), (bbt, "a", "b"))
        _add(_gate(db),   _drain(db), (bbt, "a", "b"))
        _add(_source(da), _drain(da), (bbt, "c", "b"))
        _add(_source(db), _drain(db), (bbt, "c", "b"))

    for group in building_blocks["mirror_groups"]:
        bbt = f"{_polarity(group[0])}-scm"
        gate_net = _gate(group[0])
        for d in group:
            dr = _drain(d)
            if dr and dr != gate_net:
                _add(gate_net, dr, (bbt, "a", "b"))

    for u0, u1, l0, l1 in building_blocks["cascode_groups"]:
        bbt = f"{_polarity(u0)}-ccm"
        gate_u = _gate(u0)
        gate_l = _gate(l0)
        _add(gate_u, _drain(u0), (bbt, "a", "b"))
        _add(gate_u, _drain(u1), (bbt, "a", "b"))
        _add(gate_l, _drain(l0), (bbt, "a", "b"))
        _add(gate_l, _drain(l1), (bbt, "a", "b"))
        _add(_drain(l0), _source(u0), (f"{_polarity(u0)}-ccm", "b", "c"))
        _add(_drain(l1), _source(u1), (f"{_polarity(u1)}-ccm", "b", "c"))

    logger.debug("SSFG: %d nodes, %d edges", len(nodes), len(edges))
    return nodes, edges


# ── Phase 3 — Symmetry assignment (BFS on SSFG) ───────────────────────────────

def _assign_symmetry_ssfg(
    ssfg_edges:     List[_SsfgEdge],
    seed_net_pairs: List[Tuple[str, str]],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    out_adj: Dict[str, List[Tuple[str, tuple]]] = defaultdict(list)
    for e in ssfg_edges:
        out_adj[e.src].append((e.dst, e.attr))

    sym_pairs:  List[Tuple[str, str]] = []
    self_sym:   List[str]             = []
    seen_keys:  Set[tuple]            = set()
    paired:     Set[str]              = set()

    def _key(a: str, b: str) -> tuple:
        return (a, b) if a <= b else (b, a)

    def _add_pair(a: str, b: str) -> bool:
        if a == b:
            if a not in self_sym:
                self_sym.append(a)
            return False
        k = _key(a, b)
        if k in seen_keys:
            return False
        seen_keys.add(k)
        sym_pairs.append((a, b))
        paired.update((a, b))
        return True

    queue: List[Tuple[str, str]] = []
    for a, b in seed_net_pairs:
        if _add_pair(a, b):
            queue.append((a, b))

    while queue:
        n, np = queue.pop(0)

        by_attr_n:  Dict[tuple, List[str]] = defaultdict(list)
        by_attr_np: Dict[tuple, List[str]] = defaultdict(list)
        for dst, attr in out_adj.get(n,  []):
            by_attr_n[attr].append(dst)
        for dst, attr in out_adj.get(np, []):
            by_attr_np[attr].append(dst)

        for attr in set(by_attr_n) & set(by_attr_np):
            for dst_a, dst_b in zip(by_attr_n[attr], by_attr_np[attr]):
                if dst_a == dst_b:
                    if dst_a not in self_sym:
                        self_sym.append(dst_a)
                    continue
                if dst_a == np or dst_b == n:
                    src = n if dst_a == np else np
                    if src not in self_sym:
                        self_sym.append(src)
                        logger.info("Self-sym net (single-ended conversion): %s", src)
                    continue
                if _add_pair(dst_a, dst_b):
                    queue.append((dst_a, dst_b))

        for attr, dsts in by_attr_n.items():
            for dst in dsts:
                if dst == np and n not in self_sym:
                    self_sym.append(n)
                    logger.info("Self-sym net (cross-edge): %s", n)
        for attr, dsts in by_attr_np.items():
            for dst in dsts:
                if dst == n and np not in self_sym:
                    self_sym.append(np)
                    logger.info("Self-sym net (cross-edge): %s", np)

    return sym_pairs, self_sym


# ── Phase 0 — Symmetric net registry ──────────────────────────────────────────

def _build_sym_net_registry(
    sym_net_pairs: List[Tuple[str, str]],
    self_sym_nets: List[str],
) -> Dict[str, str]:
    reg: Dict[str, str] = {}
    for a, b in sym_net_pairs:
        reg[a] = b
        reg[b] = a
    for n in self_sym_nets:
        if n not in reg:
            reg[n] = n
    return reg


# ── Phase 3b — Reverse SSFG scan for self-symmetric source nets ───────────────

def _find_self_sym_source_nets(
    ssfg_edges:        List[_SsfgEdge],
    sym_net_registry:  Dict[str, str],
) -> List[str]:
    # Index incoming edges by destination net
    by_dst: Dict[str, List[_SsfgEdge]] = defaultdict(list)
    for e in ssfg_edges:
        by_dst[e.dst].append(e)

    new_self_sym: List[str] = []
    checked: Set[Tuple[str, str]] = set()

    for net_a, net_b in list(sym_net_registry.items()):
        if net_a == net_b:
            continue
        canonical = (min(net_a, net_b), max(net_a, net_b))
        if canonical in checked:
            continue
        checked.add(canonical)

        # For each attr: find src nets that feed into both net_a and net_b
        srcs_by_attr_a: Dict[tuple, Set[str]] = defaultdict(set)
        srcs_by_attr_b: Dict[tuple, Set[str]] = defaultdict(set)
        for e in by_dst.get(net_a, []):
            srcs_by_attr_a[e.attr].add(e.src)
        for e in by_dst.get(net_b, []):
            srcs_by_attr_b[e.attr].add(e.src)

        for attr in set(srcs_by_attr_a) & set(srcs_by_attr_b):
            shared = srcs_by_attr_a[attr] & srcs_by_attr_b[attr]
            for src in shared:
                # Only mark as self-symmetric if not already a member of a known pair
                already_paired = (src in sym_net_registry and sym_net_registry[src] != src)
                if not already_paired and src not in new_self_sym:
                    new_self_sym.append(src)
                    logger.info("Self-sym source net via reverse scan: %s", src)

    return new_self_sym


# ── Phase 4 — Map symmetric nets to device pairs ──────────────────────────────

def _nets_to_device_pairs(
    sym_net_pairs: List[Tuple[str, str]],
    devices:       list,
    already_used:  Set[int],
) -> Tuple[List[Tuple[int, int]], Set[int]]:
    drain_map: Dict[str, List[int]] = defaultdict(list)
    for d in devices:
        if d["block_id"] not in already_used and _drain(d):
            drain_map[_drain(d)].append(d["block_id"])

    device_pairs: List[Tuple[int, int]] = []
    new_used: Set[int] = set()

    for net_a, net_b in sym_net_pairs:
        avail_a = [bid for bid in drain_map.get(net_a, [])
                   if bid not in already_used and bid not in new_used]
        avail_b = [bid for bid in drain_map.get(net_b, [])
                   if bid not in already_used and bid not in new_used]
        for bid_a, bid_b in zip(avail_a, avail_b):
            a, b = sorted((bid_a, bid_b))
            device_pairs.append((a, b))
            new_used.update((a, b))

    return device_pairs, new_used


# ── Phase 5b — Enhanced passive detection with net registry ───────────────────

def _mirror_net_key(
    nets:             frozenset,
    sym_net_registry: Dict[str, str],
) -> frozenset:
    return frozenset(sym_net_registry.get(n, n) for n in nets)


def find_passive_arrays_v2(
    devices:          list,
    sym_net_registry: Dict[str, str],
) -> Tuple[List[dict], List[Tuple[int, int]], List[int]]:
    """
    Returns:
      standalone_clusters — passive arrays with no detected symmetry
      passive_pairs       — (bid_a, bid_b) symmetric passive pairs
      passive_self_syms   — block_ids of self-symmetric passives
    """
    passives = [d for d in devices if _is_passive(d)]
    claimed:         Set[int]              = set()
    standalone:      List[dict]            = []
    passive_pairs:   List[Tuple[int, int]] = []
    passive_self_syms: List[int]           = []

    by_key: Dict[tuple, list] = defaultdict(list)
    for d in passives:
        key = (d["pdk_type"], _passive_nets(d))
        by_key[key].append(d)

    # Detect cross-group pairs: group A's nets mirror to group B's nets
    keys = list(by_key.keys())
    cross_paired_keys: Set[tuple] = set()

    for i, (pdk_a, nets_a) in enumerate(keys):
        if (pdk_a, nets_a) in cross_paired_keys:
            continue
        mirrored = _mirror_net_key(nets_a, sym_net_registry)
        if mirrored == nets_a:
            # The net set maps to itself — not a cross pair (handled below)
            continue
        key_b = (pdk_a, mirrored)
        if key_b not in by_key:
            continue

        group_a = [d for d in by_key[(pdk_a, nets_a)] if d["block_id"] not in claimed]
        group_b = [d for d in by_key[key_b]           if d["block_id"] not in claimed]
        if not group_a or not group_b:
            continue

        n_pairs = min(len(group_a), len(group_b))
        for k in range(n_pairs):
            a = group_a[k]["block_id"]
            b = group_b[k]["block_id"]
            passive_pairs.append((min(a, b), max(a, b)))
            claimed.update((a, b))

        # Leftover unpaired devices become self-symmetric if nets are in registry
        for d in group_a[n_pairs:] + group_b[n_pairs:]:
            bid = d["block_id"]
            if bid not in claimed:
                passive_self_syms.append(bid)
                claimed.add(bid)

        cross_paired_keys.update([(pdk_a, nets_a), key_b])
        logger.info(
            "Passive cross-sym: %s nets=%s ↔ %s → %d pairs",
            pdk_a, tuple(nets_a), tuple(mirrored), n_pairs,
        )

    # Within-group pairing: N even identical passives on nets connected to registry
    for (pdk_type, nets), group in by_key.items():
        free = [d for d in group if d["block_id"] not in claimed]
        if not free:
            continue

        nets_in_registry = [n for n in nets if n in sym_net_registry]
        if not nets_in_registry:
            # No registry connection → standalone cluster
            ids = [d["block_id"] for d in free]
            standalone.append({
                "members":                 ids,
                "topology":                "parallel",
                "representative_block_id": ids[0],
            })
            claimed.update(ids)
            logger.info("Passive cluster (no sym): %d × %s", len(free), pdk_type)
            continue

        all_self_sym_nets = all(sym_net_registry.get(n) == n for n in nets_in_registry)

        if all_self_sym_nets:
            # All terminal nets are self-symmetric → devices sit on the axis
            for d in free:
                passive_self_syms.append(d["block_id"])
                claimed.add(d["block_id"])
            logger.info("Passive self-sym (all nets on axis): %d × %s", len(free), pdk_type)
        else:
            # Nets are associated with a symmetric pair but no cross-group partner found.
            # User note: even count → split into N/2 within-group pairs for common-centroid.
            n_free  = len(free)
            n_pairs = n_free // 2
            for k in range(n_pairs):
                # Mirror-image pairing: first vs last, converging inward (ABBA pattern)
                a = free[k]["block_id"]
                b = free[n_free - 1 - k]["block_id"]
                passive_pairs.append((min(a, b), max(a, b)))
                claimed.update((a, b))
            if n_free % 2 == 1:
                mid = free[n_pairs]["block_id"]
                passive_self_syms.append(mid)
                claimed.add(mid)
            logger.info(
                "Passive within-group sym: %d × %s → %d pairs", n_free, pdk_type, n_pairs
            )

    return standalone, passive_pairs, passive_self_syms


def find_passive_arrays(devices: list) -> list:
    """Legacy entry point (no registry). Returns standalone cluster list only."""
    standalone, _, _ = find_passive_arrays_v2(devices, {})
    return standalone


# ── Phase 6 — Compound assembly via Union-Find ────────────────────────────────

class _UnionFind:
    def __init__(self) -> None:
        self._parent: Dict[int, int] = {}

    def find(self, x: int) -> int:
        if x not in self._parent:
            self._parent[x] = x
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: int, y: int) -> None:
        self._parent[self.find(x)] = self.find(y)


def _assign_compound_ids(
    all_pairs:        List[Tuple[int, int]],
    all_self_syms:    List[int],
    id_to_dev:        Dict[int, dict],
    sym_net_registry: Dict[str, str],
) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Returns:
      pair_compound  — pair index → compound root id
      self_compound  — block_id  → compound root id
    """
    uf = _UnionFind()
    n_pairs = len(all_pairs)

    # Items: indices 0..n_pairs-1 are pair slots; n_pairs+j is self-sym slot j
    for i in range(n_pairs):
        uf.find(i)
    for j in range(len(all_self_syms)):
        uf.find(n_pairs + j)

    self_sym_index: Dict[int, int] = {bid: n_pairs + j for j, bid in enumerate(all_self_syms)}

    # Map each terminal net to the item indices that touch it
    net_to_items: Dict[str, List[int]] = defaultdict(list)

    def _index_device_nets(item_idx: int, dev: dict) -> None:
        for term, net in dev["terminals"].items():
            if term in ("bulk", "substrate") or not net:
                continue
            net_to_items[net].append(item_idx)

    for i, (bid_a, bid_b) in enumerate(all_pairs):
        da, db = id_to_dev.get(bid_a), id_to_dev.get(bid_b)
        if da:
            _index_device_nets(i, da)
        if db:
            _index_device_nets(i, db)

    for bid, item_idx in self_sym_index.items():
        d = id_to_dev.get(bid)
        if d:
            _index_device_nets(item_idx, d)

    # Union items that share a symmetric terminal net pair
    processed_pairs: Set[Tuple[str, str]] = set()
    for net_a, net_b in sym_net_registry.items():
        canonical = (min(net_a, net_b), max(net_a, net_b))
        if canonical in processed_pairs:
            continue
        processed_pairs.add(canonical)

        if net_a == net_b:
            # Self-symmetric net: all items touching this net belong to the same compound
            items = net_to_items.get(net_a, [])
            for k in range(1, len(items)):
                uf.union(items[0], items[k])
        else:
            # Symmetric pair: items touching net_a or net_b share the same axis
            items = net_to_items.get(net_a, []) + net_to_items.get(net_b, [])
            for k in range(1, len(items)):
                uf.union(items[0], items[k])

    pair_compound = {i: uf.find(i) for i in range(n_pairs)}
    self_compound = {bid: uf.find(idx) for bid, idx in self_sym_index.items()}
    return pair_compound, self_compound


# ── Phase 7 — Compound group output ───────────────────────────────────────────

def _assemble_compound_groups(
    all_pairs:     List[Tuple[int, int]],
    all_self_syms: List[int],
    pair_compound: Dict[int, int],
    self_compound: Dict[int, int],
) -> list:
    compound_data: Dict[int, dict] = {}

    def _get(cid: int) -> dict:
        if cid not in compound_data:
            compound_data[cid] = {"pairs": [], "self_symmetric": []}
        return compound_data[cid]

    for i, (a, b) in enumerate(all_pairs):
        _get(pair_compound[i])["pairs"].append([a, b])

    for bid in all_self_syms:
        _get(self_compound[bid])["self_symmetric"].append(bid)

    return [
        {
            "compound_id":               cid,
            "axis":                      "vertical",
            "pairs":                     data["pairs"],
            "self_symmetric":            data["self_symmetric"],
            "enforce_matching_variants": bool(data["pairs"]),
        }
        for cid, data in sorted(compound_data.items())
    ]


# ── Symmetric net-pair annotations (schema unchanged) ─────────────────────────

def _build_sym_net_pairs(devices: list, pairs: list) -> list:
    id_to_dev: Dict[int, dict] = {d["block_id"]: d for d in devices}
    result: list = []

    for a, b in pairs:
        da = id_to_dev.get(a)
        db = id_to_dev.get(b)
        if da is None or db is None:
            continue
        ta, tb = da["terminals"], db["terminals"]
        for term in [t for t in ta if t in tb and t != "bulk"]:
            net_a = ta[term]
            net_b = tb[term]
            if net_a != net_b:
                result.append({
                    "net_a":      net_a,
                    "net_b":      net_b,
                    "block_pair": [a, b],
                    "terminal":   term,
                })
    return result


# ── Compound cluster records (for hierarchical optimizer) ─────────────────────

def _build_compound_clusters(
    diff_pairs:     List[Tuple[dict, dict]],
    mirror_groups:  List[List[dict]],
    cascode_groups: List[Tuple[dict, dict, dict, dict]],
    self_sym_ids:   List[int],
) -> list:
    clusters: list = []
    cid = 0

    for da, db in diff_pairs:
        child_ids = sorted({da["block_id"], db["block_id"]})
        self_ids  = [s for s in self_sym_ids if s in child_ids]
        clusters.append({
            "compound_id":        cid,
            "child_block_ids":    child_ids,
            "group_type":         "diff_pair",
            "self_symmetric_ids": self_ids,
        })
        cid += 1

    for group in mirror_groups:
        all_ids  = sorted(d["block_id"] for d in group)
        self_ids = [s for s in self_sym_ids if s in all_ids]
        clusters.append({
            "compound_id":        cid,
            "child_block_ids":    all_ids,
            "group_type":         "current_mirror",
            "self_symmetric_ids": self_ids,
        })
        cid += 1

    for u0, u1, l0, l1 in cascode_groups:
        all_ids = sorted({u0["block_id"], u1["block_id"], l0["block_id"], l1["block_id"]})
        clusters.append({
            "compound_id":        cid,
            "child_block_ids":    all_ids,
            "group_type":         "cascode",
            "self_symmetric_ids": [],
        })
        cid += 1

    return clusters


# =============================================================================
# 5. PUBLIC ENTRY POINT
# =============================================================================

def detect_symmetries(devices: list, port_nets: set, power_nets: set) -> dict:
    """
    Full symmetry detection pipeline.

    Returns a symmetry_constraints dict with fields:
      groups                  — one entry per compound (mixed pdk_type, shared axis)
      passive_clusters        — parallel passive arrays with no detected symmetry
      symmetric_net_pairs     — per-terminal cross-net annotations for each MOSFET pair
      self_symmetric_nets     — nets at single-ended conversion points or tail sources
      cascode_proximity_pairs — [[upper_id, lower_id], ...] stacked device pairs
      compound_blocks         — cluster membership records for hierarchical optimizer
    """
    # ── Phase 1 ───────────────────────────────────────────────────────────────
    bbs = _recognize_building_blocks(devices, power_nets)

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    _, ssfg_edges = _build_ssfg(bbs)

    # ── Phase 3 ───────────────────────────────────────────────────────────────
    seed_pairs = [(_gate(da), _gate(db)) for da, db in bbs["diff_pairs"]]
    sym_net_pairs, self_sym_nets = _assign_symmetry_ssfg(ssfg_edges, seed_pairs)

    # ── Phase 0: registry ─────────────────────────────────────────────────────
    sym_net_registry = _build_sym_net_registry(sym_net_pairs, self_sym_nets)

    # ── Phase 3b: reverse scan for self-symmetric tail/source nets ────────────
    extra_self_sym_nets = _find_self_sym_source_nets(ssfg_edges, sym_net_registry)
    for net in extra_self_sym_nets:
        if net not in self_sym_nets:
            self_sym_nets.append(net)
        sym_net_registry[net] = net

    # ── Phase 4 ───────────────────────────────────────────────────────────────
    diff_ids: Set[int] = {d["block_id"] for pair in bbs["diff_pairs"] for d in pair}
    ssfg_device_pairs, ssfg_used = _nets_to_device_pairs(sym_net_pairs, devices, diff_ids)

    # ── Phase 5: residual mirror pairing ──────────────────────────────────────
    all_used_so_far = diff_ids | ssfg_used
    mirror_pairs:  List[Tuple[int, int]] = []
    mos_self_syms: List[int]             = []
    mirror_used:   Set[int]              = set()

    for group in bbs["mirror_groups"]:
        free = [d for d in group
                if d["block_id"] not in all_used_so_far
                and d["block_id"] not in mirror_used]
        for i in range(0, len(free) - 1, 2):
            a, b = sorted((free[i]["block_id"], free[i + 1]["block_id"]))
            mirror_pairs.append((a, b))
            mirror_used.update((a, b))
        if len(free) % 2 == 1:
            last = free[-1]["block_id"]
            if last not in mirror_used:
                mos_self_syms.append(last)
                mirror_used.add(last)

    # Cascode pairs and proximity annotations
    cascode_pairs: List[Tuple[int, int]] = []
    cascode_prox:  List[List[int]]       = []
    for u0, u1, l0, l1 in bbs["cascode_groups"]:
        a, b = sorted((u0["block_id"], u1["block_id"]))
        c, d_id = sorted((l0["block_id"], l1["block_id"]))
        cascode_pairs.extend([(a, b), (c, d_id)])
        cascode_prox.append([u0["block_id"], l0["block_id"]])
        cascode_prox.append([u1["block_id"], l1["block_id"]])

    # Shared-drain self-symmetric net heuristic
    id_to_dev: Dict[int, dict] = {d["block_id"]: d for d in devices}
    direct_dp_pairs = [(da["block_id"], db["block_id"]) for da, db in bbs["diff_pairs"]]
    for pa, pb in direct_dp_pairs + mirror_pairs + ssfg_device_pairs:
        da, db = id_to_dev.get(pa), id_to_dev.get(pb)
        if da and db:
            dr_a, dr_b = _drain(da), _drain(db)
            if dr_a and dr_a == dr_b:
                if dr_a not in self_sym_nets:
                    self_sym_nets.append(dr_a)
                if dr_a not in sym_net_registry:
                    sym_net_registry[dr_a] = dr_a

    # Devices whose drain sits on a self-symmetric net (e.g. tail transistor)
    drain_map: Dict[str, List[int]] = defaultdict(list)
    for d in devices:
        if _drain(d):
            drain_map[_drain(d)].append(d["block_id"])

    all_mos_used = diff_ids | ssfg_used | mirror_used | set(b for _, b in cascode_pairs) \
                   | set(a for a, _ in cascode_pairs)
    for net, partner in sym_net_registry.items():
        if partner != net:
            continue
        for bid in drain_map.get(net, []):
            if bid not in all_mos_used and bid not in mos_self_syms:
                mos_self_syms.append(bid)
                logger.info("Self-sym device (drain on self-sym net %s): block %d", net, bid)

    # ── Phase 5b ──────────────────────────────────────────────────────────────
    passive_clusters, passive_pairs, passive_self_syms = find_passive_arrays_v2(
        devices, sym_net_registry
    )

    # ── Phase 6: compound assignment ──────────────────────────────────────────
    all_mos_pairs = direct_dp_pairs + ssfg_device_pairs + mirror_pairs + cascode_pairs
    all_pairs     = all_mos_pairs + passive_pairs
    all_self_syms = mos_self_syms + passive_self_syms

    pair_compound, self_compound = _assign_compound_ids(
        all_pairs, all_self_syms, id_to_dev, sym_net_registry
    )

    # ── Phase 7: output ───────────────────────────────────────────────────────
    groups = _assemble_compound_groups(
        all_pairs, all_self_syms, pair_compound, self_compound
    )

    logger.info(
        "Symmetry: %d compounds, %d pairs, %d self-sym, %d passive pairs",
        len(groups), len(all_mos_pairs), len(all_self_syms), len(passive_pairs),
    )

    return {
        "groups":                  groups,
        "passive_clusters":        passive_clusters,
        "symmetric_net_pairs":     _build_sym_net_pairs(devices, all_mos_pairs),
        "self_symmetric_nets":     self_sym_nets,
        "cascode_proximity_pairs": cascode_prox,
        "compound_blocks":         _build_compound_clusters(
            bbs["diff_pairs"], bbs["mirror_groups"], bbs["cascode_groups"], mos_self_syms,
        ),
    }
