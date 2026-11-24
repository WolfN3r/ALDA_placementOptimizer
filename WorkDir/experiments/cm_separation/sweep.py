"""Separating the NMOS current mirror of OTA1 (sky01) from the rest of the circuit:
how wire R/C on the mirror lines changes the mirror currents/voltages and the OTA.

Design: the final sized OTA1 (06_ota1_magical/ota1_sized.spice, result_rounded.json).
NMOS mirror: diode M4 (vbias_n) -> M10 (tail, with M11 from the CMFB), M6/M9 (2nd-stage
sinks on OUTP/OUTM). Wires are lumped pi models (R, C/2 to VSS at both ends).

Cases (wire length in um, met1 and li1 at minimum width):
  c1a  diode M4 away from the mirror: gate line vbias_n -> gates of M10/M6/M9
  c1b  as c1a, plus the VSS line between the diode's ground and the mirror row's
       sources (M10, M11, M6, M9, M13, M12); the ground pin sits at the diode, so the
       whole mirror-row current returns through this line (worst case)
  c2   mirror row away from the OTA core: tail line (M10+M11 drains -> pair sources)
       and output lines (M6 -> OUTP, M9 -> OUTM), all of the same length
  c3   as c2, tail line and output lines of different lengths (2-D grid)
  corners  baseline, c1a/c1b/c2 at 100 um met1 and c3 with tail 1 um / outputs 100 um
           met1, over 15 corners

Runs inside the IIC-OSIC-TOOLS container (/foss/designs/11_cm_separation):
    python3 sweep.py            # all cases -> results/<case>.json
    python3 sweep.py c2 c3      # selected cases
"""
# ============================================================================
# Imports
# ============================================================================
import json
import logging
import math
import os
import re
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = '/foss/designs/06_ota1_magical'
OTA = os.path.join(SRC, 'ota1_sized.spice')
MODELS = os.path.join(SRC, 'models', 'sky130_{lib}.spice')
OUT_DIR = os.path.join(HERE, 'results')
WORKERS = 14

IB = 1.8506543563885517e-05     # A, result_rounded.json
VDD, VREF, VCMI, CL, CFB = 1.8, 0.9, 0.9, 1e-12, 1e-12
MM_SHIFT = 6.0 * 10.5e-3 / math.sqrt(4 * 13.4 * 4.535)   # V, CMRR proxy as definitions.py
R_ZERO = 1e-3                   # Ohm, a "missing" wire

# Wire per um at minimum width (sky130A.tech, nominal extract style):
# R = sheet / width; C = area cap * width + sidewall cap of both edges (neighbours as AC ground)
WIRES = {
    'met1': {'r': 0.125 / 0.14, 'c': (25.78 * 0.14 + 2 * 44.0) * 1e-18},    # 0.89 Ohm, 92 aF
    'li1':  {'r': 12.8 / 0.17,  'c': (36.99 * 0.17 + 2 * 25.5) * 1e-18},    # 75 Ohm, 57 aF
}
LENGTHS = [1, 2, 5, 10, 20, 50, 100]     # um
GRID = [1, 5, 20, 50, 100]               # um, case c3
CORNER_LIBS = ('tt', 'ss', 'ff', 'sf', 'fs')
CORNER_TEMPS = (-20, 27, 120)
CORNER_LEN = 100                         # um met1, corner check
NOMINAL = ('tt', 27)

# Devices of the differential copy Xd for the saturation margin |Vds| - |Vdsat|
MIRROR_DEVS = {'m10': 'xm10', 'm11': 'xm11', 'm6': 'xm6', 'm9': 'xm9'}
CORE_DEVS = {'m0': ('xm0', 'nfet_01v8'), 'm2': ('xm2', 'nfet_01v8'),
             'mp1a': ('xmp1a', 'pfet_01v8'), 'mp1b': ('xmp1b', 'pfet_01v8'),
             'm1': ('xm1', 'pfet_01v8_lvt'), 'm3': ('xm3', 'pfet_01v8_lvt'),
             'mp1c': ('xmp1c', 'pfet_01v8'), 'm20': ('xm20', 'pfet_01v8')}
STEP = 0.4                               # V, differential output step of the tran bench
SETTLE_TOL = 0.01

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Netlist
# ============================================================================
def set_node(text: str, dev: str, idx: int, node: str) -> str:
    """Replace terminal idx (0 = drain, 1 = gate, 2 = source, 3 = bulk) of device dev."""
    pat = re.compile(rf'^({dev}\s+)(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', re.MULTILINE | re.IGNORECASE)
    m = pat.search(text)
    nodes = list(m.groups()[1:])
    nodes[idx] = node
    return text[:m.start()] + m.group(1) + ' '.join(nodes) + text[m.end():]


def pi_wire(name: str, a: str, b: str, r: float, c: float) -> str:
    lines = [f'R{name} {a} {b} {max(r, R_ZERO):.6g}']
    if c > 0:
        lines += [f'C{name}a {a} VSS {c / 2:.6g}', f'C{name}b {b} VSS {c / 2:.6g}']
    return '\n'.join(lines)


def make_ota(w: dict) -> str:
    """ota1x, ota1x_cml, ota1x_mm with the wires w: rg/cg gate line, rs VSS line,
    rt/ct tail line, ro/co output lines. Current sense sources Vi* are always in."""
    with open(OTA) as f:
        text = f.read()
    text = re.sub(r'^\.subckt\s+ota1\s', '.subckt ota1x ', text, flags=re.MULTILINE | re.I)
    # gate line: the diode M4 keeps vbias_n, the mirror gates sit on vbf
    for dev in ('XM10', 'XM6', 'XM9'):
        text = set_node(text, dev, 1, 'vbf')
    # optional gate offsets (mismatch.py: worst-case mirror errors referred to the gates)
    ofs = w.get('ofs', {})
    for dev in ofs:
        text = set_node(text, dev, 1, f'g_{dev}')
    # VSS line: sources and bodies of the mirror row on VSSF
    for dev in ('XM10', 'XM11', 'XM6', 'XM9', 'XM13', 'XM12'):
        text = set_node(text, dev, 2, 'VSSF')
        text = set_node(text, dev, 3, 'VSSF')
    # drain lines with current sense
    text = set_node(text, 'XM10', 0, 'd10')
    text = set_node(text, 'XM11', 0, 'd11')
    text = set_node(text, 'XM6', 0, 'd6')
    text = set_node(text, 'XM9', 0, 'd9')
    extra = '\n'.join([
        pi_wire('wg', 'vbias_n', 'vbf', w['rg'], w['cg']),
        f"Rws VSSF VSS {max(w['rs'], R_ZERO):.6g}",
        'Vi10 dt d10 0', 'Vi11 dt d11 0',
        pi_wire('wt', 'dt', 'tail', w['rt'], w['ct']),
        'Vi6 d6a d6 0', pi_wire('wo6', 'd6a', 'OUTP', w['ro'], w['co']),
        'Vi9 d9a d9 0', pi_wire('wo9', 'd9a', 'OUTM', w['ro'], w['co']),
    ] + [f'V{dev}ofs g_{dev} vbf {v:.6g}' for dev, v in ofs.items()])
    ota = re.sub(r'^\.ends', extra + '\n.ends', text, count=1, flags=re.MULTILINE | re.I)

    cml = re.sub(r'^(\.subckt\s+)ota1x(\s.*)$', r'\1ota1x_cml\2 CMG CMS', ota, count=1,
                 flags=re.MULTILINE | re.I)
    cml = set_node(cml, 'XM11', 1, 'CMG')
    cml = re.sub(r'^\.ends', 'Vcms vcmfb CMS 0\n.ends', cml, count=1, flags=re.MULTILINE | re.I)

    mm = re.sub(r'^\.subckt\s+ota1x\s', '.subckt ota1x_mm ', ota, count=1, flags=re.MULTILINE | re.I)
    mm = set_node(mm, 'XMP1a', 1, 'g_mm')
    mm = re.sub(r'^\.ends', f'Vmm g_mm VBIAS_P {MM_SHIFT:.6g}\n.ends', mm, count=1,
                flags=re.MULTILINE | re.I)
    return '\n'.join([ota, cml, mm])


def dev_path(copy: str, inst: str, model: str) -> str:
    return f'@m.{copy}.{inst}.msky130_fd_pr__{model}'


def sat_saves() -> list:
    devs = [(k, i, 'nfet_01v8_lvt') for k, i in MIRROR_DEVS.items()]
    devs += [(k, i, mdl) for k, (i, mdl) in CORE_DEVS.items()]
    return [(k, dev_path('xd', i, mdl)) for k, i, mdl in devs]


AC_TB = """
Vref vref 0 {vref}
Vcm  cm   0 {vcmi}
Xd   inm  inp  outm outp vbp  vddd vref 0 ota1x
Efp  fbp  cm   outm outp 0.5
Efm  fbm  cm   outp outm 0.5
Lfp  fbp  inp  10T
Lfm  fbm  inm  10T
Cip  inp  sp   100G
Cim  inm  sm   100G
Vsp  sp   0    dc 0 ac 1
Esm  sm   0    sp 0 -1
Vddd vddd 0    {vdd}
Ibd  vbp  0    {ib}
Clp  outp 0    {cl}
Clm  outm 0    {cl}
Xc    inmc inpc outmc outpc vbpc vddc vref 0 ota1x
Efpc  fbpc cm   outmc outpc 0.5
Efmc  fbmc cm   outpc outmc 0.5
Lfpc  fbpc inpc 10T
Lfmc  fbmc inmc 10T
Cipc  inpc scm  100G
Cimc  inmc scm  100G
Vscm  scm  0    dc 0 ac 1
Vddc  vddc 0    {vdd}
Ibc   vbpc 0    {ib}
Clpc  outpc 0   {cl}
Clmc  outmc 0   {cl}
Xl    inml inpl outml outpl vbpl vddl vref 0 cmgl cmsl ota1x_cml
Efpl  fbpl cm   outml outpl 0.5
Efml  fbml cm   outpl outml 0.5
Lfpl  fbpl inpl 10T
Lfml  fbml inml 10T
Cipl  inpl 0    100G
Ciml  inml 0    100G
Lb    cmsl cmgl 10T
Cb    cmgl sinj 100G
Vinj  sinj 0    dc 0 ac 1
Vddl  vddl 0    {vdd}
Ibl   vbpl 0    {ib}
Clpl  outpl 0   {cl}
Clml  outml 0   {cl}
Xm    inmm inpm outmm outpm vbpm vddm vref 0 ota1x_mm
Efpm  fbpm cm   outmm outpm 0.5
Efmm  fbmm cm   outpm outmm 0.5
Lfpm  fbpm inpm 10T
Lfmm  fbmm inmm 10T
Cipm  inpm scmm 100G
Cimm  inmm scmm 100G
Vscmm scmm 0    dc 0 ac 1
Vddm  vddm 0    {vdd}
Ibm   vbpm 0    {ib}
Clpm  outpm 0   {cl}
Clmm  outmm 0   {cl}
"""

TRAN_TB = """
Xt   inm inp outm outp vbpt vddt vreft 0 ota1x
Vddt vddt  0 {vdd}
Vreft vreft 0 {vref}
Vcmt cmt   0 {vcmi}
Ibt  vbpt  0 {ib}
Vip  vip   0 pulse({lo} {hi} 0.1u 1n 1n 1u 2u)
Vim  vim   0 pulse({hi} {lo} 0.1u 1n 1n 1u 2u)
Cip  vip   inm {cfb}
Cim  vim   inp {cfb}
Cfp  outp  inm {cfb}
Cfm  outm  inp {cfb}
Rbp  inm   cmt 1G
Rbm  inp   cmt 1G
Clp  outp  0 {cl}
Clm  outm  0 {cl}
"""


def ac_control() -> str:
    sats = sat_saves()
    saves = ' '.join(f'{p}[vds] {p}[vdsat]' for _, p in sats)
    sat_lets = '\n'.join(f'let sat_{k} = abs({p}[vds]) - abs({p}[vdsat])' for k, p in sats)
    sat_prints = ' '.join(f'sat_{k}' for k, _ in sats)
    return f"""
.control
save all {saves}
op
let power = -i(vddd)*{VDD}
let vocm = (v(outp)+v(outm))/2 - {VREF}
let offset = v(inp) - v(inm)
let i10 = abs(i(v.xd.vi10))
let i11 = abs(i(v.xd.vi11))
let i6 = abs(i(v.xd.vi6))
let i9 = abs(i(v.xd.vi9))
let v_vbias = v(xd.vbias_n)
let vgs_far = v(xd.vbf) - v(xd.vssf)
let v_vssf = v(xd.vssf)
let v_tail = v(xd.tail)
let vds10 = v(xd.d10) - v(xd.vssf)
let vds6 = v(xd.d6) - v(xd.vssf)
let vds9 = v(xd.d9) - v(xd.vssf)
{sat_lets}
print power vocm offset i10 i11 i6 i9 v_vbias vgs_far v_vssf v_tail vds10 vds6 vds9 {sat_prints}
ac dec 20 1 10G
let tf = (v(outp)-v(outm))/(v(inp)-v(inm))
let tfdb = db(tf)
let tfph = cph(tf)*180/pi
meas ac ugbw when tfdb=0
meas ac phu find tfph when tfdb=0
let gain = tfdb[0]
let pm = 180 + phu
* a perfectly symmetric copy has CM->DM gain exactly 0; db(0) aborts the whole print line
let cmrr = gain - db(abs((v(outpc)-v(outmc))/v(scm))[0] + 1e-30)
let cmrr_mm = gain - db(abs((v(outpm)-v(outmm))/v(scmm))[0] + 1e-30)
let tl = -v(cmsl)/v(cmgl)
let tldb = db(tl)
let tlph = cph(tl)*180/pi
meas ac cm_ugb when tldb=0
meas ac cmph find tlph when tldb=0
let cm_pm = 180 + cmph
let cm_gain = tldb[0]
* one print per measure: a failed meas (no 0 dB crossing) must not drop the others
print gain
print ugbw
print pm
print cm_gain
print cm_ugb
print cm_pm
print cmrr
print cmrr_mm
noise v(outp,outm) vsp dec 10 1 100Meg
setplot noise1
* meas does not work on noise plots; dec 10 from 1 Hz puts 1 kHz at index 30, 1 MHz at 60
let f_1k = frequency[30]
let f_1m = frequency[60]
let noise_1k = 2*inoise_spectrum[30]
let noise_1m = 2*inoise_spectrum[60]
print f_1k f_1m noise_1k noise_1m
.endc
"""


def tran_control(wr: str) -> str:
    return f"""
.control
tran 0.1n 2.1u
wrdata {wr} v(outp)-v(outm)
.endc
"""


def header(lib: str, temp: float, ota: str) -> str:
    return f'* cm separation\n.include "{MODELS.format(lib=lib)}"\n{ota}\n.temp {temp}\n'


def run_ngspice(netlist: str, workdir: str, name: str) -> str:
    path = os.path.join(workdir, name)
    with open(path, 'w') as f:
        f.write(netlist + '\n.end\n')
    res = subprocess.run(['ngspice', '-b', '-D', 'ngbehavior=hsa', '-D', 'ng_nomodcheck', path],
                         capture_output=True, text=True, cwd=workdir)
    return res.stdout + res.stderr


def parse_prints(log: str) -> dict:
    out = {}
    for m in re.finditer(r'^\s*([a-z_0-9]+)\s+=\s+([-+0-9.eE]+)\s*$', log, re.MULTILINE):
        out[m.group(1)] = float(m.group(2))
    return out


def tran_measures(path: str) -> dict:
    data = np.loadtxt(path)
    t, v = data[:, 0], data[:, 1]
    res = {}
    for key, t1, t2 in (('sr_dn', 0.1e-6, 1.1e-6), ('sr_up', 1.1e-6, 2.1e-6)):
        sel = (t >= t1) & (t < t2)
        res[key] = float(np.max(np.abs(np.diff(v[sel]) / np.diff(t[sel]))))
    sel = (t >= 0.1e-6) & (t < 1.1e-6)
    ts, vs = t[sel], v[sel]
    bad = np.nonzero(np.abs(vs - vs[-1]) > SETTLE_TOL * STEP)[0]
    res['tset'] = float(ts[bad[-1]] - 0.1e-6) if len(bad) else 0.0
    return res


def simulate(point: dict) -> dict:
    lib, temp = point['corner']
    params = dict(vdd=VDD, vref=VREF, vcmi=VCMI, cl=CL, cfb=CFB, ib=IB,
                  lo=VCMI - STEP / 4, hi=VCMI + STEP / 4)
    ota = make_ota(point['w'])
    with tempfile.TemporaryDirectory() as wd:
        log = run_ngspice(header(lib, temp, ota) + AC_TB.format(**params) + ac_control(), wd, 'ac.sp')
        res = parse_prints(log)
        wr = os.path.join(wd, 'tran.dat')
        tlog = run_ngspice(header(lib, temp, ota) + TRAN_TB.format(**params) + tran_control(wr),
                           wd, 'tran.sp')
        if os.path.isfile(wr):
            res.update(tran_measures(wr))
        else:
            logger.warning("simulate: no transient result for %s\n%s", point['tag'], tlog[-2000:])
    if 'gain' not in res:
        logger.warning("simulate: incomplete AC result for %s\n%s", point['tag'], log[-3000:])
    res['vsat'] = min(v for k, v in res.items() if k.startswith('sat_'))
    return {**{k: v for k, v in point.items() if k != 'w'}, 'wires': point['w'], **res}


# ============================================================================
# Cases
# ============================================================================
def wires(rg=0.0, cg=0.0, rs=0.0, rt=0.0, ct=0.0, ro=0.0, co=0.0) -> dict:
    return dict(rg=rg, cg=cg, rs=rs, rt=rt, ct=ct, ro=ro, co=co)


def case_wires(case: str, layer: str, la: float, lb: float = None) -> dict:
    r, c = WIRES[layer]['r'], WIRES[layer]['c']
    if case == 'c1a':
        return wires(rg=r * la, cg=c * la)
    if case == 'c1b':
        return wires(rg=r * la, cg=c * la, rs=r * la)
    if case == 'c2':
        return wires(rt=r * la, ct=c * la, ro=r * la, co=c * la)
    if case == 'c3':
        return wires(rt=r * la, ct=c * la, ro=r * lb, co=c * lb)
    raise KeyError(f"case_wires: unknown case {case}")


def points(case: str) -> list:
    pts = []
    if case in ('c1a', 'c1b', 'c2'):
        pts = [dict(case=case, layer=ly, length=L, corner=NOMINAL, w=case_wires(case, ly, L))
               for ly in WIRES for L in LENGTHS]
    elif case == 'c3':
        pts = [dict(case=case, layer=ly, l_tail=lt, l_out=lo, corner=NOMINAL,
                    w=case_wires(case, ly, lt, lo))
               for ly in WIRES for lt in GRID for lo in GRID]
    elif case == 'base':
        pts = [dict(case=case, corner=NOMINAL, w=wires())]
    elif case == 'corners':
        cfgs = [('base', wires())] + [(c, case_wires(c, 'met1', CORNER_LEN, CORNER_LEN))
                                      for c in ('c1a', 'c1b', 'c2')]
        cfgs.append(('c3_t1_o100', case_wires('c3', 'met1', 1, CORNER_LEN)))
        pts = [dict(case=case, config=name, corner=(lib, t), w=w)
               for name, w in cfgs for lib in CORNER_LIBS for t in CORNER_TEMPS]
    else:
        raise KeyError(f"points: unknown case {case}")
    for i, p in enumerate(pts):
        p['tag'] = f'{case}#{i}'
    return pts


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    cases = sys.argv[1:] or ['base', 'c1a', 'c1b', 'c2', 'c3', 'corners']
    os.makedirs(OUT_DIR, exist_ok=True)
    with Pool(WORKERS) as pool:
        for case in cases:
            pts = points(case)
            logger.info("%s: %d points", case, len(pts))
            res = pool.map(simulate, pts)
            with open(os.path.join(OUT_DIR, f'{case}.json'), 'w') as f:
                json.dump(res, f, indent=1)
            logger.info("%s: done -> results/%s.json", case, case)


if __name__ == '__main__':
    main_standalone()
