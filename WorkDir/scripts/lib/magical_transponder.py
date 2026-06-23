#!/usr/bin/env python3
"""
magical_transponder.py — Host-side helpers for MAGICAL Anaroute integration.

Converts py101 JSON to MAGICAL-ready format, manages the Docker container,
runs transponder201.py inside the container, and returns route_data.json.
"""

# =============================================================================
# 1. IMPORTS  (stdlib → third-party → local lib)
# =============================================================================
import copy
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

DOCKER_IMAGE         = 'magical_szaboga1_dev_wmi:latest'
CONTAINER_SLEEP_CMD  = 'sleep 3600'
CONTAINER_WORKSPACE  = '/workspace'
CONTAINER_INPUT_DIR  = '/workspace/input'
CONTAINER_OUTPUT_DIR = '/workspace/output_route'
CONTAINER_TECH_DIR   = '/workspace/generated_tech'
CONTAINER_RUN_DIR    = '/install/MAGICAL/examples/ota1'

# Paths of container-side scripts (relative to WorkDir/Anaroute/)
_ANAROUTE_DIR = Path(__file__).parent.parent.parent / 'Anaroute'
TRANSPONDER_SRC   = str(_ANAROUTE_DIR / 'transponder201.py')
GEN_TECH_FILES_SRC = str(_ANAROUTE_DIR / 'gen_tech_files.py')

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. FORMAT CONVERSION
# =============================================================================

def convert_py101_to_magical(data: dict) -> dict:
    """
    Convert py101 placement JSON to MAGICAL-ready format for transponder201.py.

    Key transformations:
    - placed_blocks: dict (str keys) → list of dicts with block_id field
    - pins: {layer, type, side, x_min, y_min, x_max, y_max, net} → {x_min, y_min, x_max, y_max}
    - pin keys: "P0" → "B{block_id}_P0"
    - block_id and device_type added from blocks[] lookup
    - power rails (__chip_*_rail__) → virtual terminal blocks so Anaroute routes power nets to them
    """
    placement = data.get('placement', {})
    placed_dict = placement.get('placed_blocks', {})

    # Exhaustive mode: placed_blocks lives inside placement.runs[best_run_id]
    if not placed_dict and 'runs' in placement:
        best_id = placement.get('best_run_id', '')
        for run in placement.get('runs', []):
            if run.get('run_id') == best_id:
                placed_dict = run.get('placed_blocks', {})
                break
        if not placed_dict:
            for run in placement.get('runs', []):
                if run.get('status') == 'success' and run.get('placed_blocks'):
                    placed_dict = run['placed_blocks']
                    break

    blocks_list = data.get('blocks', [])
    block_info  = {b['block_id']: b for b in blocks_list}

    # --- composite group block metadata ---
    # Composite blocks (bid >= 10000, created by hierarchy_builder) use net names as pin
    # keys (e.g. "tail", "vin") instead of P<N> indices.  Build remapping tables so we
    # can convert to B<bid>_P<N> format expected by transponder201 and rebuild the
    # routing netlist to reference composite boundary pins rather than sub-block atomic pins.
    sub_to_composite: dict[int, int] = {}          # atomic sub-block bid → composite bid
    composite_pin_remap: dict[int, dict] = {}       # composite bid → {old_key → "P<N>"}
    net_to_composite_pins: dict[str, list] = {}    # net_id → ["B<bid>_P<N>", …]
    composite_block_dicts: list[dict] = []

    for bid_str, pb in placed_dict.items():
        if not bid_str.lstrip('-').isdigit():
            continue
        bid = int(bid_str)
        if 'sub_blocks' not in pb:
            continue
        for sb_bid_str in pb.get('sub_blocks', {}):
            sub_to_composite[int(sb_bid_str)] = bid
        # Assign P<N> indices: keep existing P<digit> keys, assign sequential to the rest
        pin_keys = list(pb.get('pins', {}).keys())
        p_numeric = {k: int(k[1:]) for k in pin_keys if k.startswith('P') and k[1:].isdigit()}
        non_numeric = [k for k in pin_keys if k not in p_numeric]
        next_idx = (max(p_numeric.values()) + 1) if p_numeric else 0
        key_map = {k: f'P{idx}' for k, idx in p_numeric.items()}
        for k in non_numeric:
            key_map[k] = f'P{next_idx}'
            next_idx += 1
        composite_pin_remap[bid] = key_map
        composite_block_dicts.append({'block_id': bid, 'device_type': pb.get('device_type', 'nmos_rvt')})

    for bid_str, pb in placed_dict.items():
        if not bid_str.lstrip('-').isdigit():
            continue
        bid = int(bid_str)
        if bid not in composite_pin_remap:
            continue
        key_map = composite_pin_remap[bid]
        for old_key, p_val in pb.get('pins', {}).items():
            net_id = p_val.get('net', '')
            if net_id:
                net_to_composite_pins.setdefault(net_id, []).append(f'B{bid}_{key_map[old_key]}')

    # --- real circuit blocks (atomic + composite) ---
    magical_placed = []
    real_bids = []   # only atomic bids; composite bids > max_real_bid → no OD insertion
    for bid_str, pb in placed_dict.items():
        if not bid_str.lstrip('-').isdigit():
            continue
        bid = int(bid_str)
        binfo = block_info.get(bid, {})

        pin_rects = {}
        if bid in composite_pin_remap:
            key_map = composite_pin_remap[bid]
            for old_key, p_val in pb.get('pins', {}).items():
                new_key = f'B{bid}_{key_map[old_key]}'
                pin_rects[new_key] = {
                    'x_min': p_val['x_min'],
                    'y_min': p_val['y_min'],
                    'x_max': p_val['x_max'],
                    'y_max': p_val['y_max'],
                }
        else:
            real_bids.append(bid)
            for p_key, p_val in pb.get('pins', {}).items():
                pin_idx = int(p_key.lstrip('P'))
                new_key = f'B{bid}_P{pin_idx}'
                pin_rects[new_key] = {
                    'x_min': p_val['x_min'],
                    'y_min': p_val['y_min'],
                    'x_max': p_val['x_max'],
                    'y_max': p_val['y_max'],
                }

        magical_placed.append({
            'block_id':    bid,
            'device_type': pb.get('device_type', binfo.get('device_type', 'nmos_rvt')),
            'main_bbox':   pb['main_bbox'],
            'pin_rects':   pin_rects,
        })

    # --- power rail virtual terminals ---
    # Each __chip_*_rail__ entry is an M1 stripe at the design boundary.
    # Turn it into a virtual single-pin block so Anaroute includes it in the
    # power net's connectivity.
    max_real_bid   = max(real_bids, default=-1)
    virtual_bid    = max_real_bid + 100   # leave gap; won't collide with real blocks
    rail_net_to_vid = {}  # net_id → virtual block_id
    virtual_blocks  = []

    # Highest y_max among real circuit blocks — chip rail pins are clamped to this
    # so their routing target stays within the GR grid bounds (chip rails sit above
    # the real circuit area and their physical y-position can exceed the grid top).
    safe_y_max_um = max(
        (pb['main_bbox']['y_max'] for bid_str, pb in placed_dict.items()
         if bid_str.lstrip('-').isdigit()),
        default=0.0
    )

    # Chip outline = bounding box of all real blocks + rail entries (blocks + rails)
    _real_bb   = [pb['main_bbox'] for bid_str, pb in placed_dict.items()
                  if bid_str.lstrip('-').isdigit()]
    _rail_bb   = [pb for bid_str, pb in placed_dict.items()
                  if not bid_str.lstrip('-').isdigit() and 'x_min' in pb]
    chip_outline = {
        'x_min':       min([b['x_min'] for b in _real_bb] + [r['x_min'] for r in _rail_bb], default=0.0),
        'y_min':       min([b['y_min'] for b in _real_bb] + [r['y_min'] for r in _rail_bb], default=0.0),
        'x_max':       max([b['x_max'] for b in _real_bb] + [r['x_max'] for r in _rail_bb], default=0.0),
        'y_max':       max([b['y_max'] for b in _real_bb] + [r['y_max'] for r in _rail_bb], default=0.0),
        'blocks_y_max': safe_y_max_um,
    }

    for bid_str, pb in placed_dict.items():
        if bid_str.lstrip('-').isdigit():
            continue
        net_name = pb.get('net', '')
        if not net_name:
            continue
        vbid = virtual_bid
        virtual_bid += 1
        rail_net_to_vid[net_name] = vbid

        bbox = {'x_min': pb['x_min'], 'y_min': pb['y_min'],
                'x_max': pb['x_max'], 'y_max': pb['y_max']}

        # Clamp both the block position and pin to the real-circuit y-range.
        # build_magical_db() computes pin relative coords as (pin_abs - main_bbox.y_min).
        # If main_bbox stays at the physical rail y while pin_rects are clamped lower,
        # the relative coord goes negative → clamped to 0 → clip is erased.
        # Fix: set main_bbox = pin_bbox so node.setOffset() places the block at the
        # safe y-position. Virtual blocks are excluded from OD insertion (bid > max_real_bid)
        # so moving their origin does not corrupt the GDS.
        pin_h_um = bbox['y_max'] - bbox['y_min']
        pin_bbox = {
            'x_min': bbox['x_min'],
            'x_max': bbox['x_max'],
            'y_max': min(bbox['y_max'], safe_y_max_um),
            'y_min': min(bbox['y_min'], safe_y_max_um - pin_h_um),
        }

        magical_placed.append({
            'block_id':    vbid,
            'device_type': 'nmos_rvt',
            'main_bbox':   pin_bbox,                  # block placed at safe y (not physical rail)
            'pin_rects':   {f'B{vbid}_P0': pin_bbox},
        })
        virtual_blocks.append({'block_id': vbid, 'device_type': 'nmos_rvt'})

    magical_placed.sort(key=lambda b: b['block_id'])

    # Rebuild netlist: replace sub-block atomic pins with composite boundary pins,
    # then add virtual power-rail terminal pins.
    netlist = copy.deepcopy(data['netlist'])
    for net in netlist.get('nets', []):
        net_id = net['net_id']
        new_pins = []
        for pin_ref in net.get('pins', []):
            sep = pin_ref.find('_')
            if pin_ref.startswith('B') and sep > 0:
                try:
                    if int(pin_ref[1:sep]) in sub_to_composite:
                        continue  # absorbed into composite; boundary pin added below
                except ValueError:
                    pass
            new_pins.append(pin_ref)
        new_pins.extend(net_to_composite_pins.get(net_id, []))
        vbid = rail_net_to_vid.get(net_id)
        if vbid is not None:
            new_pins.append(f'B{vbid}_P0')
        net['pins'] = new_pins

    return {
        'design_name':   'CustomDesign',
        'technology':    data.get('technology', 'gpdk090_simple_tech'),
        'max_real_bid':  max_real_bid,   # used by build_magical_db to skip OD on virtual blocks
        'blocks':        list(blocks_list) + virtual_blocks + composite_block_dicts,
        'netlist':       netlist,
        'placed_blocks': magical_placed,
        'chip_outline':  chip_outline,
    }


# =============================================================================
# 5. DOCKER HELPERS
# =============================================================================

def _run(cmd: list, capture: bool = False, check: bool = True):
    kwargs = {'check': check}
    if capture:
        kwargs['capture_output'] = True
        kwargs['text'] = True
    return subprocess.run(cmd, **kwargs)


def find_running_magical_container() -> str | None:
    """Return name of any running MAGICAL container, or None."""
    res = _run(['docker', 'ps', '--format', '{{.Names}}\t{{.Image}}'],
               capture=True, check=False)
    if res.returncode != 0:
        return None
    for line in res.stdout.strip().splitlines():
        parts = line.split('\t')
        if len(parts) == 2 and parts[1] == DOCKER_IMAGE:
            return parts[0]
    return None


def start_magical_container() -> str:
    """Start a detached MAGICAL container and return its name."""
    res = _run(['docker', 'run', '-d', '--rm', DOCKER_IMAGE, 'bash', '-c',
                CONTAINER_SLEEP_CMD], capture=True)
    container_id = res.stdout.strip()
    res2 = _run(['docker', 'inspect', '--format', '{{.Name}}', container_id],
                capture=True)
    name = res2.stdout.strip().lstrip('/')
    logger.info(f"Started MAGICAL container: {name} ({container_id[:12]})")
    return name


def ensure_magical_container(container_name: str | None = None) -> tuple:
    """Return (container_name, started_by_us)."""
    if container_name:
        res = _run(['docker', 'inspect', '--format', '{{.State.Running}}', container_name],
                   capture=True, check=False)
        if res.returncode == 0 and res.stdout.strip() == 'true':
            logger.info(f"Using specified container: {container_name}")
            return container_name, False
        logger.warning(f"Specified container '{container_name}' not running, searching ...")

    existing = find_running_magical_container()
    if existing:
        logger.info(f"Found running MAGICAL container: {existing}")
        return existing, False

    logger.info("No running MAGICAL container found, starting one ...")
    return start_magical_container(), True


def cp_to_container(container: str, src: str, dst_dir: str) -> None:
    _run(['docker', 'exec', container, 'mkdir', '-p', dst_dir])
    _run(['docker', 'cp', src, f'{container}:{dst_dir}/'])


def cp_from_container(container: str, container_path: str, local_dst: str) -> None:
    tmp = f'/tmp/_mc_{os.path.basename(container_path)}'
    _run(['docker', 'exec', container, 'cp', container_path, tmp])
    _run(['docker', 'cp', f'{container}:{tmp}', local_dst], check=False)


# =============================================================================
# 6. ROUTING EXECUTION
# =============================================================================

def run_magical_routing(magical_input: dict, pdk_tech_json: str,
                        routing_mode: str = 'combined',
                        signal_width_nm: int = 200,
                        power_width_nm: int = 500,
                        output_dir: str | None = None,
                        container_name: str | None = None,
                        enable_block_fr: bool = True) -> dict:
    """
    Run MAGICAL Anaroute routing inside the Docker container.

    Returns the parsed route_data dict (net segments + status).
    Raises RuntimeError on failure.
    """
    if not os.path.exists(TRANSPONDER_SRC):
        raise FileNotFoundError(f"transponder201.py not found: {TRANSPONDER_SRC}")
    if not os.path.exists(GEN_TECH_FILES_SRC):
        raise FileNotFoundError(f"gen_tech_files.py not found: {GEN_TECH_FILES_SRC}")
    if not os.path.exists(pdk_tech_json):
        raise FileNotFoundError(f"PDK tech JSON not found: {pdk_tech_json}")

    local_output = output_dir or str(Path(pdk_tech_json).parent.parent / 'route_output')
    os.makedirs(local_output, exist_ok=True)

    # Write magical-ready JSON to a temp file
    input_json_local = str(Path(local_output) / 'magical_input.json')
    with open(input_json_local, 'w') as f:
        json.dump(magical_input, f, indent=2)

    container, started_by_us = ensure_magical_container(container_name)

    try:
        # Copy scripts and input into container
        logger.info("Copying files into container ...")
        cp_to_container(container, TRANSPONDER_SRC,    CONTAINER_WORKSPACE)
        cp_to_container(container, GEN_TECH_FILES_SRC, CONTAINER_WORKSPACE)
        cp_to_container(container, input_json_local,   CONTAINER_INPUT_DIR)
        cp_to_container(container, pdk_tech_json,      CONTAINER_WORKSPACE)

        container_json   = f'{CONTAINER_INPUT_DIR}/magical_input.json'
        container_pdk    = f'{CONTAINER_WORKSPACE}/{os.path.basename(pdk_tech_json)}'
        container_script = f'{CONTAINER_WORKSPACE}/transponder201.py'
        container_gen    = f'{CONTAINER_WORKSPACE}/gen_tech_files.py'

        # Generate gpdk090 tech files inside container
        logger.info("Generating tech files inside container ...")
        _run(['docker', 'exec', container,
              'python3', container_gen, container_pdk, CONTAINER_TECH_DIR])

        # Run transponder201.py
        cmd = [
            'docker', 'exec', '-w', CONTAINER_RUN_DIR, container,
            'python3', container_script,
            '--input',            container_json,
            '--output',           CONTAINER_OUTPUT_DIR + '/',
            '--techdir',          CONTAINER_TECH_DIR + '/',
            '--routing-mode',     routing_mode,
            '--signal-width-nm',  str(signal_width_nm),
            '--power-width-nm',   str(power_width_nm),
        ]
        if not enable_block_fr:
            cmd.append('--no-enable-block-fr')
        logger.info(f"Running transponder201.py (mode={routing_mode}) ...")
        t0  = time.time()
        res = subprocess.run(cmd, check=False)
        elapsed = time.time() - t0
        logger.info(f"transponder201.py finished in {elapsed:.1f}s (exit={res.returncode})")

        if res.returncode != 0:
            raise RuntimeError(f"transponder201.py exited with code {res.returncode}")

        # Copy route_data.json and route.gds back to host
        route_data_local = str(Path(local_output) / 'route_data.json')
        route_gds_local  = str(Path(local_output) / 'route.gds')

        cp_from_container(container,
                          f'{CONTAINER_OUTPUT_DIR}/route_data.json',
                          route_data_local)
        # Find route.gds (name may include circuit name prefix)
        find_res = _run(['docker', 'exec', container,
                         'find', CONTAINER_OUTPUT_DIR, '-name', '*.route.gds'],
                        capture=True, check=False)
        gds_files = [p.strip() for p in find_res.stdout.strip().splitlines() if p.strip()]
        if gds_files:
            cp_from_container(container, gds_files[0], route_gds_local)
            logger.info(f"route.gds → {route_gds_local}")

        if not os.path.exists(route_data_local):
            raise RuntimeError(f"route_data.json not found after routing: {route_data_local}")

        with open(route_data_local) as f:
            route_data = json.load(f)

        route_data['route_gds_path'] = route_gds_local if os.path.exists(route_gds_local) else None
        return route_data

    finally:
        if started_by_us:
            logger.info("Stopping container (started by us) ...")
            _run(['docker', 'stop', container], check=False)


# =============================================================================
# 7. BUILD py201 NET SEGMENTS
# =============================================================================

def build_py201_nets(data: dict, route_data: dict,
                     fallback_isolated: bool = False) -> tuple:
    """
    Merge routing results into the netlist nets.

    Returns (updated_nets: list, routing_meta: dict).
    Each net gains 'route_segments' and 'route_status' fields.
    routing_meta is added to placement.routing.
    """
    net_results = {n['net_id']: n for n in route_data.get('nets', [])}
    updated_nets = []
    routed   = 0
    unrouted = 0
    unrouted_ids = []

    for net in data['netlist']['nets']:
        nid    = net['net_id']
        result = net_results.get(nid, {})
        status = result.get('status', 'unrouted')
        segs   = result.get('segments', [])

        updated = dict(net)
        updated['route_segments'] = segs
        updated['route_status']   = status

        if fallback_isolated and result.get('segments_isolated'):
            updated['route_segments_isolated'] = result['segments_isolated']

        if status != 'unrouted':
            routed += 1
        else:
            unrouted += 1
            unrouted_ids.append(nid)

        updated_nets.append(updated)

    routing_meta = {
        'method':            'anaroute_' + route_data.get('routing_mode', 'combined'),
        'routed':            routed,
        'unrouted':          unrouted,
        'unrouted_nets':     unrouted_ids,
        'fallback_isolated': fallback_isolated,
        't_routing_ms':      route_data.get('t_routing_ms', 0),
    }

    return updated_nets, routing_meta
