"""Structure tab of the Block Blueprint: the real slot pattern of a 012 (--pdk) block.
A routed variant (lib/block_router) is drawn by block_detail in "Layers" or "Abstract"
mode (selector next to the variant list, Cmd/Ctrl+E switches); an unrouted one as below.

A block inside a matched structure (diff pair, mirror, sensitive single, resistor
chain) shows its group's matching_variants; any other 012 block shows its own copy
arrays. Every slot is drawn at its position: devices coloured per netlist device,
dummies grey, the gate side as a bar (top for R0, bottom for R180), the source /
drain side letters, the guard ring band and the n-well fill outline. Coordinates
are the variant's own frame, y up; a 90° variant is drawn rotated 90° CW.
"""
from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QKeySequence, QPainterPath, QPen, QShortcut, QTransform
from PyQt6.QtWidgets import (QComboBox, QGraphicsPathItem, QGraphicsRectItem, QGraphicsScene,
                             QGraphicsSimpleTextItem, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

import block_detail
from json_loader import PlacementData

_COMPOSITE_ID_BASE = 10_000
_PALETTE = ["#d9772b", "#2f6db5", "#2e9e6a", "#a64ca6", "#b5a12f", "#c2413b", "#3fa7b5", "#6b7280"]
_DUMMY = "#7d828a"
_RING = {"p_ring": "#4f9fbf", "n_ring": "#c98a3a"}
_NWELL = "#aa44aa"
_GATE_BAR = 0.12        # fraction of the slot height drawn as the gate side
_FONT_PT = 10           # font drawn at this size, then scaled to the slot
_TEXT_FRAC = 0.12       # label height as a fraction of the slot height


def structure_for_block(data: PlacementData, bid: int) -> dict | None:
    """{"title", "variants" (dicts with slots), "chosen", "names" {block_id: inst}} or None."""
    names = {b.block_id: (b.inst or f"B{b.block_id}") for b in data.blocks}
    pr = data.placement_result
    for g in data.groups:
        mv = g.get("matching_variants") or []
        if bid in g.get("block_ids", []) and mv and "slots" in mv[0]:
            placed = pr.placed_blocks.get(_COMPOSITE_ID_BASE + g["group_id"]) if pr else None
            chosen = placed.variant_index if placed and placed.variant_index is not None else \
                next((i for i, v in enumerate(mv) if v.get("is_used")), 0)
            title = f"{g['topology_type']}: " + ", ".join(names[b] for b in g["block_ids"])
            return {"title": title, "variants": mv, "chosen": chosen, "names": names}
    block = data.block_by_id(bid)
    if block is None or not any(v.slots for v in block.variants):
        return None
    variants = [{"slots": v.slots, "guard_ring": v.guard_ring, "rows": v.rows, "cols": v.cols,
                 "rotation_deg": v.rotation_deg, "width_um": v.bbox[2], "height_um": v.bbox[3],
                 **({"routing": v.routing} if v.routing else {})}
                for v in block.variants]
    return {"title": f"copies of {names[bid]}", "variants": variants,
            "chosen": data.active_variant(block).index, "names": names}


class StructureScene(QGraphicsScene):
    def __init__(self, info: dict) -> None:
        super().__init__()
        self.info = info
        self.mode = block_detail.MODES[0]
        self.setBackgroundBrush(QBrush(QColor("#1A1A1A")))

    def show_variant(self, v: dict) -> None:
        self.clear()
        rotated = v.get("rotation_deg") == 90
        if block_detail.has_detail(v):
            # routed (lib/block_router): real pins and routing; 90° CW: (x, y) -> (y, W0 - x), W0 = height_um
            W, H = v["width_um"], v["height_um"]
            frame = QGraphicsRectItem(0.0, 0.0, W, H)
            frame.setPen(QPen(QColor("#9aa0a6"), 0))
            self.addItem(frame)
            place = (lambda x, yy: QPointF(yy, x)) if rotated else (lambda x, yy: QPointF(x, H - yy))
            block_detail.draw_variant(self, v, self.info["names"], place, self.mode)
            return
        # slots are in the unrotated frame: draw there, then rotate the whole drawing
        W, H = (v["height_um"], v["width_um"]) if rotated else (v["width_um"], v["height_um"])
        y = lambda yy: H - yy                       # json y-up -> scene y-down
        frame = QGraphicsRectItem(0.0, 0.0, W, H)
        frame.setPen(QPen(QColor("#9aa0a6"), 0))
        self.addItem(frame)
        ring = v.get("guard_ring")
        if ring:
            o = ring["opening"]
            grw = ring["grw"]
            outer = QPainterPath()
            outer.addRect(o["x_min"] - grw, y(o["y_max"] + grw), o["x_max"] - o["x_min"] + 2 * grw,
                          o["y_max"] - o["y_min"] + 2 * grw)
            inner = QPainterPath()
            inner.addRect(o["x_min"], y(o["y_max"]), o["x_max"] - o["x_min"], o["y_max"] - o["y_min"])
            band = QGraphicsPathItem(outer.subtracted(inner))
            band.setBrush(QBrush(QColor(_RING.get(ring["ring"], "#888888"))))
            band.setPen(QPen(Qt.PenStyle.NoPen))
            self.addItem(band)
            if ring["ring"] == "n_ring":
                nw = QGraphicsRectItem(0.0, 0.0, W, H)
                pen = QPen(QColor(_NWELL), 0)
                pen.setStyle(Qt.PenStyle.DashLine)
                nw.setPen(pen)
                self.addItem(nw)
        colour = {}
        for s in v["slots"]:
            bid = s.get("block_id")
            if bid is not None and bid not in colour:
                colour[bid] = QColor(_PALETTE[len(colour) % len(_PALETTE)])
        for s in v["slots"]:
            bid = s.get("block_id")
            c = colour.get(bid, QColor(_DUMMY))
            x0, top = s["x"] - s["w"] / 2, y(s["y"] + s["h"] / 2)
            r = QGraphicsRectItem(x0, top, s["w"], s["h"])
            fill = QColor(c)
            fill.setAlpha(110 if bid is not None else 60)
            r.setBrush(QBrush(fill))
            r.setPen(QPen(c, 0))
            r.setToolTip(f"{self.info['names'].get(bid, 'dummy') if bid is not None else 'dummy'}  {s.get('orient', 'R0')}"
                         f"  left={s.get('left')} right={s.get('right')}")
            self.addItem(r)
            bar_h = s["h"] * _GATE_BAR
            gy = top if s.get("orient", "R0") == "R0" else top + s["h"] - bar_h
            gate = QGraphicsRectItem(x0, gy, s["w"], bar_h)
            gate.setBrush(QBrush(c.darker(160)))
            gate.setPen(QPen(Qt.PenStyle.NoPen))
            self.addItem(gate)
            label = self.info["names"].get(bid, "") if bid is not None else "d"
            size = min(s["h"] * _TEXT_FRAC, s["w"] * 0.25)
            self._text(label, s["x"], top + s["h"] / 2, c.lighter(150), size, s["w"] * 0.9)
            for side, xx in (("left", x0 + s["w"] * 0.12), ("right", x0 + s["w"] * 0.88)):
                term = s.get(side)
                if term:
                    self._text(term[0].upper(), xx, top + s["h"] * 0.75, QColor("#e0e0e0"), size, s["w"] * 0.2)
        if rotated:
            # 90° CW like export_gds: json (x, y) -> (y, W0 - x), i.e. scene (sx, sy) -> (H0 - sy, sx)
            self.createItemGroup(self.items()).setTransform(QTransform(0, 1, -1, 0, H, 0))

    def _text(self, text: str, x: float, yy: float, colour: QColor, height: float, max_w: float) -> None:
        """Text centred at (x, yy), `height` µm tall, at most max_w µm wide."""
        t = QGraphicsSimpleTextItem(text)
        f = QFont("Courier New")
        f.setPointSizeF(_FONT_PT)
        t.setFont(f)
        t.setBrush(QBrush(colour))
        br = t.boundingRect()
        k = min(height / br.height(), max_w / br.width())
        t.setScale(k)
        t.setPos(x - br.width() * k / 2, yy - br.height() * k / 2)
        self.addItem(t)


class StructurePanel(QWidget):
    """Variant selector + summary above a CanvasView of a StructureScene."""

    def __init__(self, info: dict, view_factory) -> None:
        super().__init__()
        self.info = info
        self.scene = StructureScene(info)
        self.view = view_factory(self.scene)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(info["title"]))
        self.combo = QComboBox()
        for i, v in enumerate(info["variants"]):
            pattern = " / ".join(v["pattern"]) if v.get("pattern") else f"{v.get('rows')}x{v.get('cols')} copies"
            tag = "  [placed]" if i == info["chosen"] else ""
            self.combo.addItem(f"#{i}  {v.get('rows')}x{v.get('cols')}  {v['width_um']:.2f} x {v['height_um']:.2f} um"
                               f"  {pattern}{tag}")
        self.combo.currentIndexChanged.connect(self._show)
        row = QHBoxLayout()
        row.addWidget(self.combo, stretch=1)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Layers", "Abstract"])
        self.mode_combo.setToolTip("Drawing of routed variants  [Cmd/Ctrl+E switches]")
        self.mode_combo.currentIndexChanged.connect(self._set_mode)
        row.addWidget(self.mode_combo)
        lay.addLayout(row)
        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: self.mode_combo.setCurrentIndex(
            1 - self.mode_combo.currentIndex()))
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        lay.addWidget(self.view, stretch=1)
        self.combo.setCurrentIndex(info["chosen"])
        self._show(info["chosen"])

    def _set_mode(self, i: int) -> None:
        self.scene.mode = block_detail.MODES[i]
        self.scene.show_variant(self.info["variants"][self.combo.currentIndex()])

    def _show(self, i: int) -> None:
        v = self.info["variants"][i]
        self.scene.show_variant(v)
        sc = v.get("score")
        parts = [f"{v.get('matching_type', 'copies')}"]
        if sc:
            parts.append(f"linear {sc['lin']:.3f} uV, orient {sc['orient']:.3f} uV, rank {sc['rank']:.3f}")
        if "facing_mismatches" in v:
            parts.append(f"S/D sides on different nets: {v['facing_mismatches']}")
        if v.get("dummies"):
            parts.append(f"dummies: {v['dummies']['count']} row ends + {v['dummies']['inner_full_size']} inner")
        if v.get("guard_ring"):
            parts.append(f"ring {v['guard_ring']['ring']} grw {v['guard_ring']['grw']}")
        if v.get("rotation_deg") == 90:
            parts.append("rotated 90° CW")
        self.summary.setText("  ·  ".join(parts))
        self.view.set_y_up(v["height_um"])
        self.view.fit()
