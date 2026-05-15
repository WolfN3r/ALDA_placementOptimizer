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

        pr = data.placement_result
        if pr and pr.placed_blocks:
            self._H = max(pb.main_bbox[3] for pb in pr.placed_blocks.values())
            self._build(pr)

        lm.register_callback(self._on_layer_toggle)
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
            rect.setPen(_pen(border, 0.12))
            rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            rect.setData(0, bid)
            self._add(rect, "annotation")

            # Block label
            lbl = QGraphicsTextItem(f"B{bid}")
            f = QFont("Monospace")
            f.setPointSizeF(max(min(w, h) * 0.18, 0.25))
            lbl.setFont(f)
            lbl.setDefaultTextColor(QColor(220, 220, 220))
            br = lbl.boundingRect()
            lbl.setPos(sx + w / 2 - br.width() / 2, sy + h / 2 - br.height() / 2)
            self._add(lbl, "labels")

            # Pin dots — one per absolute pin position
            DOT_R = max(w, h) * 0.03
            for _pname, (px, py) in pb.pins.items():
                dot = QGraphicsEllipseItem(
                    px - DOT_R, self._sy(py) - DOT_R, 2 * DOT_R, 2 * DOT_R
                )
                dot.setBrush(QBrush(QColor(255, 200, 50)))
                dot.setPen(QPen(Qt.PenStyle.NoPen))
                self._add(dot, "annotation")

        self._build_nets(pr)

    def _build_nets(self, pr: PlacementResult) -> None:
        """Draw a star ratsnest from centroid to each pin for every net."""
        for net in self._data.nets:
            pts: list[tuple[float, float]] = []
            for pin_ref in net.pins:
                parts = pin_ref.split("_", 1)
                bid = int(parts[0][1:])
                pname = parts[1]
                if bid in pr.placed_blocks:
                    pb_pins = pr.placed_blocks[bid].pins
                    if pname in pb_pins:
                        px, py = pb_pins[pname]
                        pts.append((px, self._sy(py)))

            if len(pts) < 2:
                continue

            if net.net_type == "power":
                color = _POWER_COLORS.get(net.net_id, QColor(200, 100, 100))
                layer = "net_power"
            else:
                color = _SIGNAL_COLOR
                layer = "net_signal"

            pen = _pen(color, 0.09)
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
