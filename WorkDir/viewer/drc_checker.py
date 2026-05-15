"""DRC checker — pure Python, no Qt dependencies.

Checks minimum spacing between placed main_bbox rectangles using topology
rules from a PDK JSON file (gpdk090_device_rules.json format).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from json_loader import PlacementData

# ---------------------------------------------------------------------------
# DRC category → (fill hex colour, alpha 0-255) used by placement_scene
# ---------------------------------------------------------------------------
DRC_CATEGORY_COLORS: dict[str, tuple[str, int]] = {
    "same_cellNames":         ("#FFFF44", 80),
    "same_deviceGroups":      ("#FFA500", 80),
    "different_cellNames":    ("#9B59B6", 80),
    "different_bulks":        ("#FF44FF", 80),
    "different_deviceGroups": ("#FF4444", 80),
    "physical_overlap":       ("#FF4444", 120),
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DRCRules:
    device_topology: dict   # {device_type: {"device_group": str, "bulk": str}}
    device_spacing: dict    # {device_type: {category: {"active": float, "poly": float}}}
    between_topologies: dict  # {category: {"active|WPE_active": float, ...}}


@dataclass
class DRCViolation:
    bid_a: int
    bid_b: int
    category: str    # topology key (same_cellNames, different_bulks, …) or "physical_overlap"
    direction: str   # "active" | "poly" | "overlap"
    required: float  # µm; negative = overlap allowed
    actual: float    # µm; positive = gap, negative = penetration depth
    bbox_a: tuple[float, float, float, float]   # JSON Y-up absolute coords (x0,y0,x1,y1)
    bbox_b: tuple[float, float, float, float]

    @property
    def display_str(self) -> str:
        if self.category == "physical_overlap":
            return (
                f"B{self.bid_a} <-> B{self.bid_b}: physical overlap "
                f"({self.direction}: depth {abs(self.actual):.3f} µm)"
            )
        return (
            f"B{self.bid_a} <-> B{self.bid_b}: {self.category} ({self.direction})"
            f"  required {self.required:.3f} µm,  actual {self.actual:.3f} µm"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rules(pdk_path: str | Path) -> DRCRules:
    """Load and validate a PDK rules JSON file.

    Raises:
        FileNotFoundError: if pdk_path does not exist.
        ValueError: if required sections are missing.
    """
    p = Path(pdk_path)
    if not p.exists():
        raise FileNotFoundError(f"PDK file not found: {p}")
    raw: dict = json.loads(p.read_text(encoding="utf-8"))

    missing = [k for k in ("device_topology", "device_spacing", "between_topologies")
               if k not in raw]
    if missing:
        raise ValueError(f"PDK file missing sections: {', '.join(missing)}")

    return DRCRules(
        device_topology=raw["device_topology"],
        device_spacing=raw["device_spacing"],
        between_topologies=raw["between_topologies"],
    )


def run_drc(data: PlacementData, rules: DRCRules) -> list[DRCViolation]:
    """Check spacing between every pair of placed blocks.

    Uses main_bbox from placement_result.placed_blocks — absolute µm coords in
    JSON Y-up space.  Returns violations sorted by (bid_a, bid_b).
    """
    pr = data.placement_result
    if pr is None or not pr.placed_blocks:
        return []

    # Build lookup: block_id → (bbox, device_type, rotation_deg)
    placed: dict[int, tuple] = {}
    for bid, pb in pr.placed_blocks.items():
        block = data.block_by_id(bid)
        if block is None:
            continue
        rot = _get_rotation(data, bid)
        placed[bid] = (pb.main_bbox, block.device_type, rot)

    bids = sorted(placed.keys())
    violations: list[DRCViolation] = []

    for i, bid_a in enumerate(bids):
        bbox_a, dt_a, rot_a = placed[bid_a]
        for bid_b in bids[i + 1:]:
            bbox_b, dt_b, rot_b = placed[bid_b]
            violations.extend(
                _check_pair(bid_a, bid_b, bbox_a, bbox_b, dt_a, dt_b, rot_a, rot_b, rules)
            )

    return violations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_rotation(data: PlacementData, block_id: int) -> int:
    block = data.block_by_id(block_id)
    if block is None:
        return 0
    try:
        return int(data.active_variant(block).rotation_deg)
    except Exception:
        return 0


def _classify_pair(
    dt_a: str, dt_b: str, rules: DRCRules
) -> tuple[str, str]:
    """Classify a block pair via the topology decision tree.

    Returns (section, category):
      section  = "device_spacing" or "between_topologies"
      category = the PDK rule key (e.g. "same_cellNames", "different_bulks")

    Same device type  → between_topologies / same_cellNames.
    Different types   → between_topologies, category determined by group/bulk.
    Unknown type      → between_topologies / different_deviceGroups (worst case).
    """
    if dt_a == dt_b:
        return ("between_topologies", "same_cellNames")

    topo = rules.device_topology
    info_a = topo.get(dt_a)
    info_b = topo.get(dt_b)

    if info_a is None or info_b is None:
        return ("between_topologies", "different_deviceGroups")

    group_a = info_a.get("device_group", "")
    group_b = info_b.get("device_group", "")
    bulk_a  = info_a.get("bulk", "")
    bulk_b  = info_b.get("bulk", "")

    if group_a != group_b:
        return ("between_topologies", "different_deviceGroups")
    if bulk_a != bulk_b:
        return ("between_topologies", "different_bulks")
    # Same group, same bulk, different device types → same_deviceGroups
    return ("between_topologies", "same_deviceGroups")


def _get_required_spacing(
    rules: DRCRules, dt_a: str, dt_b: str
) -> tuple[str, str, float, float]:
    """Return (section, category, req_active_µm, req_poly_µm)."""
    section, category = _classify_pair(dt_a, dt_b, rules)

    if section == "device_spacing":
        entry = rules.device_spacing.get(dt_a, {}).get(category, {})
        req_active = float(entry.get("active", 0.0))
        req_poly   = float(entry.get("poly",   0.0))
    else:
        entry = rules.between_topologies.get(category, {})
        if "WPE_active" in entry:
            req_active = float(entry["WPE_active"])
            req_poly   = float(entry["WPE_poly"])
        else:
            req_active = float(entry.get("active", 0.0))
            req_poly   = float(entry.get("poly",   0.0))

    return (section, category, req_active, req_poly)


def _check_pair(
    bid_a: int,
    bid_b: int,
    bbox_a: tuple[float, float, float, float],
    bbox_b: tuple[float, float, float, float],
    dt_a: str,
    dt_b: str,
    rot_a: int,
    rot_b: int,
    rules: DRCRules,
) -> list[DRCViolation]:
    """Check one block pair using the envelope-overlap / facing-edge model.

    Rotation convention: 0°≡180° and 90°≡270° (same spacing for opposite orientations).
    rot=0 : active=X, poly=Y.  rot=90: active=Y, poly=X.

    Non-diagonal pairs (only one axis has a gap):
      - Active edge check fires when blocks share a band along the poly axis.
      - Poly   edge check fires when blocks share a band along the active axis.

    Diagonal pairs (both axes have a gap):
      - Non-WPE categories: skipped (no facing edges).
      - WPE categories (different_bulks / different_deviceGroups): rectangular-well
        corner check — both axes tested independently, because the well boundary is
        rectangular and corner clearance must be enforced in each direction.
    """
    ax0, ay0, ax1, ay1 = bbox_a
    bx0, by0, bx1, by1 = bbox_b

    x_gap     = max(0.0, max(bx0 - ax1, ax0 - bx1))
    y_gap     = max(0.0, max(by0 - ay1, ay0 - by1))
    x_overlap = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    y_overlap = max(0.0, min(ay1, by1) - max(ay0, by0))

    violations: list[DRCViolation] = []

    # --- Physical overlap: bboxes penetrate in both axes simultaneously ------
    if x_overlap > 1e-9 and y_overlap > 1e-9:
        violations.append(DRCViolation(
            bid_a=bid_a, bid_b=bid_b,
            category="physical_overlap", direction="active",
            required=0.0, actual=-x_overlap,
            bbox_a=bbox_a, bbox_b=bbox_b,
        ))
        violations.append(DRCViolation(
            bid_a=bid_a, bid_b=bid_b,
            category="physical_overlap", direction="poly",
            required=0.0, actual=-y_overlap,
            bbox_a=bbox_a, bbox_b=bbox_b,
        ))
        return violations

    # Rotation normalisation: 0°≡180°, 90°≡270°
    rot_a = rot_a % 180
    rot_b = rot_b % 180

    # Axis mapping per rotation:
    # rot=0: active=X (S/D axis horizontal), poly=Y (channel-width axis vertical)
    # rot=90: active=Y, poly=X  (axes swapped)
    if rot_a == 90 and rot_b == 90:
        active_gap, poly_gap         = y_gap, x_gap
        active_overlap, poly_overlap = y_overlap, x_overlap
        faces_active = x_gap < 1e-9   # X-band shared → active edges face each other
        faces_poly   = y_gap < 1e-9
    else:
        # both rot=0, or mixed (treated as rot=0 — same axis convention)
        active_gap, poly_gap         = x_gap, y_gap
        active_overlap, poly_overlap = x_overlap, y_overlap
        faces_active = y_gap < 1e-9   # Y-band shared → active edges face each other
        faces_poly   = x_gap < 1e-9

    _, category, req_active, req_poly = _get_required_spacing(rules, dt_a, dt_b)

    is_wpe = category in {"different_bulks", "different_deviceGroups"}

    # --- Diagonal pair -------------------------------------------------------
    if x_gap > 1e-9 and y_gap > 1e-9:
        if not is_wpe:
            return violations  # no facing edges for non-WPE rules
        # Euclidean closest-point distance between the two rectangles.
        # Per-axis independent checks produce false positives: a large gap in one
        # dimension (e.g. 13 µm in Y) makes the real corner distance far exceed
        # the threshold even when the other gap is small.
        corner_dist = math.sqrt(active_gap ** 2 + poly_gap ** 2)
        req_corner = max(req_active, req_poly)  # conservative: largest axis threshold
        if req_corner >= 0.0 and corner_dist < req_corner - 1e-9:
            violations.append(DRCViolation(
                bid_a=bid_a, bid_b=bid_b,
                category=category, direction="corner",
                required=req_corner, actual=corner_dist,
                bbox_a=bbox_a, bbox_b=bbox_b,
            ))
        return violations

    # --- Non-diagonal: facing-edge checks ------------------------------------

    # Active direction (fires when blocks share a band along the poly axis)
    if faces_active:
        if req_active >= 0.0:
            if active_gap < req_active - 1e-9:
                violations.append(DRCViolation(
                    bid_a=bid_a, bid_b=bid_b,
                    category=category, direction="active",
                    required=req_active, actual=active_gap,
                    bbox_a=bbox_a, bbox_b=bbox_b,
                ))
        else:
            # Negative rule: controlled overlap allowed; violation if depth exceeds limit
            allowed = abs(req_active)
            if active_overlap > allowed + 1e-9:
                violations.append(DRCViolation(
                    bid_a=bid_a, bid_b=bid_b,
                    category=category, direction="active",
                    required=req_active, actual=-active_overlap,
                    bbox_a=bbox_a, bbox_b=bbox_b,
                ))

    # Poly direction (fires when blocks share a band along the active axis)
    if faces_poly:
        if req_poly >= 0.0:
            if poly_gap < req_poly - 1e-9:
                violations.append(DRCViolation(
                    bid_a=bid_a, bid_b=bid_b,
                    category=category, direction="poly",
                    required=req_poly, actual=poly_gap,
                    bbox_a=bbox_a, bbox_b=bbox_b,
                ))
        else:
            allowed = abs(req_poly)
            if poly_overlap > allowed + 1e-9:
                violations.append(DRCViolation(
                    bid_a=bid_a, bid_b=bid_b,
                    category=category, direction="poly",
                    required=req_poly, actual=-poly_overlap,
                    bbox_a=bbox_a, bbox_b=bbox_b,
                ))

    return violations
