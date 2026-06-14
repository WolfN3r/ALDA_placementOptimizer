#!/usr/bin/env python3
"""
Stage 201 — Analog route placement using MAGICAL Anaroute.

Takes py101 JSON (blocks + netlist + placement with M1 pin rectangles),
sends the design to MAGICAL Anaroute via Docker, and returns py201 JSON
where each net in netlist.nets[] gains 'route_segments' and 'route_status'.

Standalone:  python 201_routingOptimizer.py input_py101.json  →  writes *_py201.json
n8n mode:    reads JSON from stdin, writes JSON to stdout
"""

# =============================================================================
# 1. IMPORTS  (stdlib → third-party → local lib)
# =============================================================================
import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from log_setup import get_logger
from magical_transponder import (
    convert_py101_to_magical,
    run_magical_routing,
    build_py201_nets,
)

# =============================================================================
# 2. CONSTANTS  (ALL hardcoded values live here — never inside functions)
# =============================================================================
DEBUG = False

SIGNAL_WIDTH_NM      = 120      # default signal wire width (nm)
POWER_WIDTH_NM       = 200      # default power wire width (nm)
ROUTING_MODE         = 'combined'  # 'combined' (default) or 'isolated'
FALLBACK_TO_ISOLATED = False     # run isolated analysis when combined fails
OUTPUT_FORMAT        = 'json'    # 'json' | 'gds' | 'both'
DOCKER_IMAGE         = 'magical_szaboga1_dev_wmi:latest'

# Auto-detected from script location: WorkDir/myPDK/gpdk090_tech_simple.json
_SCRIPT_DIR = Path(__file__).parent
_PDK_DIR    = _SCRIPT_DIR.parent / 'myPDK'
PDK_DIR     = str(_PDK_DIR)

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def _find_pdk_tech_json(pdk_dir: str) -> str:
    """Find the routing tech JSON in pdk_dir by scanning for *_tech_simple.json."""
    matches = sorted(Path(pdk_dir).glob('*_tech_simple.json'))
    if not matches:
        raise FileNotFoundError(
            f"No *_tech_simple.json found in PDK dir: {pdk_dir}")
    if len(matches) > 1:
        logger.warning(f"Multiple tech JSONs found in {pdk_dir}, using: {matches[0].name}")
    return str(matches[0])


def route(data: dict,
          routing_mode: str = ROUTING_MODE,
          fallback_to_isolated: bool = FALLBACK_TO_ISOLATED,
          signal_width_nm: int = SIGNAL_WIDTH_NM,
          power_width_nm: int = POWER_WIDTH_NM,
          output_format: str = OUTPUT_FORMAT,
          pdk_dir: str = PDK_DIR,
          output_dir: str | None = None,
          container_name: str | None = None) -> dict:
    """
    Run Anaroute on the py101 placement and return py201 JSON.

    The returned dict is a deep copy of the input with:
    - netlist.nets[*].route_segments  added
    - netlist.nets[*].route_status    added
    - placement.routing               added (metadata)
    """
    pdk_tech_json = _find_pdk_tech_json(pdk_dir)
    logger.info(f"PDK tech: {pdk_tech_json}")

    # Convert py101 → MAGICAL-ready format
    magical_input = convert_py101_to_magical(data)
    logger.info(f"Converted {len(magical_input['placed_blocks'])} placed blocks "
                f"and {len(magical_input['netlist']['nets'])} nets")

    # Run MAGICAL routing (Docker-based)
    t0 = time.time()
    try:
        route_data = run_magical_routing(
            magical_input    = magical_input,
            pdk_tech_json    = pdk_tech_json,
            routing_mode     = routing_mode,
            signal_width_nm  = signal_width_nm,
            power_width_nm   = power_width_nm,
            output_dir       = output_dir,
            container_name   = container_name,
        )
    except Exception as e:
        logger.error(f"MAGICAL routing failed: {e}")
        raise

    t_total = time.time() - t0
    logger.info(f"Routing complete in {t_total:.1f}s: "
                f"{route_data.get('routed', '?')} routed, "
                f"{route_data.get('unrouted', '?')} unrouted")

    # Trigger isolated fallback if combined had unrouted nets
    if (fallback_to_isolated and routing_mode == 'combined'
            and route_data.get('unrouted', 0) > 0):
        logger.warning(f"Combined mode left {route_data['unrouted']} unrouted nets — "
                       f"running isolated analysis ...")
        try:
            iso_data = run_magical_routing(
                magical_input    = magical_input,
                pdk_tech_json    = pdk_tech_json,
                routing_mode     = 'isolated',
                signal_width_nm  = signal_width_nm,
                power_width_nm   = power_width_nm,
                output_dir       = output_dir,
                container_name   = container_name,
            )
            # Attach isolated segments to unrouted nets in route_data
            iso_by_id = {n['net_id']: n for n in iso_data.get('nets', [])}
            for net in route_data.get('nets', []):
                if net.get('status') == 'unrouted' and net['net_id'] in iso_by_id:
                    net['segments_isolated'] = iso_by_id[net['net_id']].get('segments', [])
        except Exception as e:
            logger.warning(f"Isolated fallback failed: {e}")

    # Build py201 output
    output = copy.deepcopy(data)
    updated_nets, routing_meta = build_py201_nets(
        data, route_data, fallback_isolated=fallback_to_isolated
    )
    output['netlist']['nets'] = updated_nets
    output['placement']['routing'] = routing_meta

    if output_format in ('gds', 'both'):
        gds_path = route_data.get('route_gds_path')
        if gds_path:
            output['placement']['routing']['route_gds_path'] = gds_path
            logger.info(f"Route GDS: {gds_path}")

    return output


# =============================================================================
# 5. n8n / ENTRY POINT
# =============================================================================

def run(data: dict, **kwargs) -> dict:
    """Entry point called by main.py pipeline."""
    # Propagate any CLI-level overrides passed as kwargs
    return route(data, **{k: v for k, v in kwargs.items() if v is not None})


def process(data: dict) -> dict:
    """n8n entry point — validates input then delegates to route()."""
    if 'placement' not in data:
        raise KeyError("process: input JSON missing 'placement'")
    placement = data.get('placement', {})
    has_placed = (
        'placed_blocks' in placement
        or any(r.get('placed_blocks') for r in placement.get('runs', []))
    )
    if not has_placed:
        raise KeyError("process: placement.placed_blocks missing (single and exhaustive mode)")
    if 'netlist' not in data:
        raise KeyError("process: input JSON missing 'netlist'")
    return route(data)


def main_standalone(path: str, args: argparse.Namespace | None = None) -> None:
    with open(path) as f:
        data = json.load(f)

    kwargs = {}
    if args:
        if args.routing_mode:     kwargs['routing_mode']     = args.routing_mode
        if args.signal_width_nm:  kwargs['signal_width_nm']  = args.signal_width_nm
        if args.power_width_nm:   kwargs['power_width_nm']   = args.power_width_nm
        if args.output_format:    kwargs['output_format']     = args.output_format
        if args.pdk_dir:          kwargs['pdk_dir']           = args.pdk_dir
        if args.output_dir:       kwargs['output_dir']        = args.output_dir
        if args.fallback_isolated: kwargs['fallback_to_isolated'] = True

    result = route(data, **kwargs)
    stem = Path(path).stem
    import re as _re
    new_stem = _re.sub(r'_py\d+_', '_py201_', stem)
    if new_stem == stem:
        new_stem = stem + '_py201'
    out = Path(path).with_stem(new_stem)
    with open(out, 'w') as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved: {out}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 201 — analog route placement")
    parser.add_argument('input', nargs='?',
                        help="Path to py101 JSON (standalone mode)")
    parser.add_argument('--routing-mode',     default=ROUTING_MODE,
                        choices=['combined', 'isolated'],
                        help=f"Routing mode (default: {ROUTING_MODE})")
    parser.add_argument('--fallback-isolated', action='store_true',
                        help="Run isolated analysis if combined leaves unrouted nets")
    parser.add_argument('--signal-width-nm',  type=int, default=SIGNAL_WIDTH_NM,
                        help=f"Signal wire width in nm (default: {SIGNAL_WIDTH_NM})")
    parser.add_argument('--power-width-nm',   type=int, default=POWER_WIDTH_NM,
                        help=f"Power wire width in nm (default: {POWER_WIDTH_NM})")
    parser.add_argument('--output-format',    default=OUTPUT_FORMAT,
                        choices=['json', 'gds', 'both'],
                        help=f"Output format (default: {OUTPUT_FORMAT})")
    parser.add_argument('--pdk-dir',          default=PDK_DIR,
                        help=f"Path to PDK directory (default: {PDK_DIR})")
    parser.add_argument('--output-dir',
                        help="Output directory for route_data.json and route.gds")
    parsed = parser.parse_args()

    if parsed.input:
        main_standalone(parsed.input, parsed)
    else:
        logger.error("Usage: 201_routingOptimizer.py <s##_n##_py101_v01.json> [options]")
        sys.exit(1)
