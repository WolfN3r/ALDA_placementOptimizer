"""Mismatch, process gradient and a heat source on the NMOS mirror of OTA1 (sky01) when the
bias diode M4 sits 1-100 um away from the mirror row (case c1a: gate line only).

Step 1, mirror alone (bench): IB -> M5 (diode) -> M7 -> M4 (diode) -> gate line -> M10, M6, M9,
the drains held at their nominal OTA operating point (results/base.json). Measured: input
current I(M7), diode voltage, the mirror outputs I(M10), I(M6), I(M9), against the expected
values (ideal copy ratios times IB) and the nominal simulation.
  random    sky130 mismatch models (_mm sections), one ngspice seed per sample
  gradient  linear Vth gradient G (uV/um) over the distance d: the diode's Vth shifted by G*d
  thermal   diode (with the bias block M5/M7) at T + dT, mirror at T. ngspice ignores dtemp
            on the sky130 device wrappers, so the bias block is solved at T + dT first and
            its gate voltage drives the mirror at T (exact at DC: the gates draw no current)
  heat      a heat source of HEAT_P in a HEAT_A x HEAT_A block, HEAT_S from the near
            element; dT(r) = P / (2 pi k r) (point source on a silicon half-space).
            H1: mirror next to the source, diode d further away (diode cooler);
            H2: diode next to the source, mirror d further away (diode hotter)
  combined  heat (worse of H1/H2) + gradient G_MAX, same direction
Step 2, whole OTA: the worst mirror errors (mean +/- 3 sigma, random only and random + the
combined case at 100 um) are referred to the gates of M10/M6/M9 (dV = ln(I/I0) / (gm/Id)) and injected into the full
OTA (sweep.py, gate offsets), at tt 27 degC and at the tightest corner fs -20 degC.

Runs inside the IIC-OSIC-TOOLS container (/foss/designs/11_cm_separation):
    python3 mismatch.py      # -> results/mm_*.json
"""
# ============================================================================
# Imports
# ============================================================================
import json
import logging
import math
import os
import re
import tempfile
from multiprocessing import Pool

import numpy as np

import sweep

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'results')
SAMPLES = 200                   # Monte Carlo samples, tt_mm
CORNER_SAMPLES = 100            # Monte Carlo samples per _mm section (corner overview)
T_NOM = 27.0
MM_SECTIONS = ('tt_mm', 'ss_mm', 'ff_mm', 'sf_mm', 'fs_mm')

# expected copy ratios (unit = IB/2): M5, M7, M4 = 2; M10 = 4; M6, M9 = 32
RATIO = {'i7': 1.0, 'i10': 2.0, 'i6': 16.0, 'i9': 16.0}
DEVS = ('XM5', 'XM7', 'XM4', 'XM10', 'XM6', 'XM9')      # fixed order: same random draws

THERMAL_DT = [-5, -2, -1, -0.5, -0.2, -0.1, 0.1, 0.2, 0.5, 1, 2, 5]   # K, diode - mirror
GRADIENTS = [0.5, 1, 2, 5]      # uV/um of Vth (literature range; sky130 gives no value)
G_MAX = 5.0
HEAT_P = 20e-3                  # W, e.g. a small output buffer / LDO pass device
HEAT_A = 50.0                   # um, side of the heat-source block
HEAT_S = 10.0                   # um, gap from the block edge to the near element
K_SI = 148.0                    # W/(m K), silicon at 300 K
SIGMA_K = 3.0                   # worst case = mean +/- 3 sigma
INJECT_CORNERS = [('tt', 27), ('fs', -20)]

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Scenarios
# ============================================================================
def heat_rise(r_um: float) -> float:
    return HEAT_P / (2 * math.pi * K_SI * r_um * 1e-6)


def heat_dt(d: float) -> float:
    """dT diode - mirror for H2 (diode near the source); H1 is the negative."""
    r_near = HEAT_A / 2 + HEAT_S
    return heat_rise(r_near) - heat_rise(r_near + d)


def scenarios() -> list:
    sc = [dict(kind='base', dT=0.0, shift=0.0)]
    sc += [dict(kind='thermal', dT=float(t), shift=0.0) for t in THERMAL_DT]
    for d in sweep.LENGTHS:
        sc.append(dict(kind='heat_H1', d=d, dT=-heat_dt(d), shift=0.0))
        sc.append(dict(kind='heat_H2', d=d, dT=heat_dt(d), shift=0.0))
        for g in GRADIENTS:
            sc.append(dict(kind='grad', g=g, d=d, dT=0.0, shift=g * d * 1e-6))
        sc.append(dict(kind='grad', g=-G_MAX, d=d, dT=0.0, shift=-G_MAX * d * 1e-6))
        # diode hotter (H2) lowers its Vgs, a higher diode Vth raises it: pair them so that
        # both lower the mirror gate voltage, and the reverse
        sc.append(dict(kind='comb_lo', d=d, dT=heat_dt(d), shift=-G_MAX * d * 1e-6))
        sc.append(dict(kind='comb_hi', d=d, dT=-heat_dt(d), shift=G_MAX * d * 1e-6))
    return sc


# ============================================================================
# Mirror bench
# ============================================================================
def device_lines() -> dict:
    with open(sweep.OTA) as f:
        text = f.read()
    lines = {}
    for dev in DEVS:
        # the device line plus its '+' continuation lines
        m = re.search(rf'^{dev}\s.*?(?=^[^+])', text, re.MULTILINE | re.DOTALL)
        lines[dev] = m.group(0).rstrip('\n')
    return lines


def bench(lib: str, seed: int, temp: float, sc: list, op: dict) -> str:
    dl = device_lines()
    body = '\n'.join(dl[d] for d in DEVS)
    for dev, nodes in (('XM5', 'vbp vbp vdd vdd'), ('XM7', 'd7 vbp vdd vdd'), ('XM4', 'd4 d4 0 0'),
                       ('XM10', 'dt vg 0 0'), ('XM6', 'd6 vg 0 0'), ('XM9', 'd9 vg 0 0')):
        body = re.sub(rf'^({dev}\s+)\S+\s+\S+\s+\S+\s+\S+', rf'\g<1>{nodes}', body, flags=re.MULTILINE)
    net = [f'* mirror bench', f'.include "{sweep.MODELS.format(lib=lib)}"', f'.option seed={seed}',
           f'.temp {temp}', f'Vdd vdd 0 {sweep.VDD}', f'Ib vbp 0 {sweep.IB}', 'Vi7 d7 d4 0',
           'Vg vg 0 0.65', f"Vdt dt 0 {op['vds10']}", f"Vd6 d6 0 {op['vds6']}",
           f"Vd9 d9 0 {op['vds9']}", body, '.control']
    for i, s in enumerate(sc):
        net += [f"option temp={temp + s['dT']:.6g}", 'op', f"let vx = v(d4) + {s['shift']:.6g}",
                # print before the next op: its vectors live in this op's plot only
                'let i7 = abs(i(vi7))', f'echo "A {i} $&vx $&i7"',
                f'option temp={temp:.6g}', 'alter vg dc = $&vx', 'op',
                'let i10 = abs(i(vdt))', 'let i6 = abs(i(vd6))', 'let i9 = abs(i(vd9))',
                f'echo "R {i} $&i10 $&i6 $&i9"']
        if i == 0:
            p = '@m.xm6.msky130_fd_pr__nfet_01v8_lvt'
            q = '@m.xm10.msky130_fd_pr__nfet_01v8_lvt'
            net += [f'let gmid6 = {p}[gm] / abs({p}[id])', f'let gmid10 = {q}[gm] / abs({q}[id])',
                    'echo "G $&gmid6 $&gmid10"']
    net += ['.endc']
    return '\n'.join(net)      # run_ngspice appends .end


def run_bench(job: tuple) -> dict:
    lib, seed, temp, sc, op = job
    with tempfile.TemporaryDirectory() as wd:
        log = sweep.run_ngspice(bench(lib, seed, temp, sc, op), wd, 'mm.sp')
    rows = {}
    for m in re.finditer(r'^A (\d+) (\S+) (\S+)\s*$', log, re.MULTILINE):
        rows[int(m.group(1))] = dict(vg=float(m.group(2)), i7=float(m.group(3)))
    for m in re.finditer(r'^R (\d+) (\S+) (\S+) (\S+)\s*$', log, re.MULTILINE):
        rows.setdefault(int(m.group(1)), {}).update(zip(('i10', 'i6', 'i9'), map(float, m.groups()[1:])))
    rows = {i: r for i, r in rows.items() if len(r) == 5}
    g = re.search(r'^G (\S+) (\S+)\s*$', log, re.MULTILINE)
    if len(rows) != len(sc) or not g:
        logger.warning("run_bench: %s seed %d: %d/%d scenarios\n%s", lib, seed, len(rows), len(sc),
                       log[-2000:])
    return dict(lib=lib, seed=seed, temp=temp, gmid6=float(g.group(1)) if g else None,
                gmid10=float(g.group(2)) if g else None, rows=[rows.get(i) for i in range(len(sc))])


# ============================================================================
# Worst case -> whole OTA
# ============================================================================
def worst_offsets(mc: list, sc: list, nominal: dict) -> dict:
    """Gate offsets of M10/M6/M9 for mean +/- 3 sigma: random only (diode next to the mirror)
    and random + the combined heat/gradient case at 100 um.
    up/down: every output high/low (shared diode error, correlated); split: the M6/M9
    difference at +/- 3 sigma (individual mismatch), tail at nominal."""
    idx = {k: next(i for i, s in enumerate(sc) if s['kind'] == k and s.get('d') == sweep.LENGTHS[-1])
           for k in ('comb_lo', 'comb_hi')}
    idx['base'] = 0
    gmid = {'XM10': nominal['gmid10'], 'XM6': nominal['gmid6'], 'XM9': nominal['gmid6']}
    nom = nominal['rows'][0]
    out = {}
    for name, key, sign in (('up_rand', 'base', 1), ('down_rand', 'base', -1),
                            ('up_100um', 'comb_hi', 1), ('down_100um', 'comb_lo', -1)):
        ofs, target = {}, {}
        for dev, i in (('XM10', 'i10'), ('XM6', 'i6'), ('XM9', 'i9')):
            vals = np.array([r['rows'][idx[key]][i] for r in mc if r['rows'][idx[key]]])
            t = vals.mean() + sign * SIGMA_K * vals.std()
            target[i] = t
            ofs[dev] = math.log(t / nom[i]) / gmid[dev]
        out[name] = dict(ofs=ofs, target=target)
    diff = np.array([(r['rows'][0]['i6'] - r['rows'][0]['i9']) / 2 for r in mc if r['rows'][0]])
    half = SIGMA_K * diff.std()
    t6, t9 = nom['i6'] + half, nom['i9'] - half
    out['split'] = dict(ofs={'XM6': math.log(t6 / nom['i6']) / gmid['XM6'],
                             'XM9': math.log(t9 / nom['i9']) / gmid['XM9']},
                        target={'i10': nom['i10'], 'i6': t6, 'i9': t9})
    return out


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    with open(os.path.join(OUT_DIR, 'base.json')) as f:
        op = json.load(f)[0]
    sc = scenarios()
    with Pool(sweep.WORKERS) as pool:
        logger.info("bench: %d scenarios per run", len(sc))
        nom_tt = run_bench(('tt', 1, T_NOM, sc, op))
        mc = pool.map(run_bench, [('tt_mm', s, T_NOM, sc, op) for s in range(1, SAMPLES + 1)])
        logger.info("tt_mm: %d samples done", len(mc))
        corners_nom = pool.map(run_bench, [(lib, 1, t, sc, op) for lib in sweep.CORNER_LIBS
                                           for t in sweep.CORNER_TEMPS])
        corners_mc = pool.map(run_bench, [(sec, s, T_NOM, sc[:1], op) for sec in MM_SECTIONS
                                          for s in range(1, CORNER_SAMPLES + 1)])
        logger.info("corners done")
        worst = worst_offsets(mc, sc, nom_tt)
        pts = []
        for lib, t in INJECT_CORNERS:
            pts.append(dict(case='inject', config='nominal', corner=(lib, t), w=sweep.wires()))
            for name, wc in worst.items():
                pts.append(dict(case='inject', config=name, corner=(lib, t),
                                w={**sweep.wires(), 'ofs': wc['ofs']}))
        for i, p in enumerate(pts):
            p['tag'] = f'inject#{i}'
        inject = pool.map(sweep.simulate, pts)
    expected = {k: v * sweep.IB for k, v in RATIO.items()}
    res = dict(scenarios=sc, expected=expected, heat=dict(P=HEAT_P, a=HEAT_A, s=HEAT_S, k=K_SI),
               nominal=nom_tt, mc=mc, corners_nom=corners_nom, corners_mc=corners_mc, worst=worst,
               inject=inject)
    with open(os.path.join(OUT_DIR, 'mm_results.json'), 'w') as f:
        json.dump(res, f, indent=1)
    logger.info("wrote results/mm_results.json")


if __name__ == '__main__':
    main_standalone()
