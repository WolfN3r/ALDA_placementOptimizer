#!/usr/bin/env python3
"""
Build the 'groups' layer from symmetry detection output.

Consumes: symmetry_constraints (from detect_symmetries), all_blocks (list of
block dicts), and placement_config.  Produces a groups list where each group
is a matched active topology or a splittable passive cluster.  Groups are the
primary placement units in the hierarchical optimizer pass.
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

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_PASSIVE_DEVICE_PREFIXES = ("res_", "cap_")

# Powers-of-2 split counts generated for passive groups.
# The placer selects one split count; all others are alternatives.
_PASSIVE_SPLIT_SEQUENCE = [1, 2, 4, 8, 16]

# Symmetry mode values accepted in placement_config
_SYM_MODE_NONE       = "none"
_SYM_MODE_MODERATE   = "moderate"
_SYM_MODE_AGGRESSIVE = "aggressive"

# Topology tags that are included in "moderate" symmetry mode
_MODERATE_TAGS = frozenset({"diff_pair", "current_mirror", "tail_cm_pair"})

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _is_passive_block(blk: dict) -> bool:
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


_COMPOUND_TYPE_MAP: dict[str, str] = {
    "diff_pair":      "diff_pair",
    "current_mirror": "current_mirror",
    "cascode":        "cascode_current_mirror",
}


def _split_by_device_characteristics(bids: list, block_by_id: dict) -> list:
    """
    Split block IDs into sub-lists where every element shares the same W, L, Nf.
    Transistors with different W, L, or Nf cannot be physically co-matched, so
    they must form separate groups. M (multiplier) may differ within a sub-list;
    compute_matching_variants() handles that by summing M_i.
    """
    sub_groups: dict = {}
    for bid in bids:
        params = block_by_id.get(bid, {}).get("parameters", {})
        key = (
            round(float(params.get("width", 0.0)), 4),
            round(float(params.get("length", 0.0)), 4),
            int(params.get("num_fingers", 1)),
        )
        sub_groups.setdefault(key, []).append(bid)
    return list(sub_groups.values())


def build_groups(
    sym_constraints: dict,
    all_blocks:      list,
    placement_config: dict,
) -> List[dict]:
    """
    Build the groups list from symmetry detection output and placement config.

    Active groups come from compound_blocks (individual building blocks from
    Phase 1): one diff pair, one mirror group, or one cascode per group.
    This gives the correct granularity for matched-array computation.

    Passive groups carry split_variants (powers of 2) so the placer can choose
    how many pieces to scatter or cluster.

    placement_config keys read here:
      enable_matching          bool  — compute matching_variants for active groups
      enable_passive_splitting bool  — emit passive groups with split_variants
      passive_max_split        int   — maximum split count (clipped to power-of-2 sequence)
    """
    enable_matching  = placement_config.get("enable_matching", True)
    enable_passive   = placement_config.get("enable_passive_splitting", True)
    max_split        = placement_config.get("passive_max_split", 8)

    block_by_id: dict = {b["block_id"]: b for b in all_blocks if "error" not in b}

    groups:      List[dict] = []
    grouped_bids: set[int]  = set()
    group_id = 0

    # ── Active groups from compound_blocks (per-building-block granularity) ───
    # compound_blocks gives one entry per Phase-1 topology (diff pair, mirror,
    # cascode), which is the right granularity for matched array computation.
    # The Union-Find compound groups (sym_constraints["groups"]) merge everything
    # onto a shared axis and are used by the optimizer for symmetry enforcement,
    # not for defining matched structures.
    for cb in sym_constraints.get("compound_blocks", []):
        raw_tag  = cb.get("group_type", "current_mirror")
        tag      = _COMPOUND_TYPE_MAP.get(raw_tag, raw_tag)
        all_bids = cb.get("child_block_ids", [])
        if not all_bids:
            continue

        # Split by (W, L, Nf) so the matching engine only sees compatible devices.
        # M may differ within a sub-group; compute_matching_variants() sums M_i.
        for sub_bids in _split_by_device_characteristics(all_bids, block_by_id):
            groups.append(_build_active_group(group_id, tag, sub_bids, block_by_id, enable_matching))
            grouped_bids.update(sub_bids)
            logger.info("Active group %d: %s  blocks=%s", group_id, tag, sub_bids)
            group_id += 1

    # ── Tail-CM pair groups ───────────────────────────────────────────────────
    # Each tail transistor paired with its Vbias current mirror reference
    claimed_in_tail_cm: set[int] = set()
    for tail_bid, mirror_bid in sym_constraints.get("tail_cm_pairs", []):
        if tail_bid in claimed_in_tail_cm or mirror_bid in claimed_in_tail_cm:
            continue
        # Skip if either block was already claimed by a compound_block group
        # (e.g. a tail transistor already in a current_mirror group).
        if tail_bid in grouped_bids or mirror_bid in grouped_bids:
            logger.info(
                "Tail-CM pair [%d, %d] skipped — blocks already grouped",
                tail_bid, mirror_bid,
            )
            continue
        bids = sorted({tail_bid, mirror_bid})
        groups.append(
            _build_active_group(group_id, "tail_cm_pair", bids, block_by_id, enable_matching)
        )
        grouped_bids.update(bids)
        claimed_in_tail_cm.update(bids)
        logger.info("Tail-CM group %d: blocks=%s", group_id, bids)
        group_id += 1

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


def filter_groups_for_sym_mode(groups: List[dict], sym_mode: str) -> List[dict]:
    """
    Return the subset of groups that should be enforced in placement given the
    requested symmetry mode.

    none       — return empty list (no group constraints passed to placer)
    moderate   — return only diff-pair, current-mirror, and tail-CM groups
    aggressive — return all groups unchanged
    """
    if sym_mode == _SYM_MODE_NONE:
        return []
    if sym_mode == _SYM_MODE_MODERATE:
        return [g for g in groups if g.get("topology_type") in _MODERATE_TAGS]
    # aggressive (default)
    return list(groups)


def filter_sym_constraints_for_mode(
    sym_constraints: dict,
    sym_mode: str,
) -> dict:
    """
    Return an effective symmetry_constraints dict filtered to the given mode.

    The returned dict has the same schema as the original but with 'groups'
    filtered to only the topologies relevant for sym_mode.
    """
    if sym_mode == _SYM_MODE_AGGRESSIVE:
        return sym_constraints

    effective_tags = set() if sym_mode == _SYM_MODE_NONE else _MODERATE_TAGS
    filtered_groups = [
        g for g in sym_constraints.get("groups", [])
        if g.get("topology_tag", "") in effective_tags
    ]
    return {**sym_constraints, "groups": filtered_groups}


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

        # device_type from the first available member (for spacing function)
        device_type = "unknown"
        for bid in member_bids:
            blk = block_by_id.get(bid)
            if blk and "device_type" in blk:
                device_type = blk["device_type"]
                break

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

        composite_id = COMPOSITE_ID_BASE + group_id
        composite_list.append({
            "block_id":        composite_id,
            "device_type":     device_type,
            "variants":        variants,
            "group_block_ids": list(member_bids),
            "group_id":        group_id,
            "topology_type":   group.get("topology_type", ""),
            # Standard block fields expected by pipeline components
            "num_pins":   len(boundary_pins),
            "power_rail": power_rail,
        })
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
