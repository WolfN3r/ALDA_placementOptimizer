# lib/ - Technology Library Files

Technology definition for gpdk090 (Cadence Generic PDK 90nm), split into three files that mirror how professional PDKs organize their data.

## File Structure

```
lib/
├── gpdk090_tech_simple.json      Routing technology (LEF equivalent)
├── gpdk090_device_rules.json     Device rules & DRC (DRC deck equivalent)
├── gpdk090_gds_layers.json       GDS layer map (layer map file equivalent)
├── generation_config.json        Block generation parameters (design-specific)
└── README.md                     This file
```

## File Descriptions

### gpdk090_tech_simple.json - Routing Technology

**Professional equivalent:** Tech LEF (.tlef) file

Contains everything a router needs:
- `technology_info` - Manufacturing grid (0.005 um), database units, name
- `metal_layers` (M1-M7) - Width, spacing, area, pitch, end-of-line spacing, minstep, direction, spacing tables, GDS layer numbers
- `via_layers` (VIA1-VIA6) - Size, spacing, enclosure rules
- `via_definitions` - Named via geometries with H/V/stretched variants (like LEF VIA blocks)
- `via_generation_rules` - Parameterized via arrays (like LEF VIARULE GENERATE)
- `routing_widths` - Signal/power wire width and via cut tables
- `routing_grid` - Routing track pitch and offset

### gpdk090_device_rules.json - Device Rules & Pre-DRC

**Professional equivalent:** DRC deck (Calibre/Assura/PVS) + device model parameters

Contains everything needed for block generation and placement validation:
- `device_constraints` - L/W manufacturing bounds per device type (from DRM)
- `physical_design_rules` - Poly, active, contact rules for transistor layout
- `inter_device_spacing_matrix` - Spacing between device types (includes well + guard ring)
- `well_rules` - N-well/P-well dimensions and spacing
- `implant_rules` - N+/P+ implant rules
- `guard_ring_rules` - Substrate/well tap dimensions
- `pre_drc_checks` - Quick validation checks for placement

### gpdk090_gds_layers.json - GDS Layer Map

**Professional equivalent:** Layer mapping file (streamOut map)

Contains the complete GDS-II layer number assignments:
- All 33 layers: well, active, implant, threshold, poly, contact, metals (M1-M10), vias (VIA1-VIA9), markers
- Each layer has: GDS layer number, datatype, purpose description, category
- `device_layer_stacks` - Which layers compose each device type (for GDS export)

### generation_config.json - Generation Parameters

**Not a PDK file** - design-specific configuration for block generation.

Contains soft constraints that vary per design (vs. hard DRM limits in device_rules):
- Transistor sizing ranges (narrower than DRM limits)
- Multiplier/finger ranges
- Aspect ratio bounds
- Netlist density and pin count
- Rotation variant probabilities
- Symmetry pair probabilities

## How Scripts Load These Files

Scripts that need technology data load **both** the tech and device rules files and merge them:

```python
with open(lib_dir / "gpdk090_tech_simple.json", 'r') as f:
    tech_data = json.load(f)
with open(lib_dir / "gpdk090_device_rules.json", 'r') as f:
    device_rules = json.load(f)
tech_file = {**tech_data, **device_rules}
```

The merged dict is backward-compatible with all existing function signatures.

## What Changed From the Old Single-File Structure

The original `gpdk090_tech_simple.json` was a monolithic file containing all routing rules, device constraints, and DRC rules. It has been split into three purpose-specific files:

| Old location (single file) | New file |
|---|---|
| `technology_info` | `gpdk090_tech_simple.json` |
| `metal_layers`, `via_layers` | `gpdk090_tech_simple.json` (enhanced with EOL, minstep, pitch, spacing tables) |
| `routing_widths`, `routing_grid` | `gpdk090_tech_simple.json` (enhanced with wire width/via cut tables from MAGICAL Params.py) |
| `wide_metal_spacing_rules` | `gpdk090_tech_simple.json` -> `spacing_table` within each metal layer |
| `device_constraints` | `gpdk090_device_rules.json` |
| `physical_design_rules` | `gpdk090_device_rules.json` |
| `inter_device_spacing_matrix` | `gpdk090_device_rules.json` |
| *(not present)* | `gpdk090_device_rules.json` -> `well_rules`, `implant_rules`, `guard_ring_rules`, `pre_drc_checks` |
| GDS layer numbers (embedded) | `gpdk090_gds_layers.json` (standalone, all layers including well/implant/threshold) |
| *(not present)* | `gpdk090_tech_simple.json` -> `via_definitions`, `via_generation_rules` |

### New fields added (based on LEF standard and MAGICAL mockPDK analysis)

**In gpdk090_tech_simple.json:**
- `database_units_per_micron` - explicit resolution (LEF DATABASE MICRONS)
- `pitch` per metal layer - routing track pitch
- `eol_spacing`, `eol_within` - end-of-line spacing rules
- `minstep`, `minstep_maxedges` - minimum jog/step rules
- `spacing_table` per metal layer - width-dependent spacing (replaces old `wide_metal_spacing_rules`)
- `via_definitions` - 14 named vias with geometry for H/V orientations
- `via_generation_rules` - 6 parameterized via array rules (VIARULE GENERATE)
- `wire_width_tables`, `via_cuts_tables` - from MAGICAL Params.py

**In gpdk090_device_rules.json:**
- `well_rules` - N-well/P-well dimensions
- `implant_rules` - N+/P+ implant rules
- `guard_ring_rules` - substrate/well tap dimensions
- `pre_drc_checks` - quick validation check definitions

**In gpdk090_gds_layers.json:**
- 33 layers (vs. only M1-M7 + VIA1-VIA6 previously embedded)
- Layer categories and purposes
- `device_layer_stacks` - layer composition per device type

## Comparison with Professional PDK File Types

| Professional PDK file | Our JSON equivalent | Status |
|---|---|---|
| Tech LEF (.tlef) | `gpdk090_tech_simple.json` | Covered |
| DRC deck (Calibre) | `gpdk090_device_rules.json` | Simplified subset |
| Layer map (stream) | `gpdk090_gds_layers.json` | Covered |
| Cell LEF (.lef) | N/A - blocks are generated | Not applicable |
| SPICE models (.lib) | `device_constraints` (thin slice) | Minimal |
| Liberty (.lib) | N/A | Not applicable for analog |
| PEX/QRC | `resistance_per_sq`, `thickness` | Minimal |
| Antenna rules | Not included | Future |
| Density rules | Not included | Future |
