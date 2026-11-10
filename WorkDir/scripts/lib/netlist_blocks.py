"""
Netlist → block-JSON helpers shared by the netlist-driven block generators
(011_netlisBlocksGenerator, 012_pdkDeviceGenerator): net classes, the
"netlist" section, pin labels, parallel-passive collapsing, placement_config.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from symmetry_detector import find_passive_arrays

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

# SPICE power supply aliases (case-insensitive match)
POWER_ALIASES: frozenset = frozenset({
    "vdda", "vssa", "vddd", "vssd", "vdd", "vss", "gnd", "gnd!",
    "vcc", "vee", "avdd", "avss",
})

_PASSIVE_MAX_SPLIT = 8

# =============================================================================
# ALGORITHM
# =============================================================================

def classify_nets(all_nets: set, top_ports: list) -> dict:
    port_set = {p.lower() for p in top_ports}
    result: dict = {}
    for net in all_nets:
        lo = net.lower()
        if lo in POWER_ALIASES:
            result[net] = "power"
        elif lo in port_set:
            result[net] = "signal"
        else:
            result[net] = "internal"
    return result


def build_netlist_json(blocks: list, net_class: dict) -> dict:
    net_pins: dict = defaultdict(list)
    for blk in blocks:
        if "error" in blk:
            continue
        bid = blk["block_id"]
        for term, pin_lbl in blk.get("pin_assignment", {}).items():
            net = blk["terminals"].get(term)
            if net:
                net_pins[net].append(f"B{bid}_{pin_lbl}")

    nets = [
        {"net_id": net, "net_type": net_class.get(net, "internal"), "pins": pins}
        for net, pins in sorted(net_pins.items())
    ]
    n_power    = sum(1 for n in nets if n["net_type"] == "power")
    n_signal   = sum(1 for n in nets if n["net_type"] == "signal")
    n_internal = sum(1 for n in nets if n["net_type"] == "internal")
    tot_pins   = sum(blk["num_pins"] for blk in blocks if "error" not in blk)
    return {
        "num_nets":          len(nets),
        "num_power_nets":    n_power,
        "num_signal_nets":   n_signal,
        "num_internal_nets": n_internal,
        "num_pins":          tot_pins,
        "nets":              nets,
    }


def pin_assignment_for(dev: dict) -> dict:
    if dev["device_group"] != "passive":
        return {"bulk": "P0", "drain": "P1", "gate": "P2", "source": "P3"}
    terms  = list(dev["terminals"].keys())
    subs   = [t for t in terms if t == "substrate"]
    others = [t for t in terms if t != "substrate"]
    pa: dict = {}
    if subs:
        pa["substrate"] = "P0"
        for k, t in enumerate(others):
            pa[t] = f"P{k + 1}"
    else:
        for k, t in enumerate(others):
            pa[t] = f"P{k}"
    return pa


def collapse_passive_arrays(flat_devices: list) -> tuple:
    """Identical parallel passives -> one representative block.
    Returns (collapsed devices with block_id, inst -> cluster size of each
    representative, passive_clusters entries for symmetry_constraints)."""
    temp_devs = [dict(d, block_id=i) for i, d in enumerate(flat_devices)]
    raw_clusters = find_passive_arrays(temp_devs)

    inst_to_mult: dict = {}
    insts_to_drop: set = set()
    for cluster in raw_clusters:
        rep_inst = temp_devs[cluster["representative_block_id"]]["inst"]
        inst_to_mult[rep_inst] = len(cluster["members"])
        for extra_bid in cluster["members"][1:]:
            insts_to_drop.add(temp_devs[extra_bid]["inst"])

    old_to_new: dict = {}
    collapsed: list  = []
    for i, dev in enumerate(flat_devices):
        if dev["inst"] not in insts_to_drop:
            new_bid = len(collapsed)
            old_to_new[i] = new_bid
            collapsed.append(dict(dev, block_id=new_bid))

    passive_cluster_info: list = []
    for cluster in raw_clusters:
        new_rep = old_to_new.get(cluster["representative_block_id"])
        if new_rep is None:
            continue
        passive_cluster_info.append({
            "representative_block_id": new_rep,
            "original_count":          len(cluster["members"]),
            "topology":                cluster["topology"],
            "original_insts":          [flat_devices[m]["inst"] for m in cluster["members"]],
        })
    return collapsed, inst_to_mult, passive_cluster_info


def placement_config(sym_mode: str) -> dict:
    return {
        "symmetry_mode":            sym_mode,
        "enable_matching":          True,
        "enable_passive_splitting": True,
        "passive_max_split":        _PASSIVE_MAX_SPLIT,
    }
