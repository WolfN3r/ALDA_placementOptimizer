"""
Universal placement cost evaluator — topology-agnostic.

CostEvaluator.evaluate(positions, variant_map=None) → float
Works on any {block_id: (x, y)} dict produced by any topology.
"""
from __future__ import annotations

from dataclasses import dataclass


# =============================================================================
# CONSTANTS
# =============================================================================
_DEFAULT_AREA_WEIGHT   = 0.1
_DEFAULT_WL_WEIGHT     = 0.0
_DEFAULT_AR_WEIGHT     = 0.9
_DEFAULT_TARGET_AR     = 5.0

_VDD_NET_IDS: frozenset[str] = frozenset({"VDD", "AVDD", "VCC", "VDDA"})
_VSS_NET_IDS: frozenset[str] = frozenset({"VSS", "GND", "AGND", "VSSA"})


# =============================================================================
# VARIANT RESOLUTION
# =============================================================================

def resolve_variant(block: dict, bid: str, variant_map: dict[str, int]) -> dict:
    """Return the variant dict a block is actually using.

    Prefers variant_map[bid] — the optimizer's live, per-candidate selection —
    since a composite/grouped block's static `is_used` flag is frozen to
    variant 0 at construction time (hierarchy_builder.build_composite_blocks)
    and never reflects what the topology later selects during search. Falls
    back to `is_used`/variants[0] only when bid has no entry in variant_map
    (individual blocks, or pre-search callers with no variant_map yet).
    """
    variants = block.get("variants", [])
    idx = variant_map.get(bid)
    if idx is not None and 0 <= idx < len(variants):
        return variants[idx]
    for v in variants:
        if v.get("is_used"):
            return v
    return variants[0] if variants else {}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CostWeights:
    area_weight:               float = _DEFAULT_AREA_WEIGHT
    wirelength_weight:         float = _DEFAULT_WL_WEIGHT
    aspect_ratio_weight:       float = _DEFAULT_AR_WEIGHT
    target_aspect_ratio:       float = _DEFAULT_TARGET_AR


# =============================================================================
# EVALUATOR
# =============================================================================

class CostEvaluator:
    """
    Scores a decoded placement.

    cost = W_area × (bbox_area / init_area)
         + W_wl   × (hpwl / init_wl)          [skipped when init_wl == 0]
         + W_ar   × (aspect_ratio − target_ar)²

    Normalization by init_area and init_wl is mandatory — without it the area
    term (O(10⁴ µm²)) overwhelms the AR term (O(1)) and SA cannot be calibrated.
    """

    def __init__(
        self,
        blocks:          dict,
        nets:            list,
        init_area:       float,
        init_wl:         float,
        weights:         CostWeights | None = None,
        use_power_rails: bool = True,
    ) -> None:
        self._blocks          = blocks
        self._nets            = nets
        self._init_area       = init_area
        self._init_wl         = init_wl
        self._w               = weights or CostWeights()
        self._use_power_rails = use_power_rails

    # ------------------------------------------------------------------
    def evaluate(
        self,
        positions: dict[str, tuple[float, float]],
        variant_map: dict[str, int] | None = None,
    ) -> float:
        """Compute normalized cost for a decoded placement.

        variant_map should be the topology's current get_variant_map() —
        the live, per-candidate variant selection for composite/grouped
        blocks. Without it, composite blocks fall back to their frozen
        construction-time is_used flag (see resolve_variant()).
        """
        vm   = variant_map or {}
        area = self._bbox_area(positions, vm)
        wl   = self._hpwl(positions, vm)
        ar   = self._aspect_ratio(positions, vm)

        cost  = self._w.area_weight * (area / self._init_area)
        if self._init_wl > 0.0:
            cost += self._w.wirelength_weight * (wl / self._init_wl)
        if self._w.aspect_ratio_weight > 0.0:
            cost += self._w.aspect_ratio_weight * (ar - self._w.target_aspect_ratio) ** 2
        return cost

    # ------------------------------------------------------------------
    # Internal cost terms
    # ------------------------------------------------------------------

    def _bbox_area(
        self, positions: dict[str, tuple[float, float]], variant_map: dict[str, int]
    ) -> float:
        if not positions:
            return 0.0
        xs = [x for x, _ in positions.values()]
        ys = [y for _, y in positions.values()]
        x_spans = []
        y_spans = []
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block, bid, variant_map)
            w = variant.get("main_bbox", {}).get("x_max", 0.0)
            h = variant.get("main_bbox", {}).get("y_max", 0.0)
            x_spans.append(bx + w)
            y_spans.append(by + h)
        x_min = min(xs)
        y_min = min(ys)
        x_max = max(x_spans)
        y_max = max(y_spans)
        return max(0.0, x_max - x_min) * max(0.0, y_max - y_min)

    def _hpwl(
        self, positions: dict[str, tuple[float, float]], variant_map: dict[str, int]
    ) -> float:
        """Half-perimeter wirelength summed over all nets."""
        total = 0.0
        pin_pos = self._build_pin_positions(positions, variant_map)
        if self._use_power_rails:
            y_top, y_bot = self._rail_bounds(positions, variant_map)
        for net in self._nets:
            pins = net.get("pins", [])
            xs = [pin_pos[p][0] for p in pins if p in pin_pos]
            ys = [pin_pos[p][1] for p in pins if p in pin_pos]
            if self._use_power_rails and ys:
                nid = net.get("net_id", "").upper()
                if nid in _VDD_NET_IDS:
                    # Rail is a full-width horizontal strip: every pin on the net
                    # drops straight to it at its own x, independently of every
                    # other pin — so each pin (e.g. a device's bulk *and* source,
                    # both tied to VDD) contributes its own vertical distance,
                    # rather than the net sharing one bounding-box span.
                    total += sum(y_top - py for py in ys)
                    continue
                elif nid in _VSS_NET_IDS:
                    total += sum(py - y_bot for py in ys)
                    continue
            if len(xs) >= 2:
                total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return total

    def _aspect_ratio(
        self, positions: dict[str, tuple[float, float]], variant_map: dict[str, int]
    ) -> float:
        if not positions:
            return 1.0
        xs, ys, x_ends, y_ends = [], [], [], []
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block, bid, variant_map)
            w = variant.get("main_bbox", {}).get("x_max", 0.0)
            h = variant.get("main_bbox", {}).get("y_max", 0.0)
            xs.append(bx);    ys.append(by)
            x_ends.append(bx + w); y_ends.append(by + h)
        width  = max(x_ends) - min(xs)
        height = max(y_ends) - min(ys)
        if height == 0.0:
            return float("inf")
        return width / height

    def _rail_bounds(
        self, positions: dict[str, tuple[float, float]], variant_map: dict[str, int]
    ) -> tuple[float, float]:
        y_tops, y_bots = [], []
        for bid, (_, by) in positions.items():
            block = self._blocks.get(bid, {})
            h = self._active_variant(block, bid, variant_map).get("main_bbox", {}).get("y_max", 0.0)
            y_tops.append(by + h)
            y_bots.append(by)
        return max(y_tops), min(y_bots)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _active_variant(block: dict, bid: str, variant_map: dict[str, int]) -> dict:
        return resolve_variant(block, bid, variant_map)

    def _build_pin_positions(
        self,
        positions: dict[str, tuple[float, float]],
        variant_map: dict[str, int],
    ) -> dict[str, tuple[float, float]]:
        """Map pin name → absolute (x, y) based on block placement positions."""
        pin_pos: dict[str, tuple[float, float]] = {}
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block, bid, variant_map)
            for pname, pcoord in variant.get("pin_positions", {}).items():
                key = f"B{bid}_{pname}"
                pin_pos[key] = (bx + pcoord["x"], by + pcoord["y"])
        return pin_pos
