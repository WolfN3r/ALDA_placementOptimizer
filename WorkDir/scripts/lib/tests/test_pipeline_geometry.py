"""
pipeline.py's module-level geometry helpers (_bbox_area/_hpwl/_aspect_ratio)
must agree with CostEvaluator's and honor variant_map the same way, since
both now resolve variants via the shared cost_evaluator.resolve_variant().
"""
from cost_evaluator import CostEvaluator
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
