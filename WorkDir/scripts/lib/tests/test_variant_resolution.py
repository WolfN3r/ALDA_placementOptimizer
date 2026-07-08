"""
Unit tests for cost_evaluator.resolve_variant() — the single source of truth
for "which variant is block X actually using".

Regression context: composite/grouped blocks get variants[k]["is_used"] frozen
to k==0 at construction time (hierarchy_builder.build_composite_blocks), and
that flag is never updated when the optimizer later selects a different
variant during search. resolve_variant() must prefer the live variant_map
over that stale flag.
"""
from cost_evaluator import resolve_variant


def _block(variants):
    return {"variants": variants}


def test_variant_map_wins_over_is_used():
    # variant 0 is marked is_used, but variant_map says the optimizer chose 1 —
    # this is the exact bug scenario: resolve_variant must return variant 1.
    block = _block([
        {"main_bbox": {"x_max": 10.0, "y_max": 5.0}, "is_used": True},
        {"main_bbox": {"x_max": 20.0, "y_max": 3.0}, "is_used": False},
    ])
    v = resolve_variant(block, "bid1", {"bid1": 1})
    assert v["main_bbox"]["x_max"] == 20.0
    assert v["main_bbox"]["y_max"] == 3.0


def test_missing_bid_falls_back_to_is_used():
    block = _block([
        {"main_bbox": {"x_max": 10.0, "y_max": 5.0}, "is_used": False},
        {"main_bbox": {"x_max": 20.0, "y_max": 3.0}, "is_used": True},
    ])
    v = resolve_variant(block, "bid1", {})
    assert v["main_bbox"]["x_max"] == 20.0


def test_no_is_used_and_missing_bid_falls_back_to_variants_zero():
    block = _block([
        {"main_bbox": {"x_max": 10.0, "y_max": 5.0}},
        {"main_bbox": {"x_max": 20.0, "y_max": 3.0}},
    ])
    v = resolve_variant(block, "bid1", {})
    assert v["main_bbox"]["x_max"] == 10.0


def test_out_of_range_variant_map_index_falls_back():
    block = _block([
        {"main_bbox": {"x_max": 10.0, "y_max": 5.0}, "is_used": True},
    ])
    v = resolve_variant(block, "bid1", {"bid1": 5})
    assert v["main_bbox"]["x_max"] == 10.0


def test_empty_variants_returns_empty_dict():
    assert resolve_variant({"variants": []}, "bid1", {"bid1": 0}) == {}
    assert resolve_variant({}, "bid1", {}) == {}
