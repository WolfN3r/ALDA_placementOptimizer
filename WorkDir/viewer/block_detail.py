"""Detailed drawing of one routed 012 structure variant (lib/block_router output:
variant["routing"] = shapes, pins, devices), shared by the Structure tab of the Block
Blueprint and the placement canvas.

Modes (user 2026-11-09):
  "layers"   — close to KLayout: every metal hatched in its own colour, vias as crossed
               boxes, active areas green, S/D strips / gate pads / resistor pads as met1,
               the group colour only on the slot outline and the device label.
  "abstract" — slots filled in their group colour with the gate side as a bar, routing as
               centrelines (met3 thick, met2 / met1 thin), via2 dots.
MIM caps (012 cap detail): met3 bottom plate, capm, met4 top plate and bottom-plate strap.
Both draw the guard ring, its power pins (band outlined in the rail colour) and the block
pins (tab + net name). Coordinates are the
variant's own frame (µm, y up); `place(x, y)` maps a point to the scene (offset, y flip,
90° rotation), so one routine serves both views.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPen
from PyQt6.QtWidgets import (QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem,
                             QGraphicsSimpleTextItem)

MODES = ("layers", "abstract")
PALETTE = ["#d9772b", "#2f6db5", "#2e9e6a", "#a64ca6", "#b5a12f", "#c2413b", "#3fa7b5", "#6b7280"]
DUMMY = "#7d828a"
RING = {"p_ring": "#4f9fbf", "n_ring": "#c98a3a"}
ACTIVE = "#4caf68"
LAYER = {"met1": "#9b87e8", "met2": "#4f9ff0", "met3": "#f0b341", "met4": "#e86f8a"}
CAPM = "#c88be0"
PIN = "#ffffff"
POWER = {"p_ring": "#5588FF", "n_ring": "#FF5555"}       # ring tied to VSS / VDD (placement canvas rail colours)
_HATCH = {"met1": Qt.BrushStyle.FDiagPattern, "met2": Qt.BrushStyle.BDiagPattern, "met3": Qt.BrushStyle.HorPattern,
          "met4": Qt.BrushStyle.VerPattern}
_CENTRE_PX = {"met1": 1.0, "met2": 1.6, "met3": 3.0, "met4": 3.0}     # abstract centreline widths, screen px
_LANDING_MAX = 0.45     # µm: a metal shape shorter than this is a via landing, no centreline
_GATE_BAR = 0.12        # abstract: fraction of the slot height drawn as the gate side
_LABEL_PT = 8.0


def has_detail(v: dict) -> bool:
    return bool((v.get("routing") or {}).get("devices"))


def group_colours(v: dict) -> dict:
    """{block_id: QColor} in order of first appearance in the slots (same as the Structure tab)."""
    out: dict = {}
    for s in v["slots"]:
        bid = s.get("block_id")
        if bid is not None and bid not in out:
            out[bid] = QColor(PALETTE[len(out) % len(PALETTE)])
    return out


def draw_variant(scene, v: dict, names: dict, place, mode: str, device_labels: bool = True) -> list:
    """Add the variant's drawing to `scene`; returns the items (to remove or hide them later).
    device_labels False: no per-device names (full-chip view, where they would pile up)."""
    items: list = []
    colours = group_colours(v)
    routing = v["routing"]
    devices = {(d["row"], d["col"]): d for d in routing["devices"]}

    def qrect(r) -> QRectF:
        return QRectF(place(r[0], r[1]), place(r[2], r[3])).normalized()

    def add(item, tip: str | None = None):
        if tip:
            item.setToolTip(tip)
        scene.addItem(item)
        items.append(item)
        return item

    def box(r, brush=None, pen=None, tip=None):
        it = QGraphicsRectItem(qrect(r))
        it.setBrush(brush if brush is not None else QBrush(Qt.BrushStyle.NoBrush))
        it.setPen(pen if pen is not None else QPen(Qt.PenStyle.NoPen))
        return add(it, tip)

    def cpen(colour, width: float = 1.0) -> QPen:
        p = QPen(QColor(colour), width)
        p.setCosmetic(True)
        return p

    def line(x1, y1, x2, y2, pen, tip=None):
        it = QGraphicsLineItem(place(x1, y1).x(), place(x1, y1).y(), place(x2, y2).x(), place(x2, y2).y())
        it.setPen(pen)
        return add(it, tip)

    def label(text: str, x: float, y: float, colour) -> None:
        t = QGraphicsSimpleTextItem(text)
        f = QFont("Courier New")
        f.setPointSizeF(_LABEL_PT)
        t.setFont(f)
        t.setBrush(QBrush(QColor(colour)))
        t.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        t.setPos(place(x, y))
        add(t)

    def translucent(colour, alpha: int) -> QColor:
        c = QColor(colour)
        c.setAlpha(alpha)
        return c

    # guard ring band
    ring = v.get("guard_ring")
    if ring:
        o, g = ring["opening"], ring["grw"]
        rc = translucent(RING.get(ring["ring"], "#888888") if mode == "abstract" else ACTIVE, 130)
        for r in ((o["x_min"] - g, o["y_min"] - g, o["x_max"] + g, o["y_min"]),
                  (o["x_min"] - g, o["y_max"], o["x_max"] + g, o["y_max"] + g),
                  (o["x_min"] - g, o["y_min"], o["x_min"], o["y_max"]),
                  (o["x_max"], o["y_min"], o["x_max"] + g, o["y_max"])):
            box(r, QBrush(rc), tip=f"guard ring ({ring['ring']})")

    # devices
    for s in v["slots"]:
        bid = s.get("block_id")
        col = colours.get(bid, QColor(DUMMY))
        name = names.get(bid, f"B{bid}") if bid is not None else "dummy"
        r = (s["x"] - s["w"] / 2, s["y"] - s["h"] / 2, s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)
        d = devices.get((s["row"], s["col"]), {})
        cap = d.get("cap")
        if cap and mode == "layers":
            box(cap["met3"], QBrush(QColor(LAYER["met3"]), _HATCH["met3"]), cpen(LAYER["met3"], 0.8), f"{name} bottom plate (met3)")
            box(cap["capm"], QBrush(translucent(CAPM, 60)), cpen(CAPM, 1.2), f"{name} capm")
            for key, what in (("top", "top plate"), ("bottom", "bottom-plate strap")):
                box(cap[key], QBrush(QColor(LAYER["met4"]), _HATCH["met4"]), cpen(LAYER["met4"]), f"{name} {what} (met4)")
            box(r, pen=cpen(col, 1.6), tip=name)
        elif cap:
            box(r, QBrush(translucent(col, 110)), cpen(col), name)
            box(cap["capm"], pen=cpen(col.lighter(150), 1.2), tip=f"{name} capm")
        elif mode == "abstract":
            box(r, QBrush(translucent(col, 110 if bid is not None else 55)), cpen(col), f"{name}  {s.get('orient', 'R0')}")
            if d.get("gate"):
                h = r[3] - r[1]
                bar = (r[0], r[3] - _GATE_BAR * h, r[2], r[3]) if s.get("orient", "R0") == "R0" else \
                      (r[0], r[1], r[2], r[1] + _GATE_BAR * h)
                box(bar, QBrush(col.darker(160)), tip=f"{name} gate: {d.get('gate_net')}")
        else:
            a = d.get("active")
            if a and a[0] < a[2] and a[1] < a[3]:
                box(a, QBrush(QColor(ACTIVE), Qt.BrushStyle.BDiagPattern), tip=f"{name} active area")
            for c, net in d.get("sd", []):
                box(c, QBrush(QColor(LAYER["met1"]), _HATCH["met1"]), cpen(LAYER["met1"]), f"{name} S/D pin (met1): {net}")
            for p in d.get("gate", []):
                box(p, QBrush(QColor(LAYER["met1"]), _HATCH["met1"]), cpen(LAYER["met1"]),
                    f"{name} gate pad (met1): {d.get('gate_net')}")
            for p in d.get("pads", []):
                box(p, QBrush(QColor(LAYER["met1"]), _HATCH["met1"]), cpen(LAYER["met1"]), f"{name} end pad (met1)")
            box(r, pen=cpen(col, 1.6), tip=f"{name}  {s.get('orient', 'R0')}")
        if bid is not None and device_labels:
            label(name, r[0], r[3], col.lighter(140))

    # routing
    order = {"met1": 0, "met2": 1, "via1": 2, "met3": 3, "via2": 4}
    for sh in sorted(routing["shapes"], key=lambda q: order.get(q["layer"], 9)):
        layer, r, net = sh["layer"], sh["rect"], sh["net"]
        tip = f"{layer}: {net}"
        if layer.startswith("via"):
            if mode == "layers":
                pen = cpen("#ffffff", 0.8)
                box(r, pen=pen, tip=tip)
                line(r[0], r[1], r[2], r[3], pen)
                line(r[0], r[3], r[2], r[1], pen)
            elif layer == "via2":
                box(r, QBrush(QColor("#ffffff")), tip=tip)
            continue
        if mode == "layers":
            fill = translucent(LAYER[layer], 30)
            box(r, QBrush(fill), cpen(LAYER[layer], 0.8), tip)
            box(r, QBrush(QColor(LAYER[layer]), _HATCH[layer]))
        else:
            w, h = r[2] - r[0], r[3] - r[1]
            if max(w, h) < _LANDING_MAX:
                continue
            if w >= h:
                cy = (r[1] + r[3]) / 2
                line(r[0], cy, r[2], cy, cpen(LAYER[layer], _CENTRE_PX[layer]), tip)
            else:
                cx = (r[0] + r[2]) / 2
                line(cx, r[1], cx, r[3], cpen(LAYER[layer], _CENTRE_PX[layer]), tip)

    # power pins: the guard ring band (outlined in the rail colour)
    if ring:
        pc = POWER.get(ring["ring"], "#cccccc")
        for p in routing.get("power_pins", []):
            box(p["rect"], QBrush(translucent(pc, 70)), cpen(pc, 1.4), f"power pin {p['net']} (ring, {p['side']})")

    # block pins
    for p in routing["pins"]:
        r = p["rect"]
        box(r, QBrush(translucent(PIN, 220)), cpen(PIN), f"pin {p['net']} ({p['layer']}, {p['side']})")
        x = r[0] if p["side"] == "left" else r[2] if p["side"] == "right" else (r[0] + r[2]) / 2
        y = r[3] if p["side"] != "bottom" else r[1]
        label(p["net"], x, y, PIN if p["layer"] != "met4" else LAYER["met4"])
    return items
