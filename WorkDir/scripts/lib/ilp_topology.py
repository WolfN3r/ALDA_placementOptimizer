"""
ILP placement topology — stores (x, y) solution coordinates as state.

Not a search topology: state is a direct coordinate map, not a tree or permutation.
seed() row-packs blocks left-to-right so the pipeline has a valid initial decode()
for cost normalization. ILPOptimizer.run() replaces state with the MIP solution
via set_solution().
"""
from __future__ import annotations

# =============================================================================
# 1. IMPORTS
# =============================================================================
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from topology_base import TopologyBase
from spacing import compute_block_spacing
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

class ILPTopology(TopologyBase):
    """
    Coordinate-space topology for ILP placement.

    State is {bid: (x, y)} positions + {bid: variant_idx}.
    seed() produces a row-packed initial layout. ILPOptimizer replaces
    state with the MIP solution via set_solution().
    """

    def __init__(self, blocks: dict, nets: list, sym_groups: list | None = None) -> None:
        self._blocks:     dict                         = {bid: b for bid, b in blocks.items() if "error" not in b}
        self._nets:       list                         = nets
        self._sym_groups: list                         = sym_groups or []
        self._positions:  dict[str, tuple[float, float]] = {}
        self._variant_map: dict[str, int]              = {}

    def seed(self, blocks: dict, mode: str = "random") -> None:
        """Row-pack blocks left-to-right with variant 0 and DRC spacing between adjacent blocks."""
        valid = {bid: b for bid, b in blocks.items() if "error" not in b}
        x_cursor = 0.0
        prev_bid: str | None = None

        for bid, block in valid.items():
            variants = block.get("variants", [])
            v = variants[0] if variants else {}
            bb = v.get("main_bbox", {})
            w = bb.get("x_max", 0.0)

            if prev_bid is not None:
                spacing = compute_block_spacing(valid[prev_bid], block)
                x_cursor += spacing.x_spacing

            self._positions[bid]   = (round(x_cursor, 6), 0.0)
            self._variant_map[bid] = 0
            x_cursor += w
            prev_bid = bid

        logger.debug("ILPTopology seeded %d blocks in row-pack layout", len(valid))

    def decode(self) -> dict[str, tuple[float, float]]:
        return dict(self._positions)

    def copy_state(self) -> Any:
        return {
            "positions":   dict(self._positions),
            "variant_map": dict(self._variant_map),
        }

    def restore_state(self, saved: Any) -> None:
        self._positions   = dict(saved["positions"])
        self._variant_map = dict(saved["variant_map"])

    def capabilities(self) -> set[str]:
        # Deliberately excludes "SA" — prevents accidental SA calibration
        return {"ILP"}

    def get_variant_map(self) -> dict[str, int]:
        return dict(self._variant_map)

    def set_solution(
        self,
        positions:   dict[str, tuple[float, float]],
        variant_map: dict[str, int],
    ) -> None:
        """Atomically install the MIP solution. Called by ILPOptimizer after solving."""
        self._positions   = dict(positions)
        self._variant_map = dict(variant_map)
