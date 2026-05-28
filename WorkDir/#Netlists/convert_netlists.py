#!/usr/bin/env python3
"""
convert_netlists.py
Converts ALIGN FinFET example netlists to CMOS-style netlists.

Run from any location; paths are resolved relative to this script.
Output: examples/#Netlists/a<XY>_<circuit_name>.sp
"""
import re
import sys
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
    Returns (transformed_lines, device_params_dict, stats_dict).
    """
    rail_map  = POWER_RAIL_MAP.get(circuit_name.lower(), {})
    multi     = count_subckts(lines) > 1
    subckt_stack = []    # stack of open subckt names
    current_subckt = ''
    device_params  = {}  # ordered param_name -> value
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
    return out_lines, device_params, stats


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------
def build_header(circuit_name: str, rel_path: str, stats: dict, *,
                 source: str = None, note: str = None) -> str:
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
        '*       Device sizes are placeholders — optimizer generates new sizes.',
        '* ' + '=' * 60,
    ]
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
def convert_circuit(num: int, circuit_name: str) -> bool:
    circuit_dir = EXAMPLES_DIR / circuit_name
    if not circuit_dir.is_dir():
        print(f"  [SKIP] Directory not found: {circuit_dir}")
        return False

    sp_file = find_sp_file(circuit_dir, circuit_name)
    if sp_file is None:
        print(f"  [SKIP] No .sp file found in {circuit_dir}")
        return False

    rel_path = sp_file.relative_to(EXAMPLES_DIR)
    print(f"  [{num:02d}] {circuit_name} <- {rel_path}")

    # Read and preprocess
    raw_lines = read_file(sp_file)
    lines = join_continuations(raw_lines)
    lines = convert_comments(lines)
    lines = strip_model_decls(lines)

    # Special: collapse split resistors (mimo_bulk)
    helper_subckts_needed = set()
    if circuit_name.lower() == 'mimo_bulk':
        lines, helper_subckts_needed = collapse_split_resistors(lines)

    # Transform
    out_lines, device_params, stats = transform_file(lines, circuit_name)

    # Build param block
    param_block = build_param_block(device_params)

    # Build header
    header = build_header(circuit_name, str(rel_path), stats)

    # Assemble helper subckts for mimo_bulk
    helper_text = ''
    if helper_subckts_needed:
        parts = []
        if 'res8'  in helper_subckts_needed:
            parts.append(RES8_SUBCKT)
        if 'res18' in helper_subckts_needed:
            parts.append(RES18_SUBCKT)
        if parts:
            helper_text = '\n* --- HELPER SUBCKTS (split-resistor wrappers) ---\n' + \
                          '\n\n'.join(parts) + '\n'

    # Write output
    out_name = f"a{num:02d}_{circuit_name}.sp"
    out_path  = OUTPUT_DIR / out_name

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

    print(f"         -> {out_name}  "
          f"(M={stats['devices']}, subckts={stats['subckts']}, "
          f"types={stats['types']}, R={stats['r_count']}, C={stats['c_count']})")
    return True


def convert_magical_circuit(num: int, name: str, filename: str) -> bool:
    sp_file = MAGICAL_DIR / filename
    if not sp_file.exists():
        print(f"  [SKIP] Not found: {sp_file}")
        return False

    print(f"  [m{num:02d}] {name} <- MAGICALexamples/{filename}")

    raw_lines = read_file(sp_file)
    lines = join_continuations(raw_lines)
    lines = convert_comments(lines)
    lines = normalize_magical_format(lines)
    lines = strip_model_decls(lines)

    out_lines, device_params, stats = transform_file(lines, name)
    param_block = build_param_block(device_params)
    header = build_header(
        name, f"MAGICALexamples/{filename}", stats,
        source='MAGICAL analog layout examples',
        note='Converted from Spectre/HSPICE format to ALIGN SPICE format.',
    )

    out_name = f"m{num:02d}_{name}.sp"
    out_path  = OUTPUT_DIR / out_name
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        if param_block:
            f.write('\n'.join(param_block) + '\n')
            f.write('\n* --- CIRCUIT DEFINITION ---\n')
        for line in out_lines:
            f.write(line + '\n')

    print(f"         -> {out_name}  "
          f"(M={stats['devices']}, subckts={stats['subckts']}, "
          f"types={stats['types']}, R={stats['r_count']}, C={stats['c_count']})")
    return True


def main():
    print(f"ALIGN Netlist Converter")
    print(f"Examples dir : {EXAMPLES_DIR}")
    print(f"Output dir   : {OUTPUT_DIR}")
    print()

    ok = 0
    skip = 0
    for num, name in CIRCUIT_LIST:
        result = convert_circuit(num, name)
        if result:
            ok += 1
        else:
            skip += 1

    print(f"\nMAGICAL Netlist Converter")
    print(f"MAGICAL dir  : {MAGICAL_DIR}")
    print()
    for num, name, filename in MAGICAL_CIRCUIT_LIST:
        result = convert_magical_circuit(num, name, filename)
        if result:
            ok += 1
        else:
            skip += 1

    print(f"\nDone: {ok} converted, {skip} skipped.")


if __name__ == '__main__':
    main()
