#!/usr/bin/env python3
"""
Graph-based symmetry detection for analog netlists.

Input:  flat list of device dicts (after hierarchy expansion) + port/power net sets.
Output: symmetry_constraints dict in the same schema used by 001_L1blocksGenerator.

Detected structures:
  diff_pair      — same-type MOSFETs sharing a non-power source net, different gate nets
  current_mirror — same-type MOSFETs sharing a non-power gate net; paired up
  passive_array  — identical passives across the same two nets collapsed to one block
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from collections import defaultdict

# =============================================================================
# 2. CONSTANTS
# =============================================================================
_MOSFET_GROUPS  = frozenset({"LV", "HV"})
_PASSIVE_GROUPS = frozenset({"passive"})

# =============================================================================
# 3. LOGGING
# =============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

DEBUG  = False
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
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


def find_diff_pairs(devices: list, power_nets: set) -> list:
    mosfets: list = [d for d in devices if _is_mosfet(d)]
    by_type: dict = defaultdict(list)
    for d in mosfets:
        by_type[d["pdk_type"]].append(d)

    pairs: list = []
    used: set   = set()

    for pdk_type, group in by_type.items():
        by_source: dict = defaultdict(list)
        for d in group:
            src = _source(d)
            if src and src not in power_nets:
                by_source[src].append(d)

        for src_net, members in by_source.items():
            free = [d for d in members if d["block_id"] not in used]
            if len(free) < 2:
                continue
            # Pair first two devices with different gate nets found in the group
            for i in range(len(free)):
                found = False
                for j in range(i + 1, len(free)):
                    da, db = free[i], free[j]
                    if _gate(da) != _gate(db):
                        a, b = sorted((da["block_id"], db["block_id"]))
                        pairs.append((a, b))
                        used.add(a)
                        used.add(b)
                        found = True
                        break
                if found:
                    break

    return pairs


def find_current_mirrors(devices: list, power_nets: set, diff_pair_ids: set) -> tuple:
    mosfets: list = [
        d for d in devices
        if _is_mosfet(d) and d["block_id"] not in diff_pair_ids
    ]
    by_type: dict = defaultdict(list)
    for d in mosfets:
        by_type[d["pdk_type"]].append(d)

    pairs: list    = []
    self_sym: list = []
    used: set      = set()

    for pdk_type, group in by_type.items():
        by_gate: dict = defaultdict(list)
        for d in group:
            g = _gate(d)
            if g and g not in power_nets:
                by_gate[g].append(d)

        for gate_net, members in by_gate.items():
            if len(members) < 2:
                continue
            free = [d for d in members if d["block_id"] not in used]
            # Pair up all free members; odd device left over becomes self-symmetric
            for i in range(0, len(free) - 1, 2):
                a = free[i]["block_id"]
                b = free[i + 1]["block_id"]
                a, b = sorted((a, b))
                pairs.append((a, b))
                used.add(a)
                used.add(b)
            if len(free) % 2 == 1:
                last_id = free[-1]["block_id"]
                if last_id not in used:
                    self_sym.append(last_id)
                    used.add(last_id)

    return pairs, self_sym


def find_passive_arrays(devices: list) -> list:
    passives: list = [d for d in devices if _is_passive(d)]
    clusters: list = []
    claimed: set   = set()

    by_key: dict = defaultdict(list)
    for d in passives:
        key = (d["pdk_type"], _passive_nets(d))
        by_key[key].append(d)

    for (pdk_type, nets), group in by_key.items():
        free = [d for d in group if d["block_id"] not in claimed]
        if len(free) < 2:
            continue
        ids = [d["block_id"] for d in free]
        clusters.append({
            "members":               ids,
            "topology":              "parallel",
            "representative_block_id": ids[0],
        })
        claimed.update(ids)
        logger.info(
            "Passive parallel array: %d × %s between %s",
            len(ids), pdk_type, tuple(nets),
        )

    return clusters


def _build_sym_net_pairs(devices: list, pairs: list) -> list:
    id_to_dev: dict = {d["block_id"]: d for d in devices}
    sym_net_pairs: list = []

    for a, b in pairs:
        da = id_to_dev.get(a)
        db = id_to_dev.get(b)
        if da is None or db is None:
            continue
        ta = da["terminals"]
        tb = db["terminals"]
        for term in [t for t in ta if t in tb and t != "bulk"]:
            net_a = ta[term]
            net_b = tb[term]
            if net_a != net_b:
                sym_net_pairs.append({
                    "net_a":      net_a,
                    "net_b":      net_b,
                    "block_pair": [a, b],
                    "terminal":   term,
                })

    return sym_net_pairs


def detect_symmetries(devices: list, port_nets: set, power_nets: set) -> dict:
    diff_pairs        = find_diff_pairs(devices, power_nets)
    diff_pair_ids     = {bid for pair in diff_pairs for bid in pair}
    mirror_pairs, self_sym = find_current_mirrors(devices, power_nets, diff_pair_ids)
    passive_clusters  = find_passive_arrays(devices)

    all_pairs    = diff_pairs + mirror_pairs
    sym_net_pairs = _build_sym_net_pairs(devices, all_pairs)

    id_to_type: dict   = {d["block_id"]: d["pdk_type"] for d in devices}
    type_to_pairs: dict = defaultdict(list)
    type_to_self: dict  = defaultdict(list)

    for a, b in diff_pairs + mirror_pairs:
        type_to_pairs[id_to_type.get(a, "unknown")].append([a, b])
    for s in self_sym:
        type_to_self[id_to_type.get(s, "unknown")].append(s)

    groups = [
        {
            "axis":                      "vertical",
            "pairs":                     type_to_pairs.get(t, []),
            "self_symmetric":            type_to_self.get(t, []),
            "enforce_matching_variants": bool(type_to_pairs.get(t)),
        }
        for t in sorted(set(type_to_pairs) | set(type_to_self))
    ]

    return {
        "groups":               groups,
        "passive_clusters":     passive_clusters,
        "symmetric_net_pairs":  sym_net_pairs,
        "self_symmetric_nets":  [],
    }
