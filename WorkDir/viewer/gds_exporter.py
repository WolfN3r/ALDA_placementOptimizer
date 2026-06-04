"""GDS export — requires gdstk (pip install gdstk)."""
from __future__ import annotations
import json
from pathlib import Path

from json_loader import PlacementData

_PDK_LAYERS_PATH = Path(__file__).parent.parent / "myPDK" / "gpdk090_gds_layers.json"

# Half-side of the marker square drawn for center-point pins (no pin_optimizer)
_PIN_MARKER_HALF = 0.03   # µm → 60 nm square


def _load_layer_map() -> dict[str, int]:
    raw = json.loads(_PDK_LAYERS_PATH.read_text(encoding="utf-8"))
    return {name: info["layer"] for name, info in raw["layers"].items()}


def _bbox_layers(device_type: str, L: dict[str, int]) -> list[int]:
    """Return GDS layer numbers for main_bbox rectangles."""
    if device_type in ("nmos_hvt", "pmos_hvt"):
        return [L["OD_25"], L["PO"]]
    if device_type in ("nmos_rvt", "nmos_lvt", "pmos_rvt", "pmos_lvt"):
        return [L["OD"], L["PO"]]
    if device_type == "res_poly":
        return [L["RPO"], L["PO"]]
    if device_type == "cap_mom":
        return [L["M1"], L["PO"]]
    return [L["OD"], L["PO"]]  # fallback


def export(
    data: PlacementData,
    out_path: str | Path,
    layer_overrides: dict[str, list[int]] | None = None,
    pin_layer: int | None = None,
) -> None:
    """
    Export placed blocks to a GDS-II file.

    All block geometry is drawn flat in the TOP cell using absolute coordinates
    from PlacedBlockInfo.main_bbox.  This correctly handles all rotation cases
    because main_bbox already stores the post-rotation bounding box (same as
    what the ALDA viewer draws).

    Layer assignments:
      device bbox  → OD/OD_25 + PO for transistors; RPO+PO for res_poly; M1+PO for cap_mom
      pins         → M1 (rect if pin_optimizer ran; 60 nm square for center-point pins)
      power rails  → M1
      annotation   → ANN (layer 100): main_bbox outline only (no text labels)

    layer_overrides: {device_type: [layer1_num, layer2_num]} — overrides default bbox layers.
    pin_layer: GDS layer number for pins and power rails (default: M1 = 31).

    Requires: pip install gdstk
    """
    try:
        import gdstk
    except ImportError as e:
        raise RuntimeError("gdstk is not installed. Run: pip install gdstk") from e

    L     = _load_layer_map()
    L_M1  = pin_layer if pin_layer is not None else L["M1"]
    L_ANN = L["ANN"]  # 100

    pr           = data.placement_result
    placed_lookup: dict = pr.placed_blocks if pr else {}
    chip_rails   = pr.chip_power_rails if pr else []

    lib = gdstk.Library("ALDA_placement")
    top = lib.new_cell("TOP")

    # --- Chip-level power rails ---
    for rail in chip_rails:
        top.add(gdstk.rectangle(
            (rail["x_min"], rail["y_min"]),
            (rail["x_max"], rail["y_max"]),
            layer=L_M1,
        ))

    if placed_lookup:
        _export_from_placed_blocks(
            data, top, placed_lookup, L, L_M1, L_ANN, layer_overrides, gdstk
        )
    else:
        _export_from_block_placed(
            data, top, L, L_M1, L_ANN, layer_overrides, gdstk
        )

    lib.write_gds(str(out_path))
    print(f"GDS written to {out_path}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _export_from_placed_blocks(
    data, top, placed_lookup, L, L_M1, L_ANN, layer_overrides, gdstk
) -> None:
    """
    Primary export path: uses placement_result.placed_blocks.
    All geometry drawn flat at absolute main_bbox coordinates — rotation is
    already encoded in main_bbox (its dimensions match the placed orientation),
    so no GDS rotation transform is needed.
    """
    for bid, pb in placed_lookup.items():
        block = data.block_by_id(bid)
        if block is None:
            continue

        bx0, by0, bx1, by1 = pb.main_bbox

        # Device-layer rectangles at absolute placed position
        _layers = (
            layer_overrides.get(block.device_type) if layer_overrides else None
        ) or _bbox_layers(block.device_type, L)
        for layer_num in _layers:
            top.add(gdstk.rectangle((bx0, by0), (bx1, by1), layer=layer_num))

        # Pins
        _write_pins(top, pb.pins, L_M1, gdstk)

        # ANN: bounding-box outline only (no text)
        top.add(gdstk.rectangle((bx0, by0), (bx1, by1), layer=L_ANN))


def _export_from_block_placed(
    data, top, L, L_M1, L_ANN, layer_overrides, gdstk
) -> None:
    """
    Fallback: files where placement coords live in block.placed.
    Rotation is handled by swapping w/h for 90°/270° rotations.
    """
    for block in data.blocks:
        if not (block.placed and "x" in block.placed):
            continue

        variant = data.active_variant(block)
        vx0, vy0, vx1, vy1 = variant.bbox
        w, h = vx1 - vx0, vy1 - vy0

        px  = float(block.placed["x"])
        py  = float(block.placed["y"])
        rot = int(block.placed.get("rotation_deg", 0)) % 360

        # For 90° / 270° rotations the placed dimensions swap
        placed_w, placed_h = (h, w) if rot in (90, 270) else (w, h)
        bx0, by0 = px, py
        bx1, by1 = px + placed_w, py + placed_h

        _layers = (
            layer_overrides.get(block.device_type) if layer_overrides else None
        ) or _bbox_layers(block.device_type, L)
        for layer_num in _layers:
            top.add(gdstk.rectangle((bx0, by0), (bx1, by1), layer=layer_num))

        # ANN: outline only
        top.add(gdstk.rectangle((bx0, by0), (bx1, by1), layer=L_ANN))


def _write_pins(top, pins: dict, L_M1: int, gdstk) -> None:
    """Write pin geometry into the TOP cell."""
    h = _PIN_MARKER_HALF
    for pdata in pins.values():
        if "x_min" in pdata:
            top.add(gdstk.rectangle(
                (float(pdata["x_min"]), float(pdata["y_min"])),
                (float(pdata["x_max"]), float(pdata["y_max"])),
                layer=L_M1,
            ))
        else:
            cx, cy = float(pdata["x"]), float(pdata["y"])
            top.add(gdstk.rectangle(
                (cx - h, cy - h),
                (cx + h, cy + h),
                layer=L_M1,
            ))
