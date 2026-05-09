"""Per-block QGraphicsScene for the tab-based viewer."""
from __future__ import annotations
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtGui import QBrush, QColor

from json_loader import Block, Variant, PlacementData
from layer_manager import LayerManager
from block_item import build_block_items


class BlockScene(QGraphicsScene):
    """
    One scene per block tab.
    Builds from build_block_items() and tracks items by layer
    so that LayerManager visibility changes propagate immediately.
    """

    def __init__(self, block: Block, data: PlacementData, lm: LayerManager) -> None:
        super().__init__()
        self.block = block
        self.data = data
        self.lm = lm
        self._by_layer: dict[str, list] = {}

        self.setBackgroundBrush(QBrush(QColor("#1A1A1A")))
        self._populate(data.active_variant(block))
        lm.register_callback(self._on_layer_toggle)

    # -----------------------------------------------------------------------
    def _populate(self, variant: Variant) -> None:
        for item, layer in build_block_items(self.block, variant, self.data, self.lm):
            item.setVisible(self.lm.is_visible(layer))
            self.addItem(item)
            self._by_layer.setdefault(layer, []).append(item)

    def switch_variant(self, variant_index: int) -> None:
        """Clear and rebuild the scene with a different block variant."""
        if variant_index < 0 or variant_index >= len(self.block.variants):
            return
        self.clear()
        self._by_layer.clear()
        self._populate(self.block.variants[variant_index])

    def _on_layer_toggle(self, layer: str, visible: bool) -> None:
        for item in self._by_layer.get(layer, []):
            item.setVisible(visible)
