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


_DEVICE_FILL_DEFAULTS: dict[str, tuple[int, int, int, int]] = {
    "nmos_rvt":  (  0, 180,  70, 140),
    "nmos_lvt":  (  0, 130,  50, 140),
    "nmos_hvt":  (  0,  80,  30, 140),
    "pmos_rvt":  (180,  40,  40, 140),
    "pmos_lvt":  (140,  20,  20, 140),
    "pmos_hvt":  (100,   0,   0, 140),
    "res_poly":  (200, 120,   0, 140),
    "cap_mom":   (  0, 130, 160, 140),
}
_DEVICE_BORDER_DEFAULTS: dict[str, tuple[int, int, int]] = {
    "nmos_rvt":  (  0, 230, 100),
    "nmos_lvt":  (  0, 175,  70),
    "nmos_hvt":  (  0, 120,  50),
    "pmos_rvt":  (230,  80,  80),
    "pmos_lvt":  (190,  50,  50),
    "pmos_hvt":  (150,  20,  20),
    "res_poly":  (255, 165,   0),
    "cap_mom":   (  0, 180, 220),
}


class LayerManager:
    _DEFS = [
        # (name, display_name, r, g, b)
        ("annotation",  "Block outline (Annotation)", 200, 200, 200),
        ("net_power",   "Power nets (VDD/VSS)",       255,  80,  80),
        ("net_signal",  "Signal nets",                 80, 220,  80),
        ("labels",      "Labels",                     255, 255, 100),
        ("symmetry",    "Symmetry pairs",             255, 150, 255),
        ("drc_overlay", "DRC violations",             255, 100, 100),
    ]

    def __init__(self) -> None:
        self._layers: dict[str, LayerDef] = {
            name: LayerDef(name, disp, QColor(r, g, b))
            for name, disp, r, g, b in self._DEFS
        }
        self._callbacks: list = []
        self._render_callbacks: list = []
        self._border_width: float = 0.04
        self._device_fill:   dict[str, tuple[int, int, int, int]] = dict(_DEVICE_FILL_DEFAULTS)
        self._device_border: dict[str, tuple[int, int, int]]      = dict(_DEVICE_BORDER_DEFAULTS)

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

    def register_render_callback(self, cb) -> None:
        """Register a callback fired when block colors or border width change."""
        self._render_callbacks.append(cb)

    def _fire_render(self) -> None:
        for cb in self._render_callbacks:
            cb()

    @property
    def border_width(self) -> float:
        return self._border_width

    def set_border_width(self, w: float) -> None:
        self._border_width = max(0.001, w)

    def block_fill(self, device_type: str) -> QColor:
        rgba = self._device_fill.get(device_type, (120, 120, 120, 140))
        return QColor(*rgba)

    def block_border(self, device_type: str) -> QColor:
        rgb = self._device_border.get(device_type, (200, 200, 200))
        return QColor(*rgb)

    def get_device_fill_rgba(self, device_type: str) -> tuple[int, int, int, int]:
        return self._device_fill.get(device_type, (120, 120, 120, 140))

    def get_device_border_rgb(self, device_type: str) -> tuple[int, int, int]:
        return self._device_border.get(device_type, (200, 200, 200))

    def set_device_fill(self, device_type: str, r: int, g: int, b: int, a: int = 140) -> None:
        self._device_fill[device_type] = (r, g, b, a)

    def set_device_border(self, device_type: str, r: int, g: int, b: int) -> None:
        self._device_border[device_type] = (r, g, b)

    def device_types(self) -> list[str]:
        return list(_DEVICE_FILL_DEFAULTS.keys())

    def apply_render_settings(self) -> None:
        """Fire render callbacks after batch color/width updates."""
        self._fire_render()
