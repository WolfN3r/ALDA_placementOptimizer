"""Finger / multiplier sweep of sky01 (OTA1, sky130) at constant total width.

For one matched device pair at a time (input pair M0/M2, 1st-stage loads MP1a/b,
2nd-stage sinks M6/M9) the split of the total width W_tot = W_copy * M into
nf fingers per copy and M copies is varied; everything else stays at the sized
design (06_ota1_magical/ota1_sized.spice, tt, 27 degC). Every split is one ngspice
run (op + ac + noise) of two OTA copies: Xd (differential drive, open loop for AC)
and Xl (CMFB loop opened at the gate of M11), as in 06_ota1_magical/tb.inc.
Drain/source areas and perimeters follow nf like the xschem export (shared
diffusions), sa/sb/sd = 0 (no LOD stress), as in the sized netlist.

Runs inside the IIC-OSIC-TOOLS container (needs /foss/pdks and the trimmed models
of /foss/designs/06_ota1_magical/models, read only):
    python3 sweep.py [workdir]
Output in <workdir> (default ./results): sweep.csv (one row per run: split,
device operating point, circuit metrics), mc.csv (offset Monte Carlo of the pair),
netlists/ and raw ngspice output in runs/.
"""
# ============================================================================
# Imports
# ============================================================================
import csv
import logging
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
MODELS = '/foss/designs/06_ota1_magical/models'
PDK_SPICE = '/foss/pdks/sky130A/libs.ref/sky130_fd_pr/spice'
NGSPICE = ['ngspice', '-b', '-D', 'ngbehavior=hsa', '-D', 'ng_nomodcheck']
WORKERS = 12
DIFF_EXT = 0.29                 # um, drain/source extension used by the xschem export
W_FINGER_MIN = 0.42             # um, layout limit of 06_ota1_magical/definitions.py
W_FINGER_MAX = 100.0            # um, largest sky130 model bin (wmax = 100 um)
MC_SAMPLES = 120
MC_PAIR_SPLITS = [(32, 1), (4, 4), (1, 32)]     # (nf, M) of the input pair for the MC

# testbench values (06_ota1_magical/definitions.py and result_rounded.json)
TB = {'vdd': 1.8, 'vref': 0.9, 'vcmi': 0.9, 'cl': 1e-12, 'IB': 1.8506543563885517e-05}

# Sized design (06_ota1_magical/ota1_sized.spice): name -> d g s b model L W_copy nf M
DEVICES = {
    'XMP1b': ('intp VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 4),
    'XM0':   ('intp INM tail VSS', 'nfet_01v8', 0.6, 32.82, 4, 4),
    'XM1':   ('OUTM intp VDD VDD', 'pfet_01v8_lvt', 0.54, 29.94, 4, 2),
    'XM9':   ('OUTM vbias_n VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 32),
    'XMP1a': ('intm VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 4),
    'XM2':   ('intm INP tail VSS', 'nfet_01v8', 0.6, 32.82, 4, 4),
    'XM3':   ('OUTP intm VDD VDD', 'pfet_01v8_lvt', 0.54, 29.94, 4, 2),
    'XM6':   ('OUTP vbias_n VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 32),
    'XM10':  ('tail vbias_n VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 4),
    'XM11':  ('tail vcmfb VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 4),
    'XM5':   ('VBIAS_P VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 2),
    'XM7':   ('vbias_n VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 2),
    'XM4':   ('vbias_n vbias_n VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 2),
    'XM15':  ('vcmfb OUTP net020 VDD', 'pfet_01v8_lvt', 0.35, 13.99, 2, 2),
    'XM17':  ('net025 VREF net020 VDD', 'pfet_01v8_lvt', 0.35, 13.99, 2, 2),
    'XM19':  ('net025 VREF net028 VDD', 'pfet_01v8_lvt', 0.35, 13.99, 2, 2),
    'XM18':  ('vcmfb OUTM net028 VDD', 'pfet_01v8_lvt', 0.35, 13.99, 2, 2),
    'XMP1c': ('net020 VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 2),
    'XM20':  ('net028 VBIAS_P VDD VDD', 'pfet_01v8', 4.535, 13.4, 2, 2),
    'XM13':  ('vcmfb vcmfb VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 2),
    'XM12':  ('net025 net025 VSS VSS', 'nfet_01v8_lvt', 1.93, 3.48, 1, 2),
}
PASSIVES = """XR25 net037 intp VSS sky130_fd_pr__res_high_po_0p69 L=2.37 mult=1 m=1
XC1 net037 OUTM sky130_fd_pr__cap_mim_m3_1 W=19.095 L=19.095 MF=1 m=1
XR23 net047 intm VSS sky130_fd_pr__res_high_po_0p69 L=2.37 mult=1 m=1
XC0 net047 OUTP sky130_fd_pr__cap_mim_m3_1 W=19.095 L=19.095 MF=1 m=1
"""
# swept pairs: label -> (devices, nf values, M values)
TARGETS = {
    'pair': (('XM0', 'XM2'), (1, 2, 4, 8, 16, 32), (1, 2, 4, 8, 16, 32)),
    'load': (('XMP1a', 'XMP1b'), (1, 2, 4, 8, 16), (1, 2, 4, 8, 16)),
    'sink': (('XM6', 'XM9'), (1, 2, 4, 8, 16), (1, 2, 4, 8, 16, 32)),
}
# device whose operating point is recorded for each target (same half of the OTA)
PROBE = {'pair': 'XM0', 'load': 'XMP1b', 'sink': 'XM9'}
# probes recorded in every run (to see the effect on the neighbours)
ALL_PROBES = ('XM0', 'XMP1b', 'XM1', 'XM9', 'XM10')
OP_PARAMS = ('id', 'gm', 'gds', 'vth', 'vdsat', 'vds', 'cgg', 'cgs', 'cgd', 'cdd', 'capbd', 'capbs')

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# Netlist
# ============================================================================
def mos_line(name: str, nodes: str, model: str, l: float, w: float, nf: int, m: int) -> str:
    """One sky130 MOS instance; w is per copy (all fingers), m copies."""
    wf = w / nf
    ad = int((nf + 1) / 2) * wf * DIFF_EXT
    as_ = int((nf + 2) / 2) * wf * DIFF_EXT
    pd = 2 * int((nf + 1) / 2) * (wf + DIFF_EXT)
    ps = 2 * int((nf + 2) / 2) * (wf + DIFF_EXT)
    return (f"{name} {nodes} sky130_fd_pr__{model} L={l} W={w:.6g} nf={nf} ad={ad:.6g} as={as_:.6g}"
            f" pd={pd:.6g} ps={ps:.6g} nrd={DIFF_EXT / w:.6g} nrs={DIFF_EXT / w:.6g}"
            f" sa=0 sb=0 sd=0 mult={m} m={m}\n")


def ota_subckts(devices: dict) -> str:
    """ota1 and ota1_cml (gate of M11 on CMG, vcmfb on CMS) with the given sizes."""
    out = ''
    for cml in (False, True):
        out += '.subckt ota1_cml INM INP OUTM OUTP VBIAS_P VDD VREF VSS CMG CMS\n' if cml else \
               '.subckt ota1 INM INP OUTM OUTP VBIAS_P VDD VREF VSS\n'
        for name, (nodes, model, l, w, nf, m) in devices.items():
            if cml and name == 'XM11':
                nodes = 'tail CMG VSS VSS'
            out += mos_line(name, nodes, model, l, w, nf, m)
        out += PASSIVES + ('Vcms vcmfb CMS 0\n' if cml else '') + '.ends\n'
    return out


def dev_path(inst: str, name: str) -> str:
    return f"@m.{inst}.{name.lower()}.msky130_fd_pr__{DEVICES[name][1]}"


def testbench(devices: dict, corner: str, control: str) -> str:
    p = TB
    return f"""* OTA1 nf/M sweep
.include "{MODELS}/sky130_{corner}.spice"
{ota_subckts(devices)}
.param vdd={p['vdd']} vref={p['vref']} vcmi={p['vcmi']} cl={p['cl']} IB={p['IB']}
.temp 27
Vref vref 0 {{vref}}
Vcm  cm   0 {{vcmi}}
* Xd: differential drive (DC: output-to-input feedback through 10T inductors)
Xd   inm  inp  outm outp vbp  vddd vref 0 ota1
Efp  fbp  cm   outm outp 0.5
Efm  fbm  cm   outp outm 0.5
Lfp  fbp  inp  10T
Lfm  fbm  inm  10T
Cip  inp  sp   100G
Cim  inm  sm   100G
Vsp  sp   0    dc 0 ac 1
Esm  sm   0    sp 0 -1
Vddd vddd 0    {{vdd}}
Ibd  vbp  0    {{IB}}
Clp  outp 0    {{cl}}
Clm  outm 0    {{cl}}
* Xl: CMFB loop broken at the gate of M11
Xl    inml inpl outml outpl vbpl vddl vref 0 cmgl cmsl ota1_cml
Efpl  fbpl cm   outml outpl 0.5
Efml  fbml cm   outpl outml 0.5
Lfpl  fbpl inpl 10T
Lfml  fbml inml 10T
Cipl  inpl 0    100G
Ciml  inml 0    100G
Lb    cmsl cmgl 10T
Cb    cmgl sinj 100G
Vinj  sinj 0    dc 0 ac 1
Vddl  vddl 0    {{vdd}}
Ibl   vbpl 0    {{IB}}
Clpl  outpl 0   {{cl}}
Clml  outml 0   {{cl}}
{control}
.end
"""


def control_full() -> str:
    lets, names = [], []
    for probe in ALL_PROBES:
        for par in OP_PARAMS:
            vec = f"{probe.lower()}_{par}"
            lets.append(f"let {vec} = {dev_path('xd', probe)}[{par}]")
            names.append(vec)
    lets += ["let power = -i(vddd)*1.8", "let vocm = (v(outp)+v(outm))/2-0.9",
             "let voff = v(inp)-v(inm)", "let v_intp = v(xd.intp)", "let v_tail = v(xd.tail)"]
    names += ['power', 'vocm', 'voff', 'v_intp', 'v_tail']
    return ("\n.control\nset wr_vecnames\nset wr_singlescale\noption numdgt=7\nop\n"
            + "\n".join(lets) + f"\nwrdata op.txt {' '.join(names)}\n"
            "ac dec 40 1 10e9\n"
            "let tdm = (v(outp)-v(outm))/(v(inp)-v(inm))\nlet tcm = -v(cmsl)/v(cmgl)\n"
            "wrdata ac.txt real(tdm) imag(tdm) real(tcm) imag(tcm)\n"
            "noise v(outp,outm) vsp dec 20 1 1e8\nsetplot noise1\n"
            "wrdata noise.txt inoise_spectrum\n.endc\n")


def control_mc() -> str:
    return ("\n.control\nset wr_vecnames\noption numdgt=7\nop\n"
            "let voff = v(inp)-v(inm)\nwrdata op.txt voff\n.endc\n")


# ============================================================================
# Run and evaluate
# ============================================================================
def run_ngspice(run_dir: str, netlist: str) -> bool:
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, 'tb.cir'), 'w') as f:
        f.write(netlist)
    res = subprocess.run(NGSPICE + ['tb.cir'], cwd=run_dir, capture_output=True, text=True)
    with open(os.path.join(run_dir, 'ngspice.log'), 'w') as f:
        f.write(res.stdout + res.stderr)
    return os.path.isfile(os.path.join(run_dir, 'op.txt'))


def read_wrdata(path: str) -> dict:
    with open(path) as f:
        head = f.readline().split()
    data = np.atleast_2d(np.loadtxt(path, skiprows=1))
    return {h: data[:, i] for i, h in enumerate(head)}


def loop_metrics(freq: np.ndarray, t: np.ndarray) -> tuple:
    """DC gain (dB), unity-gain frequency (Hz), phase margin (deg) of a loop gain."""
    mag = 20 * np.log10(np.abs(t))
    phase = np.unwrap(np.angle(t)) * 180 / np.pi
    i = np.where(mag < 0)[0]
    if len(i) == 0 or i[0] == 0:
        return mag[0], float('nan'), float('nan')
    k = i[0]
    x = mag[k - 1] / (mag[k - 1] - mag[k])
    fu = 10 ** (np.log10(freq[k - 1]) + x * (np.log10(freq[k]) - np.log10(freq[k - 1])))
    ph = phase[k - 1] + x * (phase[k] - phase[k - 1])
    return mag[0], fu, 180 + ph - phase[0]      # both loops are non-inverting at DC


def evaluate(run_dir: str) -> dict:
    op = {k: float(v[0]) for k, v in read_wrdata(os.path.join(run_dir, 'op.txt')).items()
          if k != 'vref'}                    # the op plot's scale vector
    ac = read_wrdata(os.path.join(run_dir, 'ac.txt'))
    freq = ac['frequency']
    tdm = ac['real(tdm)'] + 1j * ac['imag(tdm)']
    tcm = ac['real(tcm)'] + 1j * ac['imag(tcm)']
    gain, ugbw, pm = loop_metrics(freq, tdm)
    cm_gain, _, cm_pm = loop_metrics(freq, tcm)
    nz = read_wrdata(os.path.join(run_dir, 'noise.txt'))
    vn = 2 * nz['inoise_spectrum']           # differential input = 2 * v(sp)
    op.update(gain_db=gain, ugbw_mhz=ugbw / 1e6, pm_deg=pm, cmfb_pm_deg=cm_pm,
              noise_1k_nv=float(np.interp(3, np.log10(nz['frequency']), vn)) * 1e9,
              noise_1m_nv=float(np.interp(6, np.log10(nz['frequency']), vn)) * 1e9)
    return op


def model_bins(model: str) -> list:
    """(lmin, lmax, wmin, wmax) in um of every bin of one sky130 MOS model (tt)."""
    with open(os.path.join(PDK_SPICE, f'sky130_fd_pr__{model}__tt.pm3.spice')) as f:
        text = f.read()
    rows = re.findall(r'lmin\s*=\s*(\S+)\s+lmax\s*=\s*(\S+)\s+wmin\s*=\s*(\S+)\s+wmax\s*=\s*(\S+)', text)
    return [tuple(float(x) * 1e6 for x in r) for r in rows]


def bin_index(bins: list, l: float, wf: float) -> int:
    for i, (lmin, lmax, wmin, wmax) in enumerate(bins):
        if lmin <= l < lmax and wmin <= wf < wmax:
            return i
    return -1


def splits() -> list:
    """(target, nf, M) of every run with the finger width inside the limits."""
    out = [('baseline', 0, 0)]
    for target, (names, nfs, ms) in TARGETS.items():
        _, _, _, w, nf0, m0 = DEVICES[names[0]]
        w_tot = w * m0
        out += [(target, nf, m) for nf in nfs for m in ms
                if W_FINGER_MIN <= w_tot / (nf * m) <= W_FINGER_MAX]
    return out


def sized(target: str, nf: int, m: int) -> dict:
    devices = dict(DEVICES)
    if target in TARGETS:
        for name in TARGETS[target][0]:
            nodes, model, l, w, nf0, m0 = devices[name]
            devices[name] = (nodes, model, l, w * m0 / m, nf, m)
    return devices


def run_sweep(out: str) -> list:
    bins = {mdl: model_bins(mdl) for mdl in {d[1] for d in DEVICES.values()}}
    jobs = splits()
    logger.info("sweep: %d runs", len(jobs))

    def one(job):
        target, nf, m = job
        devices = sized(target, nf, m)
        run_dir = os.path.join(out, 'runs', f'{target}_nf{nf}_m{m}')
        ok = run_ngspice(run_dir, testbench(devices, 'tt', control_full()))
        row = {'target': target, 'nf': nf, 'M': m}
        if target in TARGETS:
            _, model, l, w, _, _ = devices[TARGETS[target][0][0]]
            row.update(W_copy=w, W_finger=w / nf, W_total=w * m,
                       bin=bin_index(bins[model], l, w / nf))
        if not ok:
            logger.warning("run %s failed, see %s/ngspice.log", run_dir, run_dir)
            return row
        row.update(evaluate(run_dir))
        return row

    with ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(one, jobs))


def run_mc(out: str) -> list:
    jobs = [(nf, m, k) for nf, m in MC_PAIR_SPLITS for k in range(MC_SAMPLES)]
    logger.info("mc: %d runs", len(jobs))

    def one(job):
        nf, m, k = job
        run_dir = os.path.join(out, 'mc', f'pair_nf{nf}_m{m}', f's{k:03d}')
        control = control_mc().replace('.control\n', f'.control\nsetseed {k + 1}\nreset\n', 1)
        ok = run_ngspice(run_dir, testbench(sized('pair', nf, m), 'tt_mm', control))
        voff = read_wrdata(os.path.join(run_dir, 'op.txt'))['voff'][0] if ok else float('nan')
        return {'nf': nf, 'M': m, 'sample': k, 'voff': voff}

    with ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(one, jobs))


def write_csv(path: str, rows: list):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'results')
    os.makedirs(out, exist_ok=True)
    write_csv(os.path.join(out, 'sweep.csv'), run_sweep(out))
    logger.info("wrote %s", os.path.join(out, 'sweep.csv'))
    if '--no-mc' not in sys.argv:
        write_csv(os.path.join(out, 'mc.csv'), run_mc(out))
        logger.info("wrote %s", os.path.join(out, 'mc.csv'))


if __name__ == '__main__':
    main_standalone()
