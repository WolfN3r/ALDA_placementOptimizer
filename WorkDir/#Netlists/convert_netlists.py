#!/usr/bin/env python3
"""
convert_netlists.py
Converts ALIGN FinFET example netlists to CMOS-style netlists.

Run from any location; paths are resolved relative to this script.
Output: examples/#Netlists/a<XY>_<circuit_name>.sp
"""
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent   # examples/#Netlists/
EXAMPLES_DIR = SCRIPT_DIR.parent                 # examples/
OUTPUT_DIR   = SCRIPT_DIR

# ---------------------------------------------------------------------------
# Transistor model mapping (keys lower-cased; values are canonical names)
# ---------------------------------------------------------------------------
MODEL_MAP = {
    'nmos_rvt': 'nmos_rvt', 'pmos_rvt': 'pmos_rvt',
    'n':        'nmos_rvt', 'nfet':     'nmos_rvt',
    'p':        'pmos_rvt', 'pfet':     'pmos_rvt',
    'nmos_lvt': 'nmos_lvt', 'nlvt':     'nmos_lvt', 'lvtnfet': 'nmos_lvt',
    'pmos_lvt': 'pmos_lvt', 'plvt':     'pmos_lvt', 'pulvt':   'pmos_lvt',
    'lvtpfet':  'pmos_lvt', 'plplvt':   'pmos_lvt',
    # MAGICAL PDK types
    'nch': 'nmos_rvt', 'nch_mac': 'nmos_rvt', 'nch_25ud18_mac': 'nmos_rvt',
    'pch': 'pmos_rvt', 'pch_mac': 'pmos_rvt',
    'nch_lvt': 'nmos_lvt', 'nch_lvt_mac': 'nmos_lvt',
    'pch_lvt': 'pmos_lvt', 'pch_lvt_mac': 'pmos_lvt',
    'nch_hvt': 'nmos_hvt', 'nch_hvt_mac': 'nmos_hvt',
    'pch_hvt': 'pmos_hvt', 'pch_hvt_mac': 'pmos_hvt',
}

# ---------------------------------------------------------------------------
# Circuit list — ordered as in `ls` output
# ---------------------------------------------------------------------------
CIRCUIT_LIST = [
    ( 1, "adder"),
    ( 2, "block_spacing_bug"),
    ( 3, "bottom_plate_4path_beamforming"),
    ( 4, "bottom_plate_4path_beamforming_hierarchical"),
    ( 5, "buffer"),
    ( 6, "cascode_current_mirror_ota"),
    ( 7, "common_source"),
    ( 8, "comparator1"),
    ( 9, "current_mirror_ota"),
    (10, "double_tail_sense_amplifier"),
    (11, "five_transistor_ota"),
    (12, "five_transistor_ota_Bulk"),
    (13, "five_transistor_ota_high_frequency"),
    (14, "fixed_height"),
    (15, "high_speed_comparator"),
    (16, "high_speed_comparator_charge_flow"),
    (17, "inverter_current_starved"),
    (18, "inverter_v1"),
    (19, "inverter_v2"),
    (20, "inverter_v3"),
    (21, "linear_equalizer"),
    (22, "mimo_bulk"),
    (23, "powertrain"),
    (24, "powertrain_binary"),
    (25, "powertrain_thermo"),
    (26, "ring_oscillator"),
    (27, "sc_dc_dc_converter"),
    (28, "single_to_differential_converter"),
    (29, "switched_capacitor_filter"),
    (30, "telescopic_ota"),
    (31, "telescopic_ota_guard_ring"),
    (32, "telescopic_ota_multi_connection"),
    (33, "telescopic_ota_with_bias"),
    (34, "test_vga"),
    (35, "unity_gain_buffers"),
    (36, "variable_gain_amplifier"),
    (37, "vco_dtype_12_hierarchical"),
    (38, "vco_dtype_12_hierarchical_res"),
    (39, "vco_dtype_12_hierarchical_res_constrained"),
    (40, "VCO_type2_65"),
    (41, "vga_stage"),
]

# ---------------------------------------------------------------------------
# MAGICAL circuit list and directory
# ---------------------------------------------------------------------------
MAGICAL_DIR = SCRIPT_DIR.parent.parent / 'MAGICALexamples'

MAGICAL_CIRCUIT_LIST = [
    (1, 'comp',                        'comp.sp'),
    (2, 'ota1',                        'ota1.sp'),
    (3, 'ota2',                        'ota2.sp'),
    (4, 'telescopic_three_stage_flow', 'Telescopic_Three_stage_flow.sp'),
    (5, 'ctdsm_top',                   'CTDSM_TOP.sp'),
    (6, 'ctdsm_core_new',              'CTDSM_CORE_NEW_hspice.sp'),
]

# Power rail mapping per circuit.
# Keys are circuit names lower-cased for lookup; values map original_rail_lower -> NEW_RAIL.
# Only PRIMARY rails are mapped. Secondary rails (vdda_bb etc.) are left as-is.
POWER_RAIL_MAP = {
    "adder":                                       {"vps": "VDDA", "vgnd": "VSSA"},
    "block_spacing_bug":                           {"vss": "VSSA"},
    "bottom_plate_4path_beamforming":              {"vdda": "VDDA", "vssa": "VSSA",
                                                    "vddd": "VDDD", "vssd": "VSSD"},
    "bottom_plate_4path_beamforming_hierarchical": {"vdda": "VDDA", "vssa": "VSSA"},
    "buffer":                                      {"vdd": "VDDA", "vss": "VSSA"},
    "cascode_current_mirror_ota":                  {"vdd": "VDDA", "vss": "VSSA"},
    "common_source":                               {"vcc": "VDDA", "vss": "VSSA"},
    "comparator1":                                 {"vdd": "VDDA", "vss": "VSSA"},
    "current_mirror_ota":                          {"vdd": "VDDA", "vss": "VSSA"},
    "double_tail_sense_amplifier":                 {"vdd": "VDDA", "vss": "VSSA"},
    "five_transistor_ota":                         {"vdd": "VDDA", "vss": "VSSA"},
    "five_transistor_ota_bulk":                    {"vdd": "VDDA", "vss": "VSSA"},
    "five_transistor_ota_high_frequency":          {"vdd_ota": "VDDA", "vss_ota": "VSSA"},
    "fixed_height":                                {"vdd": "VDDD", "vss": "VSSD"},
    "high_speed_comparator":                       {"vcc": "VDDA", "vss": "VSSA"},
    "high_speed_comparator_charge_flow":           {"vcc": "VDDA", "vss": "VSSA"},
    "inverter_current_starved":                    {"vcc": "VDDA", "vss": "VSSA"},
    "inverter_v1":                                 {"vdd": "VDDA", "vss": "VSSA"},
    "inverter_v2":                                 {"vdd": "VDDA", "vss": "VSSA"},
    "inverter_v3":                                 {"vdd": "VDDA", "vss": "VSSA"},
    "linear_equalizer":                            {"vps": "VDDA", "vgnd": "VSSA"},
    "mimo_bulk":                                   {"vdda": "VDDA", "vssa": "VSSA",
                                                    "vddd": "VDDD", "vssd": "VSSD",
                                                    "vdd":  "VDDD", "vss":  "VSSD"},
    "powertrain":                                  {"vcc": "VDDA"},
    "powertrain_binary":                           {"vcc": "VDDA"},
    "powertrain_thermo":                           {"vcc": "VDDA"},
    "ring_oscillator":                             {"vccx": "VDDA", "vssx": "VSSA"},
    "sc_dc_dc_converter":                          {"vss": "VSSA"},
    "single_to_differential_converter":            {"vps": "VDDA", "vgnd": "VSSA"},
    "switched_capacitor_filter":                   {"vdd": "VDDA", "vss": "VSSA"},
    "telescopic_ota":                              {"vdd": "VDDA", "vss": "VSSA", "0": "VSSA"},
    "telescopic_ota_guard_ring":                   {"vdd": "VDDA", "vss": "VSSA"},
    "telescopic_ota_multi_connection":             {"vdd": "VDDA", "vss": "VSSA"},
    "telescopic_ota_with_bias":                    {"vdd": "VDDA", "vss": "VSSA"},
    "test_vga":                                    {"vcca": "VDDA", "vssa": "VSSA"},
    "unity_gain_buffers":                          {"vcc": "VDDA", "vss": "VSSA"},
    "variable_gain_amplifier":                     {"vps": "VDDA", "vgnd": "VSSA"},
    "vco_dtype_12_hierarchical":                   {"vdd": "VDDA", "vss": "VSSA"},
    "vco_dtype_12_hierarchical_res":               {"vdd": "VDDA", "vss": "VSSA"},
    "vco_dtype_12_hierarchical_res_constrained":   {"vdd": "VDDA", "vss": "VSSA"},
    "vco_type2_65":                                {"vdd": "VDDA", "vss": "VSSA"},
    "vga_stage":                                   {"vgnd": "VSSA"},
    # MAGICAL circuits
    "comp":                                        {"vdd": "VDDA", "gnd": "VSSA"},
    "ota1":                                        {"vdd": "VDDA", "vss": "VSSA"},
    "ota2":                                        {"vdd": "VDDA", "gnd": "VSSA"},
    "telescopic_three_stage_flow":                 {"vdd": "VDDA", "vss": "VSSA"},
    "ctdsm_top":                                   {"vdd": "VDDA", "gnd": "VSSA", "vss": "VSSA"},
    "ctdsm_core_new":                              {},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_LITERAL_RE = re.compile(
    r'^[-+]?\d+(\.\d+)?([eE][-+]?\d+)?[fpnumkKMGT]?$'
)

def is_literal(val: str) -> bool:
    """True if val is a numeric literal (not a variable/expression reference)."""
    v = val.strip().lstrip('{').rstrip('}')
    return bool(_LITERAL_RE.match(v))


# ---------------------------------------------------------------------------
# Numeric technology-scaling pass (transistor W/L, passive R/C sizing)
# See .claude/plans/netlist_technology_scaling.md for the full derivation.
# ---------------------------------------------------------------------------
GPDK_RULES_PATH    = EXAMPLES_DIR / 'myPDK' / 'gpdk090_device_rules.json'
DEVICE_CONSTRAINTS = json.loads(GPDK_RULES_PATH.read_text())['device_constraints']

GPDK_TECH_PATH   = EXAMPLES_DIR / 'myPDK' / 'gpdk090_tech_simple.json'
_MFG_GRID_UM     = json.loads(GPDK_TECH_PATH.read_text())['technology_info']['manufacturing_grid']
TRANSISTOR_GRID_UM = _MFG_GRID_UM * 10   # transistor L/W snapped to 10x the manufacturing grid

GPDK_L_MIN_TRANSISTOR   = DEVICE_CONSTRAINTS['nmos_rvt']['L']['min']   # 0.1 um, gpdk090 reference Lmin
RES_POLY_RHO_OHM_PER_SQ = 100.0                                        # gpdk090-spec-derived (Cadence GPDK090 ref manual)
RES_POLY_DEFAULT_W_UM   = DEVICE_CONSTRAINTS['res_poly']['W']['default']
CAP_DENSITY_F_PER_UM2   = 1.5e-15                                      # generic 90nm estimate, ratios matter more than exact value
SCALE_PERCENTILE        = 3.0                                          # within the plan's 1st-5th percentile band


def snap_to_grid(value_um: float, grid_um: float) -> float:
    return round(round(value_um / grid_um) * grid_um, 6)

_SUFFIX_MULT = {
    'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
    'k': 1e3, 'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12,
}
_NUM_RE = re.compile(r'^([-+]?\d*\.?\d+)((?:[eE][-+]?\d+)?)([A-Za-z]*)$')

CONVERSION_MARKER_RE = re.compile(r'SIZES CONVERTED', re.IGNORECASE)


def parse_spice_scalar(val: str) -> float | None:
    """Parse a SPICE numeric literal (optional exponent/unit suffix) to a plain base-unit float."""
    s = val.strip().lstrip('{').rstrip('}')
    m = _NUM_RE.match(s)
    if not m or not m.group(1):
        return None
    mantissa = float(m.group(1))
    if m.group(2):
        mantissa *= 10 ** int(m.group(2)[1:])
    suffix = m.group(3)
    if suffix:
        mult = _SUFFIX_MULT.get(suffix)
        if mult is None:
            return None
        mantissa *= mult
    return mantissa


def parse_length_um(val: str) -> float | None:
    """
    Parse a length-bearing literal to micrometers.
    Convention used across a*/m* netlists: a value carrying an explicit SPICE
    unit suffix or exponent is stated in meters (standard SPICE) -> x1e6 to um.
    A bare plain number with neither suffix nor exponent is already stated in
    um (this repo's own convention for these files' W/L values).
    """
    s = val.strip().lstrip('{').rstrip('}')
    m = _NUM_RE.match(s)
    if not m or not m.group(1):
        return None
    base = parse_spice_scalar(val)
    if base is None:
        return None
    if m.group(2) or m.group(3):
        return base * 1e6
    return base


def fmt_um(value: float) -> str:
    return f'{value:.4g}'


def percentile(values: list, pct: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def compute_scale_factor(percentile_L_um: float) -> float:
    return GPDK_L_MIN_TRANSISTOR / percentile_L_um


def clip_transistor(L_um: float, W_um: float, M: int, Nf: int, pdk_type: str,
                    can_split_m: bool, can_split_nf: bool) -> tuple:
    """
    Deterministic overshoot rule (plan section 3): redistribute width into M,
    then into Nf, then clip L with an aspect-preserving W rescale. A pure
    function of its own arguments -> two matched devices sharing identical
    (L, W, pdk_type, can_split_m, can_split_nf) always converge to identical
    results, with no pair-matching/iteration-order state required.
    """
    c = DEVICE_CONSTRAINTS[pdk_type]
    Lmin, Lmax = c['L']['min'], c['L']['max']
    Wmin, Wmax = c['W']['min'], c['W']['max']

    if W_um > Wmax and can_split_m:
        n = math.ceil(math.log2(W_um / Wmax))
        W_um /= 2 ** n
        M *= 2 ** n

    if W_um > Wmax and can_split_nf:
        n = math.ceil(math.log2(W_um / Wmax))
        W_um /= 2 ** n
        Nf *= 2 ** n

    if L_um > Lmax or L_um < Lmin:
        aspect = (W_um / L_um) if L_um else 1.0
        L_um = min(max(L_um, Lmin), Lmax)
        W_um = L_um * aspect

    W_um = min(max(W_um, Wmin), Wmax)

    # Snap to 10x the manufacturing grid, then re-clip -- a snap can round a
    # boundary value just outside [min, max].
    L_um = min(max(snap_to_grid(L_um, TRANSISTOR_GRID_UM), Lmin), Lmax)
    W_um = min(max(snap_to_grid(W_um, TRANSISTOR_GRID_UM), Wmin), Wmax)
    return L_um, W_um, M, Nf


def electrical_resistor_to_LW(r_ohms: float) -> tuple:
    """Section 6: fix W at res_poly's default width, solve L = R*W/rho, clip."""
    c = DEVICE_CONSTRAINTS['res_poly']
    W_um = RES_POLY_DEFAULT_W_UM
    L_um = abs(r_ohms) * W_um / RES_POLY_RHO_OHM_PER_SQ
    L_um = min(max(L_um, c['L']['min']), c['L']['max'])
    return L_um, W_um


def electrical_cap_to_LW(c_farad: float) -> tuple:
    """Section 5: no source geometry -> square sized from the generic density estimate."""
    c = DEVICE_CONSTRAINTS['cap_mom']
    side_um = math.sqrt(abs(c_farad) / CAP_DENSITY_F_PER_UM2)
    side_um = min(max(side_um, c['L']['min']), c['L']['max'])
    return side_um, side_um


def geometry_cap_to_LW(nr: float, lr_um: float, w_um: float, s_um: float) -> tuple:
    """Section 4/5: MAGICAL source footprint -> square of equal area (density cancels)."""
    c = DEVICE_CONSTRAINTS['cap_mom']
    area_um2 = nr * lr_um * (w_um + s_um)
    side_um = math.sqrt(max(area_um2, 0.0))
    side_um = min(max(side_um, c['L']['min']), c['L']['max'])
    return side_um, side_um


def scale_transistor_params(device_params: dict, device_records: list, scale_factor: float) -> None:
    """Mutate device_params in place: scale every _L/_W pair by scale_factor, clip per pdk_type."""
    model_by_dev = {r['dev_id']: r['model'] for r in device_records}
    dev_keys = defaultdict(dict)
    for pname in device_params:
        for suffix in ('_L', '_W', '_M', '_Nf'):
            if pname.endswith(suffix):
                dev_keys[pname[:-len(suffix)]][suffix] = pname
                break

    for dev_id, keys in dev_keys.items():
        if '_L' not in keys or '_W' not in keys:
            continue
        model = model_by_dev.get(dev_id)
        if model not in DEVICE_CONSTRAINTS:
            continue
        L_name, W_name = keys['_L'], keys['_W']
        L0 = parse_length_um(device_params[L_name])
        W0 = parse_length_um(device_params[W_name])
        if L0 is None or W0 is None:
            continue
        L1, W1 = L0 * scale_factor, W0 * scale_factor

        M_name, Nf_name = keys.get('_M'), keys.get('_Nf')
        M_val  = int(float(device_params[M_name]))  if M_name  and is_literal(device_params[M_name])  else 1
        Nf_val = int(float(device_params[Nf_name])) if Nf_name and is_literal(device_params[Nf_name]) else 1
        can_split_m  = bool(M_name  and is_literal(device_params[M_name]))
        can_split_nf = bool(Nf_name and is_literal(device_params[Nf_name]))

        L1, W1, M_val, Nf_val = clip_transistor(
            L1, W1, M_val, Nf_val, model, can_split_m, can_split_nf
        )

        device_params[L_name] = fmt_um(L1)
        device_params[W_name] = fmt_um(W1)
        if can_split_m:
            device_params[M_name] = str(M_val)
        if can_split_nf:
            device_params[Nf_name] = str(Nf_val)


# --- Passive component scaling ----------------------------------------------
_PARAM_ASSIGN_RE = re.compile(r'(\w+)=(\S+)')
_RC_ELEMENT_RE   = re.compile(r'^(\s*)([RC]\w*)\s+(\S+)\s+(\S+)\s+(.*)$', re.IGNORECASE)
_NON_WORD_RE     = re.compile(r'\W')


def register_passive_param(device_params: dict, prefix: str, inst: str,
                           L_um: float, W_um: float, scope: str = '') -> tuple:
    """
    Register a passive device's L/W as named .param entries (same convention
    as transistor sizing: <prefix>_[<subckt>_]<inst>_L / _W), so every device
    size in the file -- transistor or passive -- lives in one param block at
    the top instead of as an inline literal on the instance line. `scope` is
    the enclosing subckt name (with trailing '_'), when the file has more
    than one subckt and instance names can repeat across them.
    """
    safe_inst = _NON_WORD_RE.sub('', inst)
    L_name = f'{prefix}_{scope}{safe_inst}_L'
    W_name = f'{prefix}_{scope}{safe_inst}_W'
    device_params[L_name] = fmt_um(L_um)
    device_params[W_name] = fmt_um(W_um)
    return L_name, W_name


def build_param_index(lines: list) -> dict:
    """Map param_name -> (line_idx, 'name=value' token) for every '.param' assignment."""
    index = {}
    for i, line in enumerate(lines):
        if not line.lstrip().lower().startswith('.param'):
            continue
        for m in _PARAM_ASSIGN_RE.finditer(line):
            index[m.group(1)] = (i, m.group(0))
    return index


def rewrite_param_value(lines: list, param_index: dict, name: str, new_value: str) -> None:
    i, raw_token = param_index[name]
    new_token = f'{name}={new_value}'
    lines[i] = lines[i].replace(raw_token, new_token, 1)
    param_index[name] = (i, new_token)


def process_rc_line(line: str, param_index: dict, lines: list, scale_factor: float,
                    device_params: dict, scope: str = '') -> str:
    """
    a-family electrical/geometric R/C element or 'resistor'/'capacitor' subckt
    call (plan sections 6 and the length-vs-electrical split in the a21/a28
    note). Electrical values (bare direct value, or r=/c= keyword) are left
    untouched for simulation fidelity; derived physical L/W are registered as
    named .param entries (see register_passive_param) and referenced from the
    line. Pure length keyword args (w=/l= with no r=/c=) are geometric
    already and get scaled, also promoted to named .param entries.
    """
    m = _RC_ELEMENT_RE.match(line)
    if not m:
        return line
    indent, inst, n1, n2, rest = m.groups()
    rest_tokens = rest.split()
    if not rest_tokens:
        return line
    kind = 'R' if inst[0].upper() == 'R' else 'C'
    prefix = 'res' if kind == 'R' else 'cap'
    bounds = DEVICE_CONSTRAINTS['res_poly'] if kind == 'R' else DEVICE_CONSTRAINTS['cap_mom']

    def resolve_scalar(ref: str, as_length: bool):
        if is_literal(ref):
            return parse_length_um(ref) if as_length else parse_spice_scalar(ref)
        if ref in param_index:
            val = param_index[ref][1].split('=', 1)[1]
            return parse_length_um(val) if as_length else parse_spice_scalar(val)
        return None

    if len(rest_tokens) == 1 and '=' not in rest_tokens[0]:
        ref = rest_tokens[0]
        val = resolve_scalar(ref, as_length=False)
        if val is None:
            return line
        L_um, W_um = electrical_resistor_to_LW(val) if kind == 'R' else electrical_cap_to_LW(val)
        L_name, W_name = register_passive_param(device_params, prefix, inst, L_um, W_um, scope)
        return f'{indent}{inst} {n1} {n2} {ref} L={{{L_name}}} W={{{W_name}}}'

    kv_order = []
    kv = {}
    for t in rest_tokens:
        if '=' in t:
            k, v = t.split('=', 1)
            kv[k.lower()] = v
            kv_order.append((t, k, v))
        else:
            kv_order.append((t, None, None))

    if 'w' in kv and 'l' in kv and 'r' not in kv and 'c' not in kv:
        new_tokens = []
        for tok, k, v in kv_order:
            if k and k.lower() in ('w', 'l'):
                length_um = resolve_scalar(v, as_length=True)
                if length_um is None:
                    new_tokens.append(tok)
                    continue
                new_len = min(max(length_um * scale_factor, bounds['L']['min']), bounds['L']['max'])
                param_name = f'{prefix}_{scope}{_NON_WORD_RE.sub("", inst)}_{k.upper()}'
                device_params[param_name] = fmt_um(new_len)
                if v in param_index:
                    rewrite_param_value(lines, param_index, v, fmt_um(new_len))
                new_tokens.append(f'{k}={{{param_name}}}')
            else:
                new_tokens.append(tok)
        return f'{indent}{inst} {n1} {n2} ' + ' '.join(new_tokens)

    if 'r' in kv or 'c' in kv:
        key = 'r' if 'r' in kv else 'c'
        ref = kv[key]
        val = resolve_scalar(ref, as_length=False)
        if val is None:
            return line
        L_um, W_um = electrical_resistor_to_LW(val) if key == 'r' else electrical_cap_to_LW(val)
        L_name, W_name = register_passive_param(device_params, prefix, inst, L_um, W_um, scope)
        orig_tokens = [t for t, _, _ in kv_order]
        return f'{indent}{inst} {n1} {n2} ' + ' '.join(orig_tokens) + \
               f' L={{{L_name}}} W={{{W_name}}}'

    return line


def _split_x_passive_line(line: str) -> tuple | None:
    """Split an MAGICAL xC/xR instance line into (indent, inst, nets, model, kv_order) or None."""
    indent = line[:len(line) - len(line.lstrip())]
    tokens = line.split()
    non_kv_idx = [i for i, t in enumerate(tokens) if '=' not in t]
    if len(non_kv_idx) < 2:
        return None
    model_idx = non_kv_idx[-1]
    inst  = tokens[0]
    nets  = tokens[1:model_idx]
    model = tokens[model_idx]
    kv_order = []
    for t in tokens[model_idx + 1:]:
        if '=' in t:
            k, v = t.split('=', 1)
            kv_order.append((t, k, v))
        else:
            kv_order.append((t, None, None))
    return indent, inst, nets, model, kv_order


def process_xc_line(line: str, device_params: dict, scope: str = '') -> str:
    """m-family MAGICAL cfmom capacitor: unified density-based square sizing (section 4/5)."""
    parts = _split_x_passive_line(line)
    if parts is None:
        return line
    indent, inst, nets, model, kv_order = parts
    kv = {k.lower(): v for _, k, v in kv_order if k}
    if 'lr' not in kv:
        return line
    nr    = parse_spice_scalar(kv.get('nr', '1')) or 1.0
    lr_um = parse_length_um(kv['lr']) or 0.0
    w_um  = parse_length_um(kv.get('w', '0')) or 0.0
    s_um  = parse_length_um(kv.get('s', '0')) or 0.0
    side_um, _ = geometry_cap_to_LW(nr, lr_um, w_um, s_um)
    L_name, W_name = register_passive_param(device_params, 'cap', inst, side_um, side_um, scope)

    new_tokens = [tok for tok, k, v in kv_order if not (k and k.lower() in ('lr', 'w', 's'))]
    new_tokens += [f'L={{{L_name}}}', f'W={{{W_name}}}']
    return f'{indent}{inst} ' + ' '.join(nets) + f' {model} ' + ' '.join(new_tokens)


def process_xr_line(line: str, scale_factor: float, device_params: dict, scope: str = '') -> str:
    """m-family MAGICAL rppolywo resistor: scale lr/wr as lengths (section 4)."""
    parts = _split_x_passive_line(line)
    if parts is None:
        return line
    indent, inst, nets, model, kv_order = parts
    kv = {k.lower(): v for _, k, v in kv_order if k}
    if 'lr' not in kv or 'wr' not in kv:
        return line
    c = DEVICE_CONSTRAINTS['res_poly']
    lr_um = (parse_length_um(kv['lr']) or 0.0) * scale_factor
    wr_um = (parse_length_um(kv['wr']) or 0.0) * scale_factor
    lr_um = min(max(lr_um, c['L']['min']), c['L']['max'])
    wr_um = min(max(wr_um, c['W']['min']), c['W']['max'])
    L_name, W_name = register_passive_param(device_params, 'res', inst, lr_um, wr_um, scope)

    new_tokens = []
    for tok, k, v in kv_order:
        if k and k.lower() == 'lr':
            new_tokens.append(f'{k}={{{L_name}}}')
        elif k and k.lower() == 'wr':
            new_tokens.append(f'{k}={{{W_name}}}')
        else:
            new_tokens.append(tok)
    return f'{indent}{inst} ' + ' '.join(nets) + f' {model} ' + ' '.join(new_tokens)


def scale_passives(lines: list, family: str, scale_factor: float, device_params: dict) -> list:
    """
    Apply the section 4/5/6 passive conversion to one file's already-transformed
    lines. Tracks .subckt scope so instance names that repeat across sibling
    subckts (e.g. 'R0' in two different unit cells) still get distinct
    .param entries -- mirrors the transistor-side <subckt>_<inst> convention.
    """
    new_lines = list(lines)
    param_index = build_param_index(new_lines) if family == 'a' else None
    multi = count_subckts(lines) > 1
    subckt_stack = []
    for i, line in enumerate(new_lines):
        s = line.lstrip()
        if not s or s[0] in '*$.':
            lo = s.lower()
            if lo.startswith('.subckt'):
                subckt_stack.append(line.split()[1] if len(line.split()) > 1 else '')
            elif lo.startswith('.ends') or lo == '.end':
                if subckt_stack:
                    subckt_stack.pop()
            continue
        first = s.split()[0]
        scope = f'{subckt_stack[-1]}_' if (multi and subckt_stack) else ''
        if family == 'a' and first[:1].upper() in ('R', 'C'):
            new_lines[i] = process_rc_line(new_lines[i], param_index, new_lines, scale_factor,
                                            device_params, scope)
        elif family == 'm':
            fl = first.lower()
            if fl.startswith('xc'):
                new_lines[i] = process_xc_line(new_lines[i], device_params, scope)
            elif fl.startswith('xr'):
                new_lines[i] = process_xr_line(new_lines[i], scale_factor, device_params, scope)
    return new_lines


def helper_subckt_text(base_text: str, seg_r_ohms: float) -> str:
    """
    Append derived physical L/W to the mimo_bulk split-resistor helper subckt
    segments, as named .param entries local to the subckt (all segments
    share one size since they share seg_r) rather than inline literals.
    """
    L_um, W_um = electrical_resistor_to_LW(seg_r_ohms)
    text = base_text.replace('.param seg_r=', f'.param seg_L={fmt_um(L_um)} seg_W={fmt_um(W_um)} seg_r=', 1)
    return text.replace('{seg_r}', '{seg_r} L={seg_L} W={seg_W}')


def map_token(tok: str, rail_map: dict) -> str:
    """Replace a token if it exactly matches a power rail name (case-insensitive)."""
    mapped = rail_map.get(tok.lower())
    return mapped if mapped is not None else tok


def apply_rails_to_tokens(tokens: list, rail_map: dict) -> list:
    """
    Apply power rail substitution token by token.
    Skip tokens that are key=value parameters (contain '=').
    """
    out = []
    for tok in tokens:
        if '=' in tok:
            out.append(tok)          # parameter — do not touch
        else:
            out.append(map_token(tok, rail_map))
    return out


def remap_finfet_params(kv_tokens: list, inst_name: str,
                        multi_subckt: bool, subckt_name: str,
                        device_params: dict) -> list:
    """
    Rename FinFET parameters (nfin→W, l→L, nf→Nf, m→M, drop w if nfin present).
    Extract literal values into device_params dict.
    Return new list of key=value tokens for the transistor line.
    """
    raw = {}   # original_lower_key -> (original_key, value_str)
    for tok in kv_tokens:
        eq = tok.find('=')
        if eq < 0:
            raw[tok.lower()] = (tok, '')
            continue
        k, v = tok[:eq], tok[eq+1:]
        raw[k.lower()] = (k, v)

    has_nfin = 'nfin' in raw
    key_rename = {'nfin': 'W', 'l': 'L', 'nf': 'Nf', 'm': 'M', 'multi': 'M', 'w': 'W'}

    result = []
    for orig_lower, (orig_key, val) in raw.items():
        if orig_lower == 'w' and has_nfin:
            continue   # drop w when nfin present
        new_key = key_rename.get(orig_lower, orig_key)
        if not val:
            result.append(new_key)
            continue
        if is_literal(val):
            # Build param name: <subckt_prefix><inst>_<key> if multi-subckt
            if multi_subckt:
                prefix = f"{subckt_name}_"
            else:
                prefix = ""
            param_name = f"{prefix}{inst_name}_{new_key}"
            device_params[param_name] = val
            result.append(f"{new_key}={{{param_name}}}")
        else:
            result.append(f"{new_key}={val}")
    return result


def transform_m_line(line: str, rail_map: dict, inst_name: str,
                     multi_subckt: bool, subckt_name: str,
                     device_params: dict) -> str:
    """Transform a MOSFET instance line."""
    tokens = line.split()
    if len(tokens) < 6:
        return line

    leading_ws = len(line) - len(line.lstrip())
    indent = line[:leading_ws]

    instance  = tokens[0]
    nets_dgbs = tokens[1:5]
    model_tok = tokens[5]
    kv_tokens = tokens[6:]

    # Map nets
    nets_dgbs = apply_rails_to_tokens(nets_dgbs, rail_map)

    # Map model
    new_model = MODEL_MAP.get(model_tok.lower(), model_tok)

    # Remap params
    new_kv = remap_finfet_params(
        kv_tokens, inst_name, multi_subckt, subckt_name, device_params
    )

    parts = [instance] + nets_dgbs + [new_model] + new_kv
    return indent + ' '.join(parts)


# ---------------------------------------------------------------------------
# Split-resistor handling (mimo_bulk only)
# ---------------------------------------------------------------------------
RES_SERIES_START = re.compile(r'^\*\*\s*Series configuration of\s+(\w+)', re.IGNORECASE)
RES_SERIES_END   = re.compile(r'^\*\*\s*End of\s+(\w+)', re.IGNORECASE)

RES8_SUBCKT = """\
.subckt res8 n1 n2
.param seg_r=100
r1 n1 x1 {seg_r}
r2 x1 x2 {seg_r}
r3 x2 x3 {seg_r}
r4 x3 x4 {seg_r}
r5 x4 x5 {seg_r}
r6 x5 x6 {seg_r}
r7 x6 x7 {seg_r}
r8 x7 n2 {seg_r}
.ends res8"""

RES18_SUBCKT = """\
.subckt res18 n1 n2
.param seg_r=200
r1 n1 x1 {seg_r}
r2 x1 x2 {seg_r}
r3 x2 x3 {seg_r}
r4 x3 x4 {seg_r}
r5 x4 x5 {seg_r}
r6 x5 x6 {seg_r}
r7 x6 x7 {seg_r}
r8 x7 x8 {seg_r}
r9 x8 x9 {seg_r}
r10 x9 x10 {seg_r}
r11 x10 x11 {seg_r}
r12 x11 x12 {seg_r}
r13 x12 x13 {seg_r}
r14 x13 x14 {seg_r}
r15 x14 x15 {seg_r}
r16 x15 x16 {seg_r}
r17 x16 x17 {seg_r}
r18 x17 n2 {seg_r}
.ends res18"""


def collapse_split_resistors(lines: list) -> tuple:
    """
    Detect **Series configuration of R<n> ... **End of R<n> blocks,
    replace each with a single xR<n> <a> <b> res<count> line.
    Returns (new_lines, helper_subckts_needed) where helper_subckts_needed
    is a set of subckt names like {'res8', 'res18'}.
    """
    result = []
    helpers = set()
    i = 0
    while i < len(lines):
        m = RES_SERIES_START.match(lines[i].strip())
        if m:
            res_name = m.group(1)
            segments = []
            i += 1
            while i < len(lines):
                end_m = RES_SERIES_END.match(lines[i].strip())
                if end_m:
                    i += 1
                    break
                seg_line = lines[i].strip()
                if seg_line and not seg_line.startswith('*'):
                    segments.append(seg_line.split())
                i += 1
            if segments:
                count = len(segments)
                node_a = segments[0][1]   # first segment node1
                node_b = segments[-1][2]  # last segment node2
                helper_name = f"res{count}"
                helpers.add(helper_name)
                result.append(f"x{res_name} {node_a} {node_b} {helper_name}")
        else:
            result.append(lines[i])
            i += 1
    return result, helpers


# ---------------------------------------------------------------------------
# Line preprocessing
# ---------------------------------------------------------------------------
def read_file(path: Path) -> list:
    for enc in ('utf-8', 'latin-1'):
        try:
            return path.read_text(encoding=enc).splitlines()
        except UnicodeDecodeError:
            continue
    return []


def join_continuations(lines: list) -> list:
    """Merge continuation lines (+ prefix or \\ suffix) into single logical lines."""
    result = []
    current = None
    in_continuation = False
    for line in lines:
        s = line.rstrip()
        if in_continuation:
            if s.rstrip().endswith('\\'):
                current = current + ' ' + s.rstrip()[:-1].rstrip()
            else:
                current = current + ' ' + s.rstrip()
                result.append(current)
                current = None
                in_continuation = False
        elif s.lstrip().startswith('+'):
            content = s.lstrip()[1:].lstrip()
            current = (current + ' ' + content) if current is not None else content
        elif s.rstrip().endswith('\\'):
            if current is not None:
                result.append(current)   # flush pending standalone line first
            current = s.rstrip()[:-1].rstrip()
            in_continuation = True
        else:
            if current is not None:
                result.append(current)
            current = s
    if current is not None:
        result.append(current)
    return result


def convert_comments(lines: list) -> list:
    """Convert // comments to * SPICE comments."""
    out = []
    for line in lines:
        s = line.rstrip()
        stripped = s.lstrip()
        if stripped.startswith('//'):
            indent = s[:len(s) - len(stripped)]
            out.append(indent + '* ' + stripped[2:].lstrip())
        else:
            out.append(s)
    return out


def strip_model_decls(lines: list) -> list:
    """Remove .model declarations (not needed after type remapping)."""
    return [l for l in lines if not l.lstrip().lower().startswith('.model ')]


# ---------------------------------------------------------------------------
# Main per-file transformer
# ---------------------------------------------------------------------------
def is_m_line(line: str) -> bool:
    s = line.lstrip()
    return bool(s) and s[0].lower() == 'm' and not s.lower().startswith('mimo') and len(s.split()) >= 6


def get_line_type(line: str) -> str:
    s = line.lstrip().lower()
    if not s or s.startswith('*') or s.startswith('$'):
        return 'comment'
    if s.startswith('.subckt'):
        return 'subckt'
    if s.startswith('.ends') or s.strip().lower() == '.end':
        return 'ends'
    if s.startswith('.param'):
        return 'param'
    if is_m_line(line):
        return 'mosfet'
    return 'other'


def count_subckts(lines: list) -> int:
    return sum(1 for l in lines if l.lstrip().lower().startswith('.subckt'))


def transform_file(lines: list, circuit_name: str) -> tuple:
    """
    Apply all transformations to a list of logical lines.
    Returns (transformed_lines, device_params_dict, stats_dict, device_records).
    device_records is a list of {'dev_id', 'model'} used by the numeric
    scaling pass to look up each transistor's pdk_type for clipping.
    """
    rail_map  = POWER_RAIL_MAP.get(circuit_name.lower(), {})
    multi     = count_subckts(lines) > 1
    subckt_stack = []    # stack of open subckt names
    current_subckt = ''
    device_params  = {}  # ordered param_name -> value
    device_records = []  # [{'dev_id': ..., 'model': ...}, ...]
    out_lines = []

    # Stats
    mosfet_count  = 0
    subckt_count  = 0
    model_types   = set()
    r_count = 0
    c_count = 0

    for line in lines:
        s = line.lstrip()
        ltype = get_line_type(line)

        if ltype == 'comment':
            out_lines.append(line)

        elif ltype == 'subckt':
            subckt_count += 1
            tokens = line.split()
            # tokens: ['.subckt', name, port1, port2, ...]
            name = tokens[1] if len(tokens) > 1 else ''
            subckt_stack.append(name)
            current_subckt = name
            ports = apply_rails_to_tokens(tokens[2:], rail_map)
            indent = line[:len(line) - len(line.lstrip())]
            out_lines.append(indent + ' '.join([tokens[0], name] + ports))

        elif ltype == 'ends':
            # Fix mismatched or missing name
            correct_name = subckt_stack.pop() if subckt_stack else ''
            current_subckt = subckt_stack[-1] if subckt_stack else ''
            indent = line[:len(line) - len(line.lstrip())]
            if correct_name:
                out_lines.append(indent + f'.ends {correct_name}')
            else:
                out_lines.append(indent + '.ends')

        elif ltype == 'mosfet':
            tokens = line.split()
            inst = tokens[0]
            # Extract model name for stats (position 5)
            if len(tokens) >= 6:
                orig_model = tokens[5]
                new_model  = MODEL_MAP.get(orig_model.lower(), orig_model)
                model_types.add(new_model)
                prefix = f"{current_subckt}_" if multi else ""
                device_records.append({'dev_id': f"{prefix}{inst}", 'model': new_model})
            new_line = transform_m_line(
                line, rail_map, inst, multi, current_subckt, device_params
            )
            mosfet_count += 1
            out_lines.append(new_line)

        elif ltype == 'other':
            # X-lines, R-lines, C-lines, other directives
            # Apply power rail mapping to all non-parameter tokens
            tokens = line.split()
            if tokens:
                new_tokens = apply_rails_to_tokens(tokens, rail_map)
                indent = line[:len(line) - len(line.lstrip())]
                out_lines.append(indent + ' '.join(new_tokens))
                # Count passives
                first = tokens[0].lstrip().upper()
                if first.startswith('R') and len(first) > 1:
                    r_count += 1
                elif first.startswith('C') and len(first) > 1 and not first.startswith('C_'):
                    c_count += 1
                elif first.startswith('XR') and len(first) > 2:
                    r_count += 1
                elif first.startswith('XC') and len(first) > 2:
                    c_count += 1
            else:
                out_lines.append(line)

        else:  # param lines and other directives
            out_lines.append(line)

    stats = {
        'subckts': subckt_count,
        'devices': mosfet_count,
        'types':   sorted(model_types),
        'r_count': r_count,
        'c_count': c_count,
    }
    return out_lines, device_params, stats, device_records


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------
def build_header(circuit_name: str, rel_path: str, stats: dict, *,
                 source: str = None, note: str = None,
                 scale_factor: float = None, source_L_ref: float = None) -> str:
    types_str = ' '.join(stats['types']) if stats['types'] else 'none'
    src  = source or 'ALIGN analog layout examples'
    note_line = note or 'Converted from FinFET-style to CMOS-style netlist.'
    lines = [
        '* ' + '=' * 60,
        f'* Circuit : {circuit_name}',
        f'* Source  : {src}',
        f'* File    : {rel_path}',
        '* ' + '=' * 60,
        '* Stats:',
        f'*   Subcircuits  : {stats["subckts"]}',
        f'*   Devices (M)  : {stats["devices"]}',
        f'*   Device types : {types_str}',
        f'*   Passives     : {stats["r_count"]} resistors, {stats["c_count"]} capacitors',
        f'* Note: {note_line}',
    ]
    if scale_factor is not None:
        lines.append(f'* SIZES CONVERTED {date.today().isoformat()} '
                     f'scale={scale_factor:.6g} source_L_ref={source_L_ref:.6g}um')
        lines.append('*       Device/passive sizes are scaled from the real source-netlist values')
        lines.append('*       (see marker above) -- not random placeholders.')
    else:
        lines.append('*       Device sizes are placeholders — optimizer generates new sizes.')
    lines.append('* ' + '=' * 60)
    return '\n'.join(lines)


def build_param_block(device_params: dict) -> list:
    """
    Build grouped .param lines (one line per device, all params of one device together).
    Groups params by their device name prefix (<inst> or <subckt>_<inst>).
    """
    if not device_params:
        return []

    # Group by everything before the last underscore-key
    # Param name format: [subckt_]inst_KEY where KEY is W, L, Nf, M
    from collections import OrderedDict
    groups = OrderedDict()
    for pname, pval in device_params.items():
        # Strip the trailing _KEY suffix to get device id
        for suffix in ('_W', '_L', '_Nf', '_M'):
            if pname.endswith(suffix):
                dev_id = pname[:-len(suffix)]
                break
        else:
            dev_id = pname
        if dev_id not in groups:
            groups[dev_id] = {}
        groups[dev_id][pname] = pval

    lines = ['', '* --- DEVICE PARAMETERS ---']
    for dev_id, params in groups.items():
        parts = [f'{k}={v}' for k, v in params.items()]
        lines.append('.param ' + ' '.join(parts))
    lines.append('')
    return lines


# ---------------------------------------------------------------------------
# MAGICAL format normalizer
# ---------------------------------------------------------------------------

# Spectre simulation-control keywords to drop (appear after // → * conversion)
_MAGICAL_DROP_PREFIXES = {
    'simulator', 'global', 'include', 'modelparameter', 'element',
    'outputparameter', 'designparamvals', 'primitives', 'subckts',
    'saveoptions', 'simulatoroptions',
}

_RE_TOPCKT  = re.compile(r'^(\s*)topckt(\s+.*)', re.IGNORECASE)
_RE_SUBCKT  = re.compile(r'^(\s*)subckt(\s+.*)', re.IGNORECASE)   # no leading dot
_RE_ENDS    = re.compile(r'^(\s*)ends(\b.*)', re.IGNORECASE)       # no leading dot
_RE_M_PAREN = re.compile(r'^(\s*\S+\s+)\(([^)]+)\)(.*)')
_RE_C_PDK   = re.compile(r'^(\s*)(C\S+)\s+\(([^)]+)\)\s+(cfmom\S*)\s*(.*)', re.IGNORECASE)
_RE_R_PDK   = re.compile(r'^(\s*)(R\S+)\s+\(([^)]+)\)\s+(rppolywo\S*)\s*(.*)', re.IGNORECASE)


def normalize_magical_format(lines: list) -> list:
    """
    Convert Spectre/HSPICE MAGICAL lines to standard SPICE format:
      - VI+/VI- port names → VIP/VIM
      - Drop Spectre simulation-control directives
      - topckt / bare subckt → .subckt;  bare ends → .ends
      - x-prefixed MOSFET calls (HSPICE style) → M-prefixed lines
      - Parenthesised node lists on M lines → space-separated
      - PDK capacitors (cfmom*) with parens → xC instances
      - PDK resistors (rppolywo*) with parens → xR instances
    """
    out = []
    for line in lines:
        # 7a: rename VI+/VI- port tokens
        line = line.replace('VI+', 'VIP').replace('VI-', 'VIM')

        s = line.lstrip()

        # skip empty lines and SPICE comments untouched
        if not s or s.startswith('*') or s.startswith('$'):
            out.append(line)
            continue

        # 7b: drop Spectre simulation-control lines
        first_tok = s.split()[0].lower().rstrip(':')
        if first_tok in _MAGICAL_DROP_PREFIXES:
            continue

        # 7c: normalize subcircuit delimiters
        m = _RE_TOPCKT.match(line)
        if m:
            line = m.group(1) + '.subckt' + m.group(2)
            out.append(line)
            continue

        m = _RE_SUBCKT.match(line)
        if m and not line.lstrip().startswith('.subckt'):
            line = m.group(1) + '.subckt' + m.group(2)
            out.append(line)
            continue

        m = _RE_ENDS.match(line)
        if m and not line.lstrip().startswith('.ends'):
            line = m.group(1) + '.ends' + m.group(2)
            out.append(line)
            continue

        # 7d: x-prefixed MOSFET calls (HSPICE style: x<n> d g s b <model> params)
        # Find the last non-param token; if it's in MODEL_MAP → treat as MOSFET
        if s[0].lower() == 'x':
            tokens = line.split()
            # last token with no '='
            non_kv = [t for t in tokens if '=' not in t]
            if non_kv:
                candidate = non_kv[-1].lower()
                if candidate in MODEL_MAP:
                    # Rename instance token x<name> → M<name>
                    inst = tokens[0]
                    new_inst = 'M' + inst[1:]   # strip leading x/X
                    line = line.replace(inst, new_inst, 1)
                    s = line.lstrip()

        # 7e: remove parens from M-device node lists
        if is_m_line(line):
            m = _RE_M_PAREN.match(line)
            if m:
                line = m.group(1) + m.group(2).strip() + m.group(3)

        # 7f: PDK capacitor → xC instance
        m = _RE_C_PDK.match(line)
        if m:
            indent, cname, nodes, ctype, rest = m.groups()
            line = f"{indent}x{cname} {nodes.strip()} {ctype} {rest}".rstrip()
            out.append(line)
            continue

        # 7g: PDK resistor → xR instance
        m = _RE_R_PDK.match(line)
        if m:
            indent, rname, nodes, rtype, rest = m.groups()
            line = f"{indent}x{rname} {nodes.strip()} {rtype} {rest}".rstrip()
            out.append(line)
            continue

        out.append(line)
    return out


# ---------------------------------------------------------------------------
# File finder
# ---------------------------------------------------------------------------
def find_sp_file(circuit_dir: Path, circuit_name: str) -> Path | None:
    # 1. <dir>/<name>.sp
    c = circuit_dir / f"{circuit_name}.sp"
    if c.exists():
        return c
    # 2. Any .sp in top of directory
    for f in sorted(circuit_dir.glob("*.sp")):
        return f
    # 3. Subdirectories
    for sub in sorted(circuit_dir.iterdir()):
        if sub.is_dir():
            c = sub / f"{circuit_name}.sp"
            if c.exists():
                return c
            for f in sorted(sub.glob("*.sp")):
                return f
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build_circuit_job(num: int, circuit_name: str) -> dict | None:
    """Phase 1: read + syntax-transform one ALIGN circuit. No numeric scaling, no write."""
    circuit_dir = EXAMPLES_DIR / circuit_name
    if not circuit_dir.is_dir():
        print(f"  [SKIP] Directory not found: {circuit_dir}")
        return None

    sp_file = find_sp_file(circuit_dir, circuit_name)
    if sp_file is None:
        print(f"  [SKIP] No .sp file found in {circuit_dir}")
        return None

    rel_path = sp_file.relative_to(EXAMPLES_DIR)
    print(f"  [{num:02d}] {circuit_name} <- {rel_path}")

    raw_lines = read_file(sp_file)
    lines = join_continuations(raw_lines)
    lines = convert_comments(lines)
    lines = strip_model_decls(lines)

    helper_subckts_needed = set()
    if circuit_name.lower() == 'mimo_bulk':
        lines, helper_subckts_needed = collapse_split_resistors(lines)

    out_lines, device_params, stats, device_records = transform_file(lines, circuit_name)

    return {
        'family': 'a',
        'out_name': f"a{num:02d}_{circuit_name}.sp",
        'circuit_name': circuit_name,
        'rel_path': str(rel_path),
        'source': None,
        'note': None,
        'out_lines': out_lines,
        'device_params': device_params,
        'device_records': device_records,
        'stats': stats,
        'helper_subckts_needed': helper_subckts_needed,
        'log_prefix': f"[{num:02d}] {circuit_name}",
    }


def build_magical_job(num: int, name: str, filename: str) -> dict | None:
    """Phase 1: read + syntax-transform one MAGICAL circuit. No numeric scaling, no write."""
    sp_file = MAGICAL_DIR / filename
    if not sp_file.exists():
        print(f"  [SKIP] Not found: {sp_file}")
        return None

    print(f"  [m{num:02d}] {name} <- MAGICALexamples/{filename}")

    raw_lines = read_file(sp_file)
    lines = join_continuations(raw_lines)
    lines = convert_comments(lines)
    lines = normalize_magical_format(lines)
    lines = strip_model_decls(lines)

    out_lines, device_params, stats, device_records = transform_file(lines, name)

    return {
        'family': 'm',
        'out_name': f"m{num:02d}_{name}.sp",
        'circuit_name': name,
        'rel_path': f"MAGICALexamples/{filename}",
        'source': 'MAGICAL analog layout examples',
        'note': 'Converted from Spectre/HSPICE format to ALIGN SPICE format.',
        'out_lines': out_lines,
        'device_params': device_params,
        'device_records': device_records,
        'stats': stats,
        'helper_subckts_needed': set(),
        'log_prefix': f"[m{num:02d}] {name}",
    }


def compute_family_scale_factor(jobs: list) -> tuple:
    """
    Population scale factor for one source-technology family (plan section 1):
    scale = gpdk090_L_min / percentile(all *_L values in the family).
    Returns (scale_factor, percentile_L_um).
    """
    Ls = []
    for job in jobs:
        model_by_dev = {r['dev_id']: r['model'] for r in job['device_records']}
        for pname, pval in job['device_params'].items():
            if not pname.endswith('_L'):
                continue
            dev_id = pname[:-2]
            if model_by_dev.get(dev_id) not in DEVICE_CONSTRAINTS:
                continue
            v = parse_length_um(pval)
            if v is not None:
                Ls.append(v)
    if not Ls:
        return 1.0, GPDK_L_MIN_TRANSISTOR
    p = percentile(Ls, SCALE_PERCENTILE)
    return compute_scale_factor(p), p


def already_converted(out_path: Path) -> bool:
    if not out_path.exists():
        return False
    return bool(CONVERSION_MARKER_RE.search(out_path.read_text(encoding='utf-8', errors='ignore')))


def write_job(job: dict, scale_factor: float, source_L_ref: float) -> bool:
    """Phase 2: apply the numeric scaling pass (sections 1-6) and write the .sp file."""
    out_path = OUTPUT_DIR / job['out_name']
    if already_converted(out_path):
        print(f"  {job['log_prefix']}: [SKIP] {job['out_name']} already carries a "
              f"SIZES CONVERTED marker -- refusing to re-run.")
        return False

    device_params = dict(job['device_params'])
    scale_transistor_params(device_params, job['device_records'], scale_factor)
    out_lines = scale_passives(job['out_lines'], job['family'], scale_factor, device_params)

    param_block = build_param_block(device_params)
    header = build_header(
        job['circuit_name'], job['rel_path'], job['stats'],
        source=job['source'], note=job['note'],
        scale_factor=scale_factor, source_L_ref=source_L_ref,
    )

    helper_text = ''
    helper_subckts_needed = job['helper_subckts_needed']
    if helper_subckts_needed:
        parts = []
        if 'res8' in helper_subckts_needed:
            parts.append(helper_subckt_text(RES8_SUBCKT, 100.0))
        if 'res18' in helper_subckts_needed:
            parts.append(helper_subckt_text(RES18_SUBCKT, 200.0))
        if parts:
            helper_text = '\n* --- HELPER SUBCKTS (split-resistor wrappers) ---\n' + \
                          '\n\n'.join(parts) + '\n'

    out_path = OUTPUT_DIR / job['out_name']
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        if param_block:
            f.write('\n'.join(param_block) + '\n')
        if helper_text:
            f.write(helper_text + '\n')
        if param_block or helper_text:
            f.write('\n* --- CIRCUIT DEFINITION ---\n')
        for line in out_lines:
            f.write(line + '\n')

    stats = job['stats']
    print(f"         -> {job['out_name']}  "
          f"(M={stats['devices']}, subckts={stats['subckts']}, "
          f"types={stats['types']}, R={stats['r_count']}, C={stats['c_count']})")
    return True


def main():
    print(f"ALIGN Netlist Converter")
    print(f"Examples dir : {EXAMPLES_DIR}")
    print(f"Output dir   : {OUTPUT_DIR}")
    print()

    a_jobs = []
    for num, name in CIRCUIT_LIST:
        job = build_circuit_job(num, name)
        if job:
            a_jobs.append(job)

    print(f"\nMAGICAL Netlist Converter")
    print(f"MAGICAL dir  : {MAGICAL_DIR}")
    print()
    m_jobs = []
    for num, name, filename in MAGICAL_CIRCUIT_LIST:
        job = build_magical_job(num, name, filename)
        if job:
            m_jobs.append(job)

    scale_a, Lref_a = compute_family_scale_factor(a_jobs)
    scale_m, Lref_m = compute_family_scale_factor(m_jobs)
    print(f"\nNumeric scaling: a-family scale={scale_a:.6g} "
          f"(p{SCALE_PERCENTILE:g} source L={Lref_a:.6g}um)")
    print(f"Numeric scaling: m-family scale={scale_m:.6g} "
          f"(p{SCALE_PERCENTILE:g} source L={Lref_m:.6g}um)")
    print()

    ok = 0
    skip = 0
    for job in a_jobs:
        if write_job(job, scale_a, Lref_a):
            ok += 1
        else:
            skip += 1
    for job in m_jobs:
        if write_job(job, scale_m, Lref_m):
            ok += 1
        else:
            skip += 1

    print(f"\nDone: {ok} converted, {skip} skipped.")


if __name__ == '__main__':
    main()
