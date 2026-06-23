"""
Universal placement cost evaluator — topology-agnostic.

CostEvaluator.evaluate(positions) → float
Works on any {block_id: (x, y)} dict produced by any topology.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


# =============================================================================
# CONSTANTS
# =============================================================================
_DEFAULT_AREA_WEIGHT   = 0.6
_DEFAULT_WL_WEIGHT     = 0.4
_DEFAULT_AR_WEIGHT     = 0.0
_DEFAULT_TARGET_AR     = 2.0

_VDD_NET_IDS: frozenset[str] = frozenset({"VDD", "AVDD", "VCC", "VDDA"})
_VSS_NET_IDS: frozenset[str] = frozenset({"VSS", "GND", "AGND", "VSSA"})


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CostWeights:
    area_weight:               float = _DEFAULT_AREA_WEIGHT
    wirelength_weight:         float = _DEFAULT_WL_WEIGHT
    aspect_ratio_weight:       float = _DEFAULT_AR_WEIGHT
    target_aspect_ratio:       float = _DEFAULT_TARGET_AR
    device_clustering_weight:  float = 0.0


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
    def evaluate(self, positions: dict[str, tuple[float, float]]) -> float:
        """Compute normalized cost for a decoded placement."""
        area = self._bbox_area(positions)
        wl   = self._hpwl(positions)
        ar   = self._aspect_ratio(positions)

        cost  = self._w.area_weight * (area / self._init_area)
        if self._init_wl > 0.0:
            cost += self._w.wirelength_weight * (wl / self._init_wl)
        if self._w.aspect_ratio_weight > 0.0:
            cost += self._w.aspect_ratio_weight * (ar - self._w.target_aspect_ratio) ** 2
        if self._w.device_clustering_weight > 0.0:
            cost += self._w.device_clustering_weight * self._clustering_penalty(positions)
        return cost

    # ------------------------------------------------------------------
    # Internal cost terms
    # ------------------------------------------------------------------

    def _bbox_area(self, positions: dict[str, tuple[float, float]]) -> float:
        if not positions:
            return 0.0
        xs = [x for x, _ in positions.values()]
        ys = [y for _, y in positions.values()]
        x_spans = []
        y_spans = []
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block)
            w = variant.get("main_bbox", {}).get("x_max", 0.0)
            h = variant.get("main_bbox", {}).get("y_max", 0.0)
            x_spans.append(bx + w)
            y_spans.append(by + h)
        x_min = min(xs)
        y_min = min(ys)
        x_max = max(x_spans)
        y_max = max(y_spans)
        return max(0.0, x_max - x_min) * max(0.0, y_max - y_min)

    def _hpwl(self, positions: dict[str, tuple[float, float]]) -> float:
        """Half-perimeter wirelength summed over all nets."""
        total = 0.0
        pin_pos = self._build_pin_positions(positions)
        if self._use_power_rails:
            y_top, y_bot = self._rail_bounds(positions)
        for net in self._nets:
            pins = net.get("pins", [])
            xs = [pin_pos[p][0] for p in pins if p in pin_pos]
            ys = [pin_pos[p][1] for p in pins if p in pin_pos]
            if self._use_power_rails and xs:
                nid = net.get("net_id", "").upper()
                if nid in _VDD_NET_IDS:
                    # Rail is a horizontal line at y_top — x routing is only between
                    # actual pins (any point on the line matches the pin's x).
                    # Single-pin blocks still contribute their y-distance to the rail.
                    x_span = (max(xs) - min(xs)) if len(xs) >= 2 else 0.0
                    y_span = y_top - min(ys)
                    total += x_span + y_span
                    continue
                elif nid in _VSS_NET_IDS:
                    x_span = (max(xs) - min(xs)) if len(xs) >= 2 else 0.0
                    y_span = max(ys) - y_bot
                    total += x_span + y_span
                    continue
            if len(xs) >= 2:
                total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return total

    def _aspect_ratio(self, positions: dict[str, tuple[float, float]]) -> float:
        if not positions:
            return 1.0
        xs, ys, x_ends, y_ends = [], [], [], []
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block)
            w = variant.get("main_bbox", {}).get("x_max", 0.0)
            h = variant.get("main_bbox", {}).get("y_max", 0.0)
            xs.append(bx);    ys.append(by)
            x_ends.append(bx + w); y_ends.append(by + h)
        width  = max(x_ends) - min(xs)
        height = max(y_ends) - min(ys)
        if height == 0.0:
            return float("inf")
        return width / height

    def _rail_bounds(self, positions: dict[str, tuple[float, float]]) -> tuple[float, float]:
        y_tops, y_bots = [], []
        for bid, (_, by) in positions.items():
            h = self._active_variant(self._blocks.get(bid, {})).get("main_bbox", {}).get("y_max", 0.0)
            y_tops.append(by + h)
            y_bots.append(by)
        return max(y_tops), min(y_bots)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _active_variant(block: dict) -> dict:
        for v in block.get("variants", []):
            if v.get("is_used"):
                return v
        variants = block.get("variants", [])
        return variants[0] if variants else {}

    def _clustering_penalty(self, positions: dict[str, tuple[float, float]]) -> float:
        """HPWL of each device-type group's bounding box, summed and normalised by init_wl.

        Penalises layouts where blocks of the same type (e.g. nmos_lvt, pmos_rvt)
        are spread far apart, driving the optimiser to cluster them spatially.
        Single-instance types are skipped (bounding box is always zero).
        """
        type_xs: dict[str, list[float]] = defaultdict(list)
        type_ys: dict[str, list[float]] = defaultdict(list)
        for bid, (bx, by) in positions.items():
            dt = self._blocks.get(bid, {}).get("device_type", "")
            if not dt:
                continue
            variant = self._active_variant(self._blocks.get(bid, {}))
            bw = variant.get("main_bbox", {}).get("x_max", 0.0)
            bh = variant.get("main_bbox", {}).get("y_max", 0.0)
            type_xs[dt].append(bx + bw / 2.0)
            type_ys[dt].append(by + bh / 2.0)
        total = 0.0
        for dt in type_xs:
            xs, ys = type_xs[dt], type_ys[dt]
            if len(xs) < 2:
                continue
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return total / self._init_wl if self._init_wl > 0.0 else 0.0

    def _build_pin_positions(
        self, positions: dict[str, tuple[float, float]]
    ) -> dict[str, tuple[float, float]]:
        """Map pin name → absolute (x, y) based on block placement positions."""
        pin_pos: dict[str, tuple[float, float]] = {}
        for bid, (bx, by) in positions.items():
            block = self._blocks.get(bid, {})
            variant = self._active_variant(block)
            for pname, pcoord in variant.get("pin_positions", {}).items():
                key = f"B{bid}_{pname}"
                pin_pos[key] = (bx + pcoord["x"], by + pcoord["y"])
        return pin_pos
