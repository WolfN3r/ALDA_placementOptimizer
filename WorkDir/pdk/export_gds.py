#!/usr/bin/env python3
"""
Export a placement (py101 JSON from a --pdk run) to GDS with the PDK's real
PCells, so the placed structures can be checked with DRC in KLayout/magic.

Every placed block becomes one cell: each slot of its chosen variant (devices,
row-end dummies, inner dummies) as a PCell at the slot centre and orientation,
the row's merge_layers (implants) filled as one rectangle per row, the tight
guard ring and its fill, all flattened into the block cell (magic checks
overlapping subcells separately: a pfet PCell's n-well under the ring PCell's
tap gives "Can't overlap those layers" and an n-well without tap), plus one
text per slot (netlist name or "dummy") on the spec's annotation_layer.
Composite blocks take their variant from groups[group_id].matching_variants
[variant_index], single blocks from blocks[].variants[variant_index] (rotated
by rotation_deg). A variant's in-block routing (lib/block_router) is drawn on the
pdk.json "routing" layers, block pins also on their pin and label layers (net
name). Nothing between blocks is routed.

Host:    .venv/bin/python WorkDir/pdk/export_gds.py <s*_py101_*.json> <out.gds> [--drc]
         (copies itself, drc_tools.py, the JSON and pdk.json into the
         container named in <pdk>/characterize.json, runs KLayout there,
         copies the GDS back; --drc also runs every checker of the spec and
         writes <out>_drc.json: violations per rule, the block they are in,
         intrinsic PCell rules from pdk.json listed apart)
Inside:  klayout -b -rm <pcell_macro> -r export_gds.py -rd placement=.. -rd pdk=.. -rd spec=.. -rd out=.. -rd drc=0|1
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

try:
    import pya                      # only inside KLayout
    sys.path.insert(0, "/tmp/alda_gds")   # = _CONTAINER_DIR: drc_tools.py, pdk_tree.py are copied next to this script
    import drc_tools
except ImportError:
    pya = None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdk_tree

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_CONTAINER_DIR = "/tmp/alda_gds"
_PDK_DIR = Path(__file__).resolve().parent
_COMPOSITE_ID_BASE = 10_000
_ORIENT_CODE = {"R0": 0, "R180": 2}
_MARGIN_UM = 0.5                    # a DRC marker this close to a block belongs to it

# =============================================================================
# 3. LOGGING
# =============================================================================
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
logger = logging.getLogger("export_gds")

# =============================================================================
# 4. ALGORITHM (inside the container)
# =============================================================================

def _ev(expr, env: dict) -> float:
    return eval(str(expr), {"__builtins__": {}}, env)


class _Cells:
    """PCell variants of one library, parameters coerced to the declared types."""

    def __init__(self, ly, lib):
        self.ly, self.lib, self._cache = ly, lib, {}

    def get(self, pcell: str, params: dict) -> int:
        key = (pcell, tuple(sorted((k, str(v)) for k, v in params.items())))
        if key not in self._cache:
            decl = self.lib.layout().pcell_declaration(pcell)
            types = {p.name: p.type for p in decl.get_parameters()}
            p = {k: (int(round(v)) if types.get(k) == pya.PCellParameterDeclaration.TypeInt
                     and isinstance(v, float) else v) for k, v in params.items()}
            self._cache[key] = self.ly.add_pcell_variant(self.lib, self.lib.layout().pcell_id(pcell), p)
        return self._cache[key]


def _place_centred(ly, parent, cid: int, x: float, y: float, orient: str):
    code = _ORIENT_CODE[orient]
    bb = ly.cell(cid).dbbox().transformed(pya.DTrans(code, False, 0.0, 0.0))
    t = pya.DTrans(code, False, x - bb.center().x, y - bb.center().y)
    return parent.insert(pya.DCellInstArray(cid, t)), bb.moved(t.disp)


def _variant_of(data: dict, bid: int, pb: dict) -> tuple:
    """(variant, member blocks by id, title) of one placed block."""
    by_id = {b["block_id"]: b for b in data["blocks"] if "error" not in b}
    if bid >= _COMPOSITE_ID_BASE:
        group = next(g for g in data["groups"] if g["group_id"] == pb["group_id"])
        v = group["matching_variants"][pb.get("variant_index") or 0]
        if "routing" in pb:             # lib/pin_access: pins at the chosen access points, unused trunk ends cut
            v = {**v, "routing": pb["routing"]}
        return v, by_id, f"{group['topology_type']}_{'_'.join(by_id[b]['inst'] for b in group['block_ids'])}"
    blk = by_id[bid]
    idx = pb.get("variant_index")
    if idx is None:
        idx = next(i for i, v in enumerate(blk["variants"]) if v.get("is_used"))
    return blk["variants"][idx], by_id, blk["inst"]


def build_block(ly, cells: _Cells, pdk: dict, variant: dict, by_id: dict, name: str, text_layer: list):
    """One flat cell in the variant's own (unrotated) frame, origin at its bbox corner."""
    cell = ly.create_cell(name)
    rows: dict = {}
    texts = []
    for s in variant["slots"]:
        if s["block_id"] is not None:
            blk = by_id[s["block_id"]]
            model, params, label = blk["device_type"], variant.get("unit_pcell", blk["parameters"]["pcell"]), blk["inst"]
        else:
            model = variant["dummies"]["model"]
            member = by_id[next(x["block_id"] for x in variant["slots"] if x["block_id"] is not None)]
            unit = variant.get("unit_pcell", member["parameters"]["pcell"])
            params = unit if s.get("full_size_dummy") else variant["dummies"]["pcell"]
            label = "dummy"
        d = pdk["devices"][model]
        _, box = _place_centred(ly, cell, cells.get(d["pcell"], {**d["fixed"], **params}),
                                s["x"], s["y"], s["orient"])
        texts.append(pya.DText(label, s["x"], s["y"]))
        rows.setdefault(s["row"], [model, None])
        rows[s["row"]][1] = box if rows[s["row"]][1] is None else rows[s["row"]][1] + box
    for model, row_box in rows.values():
        clip = pya.Region(row_box.to_itype(ly.dbu))
        for layer in pdk["devices"][model]["merge_layers"]:
            b = (pya.Region(cell.begin_shapes_rec(ly.layer(*layer))) & clip).bbox()
            if not b.empty():
                cell.shapes(ly.layer(*layer)).insert(b.to_dtype(ly.dbu))
    for ring in filter(None, variant.get("guard_rings") or [variant.get("guard_ring")]):
        r = pdk["guard_rings"][ring["ring"]]
        env = {"IW": ring["in_w"], "IL": ring["in_l"], "GRW": ring["grw"]}
        rid = cells.get(r["pcell"], {**r["fixed"], **{k: round(_ev(v, env), 6) for k, v in r["map"].items()}})
        o = ring["opening"]
        t = pya.DTrans(o["x_min"] - _ev(r["opening"]["x0"], env), o["y_min"] - _ev(r["opening"]["y0"], env))
        cell.insert(pya.DCellInstArray(rid, t))
        tap = pya.Region(ly.cell(rid).begin_shapes_rec(ly.layer(*r["tap_layer"]))).bbox().to_dtype(ly.dbu).transformed(t)
        for f in r["fill"]:
            cell.shapes(ly.layer(*f["layer"])).insert(tap.enlarged(f["enclosure"], f["enclosure"]))
    routing = variant.get("routing")
    if routing:                         # lib/block_router: shapes in the variant frame, pins with net labels
        rl = pdk["routing"]
        gds = {**{n: l["gds"] for n, l in rl["layers"].items()}, **{n: v["gds"] for n, v in rl["vias"].items()}}
        for s in routing["shapes"]:
            cell.shapes(ly.layer(*gds[s["layer"]])).insert(pya.DBox(*s["rect"]))
        for p in routing["pins"] + routing.get("power_pins", []):   # power pins: the ring band, already drawn
            lay, b = rl["layers"][p["layer"]], pya.DBox(*p["rect"])
            for key in ("gds", "pin"):
                cell.shapes(ly.layer(*lay[key])).insert(b)
            cell.shapes(ly.layer(*lay["label"])).insert(pya.DText(p["net"], b.center().x, b.center().y))
    cell.flatten(False)                 # keep the PCell variants: later blocks reuse them
    for t in texts:
        cell.shapes(ly.layer(*text_layer)).insert(t)
    return cell


def _placed_blocks(data: dict) -> dict:
    p = data["placement"]
    if "placed_blocks" in p:
        return p["placed_blocks"]
    best = next(r for r in p["runs"] if r.get("run_id") == p.get("best_run_id"))
    return best["placed_blocks"]


def build(data: dict, pdk: dict, text_layer: list):
    """(layout, top cell, {block title: absolute DBox})."""
    ly = pya.Layout()
    ly.dbu = pdk["dbu"]
    lib = (pya.Library.library_by_name(pdk["library"], pdk["technology"])
           if pdk.get("technology") else pya.Library.library_by_name(pdk["library"]))
    cells = _Cells(ly, lib)
    top = ly.create_cell("TOP")
    boxes = {}
    for key, pb in _placed_blocks(data).items():
        if "main_bbox" not in pb:
            continue
        variant, by_id, title = _variant_of(data, int(key), pb)
        cell = build_block(ly, cells, pdk, variant, by_id, f"B{key}_{title}", text_layer)
        mb = pb["main_bbox"]
        if variant.get("rotation_deg", 0) == 90:
            # 90° CW maps the unrotated frame (0..W0, 0..H0) to (0..H0, -W0..0); W0 = rotated height
            h = variant["main_bbox"]["y_max"] if "main_bbox" in variant else variant["height_um"]
            t = pya.DTrans(3, False, mb["x_min"], mb["y_min"] + h)
        else:
            t = pya.DTrans(mb["x_min"], mb["y_min"])
        top.insert(pya.DCellInstArray(cell.cell_index(), t))
        boxes[cell.name] = pya.DBox(mb["x_min"], mb["y_min"], mb["x_max"], mb["y_max"])
    for c in [c for c in ly.top_cells() if c.cell_index() != top.cell_index()]:
        c.prune_cell()                  # PCell variants, now flattened into the blocks
    return ly, top, boxes


def drc_report(spec: dict, pdk: dict, ly, top, boxes: dict) -> dict:
    """DRC on a flat copy: the KLayout deck reports markers in the coordinates
    of the cell it finds them in, so only a flat layout gives top coordinates."""
    flat = pya.Layout()
    flat.assign(ly)
    flat_top = flat.cell(top.name)
    flat_top.flatten(True)
    gds = f"{_CONTAINER_DIR}/flat_for_drc.gds"
    flat.write(gds)
    markers = drc_tools.all_markers(spec["container"]["drc"], gds, flat_top.name, flat_top.dbbox().width(),
                                    "export", _CONTAINER_DIR)
    intrinsic = {r for rules in pdk.get("intrinsic_violations", {}).values() for r in rules}
    out = {"clean": True, "violations": {}, "intrinsic": {}}
    for rule, x1, y1, x2, y2 in markers:
        c = pya.DPoint((x1 + x2) / 2, (y1 + y2) / 2)
        near = [n for n, b in boxes.items() if b.enlarged(_MARGIN_UM, _MARGIN_UM).contains(c)]
        where = " | ".join(near) if near else "outside every block"
        bucket = out["intrinsic"] if rule in intrinsic else out["violations"]
        bucket.setdefault(rule, []).append({"block": where, "box": [round(v, 3) for v in (x1, y1, x2, y2)]})
    out["clean"] = not out["violations"]
    out["summary"] = {r: len(v) for r, v in out["violations"].items()}
    return out


def main_container(placement: str, pdk_path: str, spec_path: str, out: str, drc: bool) -> None:
    data = json.loads(Path(placement).read_text(encoding="utf-8"))
    pdk = pdk_tree.load(pdk_path)
    spec = pdk_tree.load(spec_path)
    ly, top, boxes = build(data, pdk, spec["annotation_layer"])
    ly.write(out)
    logger.info("wrote %s: %d blocks", out, len(boxes))
    if drc:
        rep = drc_report(spec, pdk, ly, top, boxes)
        Path(out).with_suffix(".drc.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
        logger.info("DRC %s: %s", "clean" if rep["clean"] else "violations", rep["summary"])

# =============================================================================
# 5. ENTRY POINT (host)
# =============================================================================

def export(placement_json: str, out_gds: str, drc: bool = False) -> dict | None:
    """Host side: run the export in the PDK container. Returns the DRC report (drc=True)."""
    placement_json, out_gds = Path(placement_json).resolve(), Path(out_gds).resolve()
    data = json.loads(placement_json.read_text(encoding="utf-8"))
    pdk_name = data.get("generation_params", {}).get("pdk")
    if not pdk_name:
        raise KeyError("export: placement JSON has no generation_params.pdk (not a --pdk run)")
    pdk_dir = _PDK_DIR / pdk_name
    spec = pdk_tree.load(pdk_dir / "characterize.json")
    c = spec["container"]["name"]
    subprocess.run(["docker", "exec", c, "mkdir", "-p", _CONTAINER_DIR], check=True)
    files = {"export_gds.py": Path(__file__).resolve(), "drc_tools.py": _PDK_DIR / "drc_tools.py",
             "pdk_tree.py": _PDK_DIR / "pdk_tree.py",
             "placement.json": placement_json, "pdk.json": pdk_dir / "pdk.json",
             "characterize.json": pdk_dir / "characterize.json"}
    for name, f in files.items():
        subprocess.run(["docker", "cp", str(f), f"{c}:{_CONTAINER_DIR}/{name}"], check=True)
    d = _CONTAINER_DIR
    inner = (f"cd {d} && rm -f out.gds out.drc.json && klayout -b -rm {spec['container']['pcell_macro']} -r {d}/export_gds.py "
             f"-rd placement={d}/placement.json -rd pdk={d}/pdk.json -rd spec={d}/characterize.json "
             f"-rd out={d}/out.gds -rd drc={int(drc)}")
    subprocess.run(["docker", "exec", c, "bash", "-lc", inner], check=True)
    subprocess.run(["docker", "cp", f"{c}:{d}/out.gds", str(out_gds)], check=True)
    logger.info("wrote %s", out_gds)
    if not drc:
        return None
    rep_path = out_gds.with_suffix(".drc.json")
    subprocess.run(["docker", "cp", f"{c}:{d}/out.drc.json", str(rep_path)], check=True)
    return json.loads(rep_path.read_text(encoding="utf-8"))


if pya is None:
    if __name__ == "__main__":
        args = [a for a in sys.argv[1:] if a != "--drc"]
        if len(args) != 2:
            sys.exit("usage: export_gds.py <s*_py101_*.json> <out.gds> [--drc]")
        rep = export(args[0], args[1], drc="--drc" in sys.argv)
        if rep is not None:
            logger.info("DRC: %s %s", "clean" if rep["clean"] else "VIOLATIONS", rep["summary"])
else:
    g = globals()
    main_container(g["placement"], g["pdk"], g["spec"], g["out"], g.get("drc", "0") == "1")
