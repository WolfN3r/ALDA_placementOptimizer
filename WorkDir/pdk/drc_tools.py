"""
DRC runners shared by characterize_pdk.py and export_gds.py (run inside the
PDK container, where the checkers live). Each returns markers
[(rule, x1, y1, x2, y2)] in µm for one GDS and its top cell; every checker is
one entry of the PDK spec's container.drc list (characterize.json).
"""
import os
import re
import subprocess
import xml.etree.ElementTree as ET

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

DRC_TIMEOUT_S = 3600

# =============================================================================
# ALGORITHM
# =============================================================================

def klayout_markers(chk: dict, gds: str, top: str, tag: str, workdir: str) -> list:
    """Markers from a KLayout deck (chk: deck, vars)."""
    rpt = f"{workdir}/{tag}_klayout.xml"
    cmd = ["klayout", "-b", "-r", os.path.expandvars(chk["deck"]),
           "-rd", f"input={gds}", "-rd", f"report={rpt}", "-rd", f"top_cell={top}"]
    for k, v in chk["vars"].items():
        cmd += ["-rd", f"{k}={v}"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, timeout=DRC_TIMEOUT_S)
    out = []
    for item in ET.parse(rpt).getroot().iter("item"):
        cat = (item.findtext("category") or "").strip("'")
        pts = []
        for val in item.iter("value"):
            pts += [(float(a), float(b)) for a, b in
                    re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", val.text or "")]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((f"klayout:{cat}", min(xs), min(ys), max(xs), max(ys)))
    return out


def magic_markers(chk: dict, gds: str, top: str, top_width_um: float, tag: str, workdir: str) -> list:
    """Markers from magic (chk: rcfile, style). magic reports internal units;
    the scale comes from the top cell's width (known in µm)."""
    res = f"{workdir}/{tag}_magic.txt"
    tcl = f"{workdir}/{tag}_magic.tcl"
    with open(tcl, "w") as f:
        f.write(f"""drc off
gds read {gds}
load {top}
select top cell
set out [open {res} w]
puts $out "BBOX [box values]"
drc style {chk['style']}
drc euclidean on
drc check
drc catchup
foreach {{why boxes}} [drc listall why] {{ foreach b $boxes {{ puts $out "$why|$b" }} }}
close $out
quit -noprompt
""")
    subprocess.run(["magic", "-dnull", "-noconsole", "-rcfile", os.path.expandvars(chk["rcfile"]), tcl],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=DRC_TIMEOUT_S)
    lines = open(res).read().splitlines()
    bx = [float(v) for v in lines[0].split()[1:]]
    scale = top_width_um / (bx[2] - bx[0])
    out = []
    for line in lines[1:]:
        why, box = line.rsplit("|", 1)
        x1, y1, x2, y2 = (float(v) * scale for v in box.split())
        out.append((f"magic:{why}", x1, y1, x2, y2))
    return out


def all_markers(checkers: list, gds: str, top: str, top_width_um: float, tag: str, workdir: str) -> list:
    """Markers of every checker in the spec's container.drc list."""
    markers = []
    for chk in checkers:
        if chk["tool"] == "klayout":
            markers += klayout_markers(chk, gds, top, tag, workdir)
        elif chk["tool"] == "magic":
            markers += magic_markers(chk, gds, top, top_width_um, tag, workdir)
        else:
            raise ValueError(f"unknown DRC tool {chk['tool']!r}")
    return markers
