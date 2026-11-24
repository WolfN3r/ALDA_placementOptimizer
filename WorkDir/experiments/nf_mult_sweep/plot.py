"""Plots of the nf/M sweep (sweep.py): device operating point and circuit metrics of
each swept pair over the finger width W_tot/(nf*M), one colour per nf.

    python3 plot.py [results_dir]
Output: <results_dir>/fig_device.png, <results_dir>/fig_circuit.png
"""
# ============================================================================
# Imports
# ============================================================================
import csv
import logging
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
PROBE = {'pair': 'xm0', 'load': 'xmp1b', 'sink': 'xm9'}
TITLE = {'pair': 'input pair M0/M2 (W_tot 131.3 um)', 'load': 'load mirror MP1a/b (W_tot 53.6 um)',
         'sink': 'sink mirror M6/M9 (W_tot 111.4 um)'}
REF_WF = {'pair': 8.205, 'load': 6.7, 'sink': 3.48}     # sized design (baseline)
DEVICE_COLS = [('Id (uA)', lambda r, p: r[p + '_id'] * 1e6),
               ('gm/Id (1/V)', lambda r, p: r[p + '_gm'] / r[p + '_id']),
               ('gm/gds', lambda r, p: r[p + '_gm'] / r[p + '_gds']),
               ('Vth (mV)', lambda r, p: abs(r[p + '_vth']) * 1e3),
               ('Cdb junction (fF)', lambda r, p: r[p + '_capbd'] * 1e15),
               ('Csb junction (fF)', lambda r, p: r[p + '_capbs'] * 1e15)]
CIRCUIT_COLS = [('DC gain (dB)', 'gain_db', 1), ('UGBW (MHz)', 'ugbw_mhz', 1), ('PM (deg)', 'pm_deg', 1),
                ('Power (mW)', 'power', 1e3), ('Output CM error (mV)', 'vocm', 1e3),
                ('Noise @1 kHz (nV/rtHz)', 'noise_1k_nv', 1)]
GAIN_VALID = 0.0                # dB; below: the OTA has lost its operating point
NF_COLORS = {1: 'tab:red', 2: 'tab:orange', 4: 'tab:green', 8: 'tab:blue', 16: 'tab:purple',
             32: 'tab:brown'}

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# Plots
# ============================================================================
def load(path: str) -> list:
    rows = []
    for r in csv.DictReader(open(path)):
        rows.append({k: (v if k == 'target' else float(v) if v not in ('', 'nan') else float('nan'))
                     for k, v in r.items()})
    return rows


def grid(rows: list, cols: list, value, out: str, title: str):
    fig, axes = plt.subplots(len(PROBE), len(cols), figsize=(4 * len(cols), 3.2 * len(PROBE)))
    base = next(r for r in rows if r['target'] == 'baseline')
    for i, target in enumerate(PROBE):
        sel = [r for r in rows if r['target'] == target]
        for j, col in enumerate(cols):
            ax = axes[i][j]
            for nf, color in NF_COLORS.items():
                pts = sorted((r['W_finger'], value(r, target, col)) for r in sel
                             if r['nf'] == nf and r['gain_db'] > GAIN_VALID)
                if pts:
                    ax.plot(*zip(*pts), 'o-', color=color, ms=4, lw=1, label=f'nf={nf}', alpha=0.8)
            if value(base, target, col) == value(base, target, col):
                ax.axhline(value(base, target, col), color='grey', ls=':', lw=1)
            ax.axvline(REF_WF[target], color='grey', ls='--', lw=1)
            ax.set_xscale('log')
            ax.xaxis.set_minor_formatter(NullFormatter())
            ax.yaxis.get_major_formatter().set_useOffset(False)
            ax.set_title(col[0] if i == 0 else '', fontsize=10)
            if j == 0:
                ax.set_ylabel(TITLE[target], fontsize=9)
            if i == len(PROBE) - 1:
                ax.set_xlabel('finger width W_tot/(nf*M) (um)')
            ax.grid(alpha=0.3)
    axes[0][0].legend(fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    logger.info("wrote %s", out)


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    res = sys.argv[1] if len(sys.argv) > 1 else 'results'
    rows = load(os.path.join(res, 'sweep.csv'))
    grid(rows, DEVICE_COLS, lambda r, t, c: c[1](r, PROBE.get(t, 'xm0')) if r['target'] != 'baseline'
         else float('nan'), os.path.join(res, 'fig_device.png'),
         'Operating point of the swept device (one half), tt 27 C; dashed: sized design')
    grid(rows, CIRCUIT_COLS, lambda r, t, c: r[c[1]] * c[2], os.path.join(res, 'fig_circuit.png'),
         'OTA1 metrics vs split of the swept pair, tt 27 C; dashed: sized design, dotted: its value')


if __name__ == '__main__':
    main_standalone()
