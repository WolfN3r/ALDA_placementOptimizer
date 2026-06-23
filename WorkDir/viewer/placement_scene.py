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
        self._route_items_by_net: dict[str, list] = {}
        self._highlighted_net: str | None = None
        self._highlighted_group: set[int] = set()
        # Flat lookup: maps every block ID (including sub_blocks) to its PlacedBlockInfo.
        # Used by symmetry / cascode / tail drawing methods that need individual device positions.
        self._flat_pb: dict[int, object] = {}

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

    # Topology fill / border colors for composite group outlines
    _COMPOSITE_FILLS: dict[str, tuple[int, int, int]] = {
        "diff_pair":              (40, 120,  40),
        "current_mirror":         (40,  80, 160),
        "cascode_current_mirror": (100, 40, 140),
        "tail_cm_pair":           (160,  90,  30),
    }

    def _build(self, pr: PlacementResult) -> None:
        from json_loader import _COMPOSITE_ID_BASE

        x_max = max(pb.main_bbox[2] for pb in pr.placed_blocks.values())

        # Build flat lookup: includes top-level ungrouped blocks + all sub_blocks.
        # Used by symmetry / cascode / tail drawing methods that reference original IDs.
        self._flat_pb = {}
        for bid, pb in pr.placed_blocks.items():
            self._flat_pb[bid] = pb
            if pb.is_composite:
                for mbid, mpb in pb.sub_blocks.items():
                    self._flat_pb[mbid] = mpb

        # Chip-level power rails (drawn first so blocks render on top)
        self._build_chip_rails(pr)

        # Floorplan outline
        outline = QGraphicsRectItem(0, 0, x_max, self._H)
        outline.setPen(_pen(QColor(90, 90, 90), 0.25))
        outline.setBrush(QBrush(Qt.GlobalColor.transparent))
        self._add(outline, "annotation")

        for bid, pb in pr.placed_blocks.items():
            if pb.is_composite:
                self._draw_composite_block(bid, pb)
            else:
                self._draw_regular_block(bid, pb)

        self._build_nets(pr)
        self._build_routes(pr)
        self._build_symmetry(pr, x_max)
        self._build_cascode_proximity_pairs(pr)
        self._build_tail_cm_pairs(pr)
        self._build_passive_clusters(pr)

    def _draw_regular_block(self, bid: int, pb) -> None:
        """Draw one ungrouped device block."""
        block = self._data.block_by_id(bid)
        x0, y0, x1, y1 = pb.main_bbox
        w, h = x1 - x0, y1 - y0
        sx, sy = x0, self._sy(y1)

        rect = QGraphicsRectItem(sx, sy, w, h)
        fill   = self._lm.block_fill(block.device_type)   if block else QColor(80, 80, 120)
        border = self._lm.block_border(block.device_type) if block else QColor(120, 120, 200)
        rect.setBrush(QBrush(fill))
        rect.setPen(_pen(border, self._lm.border_width))
        rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        rect.setData(0, bid)
        self._add(rect, "annotation")
        self._block_rects[bid] = rect

        lbl = QGraphicsTextItem(f"B{bid}")
        f = QFont("Monospace")
        f.setPointSizeF(max(min(w, h) * 0.18, 0.25))
        lbl.setFont(f)
        lbl.setDefaultTextColor(QColor(220, 220, 220))
        br = lbl.boundingRect()
        lbl.setPos(sx + w / 2 - br.width() / 2, sy + h / 2 - br.height() / 2)
        self._add(lbl, "labels")

        DOT_R = max(w, h) * 0.03
        for pname, pdata in pb.pins.items():
            self._draw_pin(pname, pdata, DOT_R)

    def _draw_composite_block(self, bid: int, pb) -> None:
        """Draw a composite group block: outer bbox + sub_block outlines inside."""
        x0, y0, x1, y1 = pb.main_bbox
        w, h = x1 - x0, y1 - y0
        sx, sy = x0, self._sy(y1)

        ttype = pb.topology_type
        r, g, b = self._COMPOSITE_FILLS.get(ttype, (60, 60, 60))
        fill_color   = QColor(r, g, b, 60)    # semi-transparent fill
        border_color = QColor(r, g, b).lighter(140)

        # Outer composite rectangle
        comp_rect = QGraphicsRectItem(sx, sy, w, h)
        comp_rect.setBrush(QBrush(fill_color))
        border_pen = _pen(border_color, self._lm.border_width * 2.5)
        border_pen.setStyle(Qt.PenStyle.DashLine)
        comp_rect.setPen(border_pen)
        comp_rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        comp_rect.setData(0, bid)
        self._add(comp_rect, "annotation")
        self._block_rects[bid] = comp_rect

        # Topology type label in the top-left corner of the composite
        lbl = QGraphicsTextItem(ttype.replace("_", " "))
        f = QFont("Monospace")
        f.setPointSizeF(max(min(w, h) * 0.10, 0.20))
        lbl.setFont(f)
        lbl.setDefaultTextColor(border_color)
        lbl.setPos(sx + 0.1, sy + 0.1)
        self._add(lbl, "labels")

        DOT_R = max(w, h) * 0.03

        # Sub-block outlines with device-type fill
        for mbid, mpb in pb.sub_blocks.items():
            member_block = self._data.block_by_id(mbid)
            mx0, my0, mx1, my1 = mpb.main_bbox
            mw, mh = mx1 - mx0, my1 - my0
            msx, msy = mx0, self._sy(my1)

            sub_rect = QGraphicsRectItem(msx, msy, mw, mh)
            mfill   = self._lm.block_fill(member_block.device_type)   if member_block else QColor(80, 80, 120)
            mborder = self._lm.block_border(member_block.device_type) if member_block else QColor(120, 120, 200)
            sub_rect.setBrush(QBrush(mfill))
            sub_rect.setPen(_pen(mborder, self._lm.border_width))
            sub_rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            sub_rect.setData(0, mbid)
            self._add(sub_rect, "annotation")
            self._block_rects[mbid] = sub_rect

            mlbl = QGraphicsTextItem(f"B{mbid}")
            mf = QFont("Monospace")
            mf.setPointSizeF(max(min(mw, mh) * 0.18, 0.25))
            mlbl.setFont(mf)
            mlbl.setDefaultTextColor(QColor(220, 220, 220))
            mbr = mlbl.boundingRect()
            mlbl.setPos(msx + mw / 2 - mbr.width() / 2, msy + mh / 2 - mbr.height() / 2)
            self._add(mlbl, "labels")

        # Group-level pins drawn last so they render on top of sub-block fills
        for pname, pdata in pb.pins.items():
            self._draw_pin(pname, pdata, DOT_R)

    def _draw_pin(self, pname: str, pdata: dict, dot_r: float) -> None:
        """Draw a single pin shape (M1 rectangle or dot fallback)."""
        if "x_min" in pdata:
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
            scene_top = self._sy(ry1)
            pin_item = QGraphicsRectItem(rx0, scene_top, rx1 - rx0, ry1 - ry0)
            pin_item.setPen(_pen(col, 0.02))
            pin_item.setBrush(QBrush(fill))
            pin_item.setZValue(10)
            net_name = pdata.get("net", "")
            if net_name:
                pin_item.setToolTip(f"{pname}: {net_name}")
            self._add(pin_item, "annotation")
        else:
            px = float(pdata.get("x", 0.0))
            py = float(pdata.get("y", 0.0))
            dot = QGraphicsEllipseItem(px - dot_r, self._sy(py) - dot_r, 2 * dot_r, 2 * dot_r)
            dot.setBrush(QBrush(QColor(255, 200, 50)))
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            dot.setZValue(10)
            self._add(dot, "annotation")

    def _build_symmetry(self, pr: PlacementResult, x_max: float) -> None:
        sc = self._data.symmetry_constraints
        if not sc:
            return

        # (block_id, layer_key, color) collected for end-of-loop self-sym rendering
        self_sym_entries: list[tuple[int, str, QColor]] = []

        for g in sc.get("groups", []):
            tag = str(g.get("topology_tag", ""))
            layer_key = self._lm.topology_layer_key(tag)
            color = self._lm.topology_tag_color(tag)

            # Normalise pair format: old=[{"block_a":a,"block_b":b}], new=[[a,b]]
            group_pairs: list[tuple[int, int]] = []
            for p in g.get("pairs", []):
                if isinstance(p, dict):
                    group_pairs.append((int(p["block_a"]), int(p["block_b"])))
                else:
                    group_pairs.append((int(p[0]), int(p[1])))

            # Collect self-sym before the placed-pair guard so they always render
            for s in g.get("self_symmetric", []):
                self_sym_entries.append((int(s), layer_key, color))

            # Axis position derived from this group's pairs only
            global_axis = sc.get("symmetry_axis", "vertical")
            axis_dir = g.get("axis", global_axis)
            placed = [(a, b) for a, b in group_pairs
                      if a in self._flat_pb and b in self._flat_pb]
            if not placed:
                continue

            axis_pen = QPen(color)
            axis_pen.setCosmetic(True)
            axis_pen.setWidthF(1.5)
            axis_pen.setStyle(Qt.PenStyle.DashLine)

            if axis_dir == "horizontal":
                midpoints = [
                    (self._sy((self._flat_pb[a].main_bbox[1] + self._flat_pb[a].main_bbox[3]) / 2)
                     + self._sy((self._flat_pb[b].main_bbox[1] + self._flat_pb[b].main_bbox[3]) / 2)) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                axis_line = QGraphicsLineItem(0, axis_pos, x_max, axis_pos)
            else:
                midpoints = [
                    ((self._flat_pb[a].main_bbox[0] + self._flat_pb[a].main_bbox[2]) / 2
                     + (self._flat_pb[b].main_bbox[0] + self._flat_pb[b].main_bbox[2]) / 2) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                axis_line = QGraphicsLineItem(axis_pos, 0, axis_pos, self._H)

            axis_line.setPen(axis_pen)
            axis_line.setZValue(50)
            self._add(axis_line, layer_key)

            # Topology tag label on the axis line
            if tag:
                lbl = QGraphicsTextItem(tag.replace("_", " "))
                f = QFont("Monospace")
                f.setPointSizeF(0.3)
                lbl.setFont(f)
                lbl.setDefaultTextColor(color)
                lbl.setZValue(55)
                br = lbl.boundingRect()
                if axis_dir == "horizontal":
                    lbl.setPos(x_max * 0.02, axis_pos - br.height() - 0.05)
                else:
                    lbl.setPos(axis_pos + 0.05, self._H * 0.02)
                self._add(lbl, layer_key)

            # Center-to-center connector for each pair in this group
            pair_pen = QPen(color)
            pair_pen.setCosmetic(True)
            pair_pen.setWidthF(1.0)
            for a, b in group_pairs:
                if a not in self._flat_pb or b not in self._flat_pb:
                    continue
                ba, bb = self._flat_pb[a].main_bbox, self._flat_pb[b].main_bbox
                cx_a = (ba[0] + ba[2]) / 2
                cy_a = self._sy((ba[1] + ba[3]) / 2)
                cx_b = (bb[0] + bb[2]) / 2
                cy_b = self._sy((bb[1] + bb[3]) / 2)
                line = QGraphicsLineItem(cx_a, cy_a, cx_b, cy_b)
                line.setPen(pair_pen)
                line.setZValue(50)
                self._add(line, layer_key)

        # Self-symmetric block markers — × cross at block center
        for s, layer_key, color in self_sym_entries:
            if s not in self._flat_pb:
                continue
            cross_pen = QPen(color)
            cross_pen.setCosmetic(True)
            cross_pen.setWidthF(1.2)
            bb = self._flat_pb[s].main_bbox
            cx = (bb[0] + bb[2]) / 2
            cy = self._sy((bb[1] + bb[3]) / 2)
            arm = min(bb[2] - bb[0], bb[3] - bb[1]) * 0.18
            for dx, dy, ex, ey in [(-arm, 0, arm, 0), (0, -arm, 0, arm)]:
                c = QGraphicsLineItem(cx + dx, cy + dy, cx + ex, cy + ey)
                c.setPen(cross_pen)
                c.setZValue(50)
                self._add(c, layer_key)

    def _build_cascode_proximity_pairs(self, pr: PlacementResult) -> None:
        """Draw vertical connector + midpoint dot for each cascode-stacked device pair."""
        sc = self._data.symmetry_constraints
        pairs = sc.get("cascode_proximity_pairs", []) if sc else []
        if not pairs:
            return
        color = self._lm.layer("sym_cascode_prox").color
        pen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.5)
        for entry in pairs:
            upper_id, lower_id = int(entry[0]), int(entry[1])
            if upper_id not in self._flat_pb or lower_id not in self._flat_pb:
                continue
            bu = self._flat_pb[upper_id].main_bbox
            bl = self._flat_pb[lower_id].main_bbox
            cx_u = (bu[0] + bu[2]) / 2
            cy_u = self._sy((bu[1] + bu[3]) / 2)
            cx_l = (bl[0] + bl[2]) / 2
            cy_l = self._sy((bl[1] + bl[3]) / 2)
            line = QGraphicsLineItem(cx_u, cy_u, cx_l, cy_l)
            line.setPen(pen)
            line.setZValue(51)
            self._add(line, "sym_cascode_prox")
            arm = 0.25
            dot = QGraphicsEllipseItem(
                (cx_u + cx_l) / 2 - arm,
                (cy_u + cy_l) / 2 - arm,
                2 * arm, 2 * arm,
            )
            dot.setPen(_pen(color, 0.03))
            dot.setBrush(QBrush(color))
            dot.setZValue(52)
            self._add(dot, "sym_cascode_prox")

    def _build_tail_cm_pairs(self, pr: PlacementResult) -> None:
        """Draw dashed connector + 'T' label for each tail-transistor / CM-ref pair."""
        sc = self._data.symmetry_constraints
        pairs = sc.get("tail_cm_pairs", []) if sc else []
        if not pairs:
            return
        color = self._lm.layer("sym_tail_cm").color
        pen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.2)
        pen.setStyle(Qt.PenStyle.DashDotLine)
        for entry in pairs:
            tail_id, mirror_id = int(entry[0]), int(entry[1])
            if tail_id not in self._flat_pb or mirror_id not in self._flat_pb:
                continue
            bt = self._flat_pb[tail_id].main_bbox
            bm = self._flat_pb[mirror_id].main_bbox
            cx_t = (bt[0] + bt[2]) / 2
            cy_t = self._sy((bt[1] + bt[3]) / 2)
            cx_m = (bm[0] + bm[2]) / 2
            cy_m = self._sy((bm[1] + bm[3]) / 2)
            line = QGraphicsLineItem(cx_t, cy_t, cx_m, cy_m)
            line.setPen(pen)
            line.setZValue(51)
            self._add(line, "sym_tail_cm")
            lbl = QGraphicsTextItem("T")
            f = QFont("Monospace")
            f.setPointSizeF(0.3)
            f.setBold(True)
            lbl.setFont(f)
            lbl.setDefaultTextColor(color)
            lbl.setZValue(55)
            br = lbl.boundingRect()
            lbl.setPos(cx_t - br.width() / 2, cy_t - br.height() / 2)
            self._add(lbl, "sym_tail_cm")

    def _build_passive_clusters(self, pr: PlacementResult) -> None:
        """Draw semi-transparent bounding rect over each passive device cluster."""
        sc = self._data.symmetry_constraints
        clusters = sc.get("passive_clusters", []) if sc else []
        if not clusters:
            return
        color = self._lm.layer("sym_passive").color
        fill = QColor(color.red(), color.green(), color.blue(), 30)
        pen = QPen(color)
        pen.setCosmetic(True)
        pen.setWidthF(1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        for cluster in clusters:
            members = [int(m) for m in cluster.get("members", [])]
            placed = [m for m in members if m in self._flat_pb]
            if not placed:
                continue
            PAD = 0.15
            x0 = min(self._flat_pb[m].main_bbox[0] for m in placed) - PAD
            y1j = max(self._flat_pb[m].main_bbox[3] for m in placed) + PAD
            x1 = max(self._flat_pb[m].main_bbox[2] for m in placed) + PAD
            y0j = min(self._flat_pb[m].main_bbox[1] for m in placed) - PAD
            rect = QGraphicsRectItem(x0, self._sy(y1j), x1 - x0, y1j - y0j)
            rect.setPen(pen)
            rect.setBrush(QBrush(fill))
            rect.setZValue(15)
            self._add(rect, "sym_passive")

    # ---- group highlight API -------------------------------------------------

    def highlight_group_blocks(self, block_ids: list[int]) -> None:
        """Highlight a set of blocks with a bright border; call with [] to clear."""
        self.clear_group_highlight()
        for bid in block_ids:
            rect = self._block_rects.get(bid)
            if rect:
                rect.setPen(_pen(QColor(255, 230, 50), 0.2))
                self._highlighted_group.add(bid)

    def clear_group_highlight(self) -> None:
        for bid in self._highlighted_group:
            rect = self._block_rects.get(bid)
            if rect:
                block = self._data.block_by_id(bid)
                border = self._lm.block_border(block.device_type) if block else QColor(120, 120, 200)
                rect.setPen(_pen(border, self._lm.border_width))
        self._highlighted_group.clear()

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

    def _build_routes(self, pr: PlacementResult) -> None:
        """Draw route_segments from py201 JSON as filled rectangles, one per segment."""
        for net in self._data.nets:
            if not net.route_segments:
                continue
            col = (
                _POWER_COLORS.get(net.net_id, QColor(200, 100, 100))
                if net.net_type == "power"
                else _SIGNAL_COLOR
            )
            fill = QColor(col.red(), col.green(), col.blue(), 60)
            pen  = _pen(QColor(col.red(), col.green(), col.blue(), 200), 0.015)
            items: list = []
            for seg in net.route_segments:
                rx0 = float(seg.get("x_min", 0))
                rx1 = float(seg.get("x_max", 0))
                ry0 = float(seg.get("y_min", 0))
                ry1 = float(seg.get("y_max", 0))
                lyr = str(seg.get("layer", ""))
                scene_top = self._sy(ry1)
                item = QGraphicsRectItem(rx0, scene_top, rx1 - rx0, ry1 - ry0)
                item.setBrush(QBrush(fill))
                item.setPen(pen)
                item.setZValue(10)
                item.setData(1, net.net_id)  # tag for click detection
                tip = f"Net: {net.net_id}"
                if lyr:
                    tip += f"  |  {lyr}"
                if net.route_status:
                    tip += f"  |  {net.route_status}"
                item.setToolTip(tip)
                items.append(item)
                self._add(item, "net_routes")
            self._route_items_by_net[net.net_id] = items

    def _net_color(self, net_id: str) -> QColor:
        for net in self._data.nets:
            if net.net_id == net_id:
                return (
                    _POWER_COLORS.get(net_id, QColor(200, 100, 100))
                    if net.net_type == "power"
                    else _SIGNAL_COLOR
                )
        return _SIGNAL_COLOR

    def _highlight_net(self, net_id: str | None) -> None:
        """Highlight all route segments of one net; dim the rest. Pass None to reset."""
        self._highlighted_net = net_id
        for nid, items in self._route_items_by_net.items():
            col = self._net_color(nid)
            if net_id is None:
                fill = QColor(col.red(), col.green(), col.blue(), 60)
                pen  = _pen(QColor(col.red(), col.green(), col.blue(), 200), 0.015)
            elif nid == net_id:
                fill = QColor(255, 230, 50, 200)
                pen  = _pen(QColor(255, 210, 0), 0.06)
            else:
                fill = QColor(col.red(), col.green(), col.blue(), 15)
                pen  = _pen(QColor(col.red(), col.green(), col.blue(), 60), 0.015)
            for item in items:
                item.setBrush(QBrush(fill))
                item.setPen(pen)

    def mousePressEvent(self, event) -> None:
        for item in self.items(event.scenePos()):
            if isinstance(item.data(1), str):   # route rectangle tagged with net_id
                self._highlight_net(item.data(1))
                event.accept()
                return
        # Clicked on something other than a route rect: clear highlight
        if self._highlighted_net is not None:
            self._highlight_net(None)
        super().mousePressEvent(event)

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
            if net.route_segments:
                continue  # routes drawn as rectangles in _build_routes()
            pts: list[tuple[float, float]] = []
            for pin_ref in net.pins:
                parts = pin_ref.split("_", 1)
                bid   = int(parts[0][1:])
                pname = parts[1]
                if bid in self._flat_pb:
                    pb_pins = self._flat_pb[bid].pins
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
        """Toggle all net lines and route segments; also respects per-layer visibility."""
        self._nets_enabled = visible
        for layer in ("net_power", "net_signal", "net_routes"):
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
            # Net layers (including routes) are also gated by the nets checkbox
            if layer in ("net_power", "net_signal", "net_routes"):
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
