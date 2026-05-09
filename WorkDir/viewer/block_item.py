"""
Build per-block graphics: main_bbox rectangle + net port stubs.

No QGraphicsItemGroup subclassing (avoids the white selection-box artifact).
Items are added directly to the scene and tagged with their layer name.
"""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsEllipseItem, QGraphicsTextItem,
)
from PyQt6.QtGui import QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt

from json_loader import Block, Variant, Net, PlacementData
from layer_manager import LayerManager


def _pen(color: QColor, width: float = 1.5, dashed: bool = False) -> QPen:
    p = QPen(color)
    p.setWidthF(width)
    p.setCosmetic(True)
    if dashed:
        p.setStyle(Qt.PenStyle.DashLine)
    return p


def _assign_exits(variant: Variant) -> dict[str, str]:
    """
    Decide which edge (top/bottom/left/right) each pin exits from.
    Pins at the top/bottom bbox edge get those sides; remaining pins
    alternate left/right.
    """
    x0, y0, x1, y1 = variant.bbox
    h = y1 - y0
    exits: dict[str, str] = {}
    center_pins: list[str] = []

    for pin in variant.pins:
        # JSON Y is up (0=bottom of block)
        if pin.y >= h * 0.85:
            exits[pin.name] = "top"
        elif pin.y <= h * 0.15:
            exits[pin.name] = "bottom"
        else:
            center_pins.append(pin.name)

    left_count = 0
    right_count = 0
    for pname in center_pins:
        if left_count <= right_count:
            exits[pname] = "left"
            left_count += 1
        else:
            exits[pname] = "right"
            right_count += 1

    return exits


def _net_color(net: Net | None) -> tuple[QColor, str]:
    """Return (color, layer_name) for a net."""
    if net is None:
        return QColor(160, 160, 160), "labels"
    if net.net_type == "power":
        c = QColor("#FF5555") if net.net_id == "VDD" else QColor("#5588FF")
        return c, "net_power"
    return QColor("#55DD55"), "net_signal"


def build_block_items(
    block: Block,
    variant: Variant,
    data: PlacementData,
    lm: LayerManager,
) -> list[tuple]:
    """
    Return list of (QGraphicsItem, layer_name) tuples.
    The caller (BlockScene) adds them to the scene and handles visibility.

    Coordinate convention used here:
      - Block occupies rect (0, 0, w, h) in scene space.
      - Y-down: y=0 is the TOP of the block (matches QGraphicsScene).
      - Pin JSON Y (Y-up, 0=bottom) is converted: scene_y = h - json_y.
    """
    items: list[tuple] = []
    x0, y0, x1, y1 = variant.bbox
    w, h = x1 - x0, y1 - y0
    cx, cy = w / 2.0, h / 2.0          # block center in scene space

    STUB = max(w, h) * 0.55             # stub length outside block
    DOT_R = max(w, h) * 0.022          # pin-dot radius
    FONT_SZ = max(min(w, h) * 0.075, 0.18)

    # -----------------------------------------------------------------------
    # 1. Main bbox rectangle — annotation layer
    # -----------------------------------------------------------------------
    rect = QGraphicsRectItem(0.0, 0.0, w, h)
    rect.setBrush(QBrush(lm.block_fill(block.device_type)))
    rect.setPen(_pen(lm.block_border(block.device_type), 2.0))
    items.append((rect, "annotation"))

    # -----------------------------------------------------------------------
    # 2. Build pin → net lookup
    # -----------------------------------------------------------------------
    pin_to_net: dict[str, Net] = {}
    for net in data.nets:
        for pin_ref in net.pins:
            parts = pin_ref.split("_", 1)
            bid = int(parts[0][1:])
            if bid == block.block_id:
                pin_to_net[parts[1]] = net

    # -----------------------------------------------------------------------
    # 4. Net port stubs
    # -----------------------------------------------------------------------
    exits = _assign_exits(variant)

    # Group pins by their assigned side to distribute along the edge
    side_pins: dict[str, list[str]] = {"top": [], "bottom": [], "left": [], "right": []}
    for pin in variant.pins:
        side = exits.get(pin.name, "left")
        side_pins[side].append(pin.name)

    def _stub(side: str, index: int, total: int, pin_name: str) -> None:
        net = pin_to_net.get(pin_name)
        color, layer = _net_color(net)

        # Edge exit point: distributed evenly along the assigned edge
        t = (index + 1) / (total + 1)   # fraction along edge (0..1)
        if side == "top":
            edge_x, edge_y = w * t, 0.0
            end_x,  end_y  = edge_x, -STUB
        elif side == "bottom":
            edge_x, edge_y = w * t, h
            end_x,  end_y  = edge_x, h + STUB
        elif side == "left":
            edge_x, edge_y = 0.0, h * t
            end_x,  end_y  = -STUB, edge_y
        else:  # right
            edge_x, edge_y = w, h * t
            end_x,  end_y  = w + STUB, edge_y

        # — Line from block center to stub endpoint (full span, colored)
        spine = QGraphicsLineItem(cx, cy, end_x, end_y)
        spine.setPen(_pen(color, 1.5))
        items.append((spine, layer))

        # — Pin dot at the edge exit point
        dot = QGraphicsEllipseItem(
            edge_x - DOT_R, edge_y - DOT_R, 2 * DOT_R, 2 * DOT_R
        )
        dot.setBrush(QBrush(color))
        dot.setPen(_pen(color, 0))
        items.append((dot, layer))

        # — Label: "Px → net_id\n(B1, B3)"
        other_blocks: list[str] = []
        net_label = pin_name
        if net is not None:
            net_label = f"{pin_name} → {net.net_id}"
            for pin_ref in net.pins:
                ps = pin_ref.split("_", 1)
                other_bid = int(ps[0][1:])
                if other_bid != block.block_id:
                    other_blocks.append(f"B{other_bid}")

        label_str = net_label
        if other_blocks:
            label_str += f"\n({', '.join(sorted(set(other_blocks)))})"

        lbl = QGraphicsTextItem(label_str)
        lf = QFont("Monospace")
        lf.setPointSizeF(max(FONT_SZ * 0.85, 0.14))
        lbl.setFont(lf)
        lbl.setDefaultTextColor(color)
        lbr = lbl.boundingRect()

        PAD = 0.1
        if side == "top":
            lbl.setPos(end_x - lbr.width() / 2, end_y - lbr.height() - PAD)
        elif side == "bottom":
            lbl.setPos(end_x - lbr.width() / 2, end_y + PAD)
        elif side == "left":
            lbl.setPos(end_x - lbr.width() - PAD, end_y - lbr.height() / 2)
        else:  # right
            lbl.setPos(end_x + PAD, end_y - lbr.height() / 2)

        items.append((lbl, "labels"))

    for side, pins in side_pins.items():
        for i, pname in enumerate(pins):
            _stub(side, i, len(pins), pname)

    return items
