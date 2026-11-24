"""Draw the three NMOS-mirror separation cases as xschem schematics, derived from
06_ota1_magical/ota1.sch, so they look like the original.

Changes per case (same nets as sweep.py; the current-sense sources are not drawn):
  ota1_c1  gate line vbias_n -> vbf (M10/M6/M9) and VSS line VSSF -> VSS
           (sources and bodies of M10, M11, M6, M9, M13, M12)
  ota1_c2  tail line dt -> tail (M10+M11 drains) and output lines d6 -> OUTP, d9 -> OUTM,
           one length L_W for all of them
  ota1_c3  as c2, tail length L_T and output length L_O
Wires are drawn as pi models with ideal R/C (devices/res.sym, capa.sym) in a
"Wire model" box; R = RW*L, C = CW*L/2 at each end.

Runs inside the IIC-OSIC-TOOLS container (/foss/designs/11_cm_separation):
    python3 make_sch.py      # -> ota1_c1.sch, ota1_c2.sch, ota1_c3.sch
"""
# ============================================================================
# Imports
# ============================================================================
import logging
import os
import re

# ============================================================================
# Constants
# ============================================================================
DEBUG = False
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = '/foss/designs/06_ota1_magical/ota1.sch'
BOX = (-1200, 560, 1760, 900)           # wire-model box (x1, y1, x2, y2)
UNIT_X0, UNIT_DX, UNIT_Y = -1100, 520, 640
WIRE_NOTE = ('Wire per um at min. width: met1 RW = 0.89 Ohm, CW = 92 aF; li1 RW = 75 Ohm, CW = 57 aF '
             '(sky130A.tech). Swept L = 1 ... 100 um.')
MIRROR_BODY = ('M10', 'M11', 'M6', 'M9', 'M13', 'M12')

CASES = {
    'ota1_c1': {
        'title': 'OTA1 case c1: bias diode M4 separated from the NMOS mirror (gate line + VSS line)',
        'sub': ('M4 stays in the bias block; M10/M6/M9 gates on vbf, the mirror row (M10, M11, M6, M9, '
                'M13, M12) on its own ground VSSF. c1a: gate line only; c1b: gate line + VSS line.'),
        'units': [('wg', 'vbias_n', 'vbf', 'L_W', True, 'gate line'),
                  ('ws', 'VSSF', 'VSS', 'L_W', False, 'VSS line (c1b), mirror current returns here')],
    },
    'ota1_c2': {
        'title': 'OTA1 case c2: NMOS mirror row separated from the OTA core (equal line lengths)',
        'sub': 'Tail line dt -> tail (M10 + M11) and output lines d6 -> OUTP, d9 -> OUTM, all of length L_W.',
        'units': [('wt', 'dt', 'tail', 'L_W', True, 'tail line (M10 + M11, 74 uA)'),
                  ('wo6', 'd6', 'OUTP', 'L_W', True, 'output line M6 (301 uA)'),
                  ('wo9', 'd9', 'OUTM', 'L_W', True, 'output line M9 (301 uA)')],
    },
    'ota1_c3': {
        'title': 'OTA1 case c3: NMOS mirror row separated, tail and output lines of different length',
        'sub': 'Tail line dt -> tail of length L_T; output lines d6 -> OUTP, d9 -> OUTM of length L_O.',
        'units': [('wt', 'dt', 'tail', 'L_T', True, 'tail line (M10 + M11, 74 uA)'),
                  ('wo6', 'd6', 'OUTP', 'L_O', True, 'output line M6 (301 uA)'),
                  ('wo9', 'd9', 'OUTM', 'L_O', True, 'output line M9 (301 uA)')],
    },
}

# ============================================================================
# Logger
# ============================================================================
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Schematic edits
# ============================================================================
def sub(text: str, old: str, new: str) -> str:
    """Replace exactly one occurrence (the source schematic is fixed; a miss is a bug)."""
    if text.count(old) != 1:
        raise ValueError(f"sub: {old!r} found {text.count(old)} times")
    return text.replace(old, new)


def relabel_net(text: str, old: str, new: str) -> str:
    """Rename a wire's net label (N lines carry lab=; netlisting uses the lab_pin)."""
    return text.replace(f'{{lab={old}}}', f'{{lab={new}}}')


def lab_pin(x, y, lab, right, n) -> str:
    return f'C {{lab_pin.sym}} {x} {y} 0 {1 if right else 0} {{name=lw{n} sig_type=std_logic lab={lab}}}'


def wire_unit(i: int, name: str, a: str, b: str, length: str, caps: bool, note: str) -> list:
    """Vertical pi model: node a on top, R, node b below, C/2 from each node to VSS."""
    x = UNIT_X0 + i * UNIT_DX
    y = UNIT_Y
    xr, xc = x + 60, x + 160
    out = [f'T {{{note}}} {x - 40} {y - 70} 0 0 0.3 0.3 {{}}',
           f'N {x} {y} {xc} {y} {{lab={a}}}',
           f'N {x} {y + 120} {xc} {y + 120} {{lab={b}}}',
           f'N {xr} {y} {xr} {y + 30} {{lab={a}}}',
           f'N {xr} {y + 90} {xr} {y + 120} {{lab={b}}}',
           lab_pin(x, y, a, False, f'{i}a'),
           lab_pin(x, y + 120, b, False, f'{i}b'),
           f'C {{res.sym}} {xr} {y + 60} 0 0 {{name=R{name} value=\\{{RW*{length}\\}} '
           f'footprint=1206 device=resistor m=1}}']
    if caps:
        out += [f'C {{capa.sym}} {xc} {y + 30} 0 0 {{name=C{name}a m=1 value=\\{{CW*{length}/2\\}} '
                f'footprint=1206 device="ceramic capacitor"}}',
                f'C {{capa.sym}} {xc} {y + 150} 0 0 {{name=C{name}b m=1 value=\\{{CW*{length}/2\\}} '
                f'footprint=1206 device="ceramic capacitor"}}',
                lab_pin(xc, y + 60, 'VSS', True, f'{i}c'),
                lab_pin(xc, y + 180, 'VSS', True, f'{i}d')]
    return out


def edit_c1(text: str) -> str:
    # gate line: the mirror gates (M10, M9, M6) on vbf; the diode M4 keeps vbias_n
    for lab in ('l4', 'l11', 'l15'):
        text = sub(text, f'{{name={lab} sig_type=std_logic lab=vbias_n}}',
                   f'{{name={lab} sig_type=std_logic lab=vbf}}')
    for old in ('N -640 -40 -600 -40 {lab=vbias_n}', 'N 640 -40 600 -40 {lab=vbias_n}',
                'N -140 -40 -180 -40 {lab=vbias_n}'):
        text = sub(text, old, old.replace('vbias_n', 'vbf'))
    # VSS line: the source buses of the mirror row (gain path and CMFB) on VSSF
    for lab in ('l52', 'l56'):
        text = sub(text, f'{{name={lab} sig_type=std_logic lab=VSS}}',
                   f'{{name={lab} sig_type=std_logic lab=VSSF}}')
    for x in (-680, 680, -100, 100, 1020, 1330):
        text = re.sub(rf'^(N {x} -10 {x} 80 \{{lab=)VSS\}}', r'\1VSSF}', text, flags=re.MULTILINE)
    text = re.sub(r'^(N -?\d+ 80 -?\d+ 80 \{lab=)VSS\}', r'\1VSSF}', text, flags=re.MULTILINE)
    # the bias block's own VSS wire (M4 source) stays VSS
    text = text.replace('N -900 -10 -900 80 {lab=VSSF}', 'N -900 -10 -900 80 {lab=VSS}')
    for dev in MIRROR_BODY:
        text = re.sub(rf'(\{{name={dev}\n(?:.*\n)*?)body=VSS\n', r'\1body=VSSF\n', text, count=1)
    return text


def edit_drains(text: str) -> str:
    # cut the drain wires of M10/M11 (tail) and M6/M9 (outputs); label the drains instead
    for old in ('N -100 -150 -100 -70 {lab=tail}\n', 'N 100 -150 100 -70 {lab=tail}\n',
                'N -680 -110 -680 -70 {lab=OUTM}\n', 'N 680 -110 680 -70 {lab=OUTP}\n'):
        text = sub(text, old, '')
    pins = [lab_pin(-100, -70, 'dt', False, 'd10'), lab_pin(100, -70, 'dt', True, 'd11'),
            lab_pin(-680, -70, 'd9', True, 'd9'), lab_pin(680, -70, 'd6', False, 'd6')]
    return text + '\n'.join(pins) + '\n'


def make_case(base: str, name: str, spec: dict) -> str:
    text = edit_c1(base) if name == 'ota1_c1' else edit_drains(base)
    text = sub(text, 'T {OTA1 (MAGICAL, Chen et al. 2021) on sky130: fully differential two-stage '
                     'Miller OTA with CMFB}', f'T {{{spec["title"]}}}')
    text = re.sub(r'^T \{Sizes are parameters.*\}( -1500 -900 )', f'T {{{spec["sub"]}}}\\1', text,
                  count=1, flags=re.MULTILINE)
    x1, y1, x2, y2 = BOX
    extra = [f'B 4 {x1} {y1} {x2} {y2} {{fill=false dash=5}}',
             f'T {{Wire model (pi: R = RW*L, C = CW*L/2 at each end)}} {x1 + 10} {y1 - 50} 0 0 0.6 0.6 {{}}',
             f'T {{{WIRE_NOTE}}} {x1 + 10} {y2 + 20} 0 0 0.4 0.4 {{}}']
    for i, unit in enumerate(spec['units']):
        extra += wire_unit(i, *unit)
    return text.rstrip('\n') + '\n' + '\n'.join(extra) + '\n'


# ============================================================================
# Entry point
# ============================================================================
def main_standalone():
    with open(SRC) as f:
        base = f.read()
    for name, spec in CASES.items():
        path = os.path.join(HERE, f'{name}.sch')
        with open(path, 'w') as f:
            f.write(make_case(base, name, spec))
        logger.info("wrote %s", path)


if __name__ == '__main__':
    main_standalone()
