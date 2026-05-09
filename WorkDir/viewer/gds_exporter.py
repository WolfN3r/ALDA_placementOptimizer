"""GDS export stub — requires gdstk (pip install gdstk)."""
from __future__ import annotations
from pathlib import Path

from json_loader import PlacementData


def export(data: PlacementData, out_path: str | Path) -> None:
    """
    Export placed blocks to a GDS-II file.

    Each block becomes a GDS cell named 'BLOCK_{block_id}'.
    The top-level cell 'TOP' references all placed blocks at their coordinates.

    Requires:  pip install gdstk
    """
    try:
        import gdstk
    except ImportError as e:
        raise RuntimeError(
            "gdstk is not installed. Run: pip install gdstk"
        ) from e

    lib = gdstk.Library("ALDA_placement")
    top = lib.new_cell("TOP")

    for block in data.blocks:
        cell = lib.new_cell(f"BLOCK_{block.block_id}")
        variant = data.active_variant(block)
        x0, y0, x1, y1 = variant.bbox
        w, h = x1 - x0, y1 - y0

        # OD rectangle — layer 6 (from gpdk090_gds_layers.json)
        od_layer = 18 if "2v" in block.device_type else 6
        cell.add(gdstk.rectangle((0, 0), (w, h), layer=od_layer))

        # Pin labels on M1 (layer 31)
        for pin in variant.pins:
            cell.add(gdstk.Label(pin.name, (pin.x, pin.y), layer=31))

        # Place in top if placement data available
        if block.placed and "x" in block.placed:
            px = float(block.placed["x"])
            py = float(block.placed["y"])
            rot = float(block.placed.get("rotation_deg", 0))
            top.add(gdstk.Reference(cell, origin=(px, py), rotation=rot * 3.14159 / 180))

    lib.write_gds(str(out_path))
    print(f"GDS written to {out_path}")
