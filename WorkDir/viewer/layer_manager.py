"""Layer definitions, colors, and visibility state."""
from __future__ import annotations
from dataclasses import dataclass
from PyQt6.QtGui import QColor


@dataclass
class LayerDef:
    name: str
    display_name: str
    color: QColor
    visible: bool = True


# Block fill/border colors keyed by device_type
_DEVICE_FILL: dict[str, tuple[int, int, int, int]] = {
    "nmos1v_nat": (0, 160, 70, 140),
    "nmos2v_nat": (0, 100, 40, 140),
    "pmos1v_nat": (180, 40, 40, 140),
    "pmos2v_nat": (120, 0,  0,  140),
}
_DEVICE_BORDER: dict[str, tuple[int, int, int]] = {
    "nmos1v_nat": (0, 230, 100),
    "nmos2v_nat": (0, 180,  60),
    "pmos1v_nat": (230,  80,  80),
    "pmos2v_nat": (200,   0,   0),
}


class LayerManager:
    _DEFS = [
        # (name, display_name, r, g, b)
        ("annotation", "Block outline (Annotation)", 200, 200, 200),
        ("net_power",  "Power nets (VDD/VSS)",       255,  80,  80),
        ("net_signal", "Signal nets",                 80, 220,  80),
        ("labels",     "Labels",                     255, 255, 100),
        ("symmetry",   "Symmetry pairs",             255, 150, 255),
        ("drc_overlay", "DRC violations",            255, 100, 100),
    ]

    def __init__(self) -> None:
        self._layers: dict[str, LayerDef] = {
            name: LayerDef(name, disp, QColor(r, g, b))
            for name, disp, r, g, b in self._DEFS
        }
        self._callbacks: list = []

    def all_layers(self) -> list[LayerDef]:
        return list(self._layers.values())

    def layer(self, name: str) -> LayerDef:
        return self._layers[name]

    def is_visible(self, name: str) -> bool:
        ld = self._layers.get(name)
        return ld.visible if ld else False

    def set_visible(self, name: str, visible: bool) -> None:
        if name in self._layers:
            self._layers[name].visible = visible
            for cb in self._callbacks:
                cb(name, visible)

    def register_callback(self, cb) -> None:
        self._callbacks.append(cb)

    def block_fill(self, device_type: str) -> QColor:
        rgba = _DEVICE_FILL.get(device_type, (120, 120, 120, 140))
        return QColor(*rgba)

    def block_border(self, device_type: str) -> QColor:
        rgb = _DEVICE_BORDER.get(device_type, (200, 200, 200))
        return QColor(*rgb)
