#!/usr/bin/env python3
"""
Human-editable library of analog topology matching rules.

Each entry defines the matching constraints and intra-device spacing for one
topology type recognised by the symmetry detector. Add a new topology by
adding one dict entry — no other code needs to change.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from __future__ import annotations

# =============================================================================
# 2. CONSTANTS  — all topology rules live here, nowhere else
# =============================================================================

# Priority used when a compound group contains mixed topology pairs.
# Higher number = takes precedence when tagging the whole group.
_TYPE_PRIORITY: dict[str, int] = {
    "diff_pair":             5,
    "cascode_current_mirror": 4,
    "current_mirror":        3,
    "tail_cm_pair":          2,
    "passive":               1,
    "tail_transistor":       0,
}

# Matching rules per topology.
#
# Field notes:
#   allowed_multipliers     — valid device multiplier values (must include >= 2 for DP)
#   rows_range              — (min, max) device rows in the matched array (excl. dummies)
#   cols_range              — (min, max) device columns per device in the array
#   dummy_cols_per_side     — gate-connected dummy columns left + right of the device array
#   dummy_rows_top_bottom   — poly-protection dummy rows above + below the device array
#   dummy_gate_policy       — "connected" ties dummy gates to power; "floating" leaves them open
#   intra_spacing_x         — µm between horizontally adjacent device slots (negative = shared bulk)
#   intra_spacing_y         — µm between vertically adjacent device slots (usually 0 for same well)
#   common_centroid         — True requires >= 2 positions per device for ABBA interdigitation
TOPOLOGY_RULES: dict[str, dict] = {
    "diff_pair": {
        # min multiplier 2 ensures at least one ABBA split (AB | BA)
        "allowed_multipliers":    [2, 4, 8],
        "rows_range":             (1, 4),
        "cols_range":             (1, 8),
        "dummy_cols_per_side":    1,
        "dummy_rows_top_bottom":  1,
        "dummy_gate_policy":      "connected",
        "intra_spacing_x":        -0.24,
        "intra_spacing_y":         0.0,
        "common_centroid":         True,
    },
    "current_mirror": {
        "allowed_multipliers":    [2, 4, 6, 8, 10, 12, 16],
        "rows_range":             (1, 4),
        "cols_range":             (1, 8),
        "dummy_cols_per_side":    1,
        "dummy_rows_top_bottom":  1,
        "dummy_gate_policy":      "connected",
        "intra_spacing_x":        -0.24,
        "intra_spacing_y":         0.0,
        "common_centroid":         False,
    },
    "cascode_current_mirror": {
        "allowed_multipliers":    [2, 4, 8],
        "rows_range":             (1, 2),   # cascodes are naturally a 2-row stack
        "cols_range":             (1, 8),
        "dummy_cols_per_side":    1,
        "dummy_rows_top_bottom":  1,
        "dummy_gate_policy":      "connected",
        "intra_spacing_x":        -0.24,
        "intra_spacing_y":         0.0,
        "common_centroid":         True,
    },
    "tail_transistor": {
        # Self-symmetric; placed alone — no matching needed
        "allowed_multipliers":    [1, 2, 4, 8],
        "rows_range":             (1, 4),
        "cols_range":             (1, 8),
        "dummy_cols_per_side":    0,
        "dummy_rows_top_bottom":  0,
        "dummy_gate_policy":      "connected",
        "intra_spacing_x":         0.0,
        "intra_spacing_y":         0.0,
        "common_centroid":         False,
    },
    "tail_cm_pair": {
        # Tail transistor + its Vbias current mirror — ratio must be preserved
        "allowed_multipliers":    [2, 4, 8],
        "rows_range":             (1, 4),
        "cols_range":             (1, 8),
        "dummy_cols_per_side":    1,
        "dummy_rows_top_bottom":  1,
        "dummy_gate_policy":      "connected",
        "intra_spacing_x":        -0.24,
        "intra_spacing_y":         0.0,
        "common_centroid":         True,
    },
}

# Fallback when an unknown topology type is requested
_DEFAULT_RULES: dict = TOPOLOGY_RULES["current_mirror"]

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def get_topology_rules(topology_type: str) -> dict:
    return TOPOLOGY_RULES.get(topology_type, _DEFAULT_RULES)


def dominant_type(types: set[str]) -> str:
    """Return the highest-priority topology tag from a set of type strings."""
    if not types:
        return "tail_transistor"
    return max(types, key=lambda t: _TYPE_PRIORITY.get(t, 0))
