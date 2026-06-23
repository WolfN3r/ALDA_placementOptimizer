"""Pure-Python TikZ snippet exporter for ALDA placement designs.

Generates a \\begin{tikzpicture}...\\end{tikzpicture} block (no \\documentclass)
suitable for \\input{} in an existing LaTeX document.  Requires only \\usepackage{tikz}.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

_COMPOSITE_ID_BASE = 10_000

# Composite-group fill colors (matching PlacementScene._COMPOSITE_FILLS)
_COMPOSITE_FILLS: dict[str, tuple[int, int, int]] = {
    "diff_pair":              (40, 120,  40),
    "current_mirror":         (40,  80, 160),
    "cascode_current_mirror": (100, 40, 140),
    "tail_cm_pair":           (160,  90,  30),
}
_TOPOLOGY_ABBREV: dict[str, str] = {
    "diff_pair":              "DP",
    "current_mirror":         "CM",
    "cascode_current_mirror": "Casc",
    "tail_cm_pair":           "Tail",
}


# ---------------------------------------------------------------------------
# Public settings dataclass
# ---------------------------------------------------------------------------

@dataclass
class TikZExportSettings:
    """Export settings that the UI dialog passes to generate()."""
    scale_pct: float = 100.0                  # 50–500%; 100% = 1 µm → 1 mm
    enabled_layers: set[str] = field(default_factory=lambda: {
        "annotation", "net_power", "net_signal", "net_routes",
        "labels", "symmetry", "sym_diff_pair", "sym_current_mirror",
        "sym_cascode", "sym_passive", "sym_tail", "sym_cascode_prox", "sym_tail_cm",
    })
    enabled_device_types: set[str] = field(default_factory=set)
    show_labels: bool = True
    label_font_size: str = "tiny"             # "tiny" | "scriptsize" | "footnotesize"
    line_width_pt: float = 0.4
    background_white: bool = True
    show_scale_bar: bool = True
    scale_bar_length_um: float = 0.0          # 0 = auto
    scale_bar_position: str = "bottom-left"   # "bottom-left" | "bottom-right"
    show_legend: bool = True
    show_net_labels: bool = False
    comment_name: str = ""
    wrap_in_figure: bool = True
    figure_placement: str = "h"               # LaTeX figure placement: h, b, t, H, !h, htbp
    figure_caption: str = ""


# ---------------------------------------------------------------------------
# Name / color helpers
# ---------------------------------------------------------------------------

def _cname(device_type: str, suffix: str) -> str:
    """TikZ \\definecolor name for a device type, e.g. alda-nmos-rvt-fill."""
    return "alda-" + device_type.replace("_", "-") + "-" + suffix


def _lname(layer_key: str) -> str:
    """TikZ \\definecolor name for a layer, e.g. alda-net-power."""
    return "alda-" + layer_key.replace("_", "-")


def _rgb(r: int, g: int, b: int) -> str:
    """Inline TikZ color specification."""
    return f"{{rgb,255:red,{r};green,{g};blue,{b}}}"


def _auto_scale_bar_length(chip_width_um: float) -> float:
    """Return a round number ≈ 15 % of the chip width."""
    target = chip_width_um * 0.15
    if target <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(max(target, 1e-9)))
    for step in (1, 2, 5, 10):
        candidate = step * magnitude
        if candidate >= target * 0.5:
            return candidate
    return magnitude * 10


def _power_rgb(net_id: str) -> tuple[int, int, int]:
    nid = net_id.upper()
    if "VDD" in nid or nid in ("VDDA", "AVDD", "VCC"):
        return (255, 85, 85)
    return (85, 136, 255)


# ---------------------------------------------------------------------------
# Coordinate-translation + emitter context
# ---------------------------------------------------------------------------

class _Ctx:
    """Holds translated-coordinate helpers and the output line buffer."""

    def __init__(self, lines: list[str], ox: float, oy: float) -> None:
        self._lines = lines
        self._ox = ox
        self._oy = oy

    def emit(self, s: str) -> None:
        self._lines.append(s)

    # Translated coordinates (shift chip origin to 0,0)
    def tx(self, v: float) -> float:
        return round(v - self._ox, 6)

    def ty(self, v: float) -> float:
        return round(v - self._oy, 6)

    def pt(self, x: float, y: float) -> str:
        return f"({self.tx(x):.4f},{self.ty(y):.4f})"

    def rect(self, x0: float, y0: float, x1: float, y1: float) -> str:
        return (f"({self.tx(x0):.4f},{self.ty(y0):.4f})"
                f" rectangle ({self.tx(x1):.4f},{self.ty(y1):.4f})")


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _draw_block(ctx: _Ctx, bid: int, pb, data, s: TikZExportSettings) -> None:
    """Emit \\filldraw for one non-composite block rectangle plus optional label."""
    x0, y0, x1, y1 = pb.main_bbox
    block = data.block_by_id(bid)
    dt = block.device_type if block else ""
    lw = s.line_width_pt

    if dt and dt in s.enabled_device_types:
        ctx.emit(f"  \\filldraw[fill={_cname(dt,'fill')}, fill opacity=0.55,")
        ctx.emit(f"    draw={_cname(dt,'border')}, line width={lw}pt]")
    else:
        ctx.emit(f"  \\filldraw[fill=gray!40, fill opacity=0.55, draw=gray!60, line width={lw}pt]")
    ctx.emit(f"    {ctx.rect(x0, y0, x1, y1)};")

    if s.show_labels and "labels" in s.enabled_layers:
        ctx.emit(f"  \\node[font=\\{s.label_font_size}] at"
                 f" ({ctx.tx((x0+x1)/2):.4f},{ctx.ty((y0+y1)/2):.4f}) {{B{bid}}};")


def _draw_pin(ctx: _Ctx, pdata: dict) -> None:
    """Emit one pin shape (M1 rect or small square fallback)."""
    if "x_min" in pdata:
        rx0, ry0 = float(pdata["x_min"]), float(pdata["y_min"])
        rx1, ry1 = float(pdata["x_max"]), float(pdata["y_max"])
        pin_type = pdata.get("type", "signal")
        side = pdata.get("side", "top")
        if pin_type == "power":
            nr, ng, nb = (255, 85, 85) if side == "top" else (85, 136, 255)
        else:
            nr, ng, nb = 68, 204, 68
        ctx.emit(f"  \\filldraw[fill={_rgb(nr,ng,nb)}, fill opacity=0.35,"
                 f" draw={_rgb(nr,ng,nb)}, line width=0.1pt]")
        ctx.emit(f"    {ctx.rect(rx0, ry0, rx1, ry1)};")
    else:
        px = float(pdata.get("x", 0.0))
        py = float(pdata.get("y", 0.0))
        arm = 0.25
        ctx.emit(f"  \\fill[yellow!80!black]"
                 f" ({ctx.tx(px-arm):.4f},{ctx.ty(py-arm):.4f})"
                 f" rectangle ({ctx.tx(px+arm):.4f},{ctx.ty(py+arm):.4f});")


def _draw_nets(ctx: _Ctx, data, flat_pb: dict, EL: set[str],
               s: TikZExportSettings) -> None:
    """Emit ratsnest lines for signal nets that have no route_segments."""
    for net in data.nets:
        if net.route_segments:
            continue
        if net.net_type == "power" and "net_power" not in EL:
            continue
        if net.net_type != "power" and "net_signal" not in EL:
            continue

        pts: list[tuple[float, float]] = []
        for pin_ref in net.pins:
            try:
                parts = pin_ref.split("_", 1)
                bid = int(parts[0][1:])
                pname = parts[1]
            except (ValueError, IndexError):
                continue
            if bid not in flat_pb:
                continue
            pdata = flat_pb[bid].pins.get(pname, {})
            if "x_min" in pdata:
                px = (float(pdata["x_min"]) + float(pdata["x_max"])) / 2
                py = (float(pdata["y_min"]) + float(pdata["y_max"])) / 2
            elif "x" in pdata:
                px, py = float(pdata["x"]), float(pdata["y"])
            else:
                continue
            pts.append((px, py))

        if not pts:
            continue

        if net.net_type == "power":
            continue

        if len(pts) < 2:
            continue
        nr, ng, nb = 68, 204, 68
        cx_net = sum(p[0] for p in pts) / len(pts)
        cy_net = sum(p[1] for p in pts) / len(pts)
        for px, py in pts:
            ctx.emit(f"  \\draw[color={_rgb(nr,ng,nb)}, line width=0.3pt]")
            ctx.emit(f"    {ctx.pt(px, py)} -- {ctx.pt(cx_net, cy_net)};")
        if s.show_net_labels:
            label = net.net_id[:8].replace("_", "\\_")
            ctx.emit(f"  \\node[font=\\tiny, text={_rgb(nr,ng,nb)}]"
                     f" at {ctx.pt(cx_net, cy_net)} {{{label}}};")


def _draw_symmetry(ctx: _Ctx, data, flat_pb: dict,
                   chip_x0: float, chip_y0: float,
                   chip_w: float, chip_h: float,
                   EL: set[str], s: TikZExportSettings, lm) -> None:
    """Emit symmetry axis lines, pair connectors, cascode/tail/passive markers."""
    sc = data.symmetry_constraints
    if not sc:
        return

    global_axis = sc.get("symmetry_axis", "vertical")

    generic_sym = "symmetry" in EL

    for grp in sc.get("groups", []):
        tag = str(grp.get("topology_tag", ""))
        layer_key = lm.topology_layer_key(tag)
        if layer_key not in EL and not generic_sym:
            continue
        sym_color = _lname("symmetry") if generic_sym else _lname(layer_key)

        group_pairs: list[tuple[int, int]] = []
        for p in grp.get("pairs", []):
            if isinstance(p, dict):
                group_pairs.append((int(p["block_a"]), int(p["block_b"])))
            else:
                group_pairs.append((int(p[0]), int(p[1])))

        axis_dir = grp.get("axis", global_axis)
        placed = [(a, b) for a, b in group_pairs if a in flat_pb and b in flat_pb]

        if placed:
            if axis_dir == "horizontal":
                midpoints = [
                    ((flat_pb[a].main_bbox[1] + flat_pb[a].main_bbox[3]) / 2
                     + (flat_pb[b].main_bbox[1] + flat_pb[b].main_bbox[3]) / 2) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                ctx.emit(f"  \\draw[color={sym_color}, dashed, line width=0.5pt]")
                ctx.emit(f"    ({ctx.tx(chip_x0):.4f},{ctx.ty(axis_pos):.4f})"
                         f" -- ({ctx.tx(chip_x0+chip_w):.4f},{ctx.ty(axis_pos):.4f});")
                if tag and s.show_labels:
                    ctx.emit(f"  \\node[font=\\tiny, color={sym_color}, right]"
                             f" at ({ctx.tx(chip_x0+chip_w*0.02):.4f},{ctx.ty(axis_pos):.4f})"
                             f" {{{tag.replace('_',' ')}}};")
            else:
                midpoints = [
                    ((flat_pb[a].main_bbox[0] + flat_pb[a].main_bbox[2]) / 2
                     + (flat_pb[b].main_bbox[0] + flat_pb[b].main_bbox[2]) / 2) / 2
                    for a, b in placed
                ]
                axis_pos = sum(midpoints) / len(midpoints)
                ctx.emit(f"  \\draw[color={sym_color}, dashed, line width=0.5pt]")
                ctx.emit(f"    ({ctx.tx(axis_pos):.4f},{ctx.ty(chip_y0):.4f})"
                         f" -- ({ctx.tx(axis_pos):.4f},{ctx.ty(chip_y0+chip_h):.4f});")
                if tag and s.show_labels:
                    ctx.emit(f"  \\node[font=\\tiny, color={sym_color}, above]"
                             f" at ({ctx.tx(axis_pos):.4f},{ctx.ty(chip_y0+chip_h):.4f})"
                             f" {{{tag.replace('_',' ')}}};")

        for a, b in group_pairs:
            if a not in flat_pb or b not in flat_pb:
                continue
            ba, bb = flat_pb[a].main_bbox, flat_pb[b].main_bbox
            ctx.emit(f"  \\draw[color={sym_color}, line width=0.4pt]")
            ctx.emit(f"    {ctx.pt((ba[0]+ba[2])/2,(ba[1]+ba[3])/2)}"
                     f" -- {ctx.pt((bb[0]+bb[2])/2,(bb[1]+bb[3])/2)};")

        for ss in grp.get("self_symmetric", []):
            ss_id = int(ss)
            if ss_id not in flat_pb:
                continue
            bb_ss = flat_pb[ss_id].main_bbox
            sx = (bb_ss[0] + bb_ss[2]) / 2
            sy = (bb_ss[1] + bb_ss[3]) / 2
            arm = min(bb_ss[2]-bb_ss[0], bb_ss[3]-bb_ss[1]) * 0.18
            ctx.emit(f"  \\draw[color={sym_color}, line width=0.5pt]"
                     f" ({ctx.tx(sx-arm):.4f},{ctx.ty(sy):.4f})"
                     f" -- ({ctx.tx(sx+arm):.4f},{ctx.ty(sy):.4f});")
            ctx.emit(f"  \\draw[color={sym_color}, line width=0.5pt]"
                     f" ({ctx.tx(sx):.4f},{ctx.ty(sy-arm):.4f})"
                     f" -- ({ctx.tx(sx):.4f},{ctx.ty(sy+arm):.4f});")

    # Cascode proximity pairs
    if "sym_cascode_prox" in EL or generic_sym:
        casc_color = _lname("symmetry") if generic_sym else "alda-sym-cascode-prox"
        for entry in sc.get("cascode_proximity_pairs", []):
            u_id, l_id = int(entry[0]), int(entry[1])
            if u_id not in flat_pb or l_id not in flat_pb:
                continue
            bu, bl = flat_pb[u_id].main_bbox, flat_pb[l_id].main_bbox
            cxu = (bu[0]+bu[2])/2; cyu = (bu[1]+bu[3])/2
            cxl = (bl[0]+bl[2])/2; cyl = (bl[1]+bl[3])/2
            ctx.emit(f"  \\draw[color={casc_color}, line width=0.5pt]")
            ctx.emit(f"    {ctx.pt(cxu, cyu)} -- {ctx.pt(cxl, cyl)};")
            mid_x = (cxu+cxl)/2; mid_y = (cyu+cyl)/2; arm = 0.25
            ctx.emit(f"  \\fill[{casc_color}]"
                     f" ({ctx.tx(mid_x-arm):.4f},{ctx.ty(mid_y-arm):.4f})"
                     f" rectangle ({ctx.tx(mid_x+arm):.4f},{ctx.ty(mid_y+arm):.4f});")

    # Tail-CM pairs
    if "sym_tail_cm" in EL or generic_sym:
        tail_color = _lname("symmetry") if generic_sym else "alda-sym-tail-cm"
        for entry in sc.get("tail_cm_pairs", []):
            t_id, m_id = int(entry[0]), int(entry[1])
            if t_id not in flat_pb or m_id not in flat_pb:
                continue
            bt, bm = flat_pb[t_id].main_bbox, flat_pb[m_id].main_bbox
            ctx.emit(f"  \\draw[color={tail_color}, dashed, line width=0.5pt]")
            ctx.emit(f"    {ctx.pt((bt[0]+bt[2])/2,(bt[1]+bt[3])/2)}"
                     f" -- {ctx.pt((bm[0]+bm[2])/2,(bm[1]+bm[3])/2)};")

    # Passive clusters
    if "sym_passive" in EL or generic_sym:
        pass_color = _lname("symmetry") if generic_sym else "alda-sym-passive"
        PAD = 0.15
        for cluster in sc.get("passive_clusters", []):
            members = [int(m) for m in cluster.get("members", [])]
            pm = [m for m in members if m in flat_pb]
            if not pm:
                continue
            x0 = min(flat_pb[m].main_bbox[0] for m in pm) - PAD
            y0 = min(flat_pb[m].main_bbox[1] for m in pm) - PAD
            x1 = max(flat_pb[m].main_bbox[2] for m in pm) + PAD
            y1 = max(flat_pb[m].main_bbox[3] for m in pm) + PAD
            ctx.emit(f"  \\draw[color={pass_color}, dashed, line width=0.5pt]")
            ctx.emit(f"    {ctx.rect(x0, y0, x1, y1)};")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate(
    data,
    lm,
    settings: TikZExportSettings,
    drc_violations=None,
) -> str:
    """Return a TikZ snippet string for the current placement.

    No \\documentclass or \\usepackage — the caller's document must have
    \\usepackage{tikz} in its preamble.
    """
    pr = data.placement_result
    if not pr or not pr.placed_blocks:
        return (
            "% No placement data available.\n"
            "% Load a JSON file processed by the placement optimizer.\n"
        )

    # Build flat block lookup (top-level + sub-blocks of composite groups)
    flat_pb: dict[int, object] = {}
    for bid, pb in pr.placed_blocks.items():
        flat_pb[bid] = pb
        if pb.is_composite:
            for mbid, mpb in pb.sub_blocks.items():
                flat_pb[mbid] = mpb

    # Chip bounding box
    all_bbs = [pb.main_bbox for pb in flat_pb.values()]
    chip_x0 = min(b[0] for b in all_bbs)
    chip_y0 = min(b[1] for b in all_bbs)
    chip_x1 = max(b[2] for b in all_bbs)
    chip_y1 = max(b[3] for b in all_bbs)
    chip_w = chip_x1 - chip_x0
    chip_h = chip_y1 - chip_y0

    S = settings.scale_pct / 100.0
    EL = settings.enabled_layers

    # Device types that are both present in the design and enabled in settings
    regular_bids = [bid for bid in flat_pb if bid < _COMPOSITE_ID_BASE]
    present_dtypes: set[str] = set()
    for bid in regular_bids:
        block = data.block_by_id(bid)
        if block and block.device_type in settings.enabled_device_types:
            present_dtypes.add(block.device_type)

    lines: list[str] = []
    ctx = _Ctx(lines, chip_x0, chip_y0)

    # ── Header ────────────────────────────────────────────────────────────
    name = settings.comment_name.strip() or "placement"
    source = Path(data.file_path).name if data.file_path else "unknown"
    ctx.emit(f"% {name} -- generated by ALDA Placement Viewer {date.today().isoformat()}")
    ctx.emit(f"% Source: {source}  |  Scale: {settings.scale_pct:.0f}% (1 um = {S:.2f} mm)")
    ctx.emit("")

    # ── Color definitions ─────────────────────────────────────────────────
    ctx.emit("% Color definitions")
    for dt in sorted(present_dtypes):
        r, g, b, _ = lm.get_device_fill_rgba(dt)
        br, bg, bb = lm.get_device_border_rgb(dt)
        ctx.emit(f"\\definecolor{{{_cname(dt,'fill')}}}{{RGB}}{{{r},{g},{b}}}")
        ctx.emit(f"\\definecolor{{{_cname(dt,'border')}}}{{RGB}}{{{br},{bg},{bb}}}")
    for lk in sorted(EL):
        try:
            ld = lm.layer(lk)
        except KeyError:
            continue
        c = ld.color
        ctx.emit(f"\\definecolor{{{_lname(lk)}}}{{RGB}}{{{c.red()},{c.green()},{c.blue()}}}")
    ctx.emit("")

    # ── figure + tikzpicture ─────────────────────────────────────────────
    if settings.wrap_in_figure:
        fp = settings.figure_placement or "h"
        ctx.emit(f"\\begin{{figure}}[{fp}]")
        ctx.emit("  \\centering")
    S_fmt = f"{S:.4g}"
    ctx.emit(f"\\begin{{tikzpicture}}[x={S_fmt}mm, y={S_fmt}mm]")
    ctx.emit("")

    if settings.background_white:
        ctx.emit("% Background")
        ctx.emit(f"  \\fill[white] (0,0) rectangle ({chip_w:.4f},{chip_h:.4f});")
        ctx.emit("")

    if "annotation" in EL:
        lw = settings.line_width_pt
        ctx.emit("% Chip outline")
        ctx.emit(f"  \\draw[color=alda-annotation, line width={lw}pt]")
        ctx.emit(f"    (0,0) rectangle ({chip_w:.4f},{chip_h:.4f});")
        ctx.emit("")

    # Chip power rails
    if "annotation" in EL and pr.chip_power_rails:
        ctx.emit("% Chip power rails")
        for rail in pr.chip_power_rails:
            rx0 = float(rail.get("x_min", 0)); rx1 = float(rail.get("x_max", 0))
            ry0 = float(rail.get("y_min", 0)); ry1 = float(rail.get("y_max", 0))
            net = str(rail.get("net", "")).upper()
            nr, ng, nb = (255, 85, 85) if ("VDD" in net or net in ("VDDA","AVDD","VCC")) else (85, 136, 255)
            ctx.emit(f"  \\filldraw[fill={_rgb(nr,ng,nb)}, fill opacity=0.47,"
                     f" draw={_rgb(nr,ng,nb)}, line width=0.2pt]")
            ctx.emit(f"    {ctx.rect(rx0, ry0, rx1, ry1)};")
        ctx.emit("")

    # ── Blocks ────────────────────────────────────────────────────────────
    if "annotation" in EL:
        ctx.emit("% Blocks")
        lw = settings.line_width_pt
        for bid, pb in pr.placed_blocks.items():
            if pb.is_composite:
                x0, y0, x1, y1 = pb.main_bbox
                ttype = pb.topology_type
                nr, ng, nb = _COMPOSITE_FILLS.get(ttype, (60, 60, 60))
                abbrev = _TOPOLOGY_ABBREV.get(ttype, ttype[:4] if ttype else "?")
                ctx.emit(f"  % Group {bid}: {ttype}")
                ctx.emit(f"  \\draw[color={_rgb(nr,ng,nb)}, dashed, line width={lw*2:.2f}pt]")
                ctx.emit(f"    {ctx.rect(x0, y0, x1, y1)};")
                if settings.show_labels and "labels" in EL:
                    ctx.emit(f"  \\node[font=\\{settings.label_font_size},"
                             f" color={_rgb(nr,ng,nb)}, above]"
                             f" at ({ctx.tx(x0):.4f},{ctx.ty(y1):.4f}) {{{abbrev}}};")
                for mbid, mpb in pb.sub_blocks.items():
                    _draw_block(ctx, mbid, mpb, data, settings)
            else:
                _draw_block(ctx, bid, pb, data, settings)
        ctx.emit("")

    # ── Pins ──────────────────────────────────────────────────────────────
    if "annotation" in EL:
        ctx.emit("% Pins")
        any_pin = False
        for bid, pb in pr.placed_blocks.items():
            targets = list(pb.sub_blocks.items()) if pb.is_composite else [(bid, pb)]
            for _, tpb in targets:
                for pdata in tpb.pins.values():
                    _draw_pin(ctx, pdata)
                    any_pin = True
        if not any_pin:
            ctx.emit("  % (no pins in this placement)")
        ctx.emit("")

    # ── Net ratsnest ──────────────────────────────────────────────────────
    if "net_power" in EL or "net_signal" in EL:
        ctx.emit("% Net connections (ratsnest)")
        _draw_nets(ctx, data, flat_pb, EL, settings)
        ctx.emit("")

    # ── Route segments ────────────────────────────────────────────────────
    if "net_routes" in EL:
        ctx.emit("% Route segments")
        any_seg = False
        for net in data.nets:
            if not net.route_segments:
                continue
            nr, ng, nb = _power_rgb(net.net_id) if net.net_type == "power" else (68, 204, 68)
            for seg in net.route_segments:
                sx0 = float(seg.get("x_min", 0)); sx1 = float(seg.get("x_max", 0))
                sy0 = float(seg.get("y_min", 0)); sy1 = float(seg.get("y_max", 0))
                ctx.emit(f"  \\filldraw[fill={_rgb(nr,ng,nb)}, fill opacity=0.4,"
                         f" draw={_rgb(nr,ng,nb)}, line width=0.1pt]")
                ctx.emit(f"    {ctx.rect(sx0, sy0, sx1, sy1)};")
                any_seg = True
        if not any_seg:
            ctx.emit("  % (no route segments in this file)")
        ctx.emit("")

    # ── Symmetry ──────────────────────────────────────────────────────────
    has_sym_layers = any(k in EL for k in (
        "symmetry", "sym_diff_pair", "sym_current_mirror", "sym_cascode",
        "sym_passive", "sym_tail", "sym_cascode_prox", "sym_tail_cm",
    ))
    if has_sym_layers:
        ctx.emit("% Symmetry annotations")
        _draw_symmetry(ctx, data, flat_pb, chip_x0, chip_y0, chip_w, chip_h, EL, settings, lm)
        ctx.emit("")

    # ── DRC overlay ───────────────────────────────────────────────────────
    if drc_violations and "drc_overlay" in EL:
        ctx.emit("% DRC violations")
        for v in drc_violations:
            ax0, ay0, ax1, ay1 = v.bbox_a
            bx0, by0, bx1, by1 = v.bbox_b
            if v.category == "physical_overlap":
                ix0 = max(ax0, bx0); iy0 = max(ay0, by0)
                ix1 = min(ax1, bx1); iy1 = min(ay1, by1)
                if ix0 < ix1 and iy0 < iy1:
                    ctx.emit(f"  \\filldraw[fill={_rgb(255,60,60)}, fill opacity=0.5,"
                             f" draw={_rgb(255,0,0)}, line width=0.3pt]")
                    ctx.emit(f"    {ctx.rect(ix0, iy0, ix1, iy1)};")
            else:
                cv_x = (ax0+ax1+bx0+bx1)/4; cv_y = (ay0+ay1+by0+by1)/4; arm = 0.5
                ctx.emit(f"  \\draw[color={_rgb(255,100,0)}, line width=0.3pt]"
                         f" ({ctx.tx(cv_x-arm):.4f},{ctx.ty(cv_y):.4f})"
                         f" -- ({ctx.tx(cv_x+arm):.4f},{ctx.ty(cv_y):.4f});")
                ctx.emit(f"  \\draw[color={_rgb(255,100,0)}, line width=0.3pt]"
                         f" ({ctx.tx(cv_x):.4f},{ctx.ty(cv_y-arm):.4f})"
                         f" -- ({ctx.tx(cv_x):.4f},{ctx.ty(cv_y+arm):.4f});")
        ctx.emit("")

    # ── Scale bar ─────────────────────────────────────────────────────────
    if settings.show_scale_bar:
        bar_len = (settings.scale_bar_length_um
                   if settings.scale_bar_length_um > 0
                   else _auto_scale_bar_length(chip_w))
        margin = chip_h * 0.05
        tick_h = chip_h * 0.015
        bar_y = chip_y0 - margin
        bar_x0 = ((chip_x0 + chip_w - bar_len)
                  if settings.scale_bar_position == "bottom-right"
                  else chip_x0)
        bar_x1 = bar_x0 + bar_len
        mid_bar = (bar_x0 + bar_x1) / 2

        ctx.emit("% Scale bar")
        ctx.emit(f"  \\draw[line width=1.0pt]"
                 f" ({ctx.tx(bar_x0):.4f},{ctx.ty(bar_y):.4f})"
                 f" -- ({ctx.tx(bar_x1):.4f},{ctx.ty(bar_y):.4f});")
        ctx.emit(f"  \\draw[line width=0.6pt]"
                 f" ({ctx.tx(bar_x0):.4f},{ctx.ty(bar_y-tick_h):.4f})"
                 f" -- ({ctx.tx(bar_x0):.4f},{ctx.ty(bar_y+tick_h):.4f});")
        ctx.emit(f"  \\draw[line width=0.6pt]"
                 f" ({ctx.tx(bar_x1):.4f},{ctx.ty(bar_y-tick_h):.4f})"
                 f" -- ({ctx.tx(bar_x1):.4f},{ctx.ty(bar_y+tick_h):.4f});")
        label = (f"{bar_len:.0f}\\,$\\mu$m" if bar_len >= 1.0
                 else f"{bar_len:.2f}\\,$\\mu$m")
        ctx.emit(f"  \\node[font=\\tiny, below]"
                 f" at ({ctx.tx(mid_bar):.4f},{ctx.ty(bar_y):.4f}) {{{label}}};")
        ctx.emit("")

    # ── Legend ────────────────────────────────────────────────────────────
    if settings.show_legend and present_dtypes:
        swatch_h = max(chip_h * 0.04, 1.0)
        swatch_w = swatch_h * 1.5
        gap_x = chip_w * 0.06
        row_h = swatch_h * 1.5
        tx_off = swatch_w + chip_w * 0.015
        lx0 = chip_x1 + gap_x       # left edge of legend (in JSON coords)

        ctx.emit("% Legend")
        row = 0
        for dt in sorted(present_dtypes):
            r, g, b, _ = lm.get_device_fill_rgba(dt)
            br, bg, bb = lm.get_device_border_rgb(dt)
            lw = settings.line_width_pt
            y_top = chip_y1 - row * row_h
            y_bot = y_top - swatch_h
            ctx.emit(f"  \\filldraw[fill={_rgb(r,g,b)}, fill opacity=0.55,"
                     f" draw={_rgb(br,bg,bb)}, line width={lw}pt]")
            ctx.emit(f"    {ctx.rect(lx0, y_bot, lx0+swatch_w, y_top)};")
            label = dt.replace("_", "\\_")
            ctx.emit(f"  \\node[font=\\tiny, right]"
                     f" at ({ctx.tx(lx0+tx_off):.4f},{ctx.ty((y_top+y_bot)/2):.4f})"
                     f" {{{label}}};")
            row += 1

        # Symmetry legend entry
        if "symmetry" in EL:
            y_top = chip_y1 - row * row_h
            y_mid = y_top - swatch_h / 2
            ctx.emit(f"  \\draw[color={_lname('symmetry')}, dashed, line width=1.5pt]")
            ctx.emit(f"    ({ctx.tx(lx0):.4f},{ctx.ty(y_mid):.4f})"
                     f" -- ({ctx.tx(lx0+swatch_w):.4f},{ctx.ty(y_mid):.4f});")
            ctx.emit(f"  \\node[font=\\tiny, right]"
                     f" at ({ctx.tx(lx0+tx_off):.4f},{ctx.ty(y_mid):.4f})"
                     f" {{Symmetry}};")
            row += 1
        else:
            sym_layers = [lk for lk in sorted(EL) if lk.startswith("sym_")]
            for lk in sym_layers:
                try:
                    ld = lm.layer(lk)
                except KeyError:
                    continue
                y_top = chip_y1 - row * row_h
                y_mid = y_top - swatch_h / 2
                ctx.emit(f"  \\draw[color={_lname(lk)}, line width=1.5pt]")
                ctx.emit(f"    ({ctx.tx(lx0):.4f},{ctx.ty(y_mid):.4f})"
                         f" -- ({ctx.tx(lx0+swatch_w):.4f},{ctx.ty(y_mid):.4f});")
                label = ld.display_name.replace("_", "\\_")
                ctx.emit(f"  \\node[font=\\tiny, right]"
                         f" at ({ctx.tx(lx0+tx_off):.4f},{ctx.ty(y_mid):.4f})"
                         f" {{{label}}};")
                row += 1
        ctx.emit("")

    ctx.emit("\\end{tikzpicture}")
    if settings.wrap_in_figure:
        if settings.figure_caption:
            caption = settings.figure_caption.replace("_", "\\_")
            ctx.emit(f"  \\caption{{{caption}}}")
        ctx.emit("\\end{figure}")
    return "\n".join(lines)
