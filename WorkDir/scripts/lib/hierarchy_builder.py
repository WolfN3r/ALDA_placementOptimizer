#!/usr/bin/env python3
"""
Build the 'groups' layer from symmetry detection output.

Consumes: symmetry_constraints (from detect_symmetries), all_blocks (list of
block dicts), and placement_config.  Produces a groups list where each group
is a matched active topology or a splittable passive cluster.  Groups are the
primary placement units in the hierarchical optimizer pass.

Active groups follow Eick 2011 §V: building blocks (dp, mirror banks, level
shifters, cascode mirrors, latches) and symmetric device pairs are merged into
matching groups, so a group never cuts a symmetric pair. Every group then gets
a symmetry annotation, independent of the symmetry mode:
  {"axis_id": compound id, "level": "hard" | "soft"} or None
  hard — the group contains a diff pair or touches its drain/source nets
         (load mirror, cascodes, the mirror feeding the tail);
  soft — the group shares that axis through a symmetric pair further out.
101_placementOptimizer.py decides per mode which levels it enforces.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from __future__ import annotations
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup        import get_logger
from topology_library import get_topology_rules
from matching_engine  import compute_matching_variants
from spacing          import compute_block_spacing, MIXED_TYPE_SEP
import pin_access

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_PASSIVE_DEVICE_PREFIXES = ("res_", "cap_")
_PASSIVE_CLASSES = frozenset({"res", "cap"})

# Powers-of-2 split counts generated for passive groups.
# The placer selects one split count; all others are alternatives.
_PASSIVE_SPLIT_SEQUENCE = [1, 2, 4, 8, 16]

# Detector building-block type → group topology_type, in tag priority order
# (a group mixing several blocks takes the first tag present).
_TAG_OF_BB: dict[str, str] = {
    "dp":   "diff_pair",
    "xcpl": "cross_coupled",
    "ccm":  "cascode_current_mirror",
    "scm":  "current_mirror",
    "ls":   "level_shifter",
    "inv":   "inverter",
    "nand2": "nand2",
    "nor2":  "nor2",
    "tg":    "transmission_gate",
}
_DIGITAL_BB     = frozenset({"inv", "nand2", "nor2", "tg"})
_PROXIMITY_TAGS = frozenset(_TAG_OF_BB[k] for k in _DIGITAL_BB)
_TAG_ORDER = [_TAG_OF_BB[k] for k in ("dp", "xcpl", "ccm", "scm", "ls")] + ["paired_symmetric"] \
             + [_TAG_OF_BB[k] for k in ("inv", "nand2", "nor2", "tg")]

# Symmetry mode → group symmetry levels that become axis constraints (101) and
# are drawn as axes (viewer). Every mode places the matched groups.
SYM_MODE_LEVELS: dict[str, tuple] = {
    "matched":  (),
    "balanced": ("hard",),
    "mirrored": ("hard", "soft"),
}
# Mode names in JSON files written before the 2026-10-20 rename.
LEGACY_SYM_MODES: dict[str, str] = {"none": "matched", "moderate": "balanced", "aggressive": "mirrored"}

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _is_passive_block(blk: dict) -> bool:
    """device_class (PDK-generic, set by 012) wins; gpdk090 names start res_/cap_."""
    if blk.get("device_class"):
        return blk["device_class"] in _PASSIVE_CLASSES
    return blk.get("device_type", "").startswith(_PASSIVE_DEVICE_PREFIXES)


def _passive_split_variants(max_split: int) -> List[int]:
    return [n for n in _PASSIVE_SPLIT_SEQUENCE if n <= max_split]


def _build_active_group(
    group_id:       int,
    topology_tag:   str,
    block_ids:      List[int],
    block_by_id:    dict,
    enable_matching: bool,
) -> dict:
    rules   = get_topology_rules(topology_tag)
    members = [block_by_id[bid] for bid in block_ids if bid in block_by_id]
    variants = compute_matching_variants(members, rules) if enable_matching and members else []
    return {
        "group_id":          group_id,
        "topology_type":     topology_tag,
        "block_ids":         block_ids,
        "matching_variants": variants,
        "intra_spacing":     {
            "x_um": rules["intra_spacing_x"],
            "y_um": rules["intra_spacing_y"],
        },
        "ungroup": False,
    }


def _collect_block_ids(compound_group: dict) -> List[int]:
    ids: List[int] = []
    for a, b in compound_group.get("pairs", []):
        if a not in ids:
            ids.append(a)
        if b not in ids:
            ids.append(b)
    for ss in compound_group.get("self_symmetric", []):
        if ss not in ids:
            ids.append(ss)
    return ids


def _device_key(bid: int, block_by_id: dict) -> tuple:
    params = block_by_id.get(bid, {}).get("parameters", {})
    return (
        # fixed-width models (e.g. res_xhigh_po_0p35) carry width None: the model name fixes it
        round(float(params.get("width") or 0.0), 4),
        round(float(params.get("length") or 0.0), 4),
        int(params.get("num_fingers", 1)),
    )


def _split_by_device_characteristics(bids: list, block_by_id: dict) -> dict:
    """
    Split block IDs into sub-lists where every element shares the same W, L, Nf,
    keyed by that triple. Transistors with different W, L, or Nf cannot be
    physically co-matched, so they must form separate groups. M (multiplier) may
    differ within a sub-list; compute_matching_variants() handles that by summing M_i.
    """
    sub_groups: dict = {}
    for bid in bids:
        sub_groups.setdefault(_device_key(bid, block_by_id), []).append(bid)
    return sub_groups


def _find(parent: dict, x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent: dict, a, b) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[ra] = rb


def _polarity(blk: dict) -> str:
    if blk.get("device_class"):
        return "p" if blk["device_class"] == "pmos" else "n"
    return "p" if "pmos" in blk.get("device_type", "") else "n"


def _switches(block_by_id: dict, bb_of: dict) -> set:
    """
    Single transistors whose gate net also drives a transistor of the opposite
    polarity: a digital signal (clock, logic) drives N and P, a bias net never does.
    """
    gate_pols: dict[str, set] = {}
    for blk in block_by_id.values():
        gate = blk.get("terminals", {}).get("gate")
        if gate:
            gate_pols.setdefault(gate, set()).add(_polarity(blk))
    return {
        bid for bid, blk in block_by_id.items()
        if bid not in bb_of and blk.get("terminals", {}).get("gate")
        and len(gate_pols[blk["terminals"]["gate"]]) == 2
    }


def _is_split_pair(a: int, b: int, bb_of: dict, switches: set, block_by_id: dict, sym_mode: str) -> bool:
    """B/B' (two mirrored groups) instead of one merged self-symmetric group."""
    if bb_of.get(a) in _DIGITAL_BB and bb_of.get(b) in _DIGITAL_BB:
        return True
    if a in switches and b in switches:
        return True
    if _is_passive_block(block_by_id[a]) and _is_passive_block(block_by_id[b]):
        return sym_mode == "mirrored"
    return False


def _components(sym_constraints: dict, block_by_id: dict, sym_mode: str) -> tuple:
    """
    Union building blocks, series stacks, merged pairs (Eick M_B, M_S) and, per side,
    switches sharing gate + source. Returns (components in block order, bb type per
    block, split pairs [(a_L, b_R, compound_id)], merged pairs [(a, b, compound_id)]).
    """
    parent: dict = {}
    bb_of: dict[int, str] = {}
    for bb in sym_constraints.get("building_blocks", []):
        devs = [b for b in bb["devices"] if b in block_by_id]
        for b in devs:
            _union(parent, devs[0], b)
            bb_of[b] = bb["type"]
    for members in sym_constraints.get("logical_devices", []):
        devs = [b for b in members if b in block_by_id]
        for b in devs:
            _union(parent, devs[0], b)

    switches = _switches(block_by_id, bb_of)
    split, merged = [], []
    for cg in sym_constraints.get("groups", []):
        for a, b in cg["pairs"]:
            if a not in block_by_id or b not in block_by_id:
                continue
            if _is_split_pair(a, b, bb_of, switches, block_by_id, sym_mode):
                split.append((a, b, cg["compound_id"]))
                parent.setdefault(a, a)
                parent.setdefault(b, b)
            else:
                _union(parent, a, b)
                merged.append((a, b, cg["compound_id"]))

    by_key: dict[tuple, list] = {}
    for a, b, _ in split:
        for bid, side in ((a, "L"), (b, "R")):
            if bid in switches:
                t = block_by_id[bid]["terminals"]
                key = (t.get("gate"), t.get("source"), block_by_id[bid].get("device_type"), side)
                by_key.setdefault(key, []).append(bid)
    for devs in by_key.values():
        for b in devs:
            _union(parent, devs[0], b)

    split_bids = {x for a, b, _ in split for x in (a, b)}
    comps: dict = {}
    for bid in block_by_id:
        if bid in parent:
            comps.setdefault(_find(parent, bid), []).append(bid)
    components = [c for c in comps.values() if len(c) >= 2 or c[0] in split_bids]
    return components, bb_of, split, merged


def _component_symmetry(
    components: list, split: list, merged: list, sym_constraints: dict, block_by_id: dict,
) -> list:
    """
    Per component: {"axis_id", "level", "role", "partner" (component index), "side"} or None.
    A component joins the axis of any pair it contains (soft) or of any compound
    whose DP drain/source nets it touches (hard); components bridging two compounds
    merge their axes. Role "pair" iff all its split pairs lead to one partner
    component that points back; a pair's level is hard if either side is hard.
    """
    comp_of = {b: i for i, c in enumerate(components) for b in c}
    core_axis: dict[str, int] = {}
    for cg in sym_constraints.get("groups", []):
        for net in cg.get("core_nets", []):
            core_axis[net] = cg["compound_id"]

    axes: list[set] = [set() for _ in components]
    hard = [False] * len(components)
    partners: list[set] = [set() for _ in components]
    side: list = [None] * len(components)
    for a, b, cid in merged:
        axes[comp_of[a]].add(cid)
    for a, b, cid in split:
        ia, ib = comp_of[a], comp_of[b]
        axes[ia].add(cid)
        axes[ib].add(cid)
        if ia != ib:
            partners[ia].add(ib)
            partners[ib].add(ia)
            side[ia], side[ib] = "L", "R"
    for i, comp in enumerate(components):
        for b in comp:
            for term, net in block_by_id[b].get("terminals", {}).items():
                if term not in ("bulk", "substrate") and net in core_axis:
                    axes[i].add(core_axis[net])
                    hard[i] = True

    axis_parent: dict = {}
    for i, ax in enumerate(axes):
        linked = sorted(ax | {x for j in partners[i] for x in axes[j]})
        for x in linked[1:]:
            _union(axis_parent, linked[0], x)

    result = []
    for i, ax in enumerate(axes):
        if not ax:
            result.append(None)
            continue
        is_pair = len(partners[i]) == 1 and partners[next(iter(partners[i]))] == {i}
        if partners[i] and not is_pair:
            logger.warning("Component %s has %d partner components — kept self-symmetric",
                           components[i], len(partners[i]))
        partner = next(iter(partners[i])) if is_pair else None
        result.append({
            "axis_id": _find(axis_parent, min(ax)),
            "level":   "hard" if hard[i] or (is_pair and hard[partner]) else "soft",
            "role":    "pair" if is_pair else "self",
            "partner": partner,
            "side":    side[i] if is_pair else None,
        })
    return result


def _proximity_variants(block_ids: List[int], block_by_id: dict) -> List[dict]:
    """
    Standard-cell style layout of a digital block: P row above N row, devices left
    to right in role order, gaps from the PDK spacing rules between the types
    (spacing.compute_block_spacing — same rules the placers enforce).
    """
    def dims(bid: int) -> tuple[float, float]:
        variants = block_by_id[bid]["variants"]
        bb = next((v for v in variants if v.get("is_used")), variants[0])["main_bbox"]
        return bb["x_max"] - bb["x_min"], bb["y_max"] - bb["y_min"]

    rows = {"p": [b for b in block_ids if _polarity(block_by_id[b]) == "p"],
            "n": [b for b in block_ids if _polarity(block_by_id[b]) == "n"]}
    width, height = 0.0, 0.0
    for pol, row in rows.items():
        if not row:
            continue
        gap = compute_block_spacing(block_by_id[row[0]], block_by_id[row[0]]).x_spacing
        width = max(width, sum(dims(b)[0] for b in row) + gap * (len(row) - 1))
        height += max(dims(b)[1] for b in row)
    if rows["p"] and rows["n"]:
        height += compute_block_spacing(block_by_id[rows["p"][0]], block_by_id[rows["n"][0]]).y_spacing
    return [{
        "rows": 2 if rows["p"] and rows["n"] else 1,
        "cols_per_device": 1,
        "dummy_cols_per_side": 0,
        "dummy_rows_top_bottom": 0,
        "matching_type": "proximity",
        "width_um": round(width, 4),
        "height_um": round(height, 4),
    }]


def build_groups(
    sym_constraints: dict,
    all_blocks:      list,
    placement_config: dict,
) -> List[dict]:
    """
    Build the groups list from symmetry detection output and placement config.

    Active groups are matching components (building blocks + their merged pairs),
    split by (W, L, Nf) so the matching engine only sees compatible devices.
    Digital blocks, switches and (in mirrored mode) passives keep their pairs as two
    mirrored groups B / B' instead; their (W, L, Nf) sub-groups pair key by key.
    Digital blocks are proximity groups (mixed N/P, one standard-cell variant).

    Passive groups carry split_variants (powers of 2) so the placer can choose
    how many pieces to scatter or cluster.

    placement_config keys read here:
      enable_matching          bool  — compute matching_variants for active groups
      enable_passive_splitting bool  — emit passive groups with split_variants
      passive_max_split        int   — maximum split count (clipped to power-of-2 sequence)
      symmetry_mode            str   — passives are B / B' only in "mirrored"
    """
    enable_matching  = placement_config.get("enable_matching", True)
    enable_passive   = placement_config.get("enable_passive_splitting", True)
    max_split        = placement_config.get("passive_max_split", 8)
    sym_mode         = placement_config.get("symmetry_mode", "balanced")
    sym_mode         = LEGACY_SYM_MODES.get(sym_mode, sym_mode)

    block_by_id: dict = {b["block_id"]: b for b in all_blocks if "error" not in b}

    groups:      List[dict] = []
    grouped_bids: set[int]  = set()

    # ── Active groups: components, sub-groups per (W, L, Nf), symmetry roles ──
    components, bb_of, split, merged = _components(sym_constraints, block_by_id, sym_mode)
    symmetry = _component_symmetry(components, split, merged, sym_constraints, block_by_id)

    planned = []    # (component index, key, tag, block ids)
    for i, comp in enumerate(components):
        tags = {_TAG_OF_BB.get(bb_of.get(b), "paired_symmetric") for b in comp}
        tag  = next(t for t in _TAG_ORDER if t in tags)
        if tag in _PROXIMITY_TAGS:
            planned.append((i, None, tag, comp))
        else:
            for key, sub_bids in _split_by_device_characteristics(comp, block_by_id).items():
                planned.append((i, key, tag, sub_bids))
    gid_of = {(i, key): gid for gid, (i, key, _, _) in enumerate(planned)}

    for gid, (i, key, tag, sub_bids) in enumerate(planned):
        if tag in _PROXIMITY_TAGS:
            group = _build_active_group(gid, tag, sub_bids, block_by_id, False)
            group["matching_variants"] = _proximity_variants(sub_bids, block_by_id)
        else:
            group = _build_active_group(gid, tag, sub_bids, block_by_id, enable_matching)
        sym = dict(symmetry[i]) if symmetry[i] else None
        if sym and sym["role"] == "pair":
            sym["partner"] = gid_of.get((sym["partner"], key))
            if sym["partner"] is None:
                logger.warning("Group %d %s: no partner sub-group with the same W/L/Nf", gid, sub_bids)
                sym = None
        group["symmetry"] = sym
        groups.append(group)
        grouped_bids.update(sub_bids)
        logger.info("Active group %d: %s  blocks=%s  symmetry=%s", gid, tag, sub_bids, sym)
    group_id = len(planned)

    # ── Passive free groups ───────────────────────────────────────────────────
    if enable_passive:
        splits = _passive_split_variants(max_split)
        for blk in all_blocks:
            if "error" in blk:
                continue
            bid = blk["block_id"]
            if bid in grouped_bids:
                continue
            if not _is_passive_block(blk):
                continue
            groups.append({
                "group_id":      group_id,
                "topology_type": "passive_free",
                "block_ids":     [bid],
                "split_variants": splits,
                "ungroup": False,
            })
            grouped_bids.add(bid)
            logger.info(
                "Passive group %d: block %d (%s)  splits=%s",
                group_id, bid, blk.get("device_type", "?"), splits,
            )
            group_id += 1

    logger.info(
        "Hierarchy builder: %d groups total (%d blocks covered)",
        len(groups), len(grouped_bids),
    )
    return groups


# =============================================================================
# 5. COMPOSITE BLOCK BUILDER
# =============================================================================

# Composite block IDs start above this base to avoid collision with real device IDs
# (real device IDs are assigned sequentially from 0 by the block generator).
COMPOSITE_ID_BASE = 10_000

_POWER_NET_TYPES = frozenset({"power"})


def _parse_bid(pin_ref: str) -> int | None:
    """Extract block_id int from 'B<id>_<pin>' string; return None on failure."""
    if not pin_ref.startswith("B"):
        return None
    sep = pin_ref.find("_", 1)
    if sep < 0:
        return None
    try:
        return int(pin_ref[1:sep])
    except ValueError:
        return None


def _boundary_pins_for_group(nets: list, member_bids: set) -> list[tuple[str, str]]:
    """
    Return (pin_name, net_id) pairs for the boundary pins a composite group needs.

    Rules:
      - Power net (net_type=="power"): always → ("P0", net_id), one per group.
      - Signal/internal net with ≥1 pin outside the group
        OR with only 1 total connection (dangling input): → (net_id, net_id).
      - Signal/internal net where every connection belongs to ≥2 distinct
        member blocks with no outside blocks: internal-only → skip.
    """
    seen_power = False
    result: list[tuple[str, str]] = []
    for net in nets:
        net_id   = net.get("net_id", "")
        net_type = net.get("net_type", "signal")
        is_power = net_type in _POWER_NET_TYPES

        blocks_on_net: set[int] = set()
        for p in net.get("pins", []):
            bid = _parse_bid(p)
            if bid is not None:
                blocks_on_net.add(bid)

        member_blocks = blocks_on_net & member_bids
        if not member_blocks:
            continue  # net does not touch this composite at all

        outside_blocks = blocks_on_net - member_bids
        is_internal = (
            not is_power
            and len(outside_blocks) == 0
            and len(member_blocks) >= 2
        )

        if is_internal:
            continue

        if is_power:
            if not seen_power:
                result.append(("P0", net_id))
                seen_power = True
        else:
            result.append((net_id, net_id))

    return result


def build_composite_blocks(
    filtered_groups: List[dict],
    block_by_id:     dict,
    nets:            list | None = None,
) -> tuple:
    """
    Convert filtered placement groups into composite block dicts for the placer.

    Each group becomes one composite block whose variants come from the group's
    matching_variants.  The composite block carries a device_type field so
    compute_block_spacing() can assign the correct PDK clearance between groups.

    Returns
    -------
    composite_list : list[dict]
        Composite block dicts shaped like regular block dicts (block_id,
        device_type, variants, ...) — pass these directly to _build_blocks_dict.
    excluded_ids : set[int]
        Original block_ids that are now inside a composite.  Remove the
        corresponding individual blocks from the placer's effective block set.
    """
    composite_list: List[dict] = []
    excluded_ids:   set = set()

    for group in filtered_groups:
        group_id     = group.get("group_id", 0)
        member_bids  = group.get("block_ids", [])
        matching_mvs = group.get("matching_variants", [])
        intra_sp     = group.get("intra_spacing", {"x_um": 0.0, "y_um": 0.0})

        if not member_bids or not matching_mvs:
            continue

        # device_type for the spacing function: the member type, or all member
        # types joined (mixed digital block → worst-case spacing over them)
        member_types = sorted({block_by_id[b]["device_type"] for b in member_bids
                               if "device_type" in block_by_id.get(b, {})})
        device_type = MIXED_TYPE_SEP.join(member_types) or "unknown"

        # Determine power rail from member blocks (first non-None wins).
        power_rail: str | None = None
        for bid in member_bids:
            rail = (block_by_id.get(bid) or {}).get("power_rail")
            if rail:
                power_rail = rail
                break

        # Compute boundary pins when net information is available.
        if nets is not None:
            boundary_pins = _boundary_pins_for_group(nets, set(member_bids))
        else:
            boundary_pins = [("center", "center")]

        # Build variants from matching_variants; carry layout fields for
        # post-placement expansion back to individual device coordinates.
        variants: List[dict] = []
        for k, mv in enumerate(matching_mvs):
            w = float(mv.get("width_um",  0.0))
            h = float(mv.get("height_um", 0.0))

            # Pin positions: power pin at fixed top/bottom edge; signal pins at center.
            pin_positions: dict = {}
            for pname, _ in boundary_pins:
                if pname == "P0":
                    py = h if power_rail == "VDD" else 0.0
                    pin_positions["P0"] = {"x": w / 2.0, "y": py}
                else:
                    pin_positions[pname] = {"x": w / 2.0, "y": h / 2.0}

            variants.append({
                "main_bbox": {
                    "x_min": 0.0, "y_min": 0.0,
                    "x_max": w,   "y_max": h,
                },
                "is_used":        (k == 0),
                "rotation_deg":   mv.get("rotation_deg", 0),
                "pin_positions":  pin_positions,
                # Layout parameters needed for post-placement device expansion
                "rows":                  mv.get("rows", 1),
                "cols_per_device":       mv.get("cols_per_device", len(member_bids)),
                "dummy_cols_per_side":   mv.get("dummy_cols_per_side", 0),
                "dummy_rows_top_bottom": mv.get("dummy_rows_top_bottom", 0),
                "intra_spacing_x":       float(intra_sp.get("x_um", 0.0)),
                "intra_spacing_y":       float(intra_sp.get("y_um", 0.0)),
                # Metadata carried to output JSON for downstream consumers
                "matching_type":         mv.get("matching_type") or "",
                "width_um":              w,
                "height_um":             h,
            })
            if mv.get("routing"):       # routed 012 structure: pins = its access segments
                variants[-1]["routed"] = mv
                pin_access.attach(variants[-1], mv, {p: n for p, n in boundary_pins if p != "P0"})

        composite_id = COMPOSITE_ID_BASE + group_id
        composite_entry = {
            "block_id":        composite_id,
            "device_type":     device_type,
            "variants":        variants,
            "group_block_ids": list(member_bids),
            "group_id":        group_id,
            "topology_type":   group.get("topology_type", ""),
            # Standard block fields expected by pipeline components
            "num_pins":   len(boundary_pins),
            "power_rail": power_rail,
        }
        composite_list.append(composite_entry)
        excluded_ids.update(member_bids)
        logger.info(
            "Composite block %d ← group %d (%s)  members=%s  %d variant(s)",
            composite_id, group_id, group.get("topology_type", ""),
            member_bids, len(variants),
        )

    return composite_list, excluded_ids


def remap_nets_for_composites(
    nets:             list,
    composite_blocks: List[dict],
    block_by_id:      dict,  # kept for API symmetry, not used internally
) -> list:
    """
    Return a remapped net list where pin references belonging to composite-block
    members are replaced with a named pin on the composite block.

    Mapping rules per net:
      - Power net  → "B{composite_id}_P0"
      - Signal/internal net that crosses group boundary or is dangling
                   → "B{composite_id}_{net_id}"
      - Signal/internal net purely internal to one composite (≥2 distinct
        member blocks, no outside connections) → composite pin suppressed
        (member refs removed; net may have 0 pins if no outside connections)

    Multiple member pins from the same composite on one net → deduplicated
    (at most one composite pin reference per composite per net).
    """
    # Map original block_id (int) → composite block_id (int)
    bid_to_comp: dict = {}
    comp_member_sets: dict = {}   # comp_id → set of member block_ids
    for cb in composite_blocks:
        comp_id = cb["block_id"]
        members = {int(m) for m in cb.get("group_block_ids", [])}
        comp_member_sets[comp_id] = members
        for mbid in members:
            bid_to_comp[mbid] = comp_id

    if not bid_to_comp:
        return list(nets)

    remapped: List[dict] = []
    for net in nets:
        net_id   = net.get("net_id", "")
        is_power = net.get("net_type", "signal") in _POWER_NET_TYPES

        # Classify every pin as belonging to a composite or staying outside
        # comp_pins: comp_id → set of distinct member block_ids on this net
        comp_pins: dict[int, set] = {}
        outside_bids: set = set()
        for pin_ref in net.get("pins", []):
            bid = _parse_bid(pin_ref)
            if bid is None:
                outside_bids.add(pin_ref)   # non-standard ref — treat as outside
                continue
            comp_id = bid_to_comp.get(bid)
            if comp_id is None:
                outside_bids.add(bid)
            else:
                comp_pins.setdefault(comp_id, set()).add(bid)

        new_pins: List[str] = []

        # Keep outside pins unchanged
        for pin_ref in net.get("pins", []):
            bid = _parse_bid(pin_ref)
            if bid is None or bid_to_comp.get(bid) is None:
                new_pins.append(pin_ref)

        # For each composite that this net touches, decide whether to emit a pin
        for comp_id, member_bids_on_net in comp_pins.items():
            is_internal = (
                not is_power
                and len(outside_bids) == 0
                and len(comp_pins) == 1        # only this composite involved
                and len(member_bids_on_net) >= 2
            )
            if is_internal:
                continue  # net is local to this composite — no boundary pin

            pin_name = "P0" if is_power else net_id
            new_pins.append(f"B{comp_id}_{pin_name}")

        remapped.append({**net, "pins": new_pins})

    return remapped
