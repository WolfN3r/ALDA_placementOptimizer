#!/usr/bin/env python3
"""
gen_tech_files.py — Generate MAGICAL / ANAROUTE tech files from gpdk090_tech_simple.json.

Produces three files required by transponder201.py:
  techfile.simple  — parsed by magicalFlow.parseSimpleTechFile()
  myPDK.techfile   — parsed by anaroutePy.parseTechfile()
  myPDK.lef        — parsed by anaroutePy.parseLef()

Usage:
  python3 lib/gen_tech_files.py lib/gpdk090_tech_simple.json /tmp/gpdk090_tech/
  python3 lib/gen_tech_files.py lib/gpdk090_tech_simple.json /tmp/gpdk090_wide_tech/

The output directory is created if it does not exist.
"""

import json
import os
import sys


# ---------------------------------------------------------------------------
# mockPDK "device" layers that MAGICAL requires for basic circuit setup.
# These are interleaved with the routing layers in ASCENDING GDS number order.
# In mockPDK (M1=31) they all fall before M1.  For gpdk090 (M1=7) they
# are interleaved: NW(3) and OD(6) come before M1(7), the rest after.
#
# NOTE: build_magical_db() now uses tDB.layerNameToIdx('M1') to find M1's
# ordinal index dynamically, so M1 does NOT need to be at index 10.
# ---------------------------------------------------------------------------
MOCK_BASE_LAYERS = [
    ("NW",     3),
    ("OD",     6),
    ("VTL_N", 12),
    ("VTL_P", 13),
    ("PO",    17),
    ("OD_25", 18),
    ("PP",    25),
    ("NP",    26),
    ("RPO",   29),
    # CO (contact) not included: gpdk090 GDS 6 is used by OD and there is
    # no safe fixed number that avoids all gpdk090 metal/via conflicts.
    # Our transponder does not use CO (no MAGICAL device generation).
]


def generate_tech_files(gpdk_json_path, output_dir):
    """
    Read gpdk090_tech_simple.json and write three tech files to output_dir.

    Returns dict with paths to the three generated files:
      {'techfile_simple': ..., 'techfile': ..., 'lef': ...}
    """
    with open(gpdk_json_path) as f:
        tech = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    output_dir = output_dir.rstrip('/') + '/'

    metals = tech['metal_layers']
    vias   = tech['via_layers']

    # Ordered metal layer names (M1 first)
    metal_names = [k for k in metals if not k.startswith('_')]
    via_names   = [k for k in vias   if not k.startswith('_')]

    # -----------------------------------------------------------------------
    # 1. techfile.simple — for magicalFlow.parseSimpleTechFile()
    #    Format: one "NAME    GDS_LAYER" pair per line (whitespace separated)
    #    TechDB requires ASCENDING GDS layer numbers — merge all layer
    #    sources (base + metals + vias) and sort by GDS number.
    # -----------------------------------------------------------------------
    simple_path = output_dir + 'techfile.simple'

    # Build combined layer list: (name, gds_number)
    all_layers = list(MOCK_BASE_LAYERS)
    for name in metal_names:
        all_layers.append((name, metals[name]['gds_layer']))
    for name in via_names:
        all_layers.append((name, vias[name]['gds_layer']))

    # Check for GDS number conflicts (two layers with same GDS number)
    from collections import Counter
    gds_counts = Counter(gds for _, gds in all_layers)
    conflicts = {gds for gds, cnt in gds_counts.items() if cnt > 1}
    if conflicts:
        # Remove conflicting base layers (keep routing layers)
        routing_names = set(metal_names) | set(via_names)
        all_layers = [(n, g) for n, g in all_layers
                      if g not in conflicts or n in routing_names]

    # Sort by GDS number (required by TechDB)
    all_layers.sort(key=lambda x: x[1])

    with open(simple_path, 'w') as f:
        for name, gds in all_layers:
            f.write(f"{name:<16}{gds}\n")
    print(f"[gen_tech_files] Wrote techfile.simple: {simple_path} "
          f"({len(all_layers)} layers, M1=GDS{metals['M1']['gds_layer']})")

    # -----------------------------------------------------------------------
    # 2. myPDK.techfile — for anaroutePy.parseTechfile()
    #    Format: techLayers( … ) section listing routing layers and their GDS numbers.
    # -----------------------------------------------------------------------
    techfile_path = output_dir + 'myPDK.techfile'
    with open(techfile_path, 'w') as f:
        f.write("techLayers(\n")
        f.write(" ;( techLayer       number  abbreviation     )\n")
        f.write(" ;( ---------       ------  ------------     )\n")
        # Reference layers from the base set (OD, PO always present)
        base_dict = dict(MOCK_BASE_LAYERS)
        f.write(f"  ( OD              {base_dict['OD']:<6} OD               )\n")
        f.write(f"  ( PO              {base_dict['PO']:<6} PO               )\n")
        for name in metal_names:
            gds = metals[name]['gds_layer']
            f.write(f"  ( {name:<15} {gds:<6} {name:<16} )\n")
        for name in via_names:
            gds = vias[name]['gds_layer']
            f.write(f"  ( {name:<15} {gds:<6} {name:<16} )\n")
        f.write(")\n")
    print(f"[gen_tech_files] Wrote myPDK.techfile:   {techfile_path}")

    # -----------------------------------------------------------------------
    # 3. myPDK.lef — for anaroutePy.parseLef()
    #    Standard LEF 5.8 format with LAYER and VIA sections.
    # -----------------------------------------------------------------------
    lef_path = output_dir + 'myPDK.lef'

    # Build preferred direction map (alternate H/V by layer index)
    pref_dir = {}
    for i, name in enumerate(metal_names):
        d = metals[name].get('preferred_direction', 'HORIZONTAL').upper()
        pref_dir[name] = d

    with open(lef_path, 'w') as f:
        f.write("VERSION 5.8 ;\n")
        f.write('BUSBITCHARS "[]" ;\n')
        f.write('DIVIDERCHAR "/" ;\n\n')
        f.write("UNITS\n")
        f.write("  CAPACITANCE PICOFARADS 1 ;\n")
        # Use 2000 database units per micron (0.5nm precision) — same as mockPDK.
        # ANAROUTE asserts pin coords % 10 == 0 or 8; with 2000 units/µm a
        # 0.005µm grid gives 10-unit steps, satisfying the alignment check.
        f.write("  DATABASE MICRONS 2000 ;\n")
        f.write("END UNITS\n\n")
        f.write("MANUFACTURINGGRID 0.005 ;\n\n")

        # Non-routing base layers
        f.write("LAYER PO\n  TYPE MASTERSLICE ;\nEND PO\n\n")
        f.write("LAYER CO\n  TYPE CUT ;\nEND CO\n\n")

        for i, name in enumerate(metal_names):
            m = metals[name]
            w  = m['min_width']
            sp = m['min_spacing']
            d  = pref_dir[name]
            # Routing-model pitch: use half the DRC minimum spacing so ANAROUTE's
            # global router has more track options.  The reduced spacing is stored in
            # sp_r for all LEF SPACING / SPACINGTABLE fields; this makes the routing
            # model denser without changing the physical design-rule numbers stored
            # in gpdk090_tech_simple.json.
            sp_r  = sp * 0.5           # half the DRC min_spacing (routing model only)
            pitch = w + sp_r           # finer pitch → more tracks available
            f.write(f"LAYER {name}\n")
            f.write(f"  TYPE ROUTING ;\n")
            # LEF only accepts HORIZONTAL or VERTICAL.  'ANY'/'BOTH' fall back to
            # HORIZONTAL; Anaroute treats this as a soft hint and still uses the
            # layer in both orientations.
            lef_dir = d if d in ('HORIZONTAL', 'VERTICAL') else 'HORIZONTAL'
            f.write(f"  DIRECTION {lef_dir} ;\n")
            f.write(f"  PITCH {pitch:.3f} {pitch:.3f} ;\n")
            f.write(f"  WIDTH {w:.3f} ;\n")
            area = m.get('min_area', round(w * w, 4))
            f.write(f"  AREA {area:.4f} ;\n")
            f.write(f"  SPACINGTABLE\n")
            f.write(f"    PARALLELRUNLENGTH 0\n")
            f.write(f"    WIDTH 0    {sp_r:.3f}\n")
            f.write(f"    WIDTH 0.15 {sp_r:.3f} ;\n")
            f.write(f"  SPACING {sp_r:.3f} ENDOFLINE {sp_r:.3f} WITHIN {sp_r/2:.3f} ;\n")
            f.write(f"END {name}\n\n")

            # Add via cut layer right after each metal (except last)
            via_name = f"VIA{i+1}"
            if via_name in vias and i < len(metal_names) - 1:
                v = vias[via_name]
                via_sp = v.get('min_spacing', sp)
                f.write(f"LAYER {via_name}\n")
                f.write(f"  TYPE CUT ;\n")
                f.write(f"  SPACING {via_sp:.3f} ;\n")
                f.write(f"  WIDTH {v['size']:.3f} ;\n")
                f.write(f"END {via_name}\n\n")

        # Named VIA cells (one per metal transition in each orientation)
        via_cell_idx = 0
        for i, vname in enumerate(via_names):
            v = vias[vname]
            lower_metal = v['connects'][0]   # e.g. "M1"
            upper_metal = v['connects'][1]   # e.g. "M2"
            lo_m = metals[lower_metal]
            hi_m = metals[upper_metal]
            lo_w = lo_m['min_width']
            hi_w = hi_m['min_width']
            via_size = v['size']
            enc_lo = v.get('enclosure_by_lower', 0.06)
            enc_hi = v.get('enclosure_by_upper', 0.005)
            enc_lo2 = v.get('enclosure_by_lower_two_sides', 0.06)
            enc_hi2 = v.get('enclosure_by_upper_two_sides', 0.06)
            half = via_size / 2.0

            # HV orientation: lower is horizontal, upper is vertical
            lo_dir = pref_dir[lower_metal]
            hi_dir = pref_dir[upper_metal]

            for orient in ['HV', 'VH']:
                # For HV: lower metal extends wider in Y (horizontal preferred)
                if orient == 'HV':
                    lo_ext_h = max(enc_lo2, half)   # long axis of lower
                    lo_ext_v = max(enc_lo, half)
                    hi_ext_h = max(enc_hi, half)
                    hi_ext_v = max(enc_hi2, half)   # long axis of upper
                else:
                    lo_ext_h = max(enc_lo, half)
                    lo_ext_v = max(enc_lo2, half)
                    hi_ext_h = max(enc_hi2, half)
                    hi_ext_v = max(enc_hi, half)
                cell_name = f"{vname}_{via_cell_idx}_{orient}"
                is_default = " DEFAULT" if orient == 'HV' else ""
                f.write(f"VIA {cell_name}{is_default} \n")
                f.write(f"    LAYER {lower_metal} ;\n")
                f.write(f"        RECT {-lo_ext_h:.6f} {-lo_ext_v:.6f} "
                        f"{lo_ext_h:.6f} {lo_ext_v:.6f} ;\n")
                f.write(f"    LAYER {vname} ;\n")
                f.write(f"        RECT {-half:.6f} {-half:.6f} {half:.6f} {half:.6f} ;\n")
                f.write(f"    LAYER {upper_metal} ;\n")
                f.write(f"        RECT {-hi_ext_h:.6f} {-hi_ext_v:.6f} "
                        f"{hi_ext_h:.6f} {hi_ext_v:.6f} ;\n")
                f.write(f"END {cell_name}\n\n")
                via_cell_idx += 1

        # VIAG generate rules (one per metal pair)
        for i, vname in enumerate(via_names):
            v = vias[vname]
            lower_metal = v['connects'][0]
            upper_metal = v['connects'][1]
            lo_m = metals[lower_metal]
            hi_m = metals[upper_metal]
            via_size = v['size']
            enc_lo = max(v.get('enclosure_by_lower', 0.03), 0.03)
            enc_hi = max(v.get('enclosure_by_upper', 0.03), 0.03)
            via_sp = v.get('min_spacing', 0.14)
            half = via_size / 2.0

            f.write(f"VIARULE VIAG{i+1}{i+2} GENERATE\n")
            f.write(f"  LAYER {lower_metal} ;\n")
            f.write(f"    ENCLOSURE {enc_lo:.3f} 0 ;\n")
            f.write(f"    WIDTH {lo_m['min_width']:.3f} TO 4.50 ;\n")
            f.write(f"  LAYER {upper_metal} ;\n")
            f.write(f"    ENCLOSURE {enc_hi:.3f} 0 ;\n")
            f.write(f"    WIDTH {hi_m['min_width']:.3f} TO 4.50 ;\n")
            f.write(f"  LAYER {vname} ;\n")
            f.write(f"    RECT {-half:.3f} {-half:.3f} {half:.3f} {half:.3f} ;\n")
            f.write(f"    SPACING {via_sp:.3f} BY {via_sp:.3f} ;\n")
            f.write(f"END VIAG{i+1}{i+2}\n\n")

        f.write("SITE CoreSite\n  CLASS CORE ;\n  SIZE 0.2 BY 1.71 ;\nEND CoreSite\n\n")
        f.write("END LIBRARY\n")

    print(f"[gen_tech_files] Wrote myPDK.lef:         {lef_path}")

    return {
        'techfile_simple': simple_path,   # techfile.simple
        'techfile':        techfile_path, # myPDK.techfile
        'lef':             lef_path,      # myPDK.lef
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: python3 {sys.argv[0]} <gpdk090_tech_simple.json> <output_dir>")
        sys.exit(1)
    result = generate_tech_files(sys.argv[1], sys.argv[2])
    print("\nGenerated files:")
    for k, v in result.items():
        size = os.path.getsize(v)
        print(f"  {k}: {v} ({size} bytes)")
