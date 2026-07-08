"""
CostEvaluator tests focused on the variant-selection fix: composite/grouped
blocks must be measured using the variant the optimizer actually selected
(variant_map), not the frozen construction-time is_used flag.
"""
from cost_evaluator import CostEvaluator, CostWeights


def _fixture():
    # "A" — plain block, single variant.
    # "B" — composite-style block: two variants, is_used stuck on variant 0
    # (reproducing hierarchy_builder.build_composite_blocks's "is_used": k==0).
    blocks = {
        "A": {"variants": [
            {"main_bbox": {"x_max": 2.0, "y_max": 1.0}, "is_used": True, "pin_positions": {}},
        ]},
        "B": {"variants": [
            {"main_bbox": {"x_max": 4.0, "y_max": 2.0}, "is_used": True, "pin_positions": {}},
            {"main_bbox": {"x_max": 10.0, "y_max": 3.0}, "is_used": False, "pin_positions": {}},
        ]},
    }
    positions = {"A": (0.0, 0.0), "B": (2.0, 0.0)}
    nets: list = []
    return blocks, positions, nets


def test_bbox_area_honors_variant_map_over_is_used():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(blocks, nets, init_area=1.0, init_wl=1.0, use_power_rails=False)

    # Optimizer actually selected variant 1 (10x3) for B.
    area_with_map = ev._bbox_area(positions, {"B": 1})
    # x spans: A [0,2], B [2,12] -> x_max=12; y spans: A [0,1], B [0,3] -> y_max=3
    assert area_with_map == 12.0 * 3.0

    # Without a variant_map, falls back to the stale is_used flag (variant 0, 4x2).
    area_fallback = ev._bbox_area(positions, {})
    assert area_fallback == 6.0 * 2.0

    assert area_with_map != area_fallback


def test_aspect_ratio_honors_variant_map():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(blocks, nets, init_area=1.0, init_wl=1.0, use_power_rails=False)

    assert ev._aspect_ratio(positions, {"B": 1}) == 12.0 / 3.0
    assert ev._aspect_ratio(positions, {}) == 6.0 / 2.0


def test_evaluate_default_variant_map_is_backward_compatible():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(
        blocks, nets, init_area=12.0, init_wl=1.0,
        weights=CostWeights(area_weight=1.0, wirelength_weight=0.0),
        use_power_rails=False,
    )
    # No variant_map passed at all -> same as passing None -> falls back to is_used.
    cost_no_arg = ev.evaluate(positions)
    cost_none   = ev.evaluate(positions, None)
    cost_empty  = ev.evaluate(positions, {})
    assert cost_no_arg == cost_none == cost_empty
    # area = 12.0 (fallback bbox), init_area = 12.0 -> area term = 1.0
    assert cost_no_arg == 1.0


def test_evaluate_uses_variant_map_when_given():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(
        blocks, nets, init_area=36.0, init_wl=1.0,
        weights=CostWeights(area_weight=1.0, wirelength_weight=0.0),
        use_power_rails=False,
    )
    cost = ev.evaluate(positions, {"B": 1})
    # area = 36.0 (true bbox with B's real selected variant), init_area = 36.0
    assert cost == 1.0
