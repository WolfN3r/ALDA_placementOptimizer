"""Scene that renders the full floorplan placement."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsPolygonItem,
)
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF
from PyQt6.QtCore import Qt, QPointF, pyqtSignal

from drc_checker import DRCViolation, DRC_CATEGORY_COLORS

from json_loader import PlacementData, PlacementResult
from layer_manager import LayerManager

_POWER_COLORS: dict[str, QColor] = {
    "VDD": QColor("#FF5555"),
    "VSS": QColor("#5588FF"),
}
_SIGNAL_COLOR = QColor("#44CC44")


def _pen(color: QColor, width: float = 0.1, cosmetic: bool = False) -> QPen:
    p = QPen(color)
    p.setWidthF(width)
    p.setCosmetic(cosmetic)
    return p


class PlacementScene(QGraphicsScene):
    """Full-chip placement view: blocks at absolute positions + net ratsnest.

    Coordinate convention:
      JSON uses Y-up (y=0 at bottom of chip).
      Qt scene uses Y-down (y=0 at top).
      Conversion: scene_y = H - json_y  where H = max placed y_max.
    """

    block_selected = pyqtSignal(object)  # int bid when a block rect is clicked, None on deselect

    def __init__(self, data: PlacementData, lm: LayerManager) -> None:
        super().__init__()
        self.setBackgroundBrush(QBrush(QColor("#1A1A1A")))
        self._data = data
        self._lm = lm
        self._net_items: list = []
        self._drc_items: list[QGraphicsItem] = []
        self._by_layer: dict[str, list] = {}
        self._nets_enabled = True
        self._H = 0.0
        self._block_rects: dict[int, QGraphicsRectItem] = {}

        pr = data.placement_result
        if pr and pr.placed_blocks:
            self._H = max(pb.main_bbox[3] for pb in pr.placed_blocks.values())
            self._build(pr)

        lm.register_callback(self._on_layer_toggle)
        lm.register_render_callback(self._refresh_block_styles)
        self.selectionChanged.connect(self._on_selection_changed)

    # ---- helpers ------------------------------------------------------------

    def _sy(self, json_y: float) -> float:
        return self._H - json_y

    def _add(self, item, layer: str) -> None:
        """Add item to scene, set initial visibility from layer manager, and track by layer."""
        item.setVisible(self._lm.is_visible(layer))
        self.addItem(item)
        self._by_layer.setdefault(layer, []).append(item)

    # ---- build scene --------------------------------------------------------

    def _build(self, pr: PlacementResult) -> None:
        x_max = max(pb.main_bbox[2] for pb in pr.placed_blocks.values())

        # Chip-level power rails (drawn first so blocks render on top)
        self._build_chip_rails(pr)

        # Floorplan outline
        outline = QGraphicsRectItem(0, 0, x_max, self._H)
        outline.setPen(_pen(QColor(90, 90, 90), 0.25))
        outline.setBrush(QBrush(Qt.GlobalColor.transparent))
        self._add(outline, "annotation")

        for bid, pb in pr.placed_blocks.items():
            block = self._data.block_by_id(bid)
            x0, y0, x1, y1 = pb.main_bbox
            w, h = x1 - x0, y1 - y0
            sx = x0
            sy = self._sy(y1)   # scene top = JSON y_max (flipped)

            # Block fill rectangle
            rect = QGraphicsRectItem(sx, sy, w, h)
            fill   = self._lm.block_fill(block.device_type)   if block else QColor(80, 80, 120)
            border = self._lm.block_border(block.device_type) if block else QColor(120, 120, 200)
            rect.setBrush(QBrush(fill))
            rect.setPen(_pen(border, self._lm.border_width))
            rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            rect.setData(0, bid)
            self._add(rect, "annotation")
            self._block_rects[bid] = rect

            # Block label
            lbl = QGraphicsTextItem(f"B{bid}")
            f = QFont("Monospace")
            f.setPointSizeF(max(min(w, h) * 0.18, 0.25))
            lbl.setFont(f)
            lbl.setDefaultTextColor(QColor(220, 220, 220))
            br = lbl.boundingRect()
            lbl.setPos(sx + w / 2 - br.width() / 2, sy + h / 2 - br.height() / 2)
            self._add(lbl, "labels")

            # Pin shapes — rectangle (new format) or dot fallback (old format)
            DOT_R = max(w, h) * 0.03
            for pname, pdata in pb.pins.items():
                if "x_min" in pdata:
                    # New M1 rectangle format
                    rx0 = float(pdata["x_min"])
                    rx1 = float(pdata["x_max"])
                    ry0 = float(pdata["y_min"])
                    ry1 = float(pdata["y_max"])
                    pin_type = pdata.get("type", "signal")
                    if pin_type == "power":
                        side = pdata.get("side", "top")
                        col = _POWER_COLORS.get("VDD" if side == "top" else "VSS", QColor(220, 100, 100))
                    else:
                        col = _SIGNAL_COLOR
                    fill = QColor(col.red(), col.green(), col.blue(), 90)
                    scene_top = self._sy(ry1)   # JSON y_max → scene top (Y-flip)
                    pin_item = QGraphicsRectItem(rx0, scene_top, rx1 - rx0, ry1 - ry0)
                    pin_item.setPen(_pen(col, 0.02))
                    pin_item.setBrush(QBrush(fill))
                    net_name = pdata.get("net", "")
                    if net_name:
                        pin_item.setToolTip(f"{pname}: {net_name}")
                    self._add(pin_item, "annotation")
                else:
                    # Old center-point format — dot fallback
                    px = float(pdata.get("x", 0.0))
                    py = float(pdata.get("y", 0.0))
                    dot = QGraphicsEllipseItem(
                        px - DOT_R, self._sy(py) - DOT_R, 2 * DOT_R, 2 * DOT_R
                    )
                    dot.setBrush(QBrush(QColor(255, 200, 50)))
                    dot.setPen(QPen(Qt.PenStyle.NoPen))
                    self._add(dot, "annotation")

        self._build_nets(pr)
        self._build_symmetry(pr, x_max)

    def _build_symmetry(self, pr: PlacementResult, x_max: float) -> None:
        sc = self._data.symmetry_constraints
        if not sc:
            return

        color = self._lm.layer("symmetry").color
        all_self_sym: list[int] = []

        axis_pen = QPen(color)
        axis_pen.setCosmetic(True)
        axis_pen.setWidthF(1.5)
        axis_pen.setStyle(Qt.PenStyle.DashLine)

        pair_pen = QPen(color)
        pair_pen.setCosmetic(True)
        pair_pen.setWidthF(1.0)

        for g in sc.get("groups", []):
            # Normalise pair format: old=[{"block_a":a,"block_b":b}], new=[[a,b]]
            group_pairs: list[tuple[int, int]] = []
            for p in g.get("pairs", []):
                if isinstance(p, dict):
                    group_pairs.append((int(p["block_a"]), int(p["block_b"])))
                else:
                    group_pairs.append((int(p[0]), int(p[1])))

            for s in g.get("self_symmetric", []):
                all_self_sym.append(int(s))

            # Axis position derived from this group's pairs only (each group is independent)
            global_axis = sc.get("symmetry_axis", "vertical")
            axis_dir = g.get("axis", global_axis)
            placed = [(a, b) for a, b in group_pairs
                      if a in pr.placed_blocks and b in pr.placed_blocks]
            if not placed:
                continue

            if axis_dir == "horizontal":
                # Horizontal axis: midpoint in Y (JSON Y-up → scene Y-down via _sy)
                midpoints = [
                    (self._sy((pr.placed_blocks[a].main_bbox[1] + pr.placed_blocks[a].main_bbox[3]) / 2)
                     + self._sy((pr.placed_blocks[b].main_bbox[1] + pr.placed_blocks[b].main_bbox[3]) / 2)) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                axis_line = QGraphicsLineItem(0, axis_pos, x_max, axis_pos)
            else:
                # Vertical axis: midpoint in X
                midpoints = [
                    ((pr.placed_blocks[a].main_bbox[0] + pr.placed_blocks[a].main_bbox[2]) / 2
                     + (pr.placed_blocks[b].main_bbox[0] + pr.placed_blocks[b].main_bbox[2]) / 2) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                axis_line = QGraphicsLineItem(axis_pos, 0, axis_pos, self._H)

            # One dashed axis line per group
            axis_line.setPen(axis_pen)
            axis_line.setZValue(50)
            self._add(axis_line, "symmetry")

            # Center-to-center connector for each pair in this group
            for a, b in group_pairs:
                if a not in pr.placed_blocks or b not in pr.placed_blocks:
                    continue
                ba, bb = pr.placed_blocks[a].main_bbox, pr.placed_blocks[b].main_bbox
                cx_a = (ba[0] + ba[2]) / 2
                cy_a = self._sy((ba[1] + ba[3]) / 2)
                cx_b = (bb[0] + bb[2]) / 2
                cy_b = self._sy((bb[1] + bb[3]) / 2)
                line = QGraphicsLineItem(cx_a, cy_a, cx_b, cy_b)
                line.setPen(pair_pen)
                line.setZValue(50)
                self._add(line, "symmetry")

        # Self-symmetric block markers — × cross at block center
        cross_pen = QPen(color)
        cross_pen.setCosmetic(True)
        cross_pen.setWidthF(1.2)
        for s in all_self_sym:
            if s not in pr.placed_blocks:
                continue
            bb = pr.placed_blocks[s].main_bbox
            cx = (bb[0] + bb[2]) / 2
            cy = self._sy((bb[1] + bb[3]) / 2)
            arm = min(bb[2] - bb[0], bb[3] - bb[1]) * 0.18
            for dx, dy, ex, ey in [(-arm, 0, arm, 0), (0, -arm, 0, arm)]:
                c = QGraphicsLineItem(cx + dx, cy + dy, cx + ex, cy + ey)
                c.setPen(cross_pen)
                c.setZValue(50)
                self._add(c, "symmetry")

    def _build_chip_rails(self, pr: PlacementResult) -> None:
        """Render chip-level VDD/VSS power rail rectangles outside the placement."""
        for rail_dict in getattr(pr, "chip_power_rails", []):
            rx0 = float(rail_dict.get("x_min", 0))
            rx1 = float(rail_dict.get("x_max", 0))
            ry0 = float(rail_dict.get("y_min", 0))
            ry1 = float(rail_dict.get("y_max", 0))
            net = str(rail_dict.get("net", "")).upper()
            col = _POWER_COLORS.get("VDD" if "VDD" in net or net in ("VDDA", "AVDD", "VCC") else "VSS",
                                    QColor(180, 100, 100))
            fill = QColor(col.red(), col.green(), col.blue(), 120)
            scene_top = self._sy(ry1)
            item = QGraphicsRectItem(rx0, scene_top, rx1 - rx0, ry1 - ry0)
            item.setPen(_pen(col, 0.04))
            item.setBrush(QBrush(fill))
            item.setToolTip(f"Chip rail: {rail_dict.get('net', '')}")
            self._add(item, "annotation")

    def _build_nets(self, pr: PlacementResult) -> None:
        """Draw net ratsnest.  Power nets show vertical lines to chip rails."""
        # Build chip-rail lookup: net_name (lower) → rail centre (JSON coords)
        rail_by_net: dict[str, tuple[float, float]] = {}
        for rail in getattr(pr, "chip_power_rails", []):
            nid = str(rail.get("net", "")).lower()
            rx  = (float(rail.get("x_min", 0)) + float(rail.get("x_max", 0))) / 2
            ry  = (float(rail.get("y_min", 0)) + float(rail.get("y_max", 0))) / 2
            rail_by_net[nid] = (rx, ry)

        for net in self._data.nets:
            pts: list[tuple[float, float]] = []
            for pin_ref in net.pins:
                parts = pin_ref.split("_", 1)
                bid   = int(parts[0][1:])
                pname = parts[1]
                if bid in pr.placed_blocks:
                    pb_pins = pr.placed_blocks[bid].pins
                    if pname in pb_pins:
                        pdata = pb_pins[pname]
                        if "x_min" in pdata:
                            px = (float(pdata["x_min"]) + float(pdata["x_max"])) / 2
                            py = (float(pdata["y_min"]) + float(pdata["y_max"])) / 2
                        else:
                            px = float(pdata.get("x", 0.0))
                            py = float(pdata.get("y", 0.0))
                        pts.append((px, self._sy(py)))

            if len(pts) < 1:
                continue

            if net.net_type == "power":
                color = _POWER_COLORS.get(net.net_id, QColor(200, 100, 100))
                layer = "net_power"
            else:
                color = _SIGNAL_COLOR
                layer = "net_signal"

            pen = _pen(color, 0.09)

            # Power nets: draw a vertical connection from each pin to the chip rail
            chip_rail = rail_by_net.get(net.net_id.lower())
            if net.net_type == "power" and chip_rail is not None:
                rail_scene_y = self._sy(chip_rail[1])
                for px, scene_py in pts:
                    line = QGraphicsLineItem(px, scene_py, px, rail_scene_y)
                    line.setPen(pen)
                    self._net_items.append(line)
                    self._add(line, layer)
                continue  # skip star ratsnest for power nets

            # Signal / internal nets: standard star ratsnest from centroid
            if len(pts) < 2:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            for px, py in pts:
                line = QGraphicsLineItem(px, py, cx, cy)
                line.setPen(pen)
                self._net_items.append(line)
                self._add(line, layer)

    # ---- public API ---------------------------------------------------------

    def set_nets_visible(self, visible: bool) -> None:
        """Toggle all net lines; also respects per-layer visibility."""
        self._nets_enabled = visible
        for layer in ("net_power", "net_signal"):
            layer_vis = self._lm.is_visible(layer)
            for item in self._by_layer.get(layer, []):
                item.setVisible(visible and layer_vis)

    def _on_selection_changed(self) -> None:
        bid = None
        for item in self.selectedItems():
            d = item.data(0)
            if isinstance(d, int):
                bid = d
                break
        self.block_selected.emit(bid)

    def _on_layer_toggle(self, layer: str, visible: bool) -> None:
        for item in self._by_layer.get(layer, []):
            # Net layers are also gated by the nets checkbox
            if layer in ("net_power", "net_signal"):
                item.setVisible(visible and self._nets_enabled)
            else:
                item.setVisible(visible)
        if layer == "drc_overlay":
            for item in self._drc_items:
                item.setVisible(visible)

    def _refresh_block_styles(self) -> None:
        """Update pen/brush of all block rects when colors or border width change."""
        for bid, rect in self._block_rects.items():
            block = self._data.block_by_id(bid)
            fill   = self._lm.block_fill(block.device_type)   if block else QColor(80, 80, 120)
            border = self._lm.block_border(block.device_type) if block else QColor(120, 120, 200)
            rect.setBrush(QBrush(fill))
            rect.setPen(_pen(border, self._lm.border_width))

    # ---- DRC overlay ---------------------------------------------------------

    def clear_drc(self) -> None:
        """Remove all DRC overlay items from the scene."""
        for item in self._drc_items:
            self.removeItem(item)
        self._drc_items.clear()

    def highlight_drc(self, violations: list[DRCViolation]) -> None:
        """Add DRC overlay items for the given violations.

        Appends to existing items — call clear_drc() first to reset.
        Respects the drc_overlay layer visibility setting.
        """
        layer_visible = self._lm.is_visible("drc_overlay")
        for idx, v in enumerate(violations):
            if v.category == "physical_overlap":
                item = self._drc_overlap_rect(v)
            else:
                item = self._drc_gap_polygon(v)
            item.setData(0, idx)
            item.setZValue(100)
            item.setVisible(layer_visible)
            self.addItem(item)
            self._drc_items.append(item)

    def _drc_gap_polygon(self, v: DRCViolation) -> QGraphicsPolygonItem:
        """Quadrilateral connecting the full facing edges of two blocks.

        direction="active" → horizontal gap → polygon spans A's full right edge
        to B's full left edge: (A top-right)→(A bot-right)→(B bot-left)→(B top-left).

        direction="poly" → vertical gap → polygon spans A's full top edge to B's
        full bottom edge: (A top-left)→(A top-right)→(B bot-right)→(B bot-left).

        Uses full-side extents (no band clipping) so the polygon is always visible
        regardless of how much the two blocks overlap in the orthogonal axis.
        All coords: JSON Y-up → scene Y-down via (H - y).
        """
        ax0, ay0, ax1, ay1 = v.bbox_a
        bx0, by0, bx1, by1 = v.bbox_b
        H = self._H

        if v.direction == "active":
            # Polygon between vertical (left / right) sides.
            # A = left block (smaller center-X), B = right block.
            if (ax0 + ax1) > (bx0 + bx1):
                ax0, ay0, ax1, ay1, bx0, by0, bx1, by1 = (
                    bx0, by0, bx1, by1, ax0, ay0, ax1, ay1
                )
            pts = [
                QPointF(ax1, H - ay1),   # A top-right
                QPointF(ax1, H - ay0),   # A bot-right
                QPointF(bx0, H - by0),   # B bot-left
                QPointF(bx0, H - by1),   # B top-left
            ]
        else:
            # Polygon between horizontal (top / bottom) sides.
            # A = lower block (smaller center-Y in JSON Y-up), B = upper block.
            if (ay0 + ay1) > (by0 + by1):
                ax0, ay0, ax1, ay1, bx0, by0, bx1, by1 = (
                    bx0, by0, bx1, by1, ax0, ay0, ax1, ay1
                )
            pts = [
                QPointF(ax0, H - ay1),   # A top-left
                QPointF(ax1, H - ay1),   # A top-right
                QPointF(bx1, H - by0),   # B bot-right
                QPointF(bx0, H - by0),   # B bot-left
            ]

        polygon = QPolygonF(pts)
        item = QGraphicsPolygonItem(polygon)
        hex_color, alpha = DRC_CATEGORY_COLORS.get(v.category, ("#FF4444", 80))
        fill = QColor(hex_color)
        fill.setAlpha(alpha)
        border = QColor(hex_color)
        item.setBrush(QBrush(fill))
        pen = QPen(border)
        pen.setWidthF(0.1)
        pen.setCosmetic(True)
        item.setPen(pen)
        return item

    def _drc_overlap_rect(self, v: DRCViolation) -> QGraphicsRectItem:
        """Intersection rectangle with diagonal stripe fill for hard overlaps."""
        ax0, ay0, ax1, ay1 = v.bbox_a
        bx0, by0, bx1, by1 = v.bbox_b
        H = self._H

        ix0 = max(ax0, bx0)
        iy0 = max(ay0, by0)
        ix1 = min(ax1, bx1)
        iy1 = min(ay1, by1)

        w = ix1 - ix0
        h = iy1 - iy0
        scene_y_top = H - iy1   # JSON y_max → scene y_min (Y-down)

        item = QGraphicsRectItem(ix0, scene_y_top, w, h)
        hex_color, alpha = DRC_CATEGORY_COLORS["physical_overlap"]
        stripe = QColor(hex_color)
        stripe.setAlpha(alpha)
        item.setBrush(QBrush(stripe, Qt.BrushStyle.BDiagPattern))
        border = QColor(hex_color)
        pen = QPen(border)
        pen.setWidthF(0.1)
        pen.setCosmetic(True)
        item.setPen(pen)
        return item
