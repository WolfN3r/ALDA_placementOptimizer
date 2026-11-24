"""Plots of the mismatch / gradient / heat-source tests (results/mm_results.json, mismatch.py).

Output (plots/):
  mm_currents.png    Monte Carlo (tt_mm 27 degC) of the mirror input and outputs vs expected
  mm_distance.png    systematic shift from heat source and gradient vs distance, against
                     the random spread; current change vs diode temperature over corners
  mm_corners.png     output error vs expected (nominal corners) and random sigma per _mm section
  mm_ota.png         whole OTA with the worst-case mirror errors injected

Runs inside the IIC-OSIC-TOOLS container (/foss/designs/11_cm_separation):
    python3 plot_mismatch.py
"""
# ============================================================================
# Imports
# ============================================================================
import json
import logging
import os

import matplotlib.pyplot as plt
import numpy as np

import plot
from plot import INK, MUTED, GRID, SPEC_COLOR, SURFACE, style

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'plots')
C1, C2, C3, C4 = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'   # categorical slots 1-4
BAND1, BAND3 = '#d6e4f5', '#eef3fa'                            # +/-1 and 3 sigma (slot-1 tints)
CURRENTS = [('i7', 'input I(M7) (diode current)'), ('i10', 'output I(M10) (tail)'),
            ('i6', 'output I(M6) (2nd stage)'), ('i9', 'output I(M9) (2nd stage)')]
DIST_SERIES = [('heat_H2', None, C1, 'o', 'heat source 20 mW, diode hotter (H2)'),
               ('grad', 1, C2, 's', 'gradient 1 uV/um'),
               ('grad', 5, C3, '^', 'gradient 5 uV/um'),
               ('comb_hi', None, C4, 'D', 'heat + 5 uV/um, same direction')]
INJECT_CFGS = [('nominal', 'nominal'), ('up_rand', '+3 sigma, random only'),
               ('up_100um', '+3 sigma, diode 100 um away'), ('down_rand', '-3 sigma, random only'),
               ('down_100um', '-3 sigma, diode 100 um away'), ('split', 'M6/M9 split 3 sigma')]
INJECT_METRICS = [('i6', 'I(M6) [uA]', 1e6, []), ('i11', 'I(M11) CMFB tail [uA]', 1e6, []),
                  ('vsat', 'worst sat. margin [mV]', 1e3, [50]),
                  ('vocm', 'output CM error [mV]', 1e3, [-30, 30]),
                  ('power', 'power [mW]', 1e3, [1.5]), ('ugbw', 'UGB [MHz]', 1e-6, [120]),
                  ('pm', 'phase margin [deg]', 1, [60, 80]), ('offset', 'input offset [uV]', 1e6, [])]
INJECT_CORNERS = [(['tt', 27], C1, 'o', 'tt 27 degC'), (['fs', -20], C2, 's', 'fs -20 degC')]
DPI = 150

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Plots
# ============================================================================
def save(fig, title, path, note=None):
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, ha='left')
    if note:
        fig.text(0.01, 0.005, note, color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.03 if note else 0, 1, 0.95))
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def currents_figure(R, path):
    mc, exp, nom = R['mc'], R['expected'], R['nominal']['rows'][0]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), facecolor=SURFACE)
    for ax, (k, label) in zip(axes, CURRENTS):
        style(ax)
        v = np.array([r['rows'][0][k] for r in mc]) * 1e6
        m, s = v.mean(), v.std()
        ax.axvspan(m - 3 * s, m + 3 * s, color=BAND3, zorder=0)
        ax.hist(v, bins=24, color=C1, edgecolor=SURFACE, linewidth=1, zorder=2)
        ax.axvline(exp[k] * 1e6, color=INK, linestyle='--', linewidth=1.2, zorder=3)
        ax.axvline(nom[k] * 1e6, color=MUTED, linestyle=':', linewidth=1.5, zorder=3)
        ax.set_title(label, color=INK, fontsize=10)
        ax.set_xlabel('current [uA]', color=INK, fontsize=9)
        ax.text(0.02, 0.97, f'mean {m:.2f}\nsigma {s:.3f} ({100 * s / m:.2f} %)\n'
                f'vs expected {100 * (m / (exp[k] * 1e6) - 1):+.2f} %',
                transform=ax.transAxes, va='top', fontsize=8, color=INK, zorder=4,
                bbox=dict(facecolor=SURFACE, edgecolor=GRID, boxstyle='round,pad=0.3'))
    axes[0].set_ylabel('samples', color=INK, fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=C1), plt.Rectangle((0, 0), 1, 1, color=BAND3),
               plt.Line2D([], [], color=INK, linestyle='--'), plt.Line2D([], [], color=MUTED, linestyle=':')]
    fig.legend(handles, ['Monte Carlo, 200 samples', 'mean +/- 3 sigma', 'expected (ideal ratio x IB)',
                         'nominal simulation'], loc='upper right', ncol=4, frameon=False, fontsize=8.5)
    save(fig, 'Mirror alone, random mismatch (tt_mm 27 degC)', path,
         'Expected: I(M7) = IB, I(M10) = 2 IB, I(M6) = I(M9) = 16 IB (IB = 18.51 uA). The offset of the '
         'nominal from expected is Vds (channel-length modulation): tail 263 mV, sinks 887 mV, diode 652 mV.')


def distance_figure(R, path):
    sc, nom_rows, mc = R['scenarios'], R['nominal']['rows'], R['mc']
    base = nom_rows[0]['i6']
    sig = np.array([r['rows'][0]['i6'] for r in mc]).std() / base * 100
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6), facecolor=SURFACE)
    style(ax1, 'I(M6) shift vs diode next to mirror [%]')
    ax1.axhspan(-3 * sig, 3 * sig, color=BAND3, zorder=0)
    ax1.axhspan(-sig, sig, color=BAND1, zorder=0)
    for kind, g, color, marker, label in DIST_SERIES:
        pts = [(s['d'], 100 * (nom_rows[i]['i6'] / base - 1)) for i, s in enumerate(sc)
               if s['kind'] == kind and (g is None or s.get('g') == g)]
        xs, ys = zip(*pts)
        ax1.plot(xs, ys, color=color, marker=marker, linewidth=2, markersize=6,
                 markeredgecolor=SURFACE, label=label)
    ax1.set_xscale('log')
    ax1.set_xlabel('diode-to-mirror distance [um]', color=INK, fontsize=9)
    ax1.set_ylim(-5.5, 5.5)
    ax1.text(1.05, 3 * sig - 0.5, f'random +/- 3 sigma ({3 * sig:.1f} %)', fontsize=8, color=MUTED)
    ax1.text(1.05, sig - 0.45, f'+/- 1 sigma ({sig:.2f} %)', fontsize=8, color=MUTED)
    ax1.legend(frameon=False, fontsize=8, loc='lower left')
    ax1.set_title('Systematic shift vs random spread (tt 27 degC)', color=INK, fontsize=10)

    style(ax2, 'I(M6) change [%]')
    th = [(i, s['dT']) for i, s in enumerate(sc) if s['kind'] in ('base', 'thermal')]
    th.sort(key=lambda x: x[1])
    curves = []
    for r in R['corners_nom']:
        b = r['rows'][0]['i6']
        curves.append([100 * (r['rows'][i]['i6'] / b - 1) for i, _ in th])
    curves = np.array(curves)
    dts = [t for _, t in th]
    ax2.fill_between(dts, curves.min(axis=0), curves.max(axis=0), color=BAND1, label='range over 15 corners')
    tt = next(r for r in R['corners_nom'] if r['lib'] == 'tt' and r['temp'] == 27)
    ax2.plot(dts, [100 * (tt['rows'][i]['i6'] / tt['rows'][0]['i6'] - 1) for i, _ in th], color=C1,
             marker='o', linewidth=2, markersize=5, markeredgecolor=SURFACE, label='tt 27 degC')
    ax2.set_xlabel('diode (with M5/M7) temperature - mirror temperature [K]', color=INK, fontsize=9)
    ax2.legend(frameon=False, fontsize=8)
    ax2.set_title('Current change per kelvin between diode and mirror', color=INK, fontsize=10)
    h = R['heat']
    save(fig, 'Diode far from the mirror: heat source and process gradient', path,
         f"Heat source: {h['P'] * 1e3:.0f} mW in a {h['a']:.0f} x {h['a']:.0f} um block, "
         f"{h['s']:.0f} um from the near element, dT = P/(2 pi k r), k = {h['k']:.0f} W/mK. "
         'Gradient: Vth of the diode shifted by G x d. I(M10) and I(M9) shift by the same %.')


def corners_figure(R, path):
    exp = R['expected']
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.4), facecolor=SURFACE)
    style(ax1, 'nominal vs expected [%]')
    names = [f"{r['lib']} {r['temp']:g}" for r in R['corners_nom']]
    x = np.arange(len(names))
    for k, color, marker, label in (('i7', C1, 'o', 'I(M7) input'), ('i10', C2, 's', 'I(M10) tail'),
                                    ('i6', C3, '^', 'I(M6) sinks')):
        ax1.plot(x, [100 * (r['rows'][0][k] / exp[k] - 1) for r in R['corners_nom']], color=color,
                 marker=marker, linestyle='none', markersize=7, markeredgecolor=SURFACE, label=label)
    ax1.axhline(0, color=MUTED, linewidth=1)
    ax1.set_xticks(x, names, rotation=60, fontsize=8)
    ax1.legend(frameon=False, fontsize=8)
    ax1.set_title('Systematic error vs expected (no mismatch), 15 corners', color=INK, fontsize=10)

    style(ax2, 'sigma [% of mean]')
    secs = ['tt_mm', 'ss_mm', 'ff_mm', 'sf_mm', 'fs_mm']
    width = 0.2
    for j, (k, color, label) in enumerate((('i7', C1, 'I(M7)'), ('i10', C2, 'I(M10)'),
                                           ('i6', C3, 'I(M6)'), ('d69', C4, 'I(M6) - I(M9)'))):
        vals = []
        for sec in secs:
            rows = [r['rows'][0] for r in R['corners_mc'] if r['lib'] == sec and r['rows'][0]]
            if k == 'd69':
                v = np.array([r['i6'] - r['i9'] for r in rows]) / np.mean([r['i6'] for r in rows])
            else:
                v = np.array([r[k] for r in rows]) / np.mean([r[k] for r in rows])
            vals.append(100 * v.std())
        ax2.bar(np.arange(len(secs)) + (j - 1.5) * width, vals, width * 0.9, color=color, label=label)
    ax2.set_xticks(range(len(secs)), [s.replace('_mm', '') + ', 27 degC' for s in secs], fontsize=8)
    ax2.legend(frameon=False, fontsize=8)
    ax2.set_title('Random spread per process corner (100 samples each)', color=INK, fontsize=10)
    save(fig, 'Mirror over process corners', path)


def ota_figure(R, path):
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.6), sharey=True, facecolor=SURFACE)
    ys = np.arange(len(INJECT_CFGS))[::-1]
    for ax, (key, label, scale, specs) in zip(axes.flat, INJECT_METRICS):
        style(ax)
        ax.grid(False, axis='y')
        for v in specs:
            ax.axvline(v, color=SPEC_COLOR, linestyle='--', linewidth=1)
        for corner, color, marker, name in INJECT_CORNERS:
            vals = [next(r[key] for r in R['inject'] if r['config'] == cfg and r['corner'] == corner) * scale
                    for cfg, _ in INJECT_CFGS]
            ax.plot(vals, ys, color=color, marker=marker, linestyle='none', markersize=7,
                    markeredgecolor=SURFACE, label=name)
        ax.set_title(label, color=INK, fontsize=10)
    for ax in axes[:, 0]:
        ax.set_yticks(ys, [name for _, name in INJECT_CFGS], fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles.append(plt.Line2D([], [], color=SPEC_COLOR, linestyle='--'))
    labels.append('spec limit')
    fig.legend(handles, labels, loc='upper right', ncol=3, frameon=False, fontsize=8.5)
    save(fig, 'Whole OTA with worst-case mirror errors injected (gate offsets on M10/M6/M9)', path,
         '+/-3 sigma of the tt_mm Monte Carlo, all mirror outputs in the same direction (they share '
         'the diode); "100 um" adds the heat source and a 5 uV/um gradient in the same direction.')


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(plot.RES, 'mm_results.json')) as f:
        R = json.load(f)
    currents_figure(R, os.path.join(OUT, 'mm_currents.png'))
    distance_figure(R, os.path.join(OUT, 'mm_distance.png'))
    corners_figure(R, os.path.join(OUT, 'mm_corners.png'))
    ota_figure(R, os.path.join(OUT, 'mm_ota.png'))
    logger.info("wrote mismatch plots to %s", OUT)


if __name__ == '__main__':
    main_standalone()
