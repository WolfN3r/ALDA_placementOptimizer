"""
Real-data regression test for the stale-is_used-variant bug.

Uses WorkDir/json_files/s42_n5_py101_v01.json as a fixture — no solver
re-run needed. For each successful run in that file we:

  1. Reconstruct `blocks` the way hierarchy_builder.build_composite_blocks
     would build them for the composite/grouped blocks (10000, 10001),
     including the frozen "is_used": (k == 0) flag — this reproduces the
     exact stale-flag scenario that caused the bug.
  2. Reconstruct `positions` from that run's own placed_blocks main_bbox
     (the x_min/y_min corner of each top-level block).
  3. Infer variant_map by matching each block's placed (width, height)
     against its own variants list — i.e. "which variant did the optimizer
     actually place".
  4. Assert pipeline._bbox_area(positions, blocks, variant_map) equals the
     TRUE union bbox area, independently computed straight from the same
     run's placed_blocks main_bbox rectangles (ground truth, unaffected by
     the bug since _compute_placed_blocks already consumed variant_map
     correctly before this fix).

This fails against the pre-fix code (which ignores variant_map) and passes
once the resolver fix is in place.
"""
import json
from pathlib import Path

import pytest

import pipeline

_FIXTURE = (
    Path(__file__).resolve().parents[3] / "json_files" / "s42_n5_py101_v01.json"
)

_COMPOSITE_ID_BASE = 10_000


def _load_fixture() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _build_blocks(raw: dict) -> dict:
    """Mimic hierarchy_builder's output shape: plain blocks as-is, composite
    group blocks built from matching_variants with the stale is_used=(k==0)."""
    blocks: dict = {}
    for b in raw["blocks"]:
        blocks[str(b["block_id"])] = {"variants": b["variants"]}

    for group in raw["groups"]:
        composite_bid = str(_COMPOSITE_ID_BASE + group["group_id"])
        variants = []
        for k, mv in enumerate(group["matching_variants"]):
            w = float(mv["width_um"])
            h = float(mv["height_um"])
            variants.append({
                "main_bbox": {"x_min": 0.0, "y_min": 0.0, "x_max": w, "y_max": h},
                "is_used": (k == 0),   # <- the frozen construction-time flag
            })
        blocks[composite_bid] = {"variants": variants}
    return blocks


def _true_bbox_area(placed_blocks: dict, bids: list[str]) -> float:
    xs_min, ys_min, xs_max, ys_max = [], [], [], []
    for bid in bids:
        bb = placed_blocks[bid]["main_bbox"]
        xs_min.append(bb["x_min"]); ys_min.append(bb["y_min"])
        xs_max.append(bb["x_max"]); ys_max.append(bb["y_max"])
    return (max(xs_max) - min(xs_min)) * (max(ys_max) - min(ys_min))


def _infer_variant_idx(variants: list[dict], width: float, height: float) -> int:
    for i, v in enumerate(variants):
        bb = v["main_bbox"]
        if abs(bb["x_max"] - width) < 1e-3 and abs(bb["y_max"] - height) < 1e-3:
            return i
    raise AssertionError(f"no variant matches placed size ({width}, {height})")


def _successful_runs():
    raw = _load_fixture()
    return [r for r in raw["placement"]["runs"] if r.get("status") == "success"]


@pytest.mark.parametrize("run_id", [r["run_id"] for r in _successful_runs()])
def test_area_matches_true_bbox_for_every_run(run_id):
    raw = _load_fixture()
    blocks = _build_blocks(raw)
    run = next(r for r in raw["placement"]["runs"] if r["run_id"] == run_id)
    placed_blocks = run["placed_blocks"]

    bids = [
        bid for bid in placed_blocks
        if not bid.startswith("__") and bid in blocks
    ]
    assert bids, f"no top-level blocks found in {run_id}'s placed_blocks"

    positions = {
        bid: (placed_blocks[bid]["main_bbox"]["x_min"], placed_blocks[bid]["main_bbox"]["y_min"])
        for bid in bids
    }
    variant_map = {
        bid: _infer_variant_idx(
            blocks[bid]["variants"],
            placed_blocks[bid]["main_bbox"]["x_max"] - placed_blocks[bid]["main_bbox"]["x_min"],
            placed_blocks[bid]["main_bbox"]["y_max"] - placed_blocks[bid]["main_bbox"]["y_min"],
        )
        for bid in bids
    }

    computed_area = pipeline._bbox_area(positions, blocks, variant_map)
    true_area = _true_bbox_area(placed_blocks, bids)

    assert computed_area == pytest.approx(true_area, abs=1e-6)


def test_known_mismatches_from_original_bug_report_are_resolved():
    """Pins the exact numbers from the original bug investigation:
    BStarTopology+SA and SequencePairTopology+SA were under-reported at
    457.0128 (true 946.404); the three ILP-family runs were over-reported
    at 473.1048 (true 457.0128). PSOTopology was already correct (580.1946)
    by coincidence — must stay correct."""
    raw = _load_fixture()
    blocks = _build_blocks(raw)
    expected_true_area = {
        "BStarTopology+SimulatedAnnealingOptimizer":   946.404,
        "SequencePairTopology+SimulatedAnnealingOptimizer": 946.404,
        "ILPTopology+ILPOptimizer":                    457.0128,
        "ILPTopology+PSOILPOptimizer":                 457.0128,
        "ILPTopology+BStarILPOptimizer":               457.0128,
        "PSOTopology+PSOOptimizer":                    580.19464676,
    }
    for run in raw["placement"]["runs"]:
        if run["run_id"] not in expected_true_area:
            continue
        placed_blocks = run["placed_blocks"]
        bids = [bid for bid in placed_blocks if not bid.startswith("__") and bid in blocks]
        positions = {
            bid: (placed_blocks[bid]["main_bbox"]["x_min"], placed_blocks[bid]["main_bbox"]["y_min"])
            for bid in bids
        }
        variant_map = {
            bid: _infer_variant_idx(
                blocks[bid]["variants"],
                placed_blocks[bid]["main_bbox"]["x_max"] - placed_blocks[bid]["main_bbox"]["x_min"],
                placed_blocks[bid]["main_bbox"]["y_max"] - placed_blocks[bid]["main_bbox"]["y_min"],
            )
            for bid in bids
        }
        computed_area = pipeline._bbox_area(positions, blocks, variant_map)
        assert computed_area == pytest.approx(expected_true_area[run["run_id"]], abs=1e-3), run["run_id"]
