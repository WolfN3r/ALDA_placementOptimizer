"""
DRC block-to-block spacing for placement decode().

compute_block_spacing(block_a, block_b) → SpacingResult
Called inside every topology decode() to determine required clearance
between adjacent block envelopes. Backed by gpdk090_device_rules.json.

Classification and spacing values mirror drc_checker._classify_pair and
_get_required_spacing, so placement positions satisfy the same rules DRC
verification enforces.

A LUT over all (device_type_a, device_type_b) pairs is built on the first
call and reused thereafter — no file I/O or dict traversal during the SA
hot loop.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

# =============================================================================
# CONSTANTS
# =============================================================================
_RULES_PATH = Path(__file__).parent.parent.parent / "myPDK" / "gpdk090_device_rules.json"

# Fallback spacings (µm) when a PDK entry is missing — worst-case safe values
# matching same_cellNames minimums so unknown types never violate that category.
_DEFAULT_X_SPACING = 2.0
_DEFAULT_Y_SPACING = 3.0

_rules_cache: dict | None = None
_lut_cache: dict[tuple[str, str], "SpacingResult"] | None = None


def _load_rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)
    return _rules_cache


# =============================================================================
# PUBLIC API
# =============================================================================

class SpacingResult(NamedTuple):
    x_spacing: float  # required horizontal clearance (right edge A → left edge B)
    y_spacing: float  # required vertical clearance  (top edge A → bottom edge B)


def compute_block_spacing(block_a: dict, block_b: dict) -> SpacingResult:
    """
    Return minimum DRC clearance between two block envelopes.

    Classification uses the device_topology decision tree (same as
    drc_checker._classify_pair).  Values come from between_topologies (same
    as drc_checker._get_required_spacing).  A module-level LUT is built on
    the first call; SA hot-loop iterations cost only a single dict lookup.

    block_a / block_b must contain key "device_type" matching PDK names.
    """
    global _lut_cache
    dt_a: str = block_a.get("device_type", "")
    dt_b: str = block_b.get("device_type", "")

    if _lut_cache is None:
        _lut_cache = _build_lut(_load_rules())

    result = _lut_cache.get((dt_a, dt_b))
    if result is None:
        # Type not seen at LUT-build time (e.g. block has a new/unknown device_type).
        # Classify on-the-fly and cache the result for subsequent calls.
        rules = _load_rules()
        category = _classify(dt_a, dt_b, rules.get("device_topology", {}))
        result = _resolve(category, rules.get("between_topologies", {}))
        _lut_cache[(dt_a, dt_b)] = result
        _lut_cache[(dt_b, dt_a)] = result   # spacing is symmetric

    return result


# =============================================================================
# INTERNAL — LUT CONSTRUCTION
# =============================================================================

def _classify(dt_a: str, dt_b: str, device_topology: dict) -> str:
    """
    Return the between_topologies category key for a device-type pair.

    Decision tree (mirrors drc_checker._classify_pair):
      same type                           → same_cellNames
      either type unknown in PDK          → different_deviceGroups  (worst case)
      device_group differs                → different_deviceGroups
      same group, bulk differs            → different_bulks
      same group, same bulk, diff type    → same_deviceGroups
    """
    if dt_a == dt_b:
        return "same_cellNames"
    info_a = device_topology.get(dt_a)
    info_b = device_topology.get(dt_b)
    # Guard against non-dict entries (e.g. "_comment" keys in the JSON)
    if not isinstance(info_a, dict) or not isinstance(info_b, dict):
        return "different_deviceGroups"
    if info_a.get("device_group") != info_b.get("device_group"):
        return "different_deviceGroups"
    if info_a.get("bulk") != info_b.get("bulk"):
        return "different_bulks"
    return "same_deviceGroups"


def _resolve(category: str, between_topologies: dict) -> SpacingResult:
    """
    Map a between_topologies category to a SpacingResult.

    WPE entries use WPE_active / WPE_poly keys; all others use active / poly.
    (Mirrors drc_checker._get_required_spacing for the between_topologies path.)
    """
    entry = between_topologies.get(category, {})
    if "WPE_active" in entry:
        x_sp = float(entry["WPE_active"])
        y_sp = float(entry["WPE_poly"])
    else:
        x_sp = float(entry.get("active", _DEFAULT_X_SPACING))
        y_sp = float(entry.get("poly",   _DEFAULT_Y_SPACING))
    return SpacingResult(x_spacing=max(0.0, x_sp), y_spacing=max(0.0, y_sp))


# ---------------------------------------------------------------------------
# WPE pair detection (cached LUT — same pattern as _lut_cache)
# ---------------------------------------------------------------------------

_WPE_CATEGORIES: frozenset[str] = frozenset({"different_bulks", "different_deviceGroups"})
_wpe_lut_cache: dict[tuple[str, str], bool] | None = None


def is_wpe_pair(block_a: dict, block_b: dict) -> bool:
    """
    Return True when the block pair requires WPE corner-distance rules.

    Backed by the same device_topology as compute_block_spacing.  A module-level
    LUT is built on the first call — O(1) per lookup in the SA hot loop.
    """
    global _wpe_lut_cache
    dt_a: str = block_a.get("device_type", "")
    dt_b: str = block_b.get("device_type", "")
    if _wpe_lut_cache is None:
        _wpe_lut_cache = _build_wpe_lut(_load_rules())
    return _wpe_lut_cache.get((dt_a, dt_b), False)


def _build_wpe_lut(rules: dict) -> dict[tuple[str, str], bool]:
    device_topology = rules.get("device_topology", {})
    types = [k for k, v in device_topology.items() if isinstance(v, dict)] + [""]
    lut: dict[tuple[str, str], bool] = {}
    for dt_a in types:
        for dt_b in types:
            cat = _classify(dt_a, dt_b, device_topology)
            lut[(dt_a, dt_b)] = cat in _WPE_CATEGORIES
    return lut


def _build_lut(rules: dict) -> dict[tuple[str, str], SpacingResult]:
    """
    Pre-compute SpacingResult for every (dt_a, dt_b) pair.

    Enumerates all device types from device_topology plus "" (unknown fallback).
    For 4 PDK device types this yields 25 entries — built once, used for all
    subsequent compute_block_spacing calls during optimization.
    """
    device_topology    = rules.get("device_topology", {})
    between_topologies = rules.get("between_topologies", {})
    # Skip metadata keys (e.g. "_comment") — only include proper device type entries
    types = [k for k, v in device_topology.items() if isinstance(v, dict)] + [""]
    lut: dict[tuple[str, str], SpacingResult] = {}
    for dt_a in types:
        for dt_b in types:
            category          = _classify(dt_a, dt_b, device_topology)
            lut[(dt_a, dt_b)] = _resolve(category, between_topologies)
    return lut
