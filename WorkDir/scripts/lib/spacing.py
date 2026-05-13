"""
DRC block-to-block spacing for placement decode().

compute_block_spacing(block_a, block_b) → SpacingResult
Called inside every topology decode() to determine required clearance
between adjacent block envelopes. Backed by gpdk090_device_rules.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

# =============================================================================
# CONSTANTS
# =============================================================================
_RULES_PATH = Path(__file__).parent.parent.parent / "myPDK" / "gpdk090_device_rules.json"

# Fallback spacings (µm) when no device-specific rule applies
_DEFAULT_X_SPACING = 1.0
_DEFAULT_Y_SPACING = 1.0

# Conservative clearance for cross-device-type pairs (µm)
_CROSS_TYPE_SPACING = 1.5

_rules_cache: dict | None = None


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

    block_a / block_b must contain key "device_type" matching gpdk090 names.
    Negative device_spacing values (envelope overlap allowed) are clamped to 0.

    Convention for unrotated devices: active direction ≈ horizontal (source-drain),
    poly direction ≈ vertical (channel-width). compute_block_spacing does not know
    the active rotation variant — the topology decode() owns that mapping.
    """
    rules = _load_rules()
    dt_a: str = block_a.get("device_type", "")
    dt_b: str = block_b.get("device_type", "")

    if dt_a and dt_a == dt_b:
        entry = (
            rules
            .get("device_spacing", {})
            .get(dt_a, {})
            .get("same_cellNames", {})
        )
        # active → horizontal (source-drain axis), poly → vertical (channel-width axis)
        x_sp = max(0.0, float(entry.get("active", _DEFAULT_X_SPACING)))
        y_sp = max(0.0, float(entry.get("poly",   _DEFAULT_Y_SPACING)))
        return SpacingResult(x_spacing=x_sp, y_spacing=y_sp)

    # Different device types: conservative cross-type clearance
    return SpacingResult(x_spacing=_CROSS_TYPE_SPACING, y_spacing=_CROSS_TYPE_SPACING)
