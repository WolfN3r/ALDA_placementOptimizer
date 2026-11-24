"""Plots of the NMOS-mirror separation sweep (results/*.json from sweep.py).

Output (plots/):
  mirror_vs_length.png   mirror currents, worst saturation margin, output CM vs wire length
  ota_vs_length.png      gain, UGB, PM, settling vs wire length
  c3_grid.png            case c3: saturation margin and gain over tail x output length
  corners.png            15-corner range of each configuration at 100 um met1

Runs inside the IIC-OSIC-TOOLS container (/foss/designs/11_cm_separation):
    python3 plot.py
"""
# ============================================================================
# Imports
# ============================================================================
import json
import logging
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')
OUT = os.path.join(HERE, 'plots')

# categorical slots 1-4 of the reference palette (validated, adjacent pairs);
# every series also has its own marker, and the legend names it
SERIES = {
    'c1a': ('#2a78d6', 'o', 'c1a gate line'),
    'c1b': ('#eb6834', 's', 'c1b gate + VSS line'),
    'c2':  ('#1baf7a', '^', 'c2 tail = output lines'),
    'c3':  ('#eda100', 'D', 'c3 tail 1 um, output lines L'),
}
LAYERS = {'met1': 'met1 (0.89 Ohm/um)', 'li1': 'li1 (75 Ohm/um)'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e4e3df'
SPEC_COLOR = '#8a8984'
SURFACE = '#fcfcfb'
DIVERGING = ('#e34948', '#f2f1ee', '#2a78d6')     # below spec, at spec, above spec

# metric: (label, scale, spec lines, y-limits that keep the met1/li1 axes readable)
MIRROR_METRICS = [
    ('di6', 'I(M6) change [%]', 1, [], (-100, 5)),
    ('di10', 'I(M10) change [%]', 1, [], (-100, 5)),
    ('vsat', 'worst sat. margin [mV]', 1e3, [50], (-100, 100)),
    ('vocm', 'output CM error [mV]', 1e3, [-30, 30], (-150, 40)),
]
OTA_METRICS = [
    ('gain', 'DC gain [dB]', 1, [66], (40, 72)),
    ('ugbw', 'UGB [MHz]', 1e-6, [120], (0, 210)),
    ('pm', 'phase margin [deg]', 1, [60, 80], (40, 85)),
    ('tset', '1 % settling [ns]', 1e9, [], (0, 60)),
]
CORNER_CFGS = [('base', 'baseline'), ('c1a', 'c1a 100 um'), ('c1b', 'c1b 100 um'),
               ('c2', 'c2 100 um'), ('c3_t1_o100', 'c3 tail 1 / out 100 um')]
CORNER_METRICS = [('vsat', 'worst sat. margin [mV]', 1e3, [50]),
                  ('vocm', 'output CM error [mV]', 1e3, [-30, 30]),
                  ('pm', 'phase margin [deg]', 1, [60, 80]),
                  ('gain', 'DC gain [dB]', 1, [66])]
DPI = 150

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data
# ============================================================================
def load(name):
    with open(os.path.join(RES, f'{name}.json')) as f:
        return json.load(f)


def series(base: dict) -> dict:
    """{case: {layer: (lengths, rows)}}; c3 is the row with a 1 um tail."""
    out = {}
    for case in ('c1a', 'c1b', 'c2'):
        rows = load(case)
        out[case] = {ly: ([r['length'] for r in rows if r['layer'] == ly],
                          [r for r in rows if r['layer'] == ly]) for ly in LAYERS}
    rows = [r for r in load('c3') if r['l_tail'] == 1]
    out['c3'] = {ly: ([r['l_out'] for r in rows if r['layer'] == ly],
                      [r for r in rows if r['layer'] == ly]) for ly in LAYERS}
    for case in out.values():
        for _, rows in case.values():
            for r in rows:
                r['di6'] = 100 * (r['i6'] / base['i6'] - 1)
                r['di10'] = 100 * (r['i10'] / base['i10'] - 1)
    return out


# ============================================================================
# Plots
# ============================================================================
def style(ax, ylabel=None):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK, fontsize=9)


def spec_lines(ax, values):
    for v in values:
        ax.axhline(v, color=SPEC_COLOR, linestyle='--', linewidth=1)


def length_figure(data: dict, base: dict, metrics: list, title: str, path: str):
    fig, axes = plt.subplots(len(metrics), 2, figsize=(11, 2.6 * len(metrics)), sharex=True,
                             facecolor=SURFACE)
    for row, (key, label, scale, specs, ylim) in enumerate(metrics):
        for col, layer in enumerate(LAYERS):
            ax = axes[row, col]
            style(ax, label if col == 0 else None)
            base_v = 0 if key.startswith('di') else base[key] * scale
            ax.axhline(base_v, color=MUTED, linestyle=':', linewidth=1)
            spec_lines(ax, specs)
            for case, (color, marker, name) in SERIES.items():
                xs, rows = data[case][layer]
                ys = [r[key] * scale if key in r else np.nan for r in rows]
                ax.plot(xs, ys, color=color, marker=marker, markersize=6, linewidth=2,
                        markeredgecolor=SURFACE, markeredgewidth=1, label=name, clip_on=True)
            ax.set_xscale('log')
            ax.set_ylim(*ylim)
            if row == 0:
                ax.set_title(LAYERS[layer], color=INK, fontsize=10)
            if row == len(metrics) - 1:
                ax.set_xlabel('wire length [um]', color=INK, fontsize=9)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    handles += [plt.Line2D([], [], color=MUTED, linestyle=':'),
                plt.Line2D([], [], color=SPEC_COLOR, linestyle='--')]
    labels += ['baseline (no wires)', 'spec limit']
    fig.legend(handles, labels, loc='upper center', ncol=6, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.965))
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, ha='left', y=0.995)
    fig.text(0.01, 0.005, 'tt 27 degC. Points outside the axis range or missing: the OTA has '
             'broken down (no unity-gain crossing).', color=MUTED, fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def grid_figure(path: str):
    rows = load('c3')
    lt = sorted({r['l_tail'] for r in rows})
    lo = sorted({r['l_out'] for r in rows})
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('div', DIVERGING)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.4), facecolor=SURFACE)
    panels = [('vsat', 1e3, 50, (-200, 100), 'worst sat. margin [mV] (spec >= 50)', '{:.0f}'),
              ('gain', 1, 66, (-70, 70), 'DC gain [dB] (spec >= 66)', '{:.1f}')]
    for row, (key, scale, spec, lim, label, fmt) in enumerate(panels):
        for col, layer in enumerate(LAYERS):
            ax = axes[row, col]
            m = np.full((len(lt), len(lo)), np.nan)
            for r in rows:
                if r['layer'] == layer and key in r:
                    m[lt.index(r['l_tail']), lo.index(r['l_out'])] = r[key] * scale
            norm = TwoSlopeNorm(vcenter=spec, vmin=lim[0], vmax=lim[1])
            im = ax.imshow(m, cmap=cmap, norm=norm, origin='lower', aspect='auto')
            for i in range(len(lt)):
                for j in range(len(lo)):
                    ax.text(j, i, fmt.format(m[i, j]), ha='center', va='center', fontsize=8,
                            color=INK)
            ax.set_xticks(range(len(lo)), [str(v) for v in lo])
            ax.set_yticks(range(len(lt)), [str(v) for v in lt])
            ax.set_xlabel('output line length L_O [um]', color=INK, fontsize=9)
            ax.set_ylabel('tail line length L_T [um]', color=INK, fontsize=9)
            ax.tick_params(colors=MUTED, labelsize=8)
            ax.set_title(f'{LAYERS[layer]}: {label}', color=INK, fontsize=10)
            fig.colorbar(im, ax=ax, shrink=0.85).ax.tick_params(labelsize=8, colors=MUTED)
    fig.suptitle('Case c3: tail and output lines of different length (tt 27 degC). '
                 'Blue = above spec, red = below.', color=INK, fontsize=12, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def corner_figure(path: str):
    rows = load('corners')
    fig, axes = plt.subplots(1, len(CORNER_METRICS), figsize=(13, 3.8), sharey=True,
                             facecolor=SURFACE)
    ys = np.arange(len(CORNER_CFGS))[::-1]
    for ax, (key, label, scale, specs) in zip(axes, CORNER_METRICS):
        style(ax)
        for v in specs:
            ax.axvline(v, color=SPEC_COLOR, linestyle='--', linewidth=1)
        for y, (cfg, _) in zip(ys, CORNER_CFGS):
            vals = [r[key] * scale for r in rows if r['config'] == cfg and key in r]
            ax.plot([min(vals), max(vals)], [y, y], color='#2a78d6', linewidth=6,
                    solid_capstyle='round')
            tt = [r[key] * scale for r in rows if r['config'] == cfg and r['corner'] == ['tt', 27]]
            ax.plot(tt, [y], marker='o', color=INK, markersize=5, linestyle='none')
        ax.set_title(label, color=INK, fontsize=10)
        ax.grid(True, axis='x', color=GRID, linewidth=0.6)
        ax.grid(False, axis='y')
    axes[0].set_yticks(ys, [name for _, name in CORNER_CFGS])
    handles = [plt.Line2D([], [], color='#2a78d6', linewidth=6),
               plt.Line2D([], [], color=INK, marker='o', linestyle='none'),
               plt.Line2D([], [], color=SPEC_COLOR, linestyle='--')]
    fig.legend(handles, ['range over 15 corners', 'tt 27 degC', 'spec limit'], loc='upper right',
               ncol=3, frameon=False, fontsize=8.5)
    fig.suptitle('Corners (tt/ss/ff/sf/fs x -20/27/120 degC), wires in met1', color=INK,
                 fontsize=12, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    os.makedirs(OUT, exist_ok=True)
    base = load('base')[0]
    data = series(base)
    length_figure(data, base, MIRROR_METRICS, 'NMOS mirror outputs vs wire length',
                  os.path.join(OUT, 'mirror_vs_length.png'))
    length_figure(data, base, OTA_METRICS, 'OTA performance vs wire length',
                  os.path.join(OUT, 'ota_vs_length.png'))
    grid_figure(os.path.join(OUT, 'c3_grid.png'))
    corner_figure(os.path.join(OUT, 'corners.png'))
    logger.info("wrote plots to %s", OUT)


if __name__ == '__main__':
    main_standalone()
