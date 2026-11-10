"""
Generic PCell abstraction over WorkDir/pdk/<name>/pdk.json (written by
WorkDir/pdk/characterize_pdk.py, a compact tree expanded by
WorkDir/pdk/pdk_tree.py on load). One code path for every device of every
PDK: the device's pdk.json entry says how netlist values become PCell
parameters and gives its footprint as linear terms of those parameters.
Nothing here knows a PDK.

load_pdk(name)                        -> dict
pcell_params(pdk, model, values)      -> {pcell parameter: value}
footprint(pdk, model, pcell_params)   -> (width, height) of one copy, µm
pin_rects(pdk, model, params, group)  -> pin rects of one copy (PCell frame, on grid)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from spice_parser import eval_expr

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

_PDK_ROOT = Path(__file__).resolve().parents[2] / "pdk"
sys.path.insert(0, str(_PDK_ROOT))
import pdk_tree     # noqa: E402  (lives next to the PDK files, shared with the container scripts)
_ROUND = 6
_GRID_TOL = 1e-6        # in grid steps: float noise, not a real step

# =============================================================================
# ALGORITHM
# =============================================================================

def load_pdk(name: str) -> dict:
    path = _PDK_ROOT / name / "pdk.json"
    if not path.exists():
        raise FileNotFoundError(f"load_pdk: {path} missing — run WorkDir/pdk/characterize_pdk.py")
    return pdk_tree.load(path)


def snap(value: float, grid: float) -> float:
    return round(round(value / grid) * grid, _ROUND)


def pcell_params(pdk: dict, model: str, values: dict) -> dict:
    """Netlist values (e.g. {"W", "L", "nf"}) -> PCell parameters, each
    snap_params entry rounded to the grid the PCell draws it on."""
    d = pdk["devices"][model]
    env = {**pdk["netlist_defaults"], **values}
    p = {k: round(eval_expr(v, env), _ROUND) for k, v in d["map"].items()}
    for k, grid in d["snap_params"].items():
        p[k] = snap(p[k], grid)
    return p


def _linear(coefs: dict, env: dict) -> float:
    return sum(c * (1.0 if term == "1" else eval_expr(term, env)) for term, c in coefs.items())


def footprint(pdk: dict, model: str, params: dict) -> tuple[float, float]:
    fp = pdk["devices"][model]["footprint"]
    return round(_linear(fp["w"], params), _ROUND), round(_linear(fp["h"], params), _ROUND)


def _snap_up(value: float, grid: float) -> float:
    return round(math.ceil(value / grid - _GRID_TOL) * grid, _ROUND)


def _snap_down(value: float, grid: float) -> float:
    return round(math.floor(value / grid + _GRID_TOL) * grid, _ROUND)


def pin_rects(pdk: dict, model: str, params: dict, group: str) -> list:
    """Pin rects (x0, y0, x1, y1) of one copy in the PCell frame, one per shape of
    the pins group in its order. Size = max(fitted size, <size>_min) (a lower bound
    where the fit is not exact); every edge snapped inward to the grid, so the
    rect is on grid and inside the real metal."""
    g, grid = pdk["devices"][model]["pins"][group], pdk["grid"]
    n = round(eval_expr(g["count"], params))
    out = []
    for k in range(n):
        env = {**params, "k": k, "first": float(k == 0), "last": float(k == n - 1)}
        cx, cy = _linear(g["cx"], env), _linear(g["cy"], env)
        w = max(_linear(g["w"], env), g.get("w_min", 0.0))
        h = max(_linear(g["h"], env), g.get("h_min", 0.0))
        out.append((_snap_up(cx - w / 2, grid), _snap_up(cy - h / 2, grid),
                    _snap_down(cx + w / 2, grid), _snap_down(cy + h / 2, grid)))
    return out
