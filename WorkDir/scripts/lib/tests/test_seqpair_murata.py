"""
Sequence-pair decode vs. Murata et al., "Rectangle-Packing-Based Module Placement",
ICCAD 1995 (thesis reference Murata1996_SP.pdf) — approved 2026-11-05.

Example: (Γ+, Γ−) = (abdecf, cbfade), Fig. 4 / Fig. 6. The paper gives no module sizes,
so sizes are chosen here (w × h): a 2×2, b 2×1.5, c 3×1.5, d 2×3, e 1×2.5, f 2.5×2.5,
all nmos_rvt -> gpdk090 same_cellNames gaps: x 0.2, y 0.3.

Horizontal (§2.2 M^aa "right to", §3.2 longest path in G_H):
  x' right of x  <=>  x' after x in both Γ+ and Γ−
  edges a→d, a→e, b→d, b→e, b→f, d→e, c→f
  x_a = x_b = x_c = 0
  x_d = max(w_a, w_b) + 0.2                     = 2.2
  x_f = max(w_b, w_c) + 0.2                     = 3.2
  x_e = max(w_a + 0.2, w_b + 0.2, x_d + w_d + 0.2) = 4.4      width = max(5.4, 5.7) = 5.7

Vertical: the decoder uses Murata's M^ab relation mirrored in y (accepted by the user
2026-11-05: same relations, y axis flipped). Murata: x' after x in Γ+ and before x in Γ−
=> x' BELOW x; here => x' ABOVE x. Pairs (x, x'): (a: b, c, f), (b: c), (d: c, f), (e: c, f).
  y_a = y_d = y_e = 0
  y_b = y_a + h_a + 0.3                                   = 2.3
  y_f = max(y_a + h_a, y_d + h_d, y_e + h_e) + 0.3 = 3 + 0.3 = 3.3
  y_c = max(y_a + h_a, y_b + h_b, y_d + h_d, y_e + h_e) + 0.3 = 3.8 + 0.3 = 4.1
  height = max(c 5.6, f 5.8) = 5.8 — the same height as Murata's (unmirrored) packing.
"""
import pytest

from seqpair_topology import SequencePairTopology

SIZES = {"a": (2.0, 2.0), "b": (2.0, 1.5), "c": (3.0, 1.5), "d": (2.0, 3.0), "e": (1.0, 2.5), "f": (2.5, 2.5)}


def _decode(r_plus, r_minus):
    blocks = {k: {"device_type": "nmos_rvt", "variants": [
        {"main_bbox": {"x_min": 0.0, "y_min": 0.0, "x_max": w, "y_max": h}, "is_used": True}]}
        for k, (w, h) in SIZES.items()}
    topo = SequencePairTopology(blocks, [])
    topo.seed(blocks, mode="ordered")
    topo._r_plus, topo._r_minus = list(r_plus), list(r_minus)
    return topo.decode()


def test_murata_fig4_coordinates():
    pos = _decode("abdecf", "cbfade")
    expected = {"a": (0.0, 0.0), "b": (0.0, 2.3), "c": (0.0, 4.1),
                "d": (2.2, 0.0), "e": (4.4, 0.0), "f": (3.2, 3.3)}
    for k, (x, y) in expected.items():
        assert pos[k] == (pytest.approx(x, abs=1e-9), pytest.approx(y, abs=1e-9)), k


def test_murata_section_2_2_relations_of_b():
    # §2.2 example for module b: M^aa(b) = {d, e, f} right of b, M^bb(b) = ∅,
    # M^ba(b) = {a} (Murata: above b -> mirrored: below), M^ab(b) = {c} (below -> mirrored: above)
    pos = _decode("abdecf", "cbfade")
    w_b, h_b = SIZES["b"]
    for k in "def":
        assert pos[k][0] >= pos["b"][0] + w_b
    assert pos["a"][1] + SIZES["a"][1] <= pos["b"][1]
    assert pos["c"][1] >= pos["b"][1] + h_b
