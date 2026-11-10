"""
Spacing of mixed N/P blocks (digital proximity composites): the worst case over
the member device types. Expected values from myPDK/gpdk090_device_rules.json:
  between_topologies same_cellNames         active 0.2, poly 0.3
  between_topologies different_bulks        WPE_active 2, WPE_poly 3  (nmos VSSA vs pmos VDDA)
  between_topologies different_deviceGroups WPE_active 2, WPE_poly 2  (LV vs passive)
"""
import pytest

from hierarchy_builder import build_composite_blocks
from spacing import compute_block_spacing, is_wpe_pair

MIXED = {"device_type": "nmos_rvt+pmos_rvt"}


def test_mixed_vs_nmos_takes_the_pmos_well_rule():
    # nmos–nmos (0.2, 0.3) vs pmos–nmos (2, 3) → (2, 3)
    sp = compute_block_spacing(MIXED, {"device_type": "nmos_rvt"})
    assert (sp.x_spacing, sp.y_spacing) == pytest.approx((2.0, 3.0))
    assert is_wpe_pair(MIXED, {"device_type": "nmos_rvt"})


def test_mixed_vs_resistor():
    # nmos–res and pmos–res are both different_deviceGroups (2, 2)
    sp = compute_block_spacing({"device_type": "res_poly"}, MIXED)
    assert (sp.x_spacing, sp.y_spacing) == pytest.approx((2.0, 2.0))


def test_inverter_composite_lists_both_device_types():
    group = {"group_id": 0, "topology_type": "inverter", "block_ids": [1, 2],
             "matching_variants": [{"width_um": 1.0, "height_um": 2.0}]}
    blocks = {1: {"device_type": "nmos_rvt"}, 2: {"device_type": "pmos_rvt"}}
    [comp], _ = build_composite_blocks([group], blocks)
    assert comp["device_type"] == "nmos_rvt+pmos_rvt"
