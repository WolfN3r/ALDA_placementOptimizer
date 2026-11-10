#!/usr/bin/env python3
"""
Characterise a PDK's KLayout PCells into pdk.json, the only place the device
generator and the placer read PDK values from.

1. Footprints: sweeps every device / guard ring PCell listed in the spec and
   fits bbox width, height and origin as a linear combination of the spec's
   terms (e.g. "nf*L"). Fails unless the fit is exact to half a dbu.
   Pins: over the same sweep, the spec's pin shapes per device class (e.g.
   met1 S/D columns, gate pads) fitted the same way, with k = shape index.
2. Device-level minima (phase 1, per model): ring width, well fill around the
   ring tap, device-to-ring clearance per side, device-to-device gap in a row
   (x) and between rows for three orientation pairs (y). Same-model neighbours in
   one row get their merge_layers (implants) filled as one rectangle per row.
   Routed row gap: same pair with the spec's sd_via on every S/D column, so
   neighbouring contacts can take different wires up to the next metal.
   Tracks: min width and space of the spec's track layer (row-channel wires).
   Footprints of routed classes also fit the channel_layer (poly) insets.
3. Structure-level minima (phase 2): tight structures (phase-1 minima) side by
   side, gap >= 0, plus a shared-ring-edge test for two equal rings.
4. Verification: 2x2 arrays of every model in a tight ring and every structure
   pair at its minimum, DRC-checked once more.
Every distance is found with the PDK's own DRC (every checker in the spec's
container.drc, e.g. KLayout deck + magic); each scan places one
fixture per sampled distance into a single layout, one DRC run per pass
(coarse step, then PDK grid around every pass/fail transition).

Input:   <pdk_dir>/characterize.json (hand-written, PDK-specific)
Output:  <pdk_dir>/pdk.json
Both are compact trees (pdk_tree.py: families, @refs), read with pdk_tree.load;
pdk.json is written through pdk_tree.compress, which checks it expands back.
Host:    .venv/bin/python WorkDir/pdk/characterize_pdk.py WorkDir/pdk/sky130A/characterize.json
         (copies itself + the spec into the container, runs KLayout there,
         copies pdk.json back)
Inside:  klayout -b -rm <pcell_macro> -r characterize_pdk.py -rd spec=<spec> -rd out=<pdk.json>
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import itertools
import json
import logging
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import pya                      # only inside KLayout
    import numpy as np
    sys.path.insert(0, "/tmp/alda_char")   # = _CONTAINER_DIR: drc_tools.py, pdk_tree.py are copied next to this script
    import drc_tools
except ImportError:
    pya = None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdk_tree

# =============================================================================
# 2. CONSTANTS  (tool settings only — every PDK value comes from the spec)
# =============================================================================
DEBUG = False

_CONTAINER_DIR  = "/tmp/alda_char"
_COARSE_STEP    = 0.05      # µm, first DRC pass; the second pass refines to the PDK grid
_SLOT_PITCH     = 40.0      # µm between fixtures, at least; larger fixtures get their size + _SLOT_CLEAR
_SLOT_CLEAR     = 15.0      # µm between neighbouring fixtures > every rule interaction range (dnwell 6.3)
_SLOT_MARGIN    = 3.0       # µm; a marker this far outside a fixture still belongs to it
_DRC_MIN_CHUNK  = 25        # fixtures per DRC chunk at least: fewer do not pay a checker start-up
_DRC_MAX_CHUNK  = 300       # fixtures per DRC chunk at most (a 900-fixture chunk took 1.3-1.8 GB in KLayout)
_GB_PER_WORKER  = 1.0       # free memory per parallel KLayout / magic process (container VM: 8 GB)
_GENEROUS       = 2.0       # µm used for every distance not under test
_FIT_TOL_DBU    = 0.5       # max fit residual in dbu
_COEF_EPS       = 1e-9

_RANGE_GRW_MAX    = 0.60
_RANGE_CLEARANCE  = (-0.30, _GENEROUS)
_RANGE_FILL       = (0.00, _GENEROUS)    # relative to the ring tap: the well always covers it
_RANGE_DEVICE_GAP = (-1.00, _GENEROUS)
_RANGE_STRUCT_GAP = (0.00, 3.00)         # default; spec "structure_gap_range" (largest PDK spacing); never overlap
_RANGE_TRACK      = (0.005, 1.00)
_TRACK_LENGTH     = 5.0                  # µm, long enough for every width/space rule

_SIDES   = ("left", "right", "bottom", "top")
_ORIENT  = {"r0": 0, "r90": 1, "r180": 2, "r270": 3, "m0": 4, "m45": 5, "m90": 6, "m135": 7}
_Y_PAIRS = (("r0", "r0"), ("r0", "r180"), ("m0", "r0"))   # (lower, upper) row orientations
_FACTOR  = {"devices": "class", "guard_rings": None}       # pdk.json sections written as families

# =============================================================================
# 3. LOGGING
# =============================================================================
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
logger = logging.getLogger("characterize_pdk")

# =============================================================================
# 4. ALGORITHM
# =============================================================================

_EV_FUNCS = {"sqrt": math.sqrt, "max": max, "min": min}    # same names as spice_parser.eval_expr


def ev(expr, env: dict) -> float:
    """Evaluate a spec expression ("W/nf", "L-0.12", "perim/4+sqrt(...)") over netlist/ring variables."""
    return eval(str(expr), {"__builtins__": {}, **_EV_FUNCS}, env)


def workers() -> int:
    """Parallel processes now: cores, capped by free memory (/proc/meminfo MemAvailable)."""
    with open("/proc/meminfo") as f:
        avail_gb = next(int(l.split()[1]) for l in f if l.startswith("MemAvailable")) / 2**20
    return max(1, min(os.cpu_count() or 1, int(avail_gb / _GB_PER_WORKER)))


def snap(v: float, grid: float) -> float:
    return round(round(v / grid) * grid, 6)


def frange(lo: float, hi: float, step: float, grid: float) -> list:
    n = int(math.floor((hi - lo) / step + 1e-9))
    return [snap(lo + i * step, grid) for i in range(n + 1)]


class Lab:
    """One KLayout layout holding PCell variants, structures and fixtures,
    plus the minima found so far (`tight`, filled after phase 1), the models
    inside every cell (`models_in`, filled by device / place) and each model's
    intrinsic violations (`intrinsic`, filled after the baseline)."""

    def __init__(self, spec: dict):
        self.spec = spec
        self.ly = pya.Layout()
        self.ly.dbu = spec["dbu"]
        lib = (pya.Library.library_by_name(spec["library"], spec["technology"])
               if spec.get("technology") else pya.Library.library_by_name(spec["library"]))
        if lib is None:
            raise RuntimeError(f"PCell library {spec['library']!r} not loaded (pcell_macro?)")
        self.lib = lib
        self.tight: dict = {}
        self.intrinsic: dict = {}       # model -> rules it breaks on its own
        self.models_in: dict = {}       # cell index -> models drawn in it (any depth)
        self._variants: dict = {}
        self._structs: dict = {}
        self._n = 0

    def new_cell(self, prefix: str = "F"):
        self._n += 1
        return self.ly.create_cell(f"{prefix}{self._n}")

    def variant(self, pcell: str, params: dict) -> int:
        key = (pcell, tuple(sorted((k, str(v)) for k, v in params.items())))
        if key not in self._variants:
            pid = self.lib.layout().pcell_id(pcell)
            if pid is None:
                raise RuntimeError(f"PCell {pcell!r} not in library {self.spec['library']!r}")
            self._variants[key] = self.ly.add_pcell_variant(self.lib, pid, params)
        return self._variants[key]

    def device(self, model: str) -> int:
        """The model at its own drc_sample size, else its class's DRC sample size."""
        d = self.spec["devices"][model]
        env = {**self.spec["netlist_defaults"],
               **d.get("drc_sample", self.spec["drc_samples"][d["class"]]["params"])}
        cid = self.variant(d["pcell"], {**d["fixed"], **pcell_params(d, env)})
        self.models_in.setdefault(cid, set()).add(model)
        return cid

    def ring_of(self, model: str) -> str | None:
        cls = self.spec["devices"][model]["class"]
        return next((n for n, r in self.spec["guard_rings"].items() if cls in r["for_class"]), None)

    def ringed_models(self) -> list:
        return [m for m in self.spec["devices"] if self.ring_of(m)]


def place(lab: Lab, parent, cid: int, x: float, y: float, orient: str = "r0"):
    """Insert cid so its transformed bbox has its lower-left corner at (x, y)."""
    lab.models_in.setdefault(parent.cell_index(), set()).update(lab.models_in.get(cid, ()))
    code = _ORIENT[orient]
    bb = lab.ly.cell(cid).dbbox().transformed(pya.DTrans(code % 4, code >= 4, 0.0, 0.0))
    parent.insert(pya.DCellInstArray(cid, pya.DTrans(code % 4, code >= 4, x - bb.left, y - bb.bottom)))
    return pya.DBox(x, y, x + bb.width(), y + bb.height())


def layer_bbox(lab: Lab, cell, layer: list):
    return pya.Region(cell.begin_shapes_rec(lab.ly.layer(*layer))).bbox().to_dtype(lab.ly.dbu)


def merge_fill(lab: Lab, cell, model: str, row) -> None:
    """One rectangle per merge layer over the devices inside `row` (a DBox).
    Rows only: npc merged across stacked rows covers the other row's diffusion
    contacts (sky130 licon.13)."""
    clip = pya.Region(row.to_itype(lab.ly.dbu))
    for layer in lab.spec["devices"][model]["merge_layers"]:
        b = (pya.Region(cell.begin_shapes_rec(lab.ly.layer(*layer))) & clip).bbox()
        if not b.empty():
            cell.shapes(lab.ly.layer(*layer)).insert(b.to_dtype(lab.ly.dbu))


def add_ring(lab: Lab, parent, ring: str, content, clr: dict, grw: float, fill_enc: float):
    """Ring whose opening is `content` grown by clr[side]; each fill layer
    encloses the ring's tap by fill_enc. Returns the bbox of ring + fill."""
    r = lab.spec["guard_rings"][ring]
    grid = lab.spec["grid"]
    opening = pya.DBox(content.left - clr["left"], content.bottom - clr["bottom"],
                       content.right + clr["right"], content.top + clr["top"])
    env = {"IW": snap(opening.width(), grid), "IL": snap(opening.height(), grid), "GRW": grw}
    cid = lab.variant(r["pcell"], {**r["fixed"], **{k: round(ev(v, env), 6) for k, v in r["map"].items()}})
    dx = opening.left - ev(r["opening"]["x0"], env)
    dy = opening.bottom - ev(r["opening"]["y0"], env)
    parent.insert(pya.DCellInstArray(cid, pya.DTrans(dx, dy)))
    bb = lab.ly.cell(cid).dbbox().moved(dx, dy)
    tap = layer_bbox(lab, lab.ly.cell(cid), r["tap_layer"]).moved(dx, dy)
    for f in r["fill"]:
        fb = tap.enlarged(fill_enc, fill_enc)
        parent.shapes(lab.ly.layer(*f["layer"])).insert(fb)
        bb = bb + fb
    return bb


def _generous_clr() -> dict:
    return {s: _GENEROUS for s in _SIDES}


def _ring_nominal(lab: Lab, ring: str) -> tuple:
    """(grw, fill enclosure) used while the quantity under test is something else."""
    r = lab.spec["guard_rings"][ring]
    return r["grw_nominal"], (_GENEROUS if r["fill"] else 0.0)


# --- 4a. Footprint fits -------------------------------------------------------

def pcell_params(entry: dict, env: dict) -> dict:
    """entry['map'] evaluated over netlist values, each entry['snap_params']
    parameter rounded to its own grid (the PCell's drawing grid)."""
    p = {k: round(ev(v, env), 6) for k, v in entry["map"].items()}
    for k, g in entry.get("snap_params", {}).items():
        p[k] = snap(p[k], g)
    return p


def _channel_insets(lab: Lab, cid: int) -> list:
    """[bottom, top] distance from the cell bbox to the spec's channel_layer
    (poly): row gaps are set poly to poly."""
    cell = lab.ly.cell(cid)
    lb, cb = layer_bbox(lab, cell, lab.spec["channel_layer"]), cell.dbbox()
    return [lb.bottom - cb.bottom, cb.top - lb.top]


def fit_footprint(lab: Lab, entry: dict, env_defaults: dict, insets: bool = False) -> dict:
    """Terms are evaluated over the netlist variables and the (snapped) PCell
    parameters together, so they may use either (devices use PCell names).
    insets: also fit the channel-layer insets (inset_bottom, inset_top)."""
    quantities = ("w", "h", "x0", "y0") + (("inset_bottom", "inset_top") if insets else ())
    rows, vals = [], []
    sweep = entry["sweep"]
    for combo in itertools.product(*sweep.values()):
        env = {**env_defaults, **dict(zip(sweep.keys(), combo))}
        params = pcell_params(entry, env)
        cid = lab.variant(entry["pcell"], {**entry["fixed"], **params})
        b = lab.ly.cell(cid).dbbox()
        if b.empty():
            logger.warning("%s %s: empty cell, skipped", entry["pcell"], env)
            continue
        rows.append([ev(t, {**env, **params}) for t in entry["terms"]])
        vals.append([b.width(), b.height(), b.left, b.bottom] + (_channel_insets(lab, cid) if insets else []))
    A, Y = np.array(rows, float), np.array(vals, float)
    terms, pcell = entry["terms"], entry["pcell"]
    if np.linalg.matrix_rank(A) < len(terms):
        raise ValueError(f"{pcell}: sweep too small to fit terms {terms}")
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    err = float(np.abs(A @ coef - Y).max())
    if err > _FIT_TOL_DBU * lab.spec["dbu"]:
        raise ValueError(f"{pcell}: bbox is not linear in {terms} (max error {err:.4f} µm)")
    return {
        q: {t: round(float(coef[i, j]), 6) for i, t in enumerate(terms) if abs(coef[i, j]) > _COEF_EPS}
        for j, q in enumerate(quantities)
    } | {"samples": len(rows), "max_error_um": round(err, 6)}


def _pin_shapes(lab: Lab, cid: int, g: dict) -> list:
    """Merged g["layer"] shapes of the cell, minus g["minus"] (e.g. a metal resistor's
    marker splits its strip into the two ends), filtered by g's (not_)interacting
    layer, sorted along g["order"]."""
    cell = lab.ly.cell(cid)
    reg = pya.Region(cell.begin_shapes_rec(lab.ly.layer(*g["layer"]))).merged()
    if "minus" in g:
        reg = (reg - pya.Region(cell.begin_shapes_rec(lab.ly.layer(*g["minus"])))).merged()
    for key, keep in (("interacting", True), ("not_interacting", False)):
        if key in g:
            other = pya.Region(cell.begin_shapes_rec(lab.ly.layer(*g[key])))
            reg = reg.interacting(other) if keep else reg.not_interacting(other)
    boxes = [p.bbox().to_dtype(lab.ly.dbu) for p in reg.each()]
    return sorted(boxes, key=lambda b: (b.left, b.bottom) if g["order"] == "x" else (b.bottom, b.left))


def _sweep_values(v) -> list:
    """A sweep axis: a list, or {"from", "to", "step"} (dense bound sweeps)."""
    return v if isinstance(v, list) else [round(v["from"] + i * v["step"], 6)
                                          for i in range(int(round((v["to"] - v["from"]) / v["step"])) + 1)]


def _pin_samples(lab: Lab, entry: dict, env_defaults: dict, g: dict, name: str, sweep: dict) -> tuple:
    """(env per pin shape, [cx, cy, w, h] per pin shape) over the sweep."""
    envs, vals = [], []
    for combo in itertools.product(*(_sweep_values(v) for v in sweep.values())):
        env = {**env_defaults, **dict(zip(sweep.keys(), combo))}
        params = pcell_params(entry, env)
        boxes = _pin_shapes(lab, lab.variant(entry["pcell"], {**entry["fixed"], **params}), g)
        n = round(ev(g["count"], {**env, **params}))
        if len(boxes) != n:
            raise ValueError(f"{entry['pcell']} {env}: {len(boxes)} {name} pin shapes, expected {g['count']} = {n}")
        for k, b in enumerate(boxes):
            envs.append({**env, **params, "k": k, "first": float(k == 0), "last": float(k == n - 1)})
            vals.append([b.center().x, b.center().y, b.width(), b.height()])
    return envs, np.array(vals, float)


def fit_pins(lab: Lab, entry: dict, env_defaults: dict, groups: dict) -> dict:
    """Pin rects per group (PCell frame, like footprint x0/y0) as centre (cx, cy)
    and size (w, h), each linear in the group's terms (sizes: size_terms[q] if
    given) over the device sweep, with k / first / last of the shape. Centres
    must fit exactly. A size that does not (contact arrays grow in steps) is
    stored as a lower bound over the device sweep plus the group's dense
    bound_sweep: slopes fitted to all of them, constant lowered to the worst
    sample, and <q>_min = the smallest sample; size = max(both), so the rect
    always lies inside the real metal ("size_exact": false)."""
    out = {}
    tol = _FIT_TOL_DBU * lab.spec["dbu"]
    for name, g in groups.items():
        envs, Y = _pin_samples(lab, entry, env_defaults, g, name, entry["sweep"])
        bound = None
        fit, exact = {}, True
        for j, q in enumerate(("cx", "cy", "w", "h")):
            terms = g["terms"] if j < 2 else g.get("size_terms", {}).get(q, g["terms"])
            A = np.array([[ev(t, e) for t in terms] for e in envs], float)
            if np.linalg.matrix_rank(A) < len(terms):
                raise ValueError(f"{entry['pcell']}: sweep too small to fit {name} pin {q} terms {terms}")
            coef, *_ = np.linalg.lstsq(A, Y[:, j], rcond=None)
            err = float(np.abs(A @ coef - Y[:, j]).max())
            if err > tol and j < 2:
                raise ValueError(f"{entry['pcell']}: {name} pin {q} not linear in {terms} (max error {err:.4f} µm)")
            if err > tol:
                exact = False
                if bound is None:
                    bound = _pin_samples(lab, entry, env_defaults, g, name, g["bound_sweep"]) \
                        if "bound_sweep" in g else ([], np.zeros((0, 4)))
                Ab = np.array([[ev(t, e) for t in terms] for e in envs + bound[0]], float)
                yb = np.concatenate([Y[:, j], bound[1][:, j]])
                coef, *_ = np.linalg.lstsq(Ab, yb, rcond=None)    # slopes from the dense samples too
                coef[terms.index("1")] += float((yb - Ab @ coef).min())
                fit[f"{q}_min"] = round(float(yb.min()), 6)       # size = max(linear bound, this)
            fit[q] = {t: round(float(c), 6) for t, c in zip(terms, coef) if abs(c) > _COEF_EPS}
        out[name] = {"layer": g["layer"], "order": g["order"], "count": g["count"], **fit,
                     "size_exact": exact, "samples": len(envs) + (len(bound[0]) if bound else 0)}
    return out


def fit_one(lab: Lab, model: str) -> dict:
    """{"footprint", "pins"} of one spec device."""
    spec, d = lab.spec, lab.spec["devices"][model]
    return {"footprint": fit_footprint(lab, d, spec["netlist_defaults"],
                                       insets=d["class"] in spec["sd_via"]["for_class"]),
            "pins": fit_pins(lab, d, spec["netlist_defaults"], d.get("pins", spec["pins"].get(d["class"], {})))}


def fit_devices(spec: dict) -> dict:
    """{model: fit_one(...)}: one KLayout process per model (fit_model worker of this
    script), workers() at a time, MOS first (their pin bound sweeps take longest)."""
    spec_path = f"{_CONTAINER_DIR}/fit_spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec, f)
    macro = os.path.expandvars(spec["container"]["pcell_macro"])
    models = sorted(spec["devices"], key=lambda m: spec["devices"][m]["class"] not in spec["sd_via"]["for_class"])

    def job(i_model):
        i, model = i_model
        out = f"{_CONTAINER_DIR}/fit_{i}.json"
        if os.path.exists(out):
            os.remove(out)
        r = subprocess.run(["klayout", "-b", "-rm", macro, "-r", f"{_CONTAINER_DIR}/characterize_pdk.py",
                            "-rd", f"spec={spec_path}", "-rd", f"fit_model={model}", "-rd", f"out={out}"],
                           capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError(f"fit {model} failed:\n{(r.stdout + r.stderr)[-3000:]}")
        with open(out, encoding="utf-8") as f:
            return model, json.load(f)

    t0, par = time.time(), workers()
    with ThreadPoolExecutor(max_workers=par) as ex:      # threads only wait on klayout processes
        fits = dict(ex.map(job, enumerate(models)))
    logger.info("fits: %d devices in %.0f s (%d workers)", len(fits), time.time() - t0, par)
    return fits


# --- 4b. Fixture builders (each returns a cell index) --------------------------

def fx_ring(lab: Lab, model: str, clr: dict, grw: float, fill: float) -> int:
    cell = lab.new_cell()
    b = place(lab, cell, lab.device(model), 0.0, 0.0)
    add_ring(lab, cell, lab.ring_of(model), b, clr, grw, fill)
    return cell.cell_index()


def fx_pair(lab: Lab, model: str, gap: float, axis: str, oa: str, ob: str) -> int:
    cell = lab.new_cell()
    dev = lab.device(model)
    b1 = place(lab, cell, dev, 0.0, 0.0, oa)
    if axis == "x":
        b2 = place(lab, cell, dev, b1.right + gap, 0.0, ob)
        merge_fill(lab, cell, model, b1 + b2)
    else:
        b2 = place(lab, cell, dev, 0.0, b1.top + gap, ob)
    ring = lab.ring_of(model)
    add_ring(lab, cell, ring, b1 + b2, _generous_clr(), *_ring_nominal(lab, ring))
    return cell.cell_index()


def add_sd_vias(lab: Lab, parent, cid: int, at) -> None:
    """The spec's sd_via on every contact_layer shape of device cid (placed with
    its bbox lower-left at `at`) that overlaps over_layer (the S/D columns),
    centred on the overlap."""
    sv = lab.spec["sd_via"]
    cell = lab.ly.cell(cid)
    cols = (pya.Region(cell.begin_shapes_rec(lab.ly.layer(*sv["contact_layer"]))).merged()
            & pya.Region(cell.begin_shapes_rec(lab.ly.layer(*sv["over_layer"]))))
    via = lab.variant(sv["pcell"], sv["fixed"])
    vb = lab.ly.cell(via).dbbox().transformed(pya.DTrans(_ORIENT[sv["orient"]] % 4, False, 0.0, 0.0))
    shift = pya.DVector(at.left - cell.dbbox().left, at.bottom - cell.dbbox().bottom)
    for poly in cols.each():
        c = poly.bbox().to_dtype(lab.ly.dbu).center() + shift
        place(lab, parent, via, c.x - vb.width() / 2, c.y - vb.height() / 2, sv["orient"])


def fx_routed_pair(lab: Lab, model: str, gap: float) -> int:
    """Row pair with a via to the next metal on every S/D column: the gap at
    which neighbouring contacts can take different wires."""
    cell = lab.new_cell()
    dev = lab.device(model)
    b1 = place(lab, cell, dev, 0.0, 0.0)
    b2 = place(lab, cell, dev, b1.right + gap, 0.0)
    merge_fill(lab, cell, model, b1 + b2)
    add_sd_vias(lab, cell, dev, b1)
    add_sd_vias(lab, cell, dev, b2)
    ring = lab.ring_of(model)
    add_ring(lab, cell, ring, b1 + b2, _generous_clr(), *_ring_nominal(lab, ring))
    return cell.cell_index()


def fx_wires(lab: Lab, width: float, space: float | None) -> int:
    """One track_layer wire (space None) or two parallel ones `space` apart."""
    cell = lab.new_cell()
    shapes = cell.shapes(lab.ly.layer(*lab.spec["tracks"]["layer"]))
    shapes.insert(pya.DBox(0.0, 0.0, _TRACK_LENGTH, width))
    if space is not None:
        shapes.insert(pya.DBox(0.0, width + space, _TRACK_LENGTH, 2 * width + space))
    return cell.cell_index()


def _routed_models(lab: Lab) -> list:
    return [m for m in lab.ringed_models() if lab.spec["devices"][m]["class"] in lab.spec["sd_via"]["for_class"]]


def structures(lab: Lab) -> list:
    """Ring names (their class sample inside) + classes without a ring."""
    ringless = [c for c in lab.spec["drc_samples"]
                if not any(c in r["for_class"] for r in lab.spec["guard_rings"].values())]
    return list(lab.spec["guard_rings"]) + ringless


def structure(lab: Lab, name: str) -> int:
    """Tight structure: class sample in its ring at the phase-1 minima, or a
    bare ringless class sample."""
    if name not in lab._structs:
        cell = lab.new_cell("S")
        if name in lab.spec["guard_rings"]:
            model = lab.spec["drc_samples"][lab.spec["guard_rings"][name]["for_class"][0]]["model"]
            t = lab.tight["models"][model]
            b = place(lab, cell, lab.device(model), 0.0, 0.0)
            add_ring(lab, cell, name, b, t["clearance"], *lab.tight["rings"][name])
        else:
            place(lab, cell, lab.device(lab.spec["drc_samples"][name]["model"]), 0.0, 0.0)
        lab._structs[name] = cell.cell_index()
    return lab._structs[name]


def fx_struct_gap(lab: Lab, sa: str, sb: str, gap: float) -> int:
    cell = lab.new_cell()
    a = place(lab, cell, structure(lab, sa), 0.0, 0.0)
    place(lab, cell, structure(lab, sb), a.right + gap, 0.0)
    return cell.cell_index()


def tap_inset(lab: Lab, ring: str) -> float:
    """Distance from a tight structure's bbox (ring + fill) to its ring tap."""
    cell = lab.ly.cell(structure(lab, ring))
    return snap(layer_bbox(lab, cell, lab.spec["guard_rings"][ring]["tap_layer"]).left - cell.dbbox().left,
                lab.spec["grid"])


def ring_inset(lab: Lab, ring: str) -> float:
    """Distance from the bare ring PCell's bbox to its tap."""
    r = lab.spec["guard_rings"][ring]
    grw = lab.tight["rings"][ring][0]
    env = {"IW": _GENEROUS, "IL": _GENEROUS, "GRW": grw}
    cell = lab.ly.cell(lab.variant(r["pcell"], {**r["fixed"], **{k: round(ev(v, env), 6) for k, v in r["map"].items()}}))
    return snap(layer_bbox(lab, cell, r["tap_layer"]).left - cell.dbbox().left, lab.spec["grid"])


def shared_edge_gap(lab: Lab, ring: str) -> float:
    """Gap (negative) at which two equal tight structures share one tap band."""
    r = lab.spec["guard_rings"][ring]
    grw = lab.tight["rings"][ring][0]
    return snap(-(2 * tap_inset(lab, ring) + ev(r["tap_band"], {"GRW": grw})), lab.spec["grid"])


def phase1_scans(lab: Lab) -> dict:
    """key -> (lo, hi, builder(value) -> cell index)."""
    scans: dict = {}
    for ring, r in lab.spec["guard_rings"].items():
        model = lab.spec["drc_samples"][r["for_class"][0]]["model"]
        grw, fill = _ring_nominal(lab, ring)
        scans[f"grw_min/{ring}"] = (grw, _RANGE_GRW_MAX, lambda v, m=model, f=fill:
                                    fx_ring(lab, m, _generous_clr(), v, f))
        if r["fill"]:
            scans[f"fill_enclosure/{ring}"] = (*_RANGE_FILL, lambda v, m=model, g=grw:
                                              fx_ring(lab, m, _generous_clr(), g, v))
    for model in lab.ringed_models():
        grw, fill = _ring_nominal(lab, lab.ring_of(model))
        for side in _SIDES:
            scans[f"ring_clearance/{model}/{side}"] = (
                *_RANGE_CLEARANCE, lambda v, m=model, s=side, g=grw, f=fill:
                    fx_ring(lab, m, {**_generous_clr(), s: v}, g, f))
        scans[f"device_gap_x/{model}"] = (*_RANGE_DEVICE_GAP, lambda v, m=model:
                                          fx_pair(lab, m, v, "x", "r0", "r0"))
        for oa, ob in _Y_PAIRS:
            scans[f"device_gap_y/{model}/{oa}_{ob}"] = (
                *_RANGE_DEVICE_GAP, lambda v, m=model, oa=oa, ob=ob: fx_pair(lab, m, v, "y", oa, ob))
    for model in _routed_models(lab):
        scans[f"device_gap_x_routed/{model}"] = (*_RANGE_DEVICE_GAP, lambda v, m=model:
                                                 fx_routed_pair(lab, m, v))
    scans["track_width"] = (*_RANGE_TRACK, lambda v: fx_wires(lab, v, None))
    return scans


def phase2_scans(lab: Lab) -> dict:
    rng = tuple(lab.spec.get("structure_gap_range", _RANGE_STRUCT_GAP))
    scans = {f"structure_gap/{sa}|{sb}": (*rng, lambda v, sa=sa, sb=sb:
                                          fx_struct_gap(lab, sa, sb, v))
             for sa, sb in itertools.combinations_with_replacement(structures(lab), 2)}
    scans["track_space"] = (*_RANGE_TRACK, lambda v: fx_wires(lab, lab.tight["track_width"], v))
    return scans


# --- 4c. DRC passes ------------------------------------------------------------

def _chunk_gds(lab: Lab, cells: list, tag: str, pitch: float) -> dict:
    """cells on a slot grid in one flat GDS: {gds, top, width, ncol, regions}."""
    ncol = max(1, math.ceil(math.sqrt(len(cells))))
    out_ly = pya.Layout()
    out_ly.dbu = lab.ly.dbu
    top = out_ly.create_cell(f"CHAR_{tag}")
    regions = []
    for i, cid in enumerate(cells):
        x, y = (i % ncol) * pitch, (i // ncol) * pitch
        src = lab.ly.cell(cid)
        tgt = out_ly.create_cell(f"{src.name}_{i}")
        tgt.copy_tree(src)
        top.insert(pya.DCellInstArray(tgt.cell_index(), pya.DTrans(x, y)))
        regions.append(src.dbbox().moved(x, y).enlarged(_SLOT_MARGIN, _SLOT_MARGIN))
    top.flatten(True)
    gds = f"{_CONTAINER_DIR}/{tag}.gds"
    out_ly.write(gds)
    return {"gds": gds, "top": top.name, "width": top.dbbox().width(), "ncol": ncol, "regions": regions}


def run_drc(lab: Lab, cells: list, tag: str) -> list:
    """Place cells on a slot grid, run every checker in spec['container']['drc'],
    return the set of violated rule names per cell (same order as `cells`),
    without the intrinsic rules of the models in that cell (a rule one PDK cell
    breaks on its own must still count for every other model). Large passes are split into chunk
    GDS of at most _DRC_MAX_CHUNK fixtures, checked workers() at a time (each
    fixture is still alone in its slot, so the result does not depend on the
    split). The slot pitch grows with the largest fixture."""
    biggest = max(max(lab.ly.cell(c).dbbox().width(), lab.ly.cell(c).dbbox().height()) for c in cells)
    pitch = float(max(_SLOT_PITCH, math.ceil(biggest + _SLOT_CLEAR)))    # float: DTrans(int, int) is (rot, mirror)
    par = workers()
    k = max(1, math.ceil(len(cells) / _DRC_MAX_CHUNK), min(par, len(cells) // _DRC_MIN_CHUNK))
    parts = [list(range(len(cells)))[j * len(cells) // k:(j + 1) * len(cells) // k] for j in range(k)]
    tags = [tag] if k == 1 else [f"{tag}_c{j}" for j in range(k)]
    chunks = [_chunk_gds(lab, [cells[i] for i in idx], t, pitch) for idx, t in zip(parts, tags)]

    t0 = time.time()
    checkers = lab.spec["container"]["drc"]
    with ThreadPoolExecutor(max_workers=min(par, k)) as ex:      # threads only wait on klayout / magic processes
        markers = list(ex.map(lambda ct: drc_tools.all_markers(checkers, ct[0]["gds"], ct[0]["top"], ct[0]["width"],
                                                               ct[1], _CONTAINER_DIR), zip(chunks, tags)))
    logger.info("DRC %s: %d fixtures in %d chunk(s), %d parallel, %d markers in %.0f s", tag, len(cells), k,
                min(par, k), sum(map(len, markers)), time.time() - t0)

    fails: list = [set() for _ in cells]
    unassigned = 0
    for idx, ch, mk in zip(parts, chunks, markers):
        for rule, x1, y1, x2, y2 in mk:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            col = int(math.floor((cx + _SLOT_MARGIN) / pitch))
            row = int(math.floor((cy + _SLOT_MARGIN) / pitch))
            i = row * ch["ncol"] + col
            if 0 <= col < ch["ncol"] and 0 <= i < len(idx) and ch["regions"][i].contains(pya.DPoint(cx, cy)):
                fails[idx[i]].add(rule)
            else:
                unassigned += 1
    if unassigned:
        logger.warning("DRC %s: %d markers outside every fixture", tag, unassigned)
    never = set(lab.spec.get("drc_ignore", []))       # whole-layout rules, meaningless per fixture
    return [f - never - set().union(*(lab.intrinsic.get(m, set()) for m in lab.models_in.get(c, ())))
            for f, c in zip(fails, cells)]


def baseline(lab: Lab) -> dict:
    """Rules broken by a model on its own (ringed models in a generous ring,
    the others bare): intrinsic to the PCell, not caused by any distance."""
    jobs = []
    for model in lab.spec["devices"]:
        ring = lab.ring_of(model)
        if ring:
            jobs.append((model, fx_ring(lab, model, _generous_clr(), *_ring_nominal(lab, ring))))
        else:
            cell = lab.new_cell()
            place(lab, cell, lab.device(model), 0.0, 0.0)
            jobs.append((model, cell.cell_index()))
    fails = run_drc(lab, [c for _, c in jobs], "baseline")
    return {m: sorted(f) for (m, _), f in zip(jobs, fails) if f}


def scan_all(lab: Lab, scans: dict, tag: str) -> dict:
    """Coarse pass over every scan range, fine pass (PDK grid) around every
    pass/fail transition. Returns key -> {value: set(violated rules)}."""
    grid = lab.spec["grid"]
    samples: dict = {k: {} for k in scans}

    def _pass(jobs: list, t: str) -> None:
        fails = run_drc(lab, [scans[k][2](v) for k, v in jobs], t)
        for (k, v), f in zip(jobs, fails):
            samples[k][v] = f

    _pass([(k, v) for k, (lo, hi, _) in scans.items()
           for v in frange(lo, hi, _COARSE_STEP, grid)], f"{tag}_coarse")
    fine = []
    for k, s in samples.items():
        vs = sorted(s)
        for a, b in zip(vs, vs[1:]):
            if bool(s[a]) != bool(s[b]):
                fine += [(k, v) for v in frange(a, b, grid, grid)[1:-1]]
    if fine:
        _pass(fine, f"{tag}_fine")
    return {k: summarize(s) for k, s in samples.items()}


def summarize(samples: dict) -> dict:
    """min = smallest sampled value from which on every larger sample passes;
    pass_intervals = runs of consecutive passing samples."""
    vs = sorted(samples)
    if samples[vs[-1]]:
        return {"error": f"fails even at {vs[-1]}: {sorted(samples[vs[-1]])}"}
    m = vs[-1]
    for v in reversed(vs):
        if samples[v]:
            break
        m = v
    intervals, start, prev = [], None, None
    for v in vs:
        if not samples[v]:
            start = v if start is None else start
            prev = v
        elif start is not None:
            intervals.append([start, prev])
            start = None
    if start is not None:
        intervals.append([start, prev])
    first_fail = next((sorted(samples[v]) for v in reversed(vs) if samples[v]), [])
    return {"min": m, "pass_intervals": intervals, "limited_by": first_fail}


def _min(raw: dict, key: str) -> float:
    if "min" not in raw[key]:
        raise RuntimeError(f"{key}: {raw[key]['error']}")
    return raw[key]["min"]


# --- 4d. Verification of the combined minima -----------------------------------

def verify(lab: Lab, pdk: dict) -> dict:
    """Every ringed model as a 2x2 array (upper row r180, gates facing) at its
    min gaps inside a tight ring, every structure pair at its min gap, and
    every shared ring edge. All must be DRC-clean."""
    jobs = []
    for model in lab.ringed_models():
        ring = lab.ring_of(model)
        t = lab.tight["models"][model]
        clr, gx, gy = t["clearance"], t["gap"]["x"], t["gap"]["y"]["r0_r180"]
        lr = max(clr["left"], clr["right"])
        cell = lab.new_cell("V")
        dev = lab.device(model)
        b00 = place(lab, cell, dev, 0.0, 0.0, "r0")
        b10 = place(lab, cell, dev, b00.right + gx, 0.0, "r0")
        b01 = place(lab, cell, dev, 0.0, b00.top + gy, "r180")
        b11 = place(lab, cell, dev, b01.right + gx, b01.bottom, "r180")
        merge_fill(lab, cell, model, b00 + b10)
        merge_fill(lab, cell, model, b01 + b11)
        # the r180 row shows its device-frame bottom side to the ring top
        add_ring(lab, cell, ring, b00 + b10 + b01 + b11,
                 {"left": lr, "right": lr, "bottom": clr["bottom"], "top": clr["bottom"]},
                 *lab.tight["rings"][ring])
        jobs.append((f"tight_ring_2x2/{model}", cell.cell_index()))
    for model in _routed_models(lab):
        jobs.append((f"routed_pair/{model}", fx_routed_pair(lab, model, lab.tight["models"][model]["gap"]["x_routed"])))
    tr = pdk["tracks"]
    jobs.append(("tracks", fx_wires(lab, tr["width"], tr["space"])))
    for key, g in pdk["structure_gap"].items():
        sa, sb = key.split("|")
        if "min" in g:
            jobs.append((f"structure_gap/{key}", fx_struct_gap(lab, sa, sb, g["min"])))
        if sa == sb and "shared_edge_gap" in g:
            jobs.append((f"shared_edge/{key}", fx_struct_gap(lab, sa, sb, g["shared_edge_gap"])))
    fails = run_drc(lab, [c for _, c in jobs], "verify")
    return {k: (sorted(f) if f else "clean") for (k, _), f in zip(jobs, fails)}


# --- 4e. Assemble pdk.json -----------------------------------------------------

def characterize(spec: dict) -> dict:
    lab = Lab(spec)
    pdk = {
        "_generated": {"by": "characterize_pdk.py", "spec": "characterize.json",
                       "date": time.strftime("%Y-%m-%d %H:%M")},
        **{k: spec[k] for k in ("pdk", "library", "technology", "dbu", "grid",
                                "netlist_defaults", "netlist_copies", "layout_policy", "routing")},
        "devices": {}, "guard_rings": {}, "structure_gap": {},
    }
    fits = fit_devices(spec)
    for model, d in spec["devices"].items():
        pdk["devices"][model] = {
            **{k: d[k] for k in ("class", "device_group", "terminals", "pcell", "fixed", "map",
                                 "snap_params", "merge_layers")},
            **({"series": d["series"]} if "series" in d else {}),
            "ring": lab.ring_of(model),
            **fits[model],
        }
    for ring, r in spec["guard_rings"].items():
        pdk["guard_rings"][ring] = {
            **{k: r[k] for k in ("pcell", "fixed", "map", "opening", "tap_layer", "tap_band", "for_class")},
            "footprint": fit_footprint(lab, r, {}),
        }
    logger.info("footprints fitted: %d devices, %d rings", len(pdk["devices"]), len(pdk["guard_rings"]))

    pdk["intrinsic_violations"] = baseline(lab)
    lab.intrinsic = {m: set(rules) for m, rules in pdk["intrinsic_violations"].items()}
    if lab.intrinsic:
        logger.warning("intrinsic PCell violations of %d models (ignored in fixtures holding that model): %s",
                       len(lab.intrinsic), sorted(lab.intrinsic))

    raw = scan_all(lab, phase1_scans(lab), "phase1")
    lab.tight = {"rings": {}, "models": {}}
    for ring, r in spec["guard_rings"].items():
        g = pdk["guard_rings"][ring]
        g["grw_min"] = _min(raw, f"grw_min/{ring}")
        g["fill"] = [{**f, "enclosure": _min(raw, f"fill_enclosure/{ring}"), "relative_to": "tap_layer"}
                     for f in r["fill"]]
        lab.tight["rings"][ring] = (g["grw_min"], g["fill"][0]["enclosure"] if g["fill"] else 0.0)
        g["tap_inset"] = ring_inset(lab, ring)
    for model in lab.ringed_models():
        t = {"clearance": {s: _min(raw, f"ring_clearance/{model}/{s}") for s in _SIDES},
             "gap": {"x": _min(raw, f"device_gap_x/{model}"),
                     "y": {f"{a}_{b}": _min(raw, f"device_gap_y/{model}/{a}_{b}") for a, b in _Y_PAIRS}}}
        if model in _routed_models(lab):
            t["gap"]["x_routed"] = _min(raw, f"device_gap_x_routed/{model}")
        lab.tight["models"][model] = t
        pdk["devices"][model].update(t)
    lab.tight["track_width"] = _min(raw, "track_width")

    raw2 = scan_all(lab, phase2_scans(lab), "phase2")
    space = _min(raw2, "track_space")
    pdk["tracks"] = {"layer": spec["tracks"]["layer"], "width": lab.tight["track_width"], "space": space,
                     "pitch": snap(lab.tight["track_width"] + space, spec["grid"])}
    for key, v in raw2.items():
        if key == "track_space":
            continue
        pair = key.split("/", 1)[1]
        sa, sb = pair.split("|")
        if sa == sb and sa in spec["guard_rings"]:
            v["shared_edge_gap"] = shared_edge_gap(lab, sa)
        pdk["structure_gap"][pair] = v

    checks = verify(lab, pdk)
    for key, v in checks.items():
        if key.startswith("shared_edge/"):
            pdk["structure_gap"][key.split("/", 1)[1]]["shared_edge_drc"] = v
    place_diagnostics(pdk, {**raw, **raw2}, checks)
    bad = {k: v for k, v in checks.items() if v != "clean"}
    if bad:
        logger.warning("verification failures: %s", bad)
    return pdk


def place_diagnostics(pdk: dict, scans: dict, checks: dict) -> None:
    """Scan diagnostics (pass_intervals, limited_by) and verification results
    stored next to the value they explain: devices[m].scans mirrors
    devices[m].clearance / gap, guard_rings[r].scans, tracks.scans; scans' own
    min is that value, so it is not stored twice."""
    def diag(key: str) -> dict:
        return {"pass_intervals": scans[key]["pass_intervals"], "limited_by": scans[key]["limited_by"]}

    for ring, g in pdk["guard_rings"].items():
        g["scans"] = {"grw_min": diag(f"grw_min/{ring}")}
        if f"fill_enclosure/{ring}" in scans:
            g["scans"]["fill_enclosure"] = diag(f"fill_enclosure/{ring}")
    for model, d in pdk["devices"].items():
        if "clearance" not in d:
            continue
        d["scans"] = {"clearance": {s: diag(f"ring_clearance/{model}/{s}") for s in _SIDES},
                      "gap": {"x": diag(f"device_gap_x/{model}"),
                              "y": {f"{a}_{b}": diag(f"device_gap_y/{model}/{a}_{b}") for a, b in _Y_PAIRS}}}
        if f"device_gap_x_routed/{model}" in scans:
            d["scans"]["gap"]["x_routed"] = diag(f"device_gap_x_routed/{model}")
        d["verification"] = {k: checks[f"{k}/{model}"] for k in ("tight_ring_2x2", "routed_pair")
                             if f"{k}/{model}" in checks}
    pdk["tracks"]["scans"] = {"width": diag("track_width"), "space": diag("track_space")}
    pdk["tracks"]["verification"] = checks["tracks"]
    for pair, g in pdk["structure_gap"].items():
        if f"structure_gap/{pair}" in checks:
            g["verification"] = checks[f"structure_gap/{pair}"]


def write_pdk(pdk: dict, refs: dict, path) -> None:
    """pdk.json as a compact tree (pdk_tree), checked to expand back to pdk."""
    text = pdk_tree.dumps(pdk_tree.compress(pdk, refs, _FACTOR)) + "\n"    # raises before the file is touched
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(spec: dict) -> dict:
    for key in ("pdk", "container", "library", "dbu", "grid", "netlist_defaults",
                "netlist_copies", "devices", "guard_rings", "drc_samples",
                "channel_layer", "sd_via", "tracks", "layout_policy", "pins", "routing"):
        if key not in spec:
            raise KeyError(f"run: spec missing {key!r}")
    return characterize(spec)


def main_container(spec_path: str, out_path: str) -> None:
    os.makedirs(_CONTAINER_DIR, exist_ok=True)
    with open(spec_path, encoding="utf-8") as f:
        tree = json.load(f)
    pdk = run(pdk_tree.expand(tree))
    layers = {k: v for k, v in tree.get("@refs", {}).items() if isinstance(v, list)}
    write_pdk(pdk, layers, out_path)
    logger.info("wrote %s", out_path)


def main_fit_worker(spec_path: str, model: str, out_path: str) -> None:
    """One fit_devices job; the file is written only on success."""
    fit = fit_one(Lab(pdk_tree.load(spec_path)), model)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fit, f)


def main_host() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: characterize_pdk.py <pdk_dir>/characterize.json")
    spec_path = Path(sys.argv[1]).resolve()
    spec = pdk_tree.load(spec_path)
    c = spec["container"]["name"]
    subprocess.run(["docker", "exec", c, "mkdir", "-p", _CONTAINER_DIR], check=True)
    here = Path(__file__).resolve().parent
    for f in (Path(__file__).resolve(), here / "drc_tools.py", here / "pdk_tree.py", spec_path):
        subprocess.run(["docker", "cp", str(f), f"{c}:{_CONTAINER_DIR}/{f.name}"], check=True)
    inner = (f"cd {_CONTAINER_DIR} && klayout -b -rm {spec['container']['pcell_macro']} "
             f"-r {_CONTAINER_DIR}/{Path(__file__).name} "
             f"-rd spec={_CONTAINER_DIR}/{spec_path.name} -rd out={_CONTAINER_DIR}/pdk.json")
    subprocess.run(["docker", "exec", c, "bash", "-lc", inner], check=True)
    subprocess.run(["docker", "cp", f"{c}:{_CONTAINER_DIR}/pdk.json",
                    str(spec_path.parent / "pdk.json")], check=True)
    logger.info("wrote %s", spec_path.parent / "pdk.json")


if pya is None:
    if __name__ == "__main__":
        main_host()
elif "fit_model" in globals():
    main_fit_worker(globals()["spec"], globals()["fit_model"], globals()["out"])
else:
    main_container(globals()["spec"], globals()["out"])
