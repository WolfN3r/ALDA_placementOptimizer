#!/usr/bin/env python3
"""
Graph-based symmetry detection for analog netlists using the SSFG approach.

Based on: Eick et al., "Comprehensive Generation of Hierarchical Placement Rules
for Analog Integrated Circuits", IEEE TCAD 2011.

Pipeline:
  1. Building block recognition  — diff pairs, current mirrors, cascode mirrors
  2. SSFG construction           — directed net graph with (bb_type, pin_a, pin_b) edge attrs
  3. Symmetry assignment         — BFS from diff-pair input seeds; finds ALL symmetric net pairs
  4. Device pair extraction      — map symmetric nets → device pairs (cross-block MS pairs)
  5. Residual mirror pairing     — sequential MB pairing for unclaimed mirror-group devices
  6. Output assembly             — groups, passive clusters, sym net pairs,
                                   self_symmetric_nets, cascode_proximity_pairs, compound_blocks

Public API (called from 011_netlisBlocksGenerator.py):
  detect_symmetries(devices, port_nets, power_nets) -> dict
  find_passive_arrays(devices)                      -> list
"""

from collections import defaultdict, namedtuple
from typing import Dict, List, Set, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

DEBUG  = False
logger = get_logger(__name__, DEBUG)

# =============================================================================
# Constants
# =============================================================================
_MOSFET_GROUPS  = frozenset({"LV", "HV"})
_PASSIVE_GROUPS = frozenset({"passive"})

_SsfgEdge = namedtuple("_SsfgEdge", ["src", "dst", "attr"])
# attr = (bb_type_str, pin_a, pin_b), e.g. ("n-dp", "a", "b")

# =============================================================================
# Device accessors
# =============================================================================

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
    """Return 'p' for PMOS, 'n' otherwise."""
    return "p" if "pmos" in dev.get("pdk_type", "").lower() else "n"


# =============================================================================
# Phase 1 — Building block recognition
# =============================================================================

def _recognize_building_blocks(devices: list, power_nets: set) -> dict:
    """
    Identify all candidate building blocks from the flat device list.
    Order: cascodes first (consume 4 devices), then diff pairs, then mirrors.
    Returns:
      diff_pairs     — list of (dev_a, dev_b)
      mirror_groups  — list of [dev, ...]  (all same-gate, same-type devices)
      cascode_groups — list of (upper_a, upper_b, lower_a, lower_b)
    """
    mosfets: list = [d for d in devices if _is_mosfet(d)]
    by_type: Dict[str, list] = defaultdict(list)
    for d in mosfets:
        by_type[d["pdk_type"]].append(d)

    diff_pairs:     List[Tuple[dict, dict]]               = []
    mirror_groups:  List[List[dict]]                      = []
    cascode_groups: List[Tuple[dict, dict, dict, dict]]   = []
    used: Set[int] = set()

    # ── 1. Cascode detection (upper.source == lower.drain, shared internal node) ──
    # Standard cascode pattern: lower pair sits between power rail and upper pair.
    # lower.drain connects to upper.source at the internal cascode node.
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
                    # find pairs where upper.source == lower.drain (internal cascode node)
                    matched: List[Tuple[dict, dict]] = []
                    lower_ids_used = set()
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
                            break  # restart search for remaining cascodes
                if changed:
                    break

    # ── 2. Diff pair detection (exhaustive: all pairs across distinct gate nets) ──
    for pdk_type, group in by_type.items():
        by_source: Dict[str, list] = defaultdict(list)
        for d in group:
            if d["block_id"] in used:
                continue
            src = _source(d)
            if src and src not in power_nets:
                by_source[src].append(d)

        for src_net, members in by_source.items():
            # group by gate net; pair across different gate groups
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

    # ── 3. Current mirror detection (remaining devices, grouped by gate net) ──
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


# =============================================================================
# Phase 2 — SSFG construction
# =============================================================================

def _build_ssfg(building_blocks: dict) -> Tuple[set, List[_SsfgEdge]]:
    """
    Build the Structural Signal Flow Graph from recognized building blocks.
    Nodes = net names; edges carry (bb_type, pin_a, pin_b) attributes.
    No two edges with equal (src, dst, attr) are created (deduplicated).
    """
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

    # Diff pair: gate→drain (a→b) + source→drain (c→b) for both sides
    for da, db in building_blocks["diff_pairs"]:
        bbt = f"{_polarity(da)}-dp"
        _add(_gate(da),   _drain(da), (bbt, "a", "b"))
        _add(_gate(db),   _drain(db), (bbt, "a", "b"))
        _add(_source(da), _drain(da), (bbt, "c", "b"))
        _add(_source(db), _drain(db), (bbt, "c", "b"))

    # Simple current mirror: for each group find the reference transistor
    # (diode-connected: gate==drain) and add one edge per output transistor.
    for group in building_blocks["mirror_groups"]:
        bbt = f"{_polarity(group[0])}-scm"
        # Identify gate net (same for all in group) and which drains are outputs
        gate_net = _gate(group[0])
        for d in group:
            dr = _drain(d)
            if dr and dr != gate_net:          # output transistor (gate != drain)
                _add(gate_net, dr, (bbt, "a", "b"))
            # diode-connected reference: no SSFG edge needed (gate==drain, self-loop)

    # Cascode mirror: upper gate→drain + lower gate→drain + upper.drain→lower.source
    for u0, u1, l0, l1 in building_blocks["cascode_groups"]:
        bbt = f"{_polarity(u0)}-ccm"
        gate_u = _gate(u0)   # shared upper gate
        gate_l = _gate(l0)   # shared lower gate
        _add(gate_u, _drain(u0), (bbt, "a", "b"))
        _add(gate_u, _drain(u1), (bbt, "a", "b"))
        _add(gate_l, _drain(l0), (bbt, "a", "b"))
        _add(gate_l, _drain(l1), (bbt, "a", "b"))
        # Stack connections: lower.drain == upper.source (internal cascode node)
        _add(_drain(l0), _source(u0), (f"{_polarity(u0)}-ccm", "b", "c"))
        _add(_drain(l1), _source(u1), (f"{_polarity(u1)}-ccm", "b", "c"))

    logger.debug("SSFG: %d nodes, %d edges", len(nodes), len(edges))
    return nodes, edges


# =============================================================================
# Phase 3 — Hierarchical symmetry assignment (BFS on SSFG)
# =============================================================================

def _assign_symmetry_ssfg(
    ssfg_edges:     List[_SsfgEdge],
    seed_net_pairs: List[Tuple[str, str]],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    """
    Propagate symmetry through the SSFG starting from differential-pair input seeds.

    At each symmetric node pair (n, n') the algorithm looks for outgoing edge pairs
    with matching attributes and marks their destinations as symmetric (BFS).
    A self-symmetric net is recorded when both sides of an attr-matched edge lead
    to the same net, or when an edge crosses directly between two already-symmetric
    nodes.

    Returns:
      sym_net_pairs — ordered list of (net_a, net_b) symmetric net pairs
      self_sym_nets — nets identified as single-ended conversion points
    """
    # adjacency: net → [(dst, attr)]
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

        # Group outgoing edges of n and n' by attribute
        by_attr_n:  Dict[tuple, List[str]] = defaultdict(list)
        by_attr_np: Dict[tuple, List[str]] = defaultdict(list)
        for dst, attr in out_adj.get(n,  []):
            by_attr_n[attr].append(dst)
        for dst, attr in out_adj.get(np, []):
            by_attr_np[attr].append(dst)

        # Match on shared attributes
        for attr in set(by_attr_n) & set(by_attr_np):
            dsts_n  = by_attr_n[attr]
            dsts_np = by_attr_np[attr]
            for dst_a, dst_b in zip(dsts_n, dsts_np):
                # Self-symmetric: both sides collapse to the same net
                if dst_a == dst_b:
                    if dst_a not in self_sym:
                        self_sym.append(dst_a)
                    continue
                # Cross-node: an edge from n leads to n' (single-ended conversion)
                if dst_a == np or dst_b == n:
                    src = n if dst_a == np else np
                    if src not in self_sym:
                        self_sym.append(src)
                        logger.info("Self-symmetric net (conversion): %s", src)
                    continue
                if _add_pair(dst_a, dst_b):
                    queue.append((dst_a, dst_b))

        # Check for cross-directed self-symmetric edges within single-side attrs
        for attr, dsts in by_attr_n.items():
            for dst in dsts:
                if dst == np and n not in self_sym:
                    self_sym.append(n)
                    logger.info("Self-symmetric net (cross-edge): %s", n)
        for attr, dsts in by_attr_np.items():
            for dst in dsts:
                if dst == n and np not in self_sym:
                    self_sym.append(np)
                    logger.info("Self-symmetric net (cross-edge): %s", np)

    return sym_pairs, self_sym


# =============================================================================
# Phase 4 — Map symmetric nets to device pairs
# =============================================================================

def _nets_to_device_pairs(
    sym_net_pairs: List[Tuple[str, str]],
    devices:       list,
    already_used:  Set[int],
) -> Tuple[List[Tuple[int, int]], Set[int]]:
    """
    For each symmetric net pair (net_a, net_b), find devices whose drain connects
    to net_a and net_b respectively, and emit them as a symmetric device pair.
    Only unclaimed devices (not in already_used) are considered.
    """
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


# =============================================================================
# Passive arrays (public, called directly from 011_netlisBlocksGenerator.py)
# =============================================================================

def find_passive_arrays(devices: list) -> list:
    """Detect parallel passive arrays: identical passives connected to same net pair."""
    passives = [d for d in devices if _is_passive(d)]
    clusters: list  = []
    claimed:  Set[int] = set()

    by_key: Dict[tuple, list] = defaultdict(list)
    for d in passives:
        key = (d["pdk_type"], _passive_nets(d))
        by_key[key].append(d)

    for (pdk_type, nets), group in by_key.items():
        free = [d for d in group if d["block_id"] not in claimed]
        if len(free) < 2:
            continue
        ids = [d["block_id"] for d in free]
        clusters.append({
            "members":                ids,
            "topology":               "parallel",
            "representative_block_id": ids[0],
        })
        claimed.update(ids)
        logger.info("Passive array: %d × %s on %s", len(ids), pdk_type, tuple(nets))

    return clusters


# =============================================================================
# Symmetric net-pair annotations (unchanged schema)
# =============================================================================

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


# =============================================================================
# Compound cluster builder (for hierarchical optimizer)
# =============================================================================

def _build_compound_clusters(
    diff_pairs:     List[Tuple[dict, dict]],
    mirror_groups:  List[List[dict]],
    cascode_groups: List[Tuple[dict, dict, dict, dict]],
    self_sym_ids:   List[int],
) -> list:
    """
    Emit cluster membership records — no geometry, no variant generation.
    The downstream hierarchical optimizer reads these to build compound blocks.
    """
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
# Public entry point
# =============================================================================

def detect_symmetries(devices: list, port_nets: set, power_nets: set) -> dict:
    """
    Full symmetry detection pipeline.

    Returns a symmetry_constraints dict with fields:
      groups                  — symmetric pairs + self-symmetric blocks, grouped by pdk_type
      passive_clusters        — parallel passive arrays
      symmetric_net_pairs     — per-terminal cross-net annotations for each pair
      self_symmetric_nets     — nets at single-ended conversion points (NOW POPULATED)
      cascode_proximity_pairs — [[upper_id, lower_id], ...] stacked device pairs
      compound_blocks         — cluster membership records for hierarchical optimizer
    """
    # ── Phase 1: building block recognition ───────────────────────────────────
    bbs = _recognize_building_blocks(devices, power_nets)

    # ── Phase 2: SSFG ─────────────────────────────────────────────────────────
    _, ssfg_edges = _build_ssfg(bbs)

    # ── Phase 3: symmetry assignment from diff-pair input seeds ───────────────
    seed_pairs = [(_gate(da), _gate(db)) for da, db in bbs["diff_pairs"]]
    sym_net_pairs, self_sym_nets = _assign_symmetry_ssfg(ssfg_edges, seed_pairs)

    # ── Phase 4: SSFG cross-block device pairs ────────────────────────────────
    # Direct diff-pair block IDs are already established; skip them in net mapping
    diff_ids: Set[int] = {d["block_id"] for pair in bbs["diff_pairs"] for d in pair}
    ssfg_device_pairs, ssfg_used = _nets_to_device_pairs(sym_net_pairs, devices, diff_ids)

    # ── Phase 5: residual mirror pairing (devices not claimed by SSFG) ────────
    all_used_so_far = diff_ids | ssfg_used
    mirror_pairs:  List[Tuple[int, int]] = []
    self_sym_ids:  List[int]             = []
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
                self_sym_ids.append(last)
                mirror_used.add(last)

    # ── Cascode pairs and proximity annotations ────────────────────────────────
    cascode_pairs: List[Tuple[int, int]] = []
    cascode_prox:  List[List[int]]       = []
    for u0, u1, l0, l1 in bbs["cascode_groups"]:
        a, b = sorted((u0["block_id"], u1["block_id"]))
        c, d = sorted((l0["block_id"], l1["block_id"]))
        cascode_pairs.extend([(a, b), (c, d)])
        cascode_prox.append([u0["block_id"], l0["block_id"]])
        cascode_prox.append([u1["block_id"], l1["block_id"]])

    # ── Self-symmetric net heuristic: drain shared by both devices in any pair ─
    id_to_dev: Dict[int, dict] = {d["block_id"]: d for d in devices}
    direct_dp_pairs = [(da["block_id"], db["block_id"]) for da, db in bbs["diff_pairs"]]
    for a, b in direct_dp_pairs + mirror_pairs + ssfg_device_pairs:
        da = id_to_dev.get(a)
        db = id_to_dev.get(b)
        if da and db:
            dr_a, dr_b = _drain(da), _drain(db)
            if dr_a and dr_a == dr_b and dr_a not in self_sym_nets:
                self_sym_nets.append(dr_a)

    # ── Assemble all pairs ─────────────────────────────────────────────────────
    all_pairs = direct_dp_pairs + ssfg_device_pairs + mirror_pairs + cascode_pairs

    # ── Group by pdk_type for the `groups` output schema ──────────────────────
    id_to_type: Dict[int, str] = {d["block_id"]: d["pdk_type"] for d in devices}
    type_to_pairs: Dict[str, list] = defaultdict(list)
    type_to_self:  Dict[str, list] = defaultdict(list)

    for a, b in all_pairs:
        t = id_to_type.get(a, "unknown")
        type_to_pairs[t].append([a, b])
    for s in self_sym_ids:
        t = id_to_type.get(s, "unknown")
        type_to_self[t].append(s)

    groups = [
        {
            "axis":                      "vertical",
            "pairs":                     type_to_pairs.get(t, []),
            "self_symmetric":            type_to_self.get(t, []),
            "enforce_matching_variants": bool(type_to_pairs.get(t)),
        }
        for t in sorted(set(type_to_pairs) | set(type_to_self))
    ]

    passive_clusters  = find_passive_arrays(devices)
    sym_net_pair_annot = _build_sym_net_pairs(devices, all_pairs)
    compound_blocks   = _build_compound_clusters(
        bbs["diff_pairs"], bbs["mirror_groups"], bbs["cascode_groups"], self_sym_ids,
    )

    return {
        "groups":                  groups,
        "passive_clusters":        passive_clusters,
        "symmetric_net_pairs":     sym_net_pair_annot,
        "self_symmetric_nets":     self_sym_nets,
        "cascode_proximity_pairs": cascode_prox,
        "compound_blocks":         compound_blocks,
    }
