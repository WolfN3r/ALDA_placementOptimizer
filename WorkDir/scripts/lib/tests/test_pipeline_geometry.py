"""
pipeline.py's module-level geometry helpers (_bbox_area/_hpwl/_aspect_ratio)
must agree with CostEvaluator's and honor variant_map the same way, since
both now resolve variants via the shared cost_evaluator.resolve_variant().
CostEvaluator.evaluate() must measure composite blocks with the variant the
optimizer selected (variant_map), not the frozen construction-time is_used flag.
"""
import pytest

from cost_evaluator import CostEvaluator, CostWeights
import pipeline


def _fixture():
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


def test_bbox_area_honors_variant_map():
    blocks, positions, nets = _fixture()
    assert pipeline._bbox_area(positions, blocks, {"B": 1}) == 12.0 * 3.0
    assert pipeline._bbox_area(positions, blocks, {}) == 6.0 * 2.0
    assert pipeline._bbox_area(positions, blocks) == 6.0 * 2.0  # default None -> fallback


def test_aspect_ratio_honors_variant_map():
    blocks, positions, nets = _fixture()
    assert pipeline._aspect_ratio(positions, blocks, {"B": 1}) == 12.0 / 3.0
    assert pipeline._aspect_ratio(positions, blocks, {}) == 6.0 / 2.0


def test_pipeline_and_cost_evaluator_agree():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(blocks, nets, init_area=1.0, init_wl=1.0, use_power_rails=False)
    for vm in ({"B": 1}, {}, {"B": 0}):
        assert pipeline._bbox_area(positions, blocks, vm) == ev._bbox_area(positions, vm)
        assert pipeline._aspect_ratio(positions, blocks, vm) == ev._aspect_ratio(positions, vm)


def test_compute_placed_blocks_emits_variant_index():
    blocks, positions, _ = _fixture()
    placed = pipeline._compute_placed_blocks(positions, blocks, {"B": 1, "A": 0})
    assert placed["B"]["variant_index"] == 1
    assert placed["A"]["variant_index"] == 0
    # And the emitted main_bbox reflects the same (real) selected variant.
    assert placed["B"]["main_bbox"]["x_max"] == 2.0 + 10.0
    assert placed["B"]["main_bbox"]["y_max"] == 0.0 + 3.0


def test_compute_placed_blocks_defaults_missing_bid_to_variant_zero():
    blocks, positions, _ = _fixture()
    placed = pipeline._compute_placed_blocks(positions, blocks, {})
    assert placed["B"]["variant_index"] == 0
    assert placed["B"]["main_bbox"]["x_max"] == 2.0 + 4.0


def test_evaluate_default_variant_map_is_backward_compatible():
    blocks, positions, nets = _fixture()
    ev = CostEvaluator(
        blocks, nets, init_area=12.0, init_wl=1.0,
        weights=CostWeights(area_weight=1.0, wirelength_weight=0.0, aspect_ratio_weight=0.0),
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
        weights=CostWeights(area_weight=1.0, wirelength_weight=0.0, aspect_ratio_weight=0.0),
        use_power_rails=False,
    )
    cost = ev.evaluate(positions, {"B": 1})
    # area = 36.0 (true bbox with B's real selected variant), init_area = 36.0
    assert cost == 1.0


# ── HPWL and power rails, hand calculation (approved 2026-11-05) ──────────────

def _hpwl_fixture():
    # A 2x1 at (0, 0), pin p at (1, 0.5) -> absolute (1, 0.5)
    # B 4x2 at (2, 0), pin q at (0.5, 1) -> absolute (2.5, 1)
    blocks = {
        "A": {"variants": [{"main_bbox": {"x_max": 2.0, "y_max": 1.0}, "is_used": True,
                            "pin_positions": {"p": {"x": 1.0, "y": 0.5}}}]},
        "B": {"variants": [{"main_bbox": {"x_max": 4.0, "y_max": 2.0}, "is_used": True,
                            "pin_positions": {"q": {"x": 0.5, "y": 1.0}}}]},
    }
    return blocks, {"A": (0.0, 0.0), "B": (2.0, 0.0)}


@pytest.mark.parametrize("net_id, rails, expected", [
    # [USER 2026-11-10] signal nets centre to centre, as the ILP: A centre (1, 0.5), B centre (4, 1)
    ("n1",  False, 3.5),   # [HAND] |4 - 1| + |1 - 0.5| = 3 + 0.5
    ("VDD", False, 3.5),   # rails off: a supply net is an ordinary net
    ("VDD", True,  2.5),   # [HAND] top rail y = max(0 + 1, 0 + 2) = 2: (2 - 0.5) + (2 - 1)
    ("VSS", True,  1.5),   # [HAND] bottom rail y = 0: (0.5 - 0) + (1 - 0)
])
def test_hpwl_hand_calculation(net_id, rails, expected):
    blocks, positions = _hpwl_fixture()
    nets = [{"net_id": net_id, "pins": ["BA_p", "BB_q"]}]
    ev = CostEvaluator(blocks, nets, init_area=1.0, init_wl=1.0, use_power_rails=rails)
    assert ev._hpwl(positions, {}) == pytest.approx(expected, abs=1e-12)
    assert pipeline._hpwl(positions, blocks, nets, use_power_rails=rails) == pytest.approx(expected, abs=1e-12)


def test_rescale_cost_hand_calculation():
    # [HAND] init_area 10, init_wl 4, all weights 1, target AR 1:
    # 20/10 + 8/4 + (2 - 1)^2 = 2 + 2 + 1 = 5
    blocks, _ = _hpwl_fixture()
    ev = CostEvaluator(blocks, [], init_area=10.0, init_wl=4.0,
                       weights=CostWeights(area_weight=1.0, wirelength_weight=1.0,
                                           aspect_ratio_weight=1.0, target_aspect_ratio=1.0),
                       use_power_rails=False)
    assert ev.rescale_cost(20.0, 8.0, 2.0) == pytest.approx(5.0, abs=1e-12)
