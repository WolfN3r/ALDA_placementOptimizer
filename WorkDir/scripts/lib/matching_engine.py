#!/usr/bin/env python3
"""
Enumerate all valid matched-array geometries for a group of symmetric devices.

Given a list of blocks and a topology-rules dict (from topology_library),
compute every (rows × cols_per_device) combination that satisfies the matching
constraints and return a list of bounding-rectangle variants.  The placement
optimizer picks from these variants exactly as it picks block rotation variants.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from __future__ import annotations
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_ROUND_DIGITS = 3   # µm precision for width / height output

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _unit_cell_dimensions(blocks: list) -> tuple[float, float]:
    """
    Return (width_µm, height_µm) of the M=1 unit transistor (the matching unit cell).

    Prefers unit_cell_w/h stored by the block generator (exact PDK formula, 1 row × NF cols,
    no aspect ratio constraint).  Falls back to proportional scaling for old JSON files.
    """
    for blk in blocks:
        uw = blk.get("unit_cell_w")
        uh = blk.get("unit_cell_h")
        if uw and uh:
            return float(uw), float(uh)
    # Backward-compat fallback: proportional scaling full_block → M=1 unit
    for blk in blocks:
        NF     = blk.get("parameters", {}).get("num_fingers", 1)
        for v in blk.get("variants", []):
            if not v.get("is_used", False):
                continue
            bb     = v["main_bbox"]
            full_w = bb["x_max"] - bb["x_min"]
            full_h = bb["y_max"] - bb["y_min"]
            cols_L = v.get("layout", {}).get("cols", 1)
            rows_L = v.get("layout", {}).get("rows", 1)
            if cols_L > 0 and NF > 0:
                return (
                    round(full_w * NF / cols_L, _ROUND_DIGITS),
                    round(full_h / rows_L,       _ROUND_DIGITS),
                )
            M = blk.get("parameters", {}).get("multiplier", 1)
            if M > 1:
                return round(full_w / M, _ROUND_DIGITS), full_h
    return 1.0, 1.0


def _bbox_for_array(
    dev_w: float,
    dev_h: float,
    n_dev_cols: int,
    n_rows: int,
    dummy_cols: int,
    dummy_rows: int,
    spacing_x: float,
    spacing_y: float,
) -> tuple[float, float]:
    """
    Compute the bounding box of a matched device array.

    The array has n_dev_cols device-width columns (all devices together) plus
    dummy_cols on each side, and n_rows device-height rows plus dummy_rows on
    each side.  spacing_x / spacing_y are applied between every adjacent pair
    of columns / rows (can be negative for shared-bulk overlap).
    """
    total_cols = n_dev_cols + 2 * dummy_cols
    total_rows = n_rows     + 2 * dummy_rows

    if total_cols > 1:
        w = dev_w * total_cols + (total_cols - 1) * spacing_x
    else:
        w = dev_w

    if total_rows > 1:
        h = dev_h * total_rows + (total_rows - 1) * spacing_y
    else:
        h = dev_h

    return max(0.0, round(w, _ROUND_DIGITS)), max(0.0, round(h, _ROUND_DIGITS))


def compute_matching_variants(blocks: list, rules: dict) -> List[dict]:
    """
    Return all valid matching-array variants for the given group of blocks.

    Each variant describes how many device rows and columns per device are used,
    how many dummy columns/rows are added, and the resulting bounding rectangle.
    The placer selects one variant during optimisation.

    Enumeration is driven by total_M = sum(multiplier_i), not by rule-defined bounds.
    Only factorizations (rows, total_dev_cols) of total_M are generated, filtered by:
      - total_dev_cols must be divisible by num_devices (equal column allocation)
      - rows <= total_dev_cols (exclude tall-thin strips with bad matching shape)
    matching_type is "common_centroid" when rows >= 2, else "interdigitated".
    """
    if not blocks:
        return []

    dev_w, dev_h = _unit_cell_dimensions(blocks)
    num_devices  = len(blocks)

    dummy_cols   = rules["dummy_cols_per_side"]
    dummy_rows   = rules["dummy_rows_top_bottom"]
    spacing_x    = rules["intra_spacing_x"]
    spacing_y    = rules["intra_spacing_y"]

    multipliers = [b["parameters"].get("multiplier", 1) for b in blocks]
    total_M = sum(multipliers)
    if len(set(multipliers)) > 1:
        logger.info(
            "Unequal multipliers in group %s — using sum=%d across %d devices "
            "(equal column split per device, total_M columns in array)",
            [b.get("block_id") for b in blocks], total_M, len(blocks),
        )
    if total_M <= 1:
        logger.info("total_M=%d: single transistor, no matching variants generated", total_M)
        return []

    variants: List[dict] = []

    for total_dev_cols in range(1, total_M + 1):
        if total_M % total_dev_cols != 0:
            continue                        # total_dev_cols must divide total_M
        rows = total_M // total_dev_cols
        if total_dev_cols % num_devices != 0:
            continue                        # must split equally across devices
        if rows > total_dev_cols:
            continue                        # tall-thin strip: bad matching shape
        cols_per_dev = total_dev_cols // num_devices

        m_type = "common_centroid" if rows >= 2 else "interdigitated"

        w, h = _bbox_for_array(
            dev_w, dev_h,
            total_dev_cols, rows,
            dummy_cols, dummy_rows,
            spacing_x, spacing_y,
        )

        variants.append({
            "rows":                  rows,
            "cols_per_device":       cols_per_dev,
            "matching_type":         m_type,
            "dummy_cols_per_side":   dummy_cols,
            "dummy_rows_top_bottom": dummy_rows,
            "width_um":              w,
            "height_um":             h,
        })
        logger.debug(
            "Variant rows=%d cols_per_dev=%d (%s) → %.3f × %.3f µm",
            rows, cols_per_dev, m_type, w, h,
        )

    logger.info(
        "Matching variants for %d devices (total_M=%d, unit_cell=%.3f × %.3f µm): %d combinations",
        num_devices, total_M, dev_w, dev_h, len(variants),
    )
    return variants
