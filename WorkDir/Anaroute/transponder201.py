#!/usr/bin/env python3
"""
transponder201.py — py201 converted JSON → MagicalDB → ANAROUTE routing → route_data.json

Runs inside the magical_szaboga1_dev_wmi:latest Docker container.
Converts the MAGICAL-ready placement JSON produced by magical_transponder.py
into a MagicalDB, runs ANAROUTE, and writes:
  - route.gds       : routed GDS (combined: multi-layer; isolated: M1-only)
  - route_data.json : per-net routing segments and status for py201 JSON output

Input JSON format (magical-ready, produced by magical_transponder.convert_py101_to_magical):
  {
    "design_name": "CustomDesign",
    "technology": "gpdk090_simple_tech",
    "blocks": [...],
    "netlist": {...},
    "placed_blocks": [
      {
        "block_id": 0,
        "device_type": "nmos_rvt",
        "main_bbox": {"x_min": 13.46, "y_min": 0.915, ...},
        "pin_rects": {"B0_P0": {"x_min": 13.46, ...}, ...}
      }
    ]
  }

Sub-process mode (crash isolation for ANAROUTE C++ assertions):
  python3 transponder201.py --route-mode combined-helper <cfg_json>
  python3 transponder201.py --route-mode net-helper <cfg_json> <net_idx> <out_gds>

Usage (normal mode, called by the host via docker exec):
  python3 transponder201.py --input input.json --output /workspace/output_route/ \
                            --techdir /workspace/generated_tech/ \
                            --routing-mode combined \
                            --signal-width-nm 200 --power-width-nm 500
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import argparse
import json
import math
import os
import subprocess
import sys
import time
from collections import deque

MAGICAL_FLOW_PATH = '/install/MAGICAL/flow/python'
sys.path.insert(0, MAGICAL_FLOW_PATH)

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DESIGN_NAME           = 'CustomDesign'
MARGIN_NM             = 2000     # 2 µm boundary margin around design
GRID_STEP_NM          = 200      # routing grid pitch
SYM_AXIS_MULT         = 10       # symAxis = xHi + MULT * width  (far right, no false sym)
MAX_COMBINED_RETRIES  = 5        # max retries when combined routing crashes on a net
DEFAULT_RUN_DIR       = '/install/MAGICAL/examples/ota1'  # MAGICAL C++ CWD

# GDS layer numbers → layer names (metals + vias used in routing output)
GDS_LAYER_TO_NAME = {
    31: 'M1', 32: 'M2', 33: 'M3', 34: 'M4', 35: 'M5', 36: 'M6', 37: 'M7',
    51: 'VIA1', 52: 'VIA2', 53: 'VIA3', 54: 'VIA4', 55: 'VIA5', 56: 'VIA6',
}

# Via layer → (lower metal, upper metal) connectivity
VIA_CONNECTS = {
    'VIA1': ('M1', 'M2'), 'VIA2': ('M2', 'M3'), 'VIA3': ('M3', 'M4'),
    'VIA4': ('M4', 'M5'), 'VIA5': ('M5', 'M6'), 'VIA6': ('M6', 'M7'),
}

# =============================================================================
# 3. UNIT HELPERS
# =============================================================================

def um_to_nm(um: float) -> int:
    raw = int(round(float(um) * 1000))
    return round(raw / 5) * 5  # snap to 5nm manufacturing grid (LEF abs(xl)%10==0 or 8)


def nm_to_um(nm: int) -> float:
    return float(nm) / 1000.0


# =============================================================================
# 4. BUILD MagicalDB
# =============================================================================

def build_magical_db(json_data: dict, simple_tech_file: str,
                     enable_block_fr: bool = True):
    """
    Build magicalFlow.DesignDB + TechDB from the MAGICAL-ready placement JSON.

    Returns (db, tDB, top_ckt_idx, bid_to_node_idx, block_sub_ckt).
    Uses exact M1 pin rectangles from pin_rects (no synthetic ±350nm boxes).
    """
    import magicalFlow

    blocks      = json_data['blocks']
    placed_list = json_data['placed_blocks']
    netlist     = json_data['netlist']

    block_by_id  = {b['block_id']: b for b in blocks}
    placed_by_id = {pb['block_id']: pb for pb in placed_list}
    max_real_bid = json_data.get('max_real_bid', -1)  # virtual chip rail blocks have bid > max_real_bid

    # -- Tech DB -----------------------------------------------------------
    tDB = magicalFlow.TechDB()
    magicalFlow.parseSimpleTechFile(simple_tech_file, tDB)
    m1_tech_idx = tDB.layerNameToIdx('M1')
    od_tech_idx  = tDB.layerNameToIdx('OD')
    print(f"[transponder201] TechDB: dbu={tDB.units().dbu}, M1 tech_idx={m1_tech_idx}")

    # -- Design DB ---------------------------------------------------------
    db = magicalFlow.DesignDB()

    # Step 1: top circuit at index 0
    top_ckt_idx = db.allocateCkt()   # always 0
    top_ckt = db.subCkt(top_ckt_idx)
    top_ckt.name = json_data.get('design_name', DESIGN_NAME)

    # Step 2: sub-circuit per block
    block_sub_ckt = {}   # block_id → sub_ckt_idx

    for bid in sorted(placed_by_id.keys()):
        placed = placed_by_id[bid]
        block  = block_by_id[bid]

        sub_ckt_idx = db.allocateCkt()
        sub_ckt = db.subCkt(sub_ckt_idx)
        sub_ckt.name = f'{top_ckt.name}_B{bid}'

        dev_type = block['device_type'].lower()
        if 'pmos' in dev_type:
            sub_ckt.implType = magicalFlow.ImplTypePCELL_Pch
        else:
            sub_ckt.implType = magicalFlow.ImplTypePCELL_Nch

        # Block bounding box (nm, relative to block origin = lower-left corner)
        bbox    = placed['main_bbox']
        pos_x   = bbox['x_min']   # block origin (µm)
        pos_y   = bbox['y_min']
        w_nm    = um_to_nm(bbox['x_max'] - bbox['x_min'])
        h_nm    = um_to_nm(bbox['y_max'] - bbox['y_min'])
        sub_ckt.layout().setBoundary(0, 0, w_nm, h_nm)

        # Step 2a: create one net per pin slot
        pin_rects = placed['pin_rects']   # {"B{bid}_P{k}": {x_min, y_min, x_max, y_max}}
        max_pin_k = max(int(k.split('_P')[1]) for k in pin_rects.keys()) if pin_rects else -1

        for pin_k in range(max_pin_k + 1):
            net_idx = sub_ckt.allocateNet()
            net = sub_ckt.net(net_idx)
            net.name = str(pin_k)

            pin_key = f'B{bid}_P{pin_k}'
            if pin_key in pin_rects:
                r = pin_rects[pin_key]
                # Convert absolute µm → relative nm
                xlo = um_to_nm(r['x_min'] - pos_x)
                ylo = um_to_nm(r['y_min'] - pos_y)
                xhi = um_to_nm(r['x_max'] - pos_x)
                yhi = um_to_nm(r['y_max'] - pos_y)
                # Clamp to block boundary
                xlo = max(xlo, 0);  ylo = max(ylo, 0)
                xhi = min(xhi, w_nm); yhi = min(yhi, h_nm)
                if xlo >= xhi: xhi = xlo + 10
                if ylo >= yhi: yhi = ylo + 10
            else:
                print(f"[transponder201] WARNING: pin {pin_key} missing, using block centre")
                xlo = w_nm // 4;  ylo = h_nm // 4
                xhi = 3 * w_nm // 4; yhi = 3 * h_nm // 4

            net.setIoShape(xlo, ylo, xhi, yhi)
            net.ioLayer = 1   # M1 routing layer index
            sub_ckt.layout().insertRect(m1_tech_idx, xlo, ylo, xhi, yhi)

        block_sub_ckt[bid] = sub_ckt_idx
        print(f"[transponder201] B{bid}: sub_ckt={sub_ckt_idx}, type={dev_type}, "
              f"bbox=({w_nm},{h_nm})nm, pins={max_pin_k + 1}")

    # Step 3: nodes in top circuit
    bid_to_node_idx = {}
    for bid in sorted(placed_by_id.keys()):
        node_idx = top_ckt.allocateNode()
        node = top_ckt.node(node_idx)
        node.name    = f'B{bid}'
        node.refName = block_by_id[bid]['device_type']
        node.graphIdx = block_sub_ckt[bid]
        placed = placed_by_id[bid]
        x_nm = um_to_nm(placed['main_bbox']['x_min'])
        y_nm = um_to_nm(placed['main_bbox']['y_min'])
        node.setOffset(x_nm, y_nm)
        bid_to_node_idx[bid] = node_idx

    # Step 3b: grid-pad node — widen design x-range so findOrigin() computes a larger
    # grid step that covers the full y-extent with the fixed 24 valid y-cells.
    # findOrigin uses node bounding boxes; adding a zero-size node at the required
    # x position forces step = req_x / 34, giving 24*step > y_max.
    if bid_to_node_idx:
        _y_max_nm = max(um_to_nm(placed_by_id[bid]['main_bbox']['y_max'])
                        for bid in bid_to_node_idx)
        _x_max_nm = max(um_to_nm(placed_by_id[bid]['main_bbox']['x_max'])
                        for bid in bid_to_node_idx)
        # 24 valid y-cells; require 24 * step_nm > _y_max_nm + 620 (offset)
        _req_x_nm = math.ceil((_y_max_nm + 620) * 34 / 24)
        if _x_max_nm < _req_x_nm:
            _pad_sub_idx = db.allocateCkt()
            _pad_sub = db.subCkt(_pad_sub_idx)
            _pad_sub.name = f'{top_ckt.name}_GridPad'
            _pad_sub.implType = magicalFlow.ImplTypePCELL_Nch
            _pad_sub.layout().setBoundary(0, 0, 1, 1)
            _pad_ni = top_ckt.allocateNode()
            _pad_n  = top_ckt.node(_pad_ni)
            _pad_n.name     = '_grid_pad'
            _pad_n.refName  = 'nmos_rvt'
            _pad_n.graphIdx = _pad_sub_idx
            _pad_n.setOffset(_req_x_nm, 0)
            _est_step = _req_x_nm // 34
            print(f"[transponder201] Grid-pad node at x={nm_to_um(_req_x_nm):.2f}µm "
                  f"(est. step≈{_est_step}nm, y-coverage≈{nm_to_um(24*_est_step-620):.2f}µm "
                  f"> y_max={nm_to_um(_y_max_nm):.2f}µm)")

    # Step 4: top-level nets from netlist
    for net_data in netlist['nets']:
        net_idx = top_ckt.allocateNet()
        top_net = top_ckt.net(net_idx)
        top_net.name = net_data['net_id']
        for pin_ref in net_data['pins']:
            parts = pin_ref.split('_P')
            bid   = int(parts[0][1:])
            pnum  = int(parts[1])
            pin_idx = top_ckt.allocatePin()
            pin = top_ckt.pin(pin_idx)
            pin.nodeIdx   = bid_to_node_idx[bid]
            pin.netIdx    = net_idx
            pin.intNetIdx = pnum
            pin.valid     = True
            top_net.appendPinIdx(pin_idx)
            top_ckt.node(bid_to_node_idx[bid]).appendPinIdx(pin_idx)

    # Step 5: mark all nets as analog (power stripe algorithm crashes on small grids)
    for ni in range(top_ckt.numNets()):
        top_ckt.net(ni).markAnalogFlag()

    # Step 6: identify root circuit
    db.findRootCkt()

    # Step 7: build top layout
    # OD shapes are inserted flat into the top-level layout at absolute main_bbox coordinates
    # so the placement GDS contains OD at the top cell level (not buried in sub-cells),
    # which is what the FR engine requires to enforce forbidden regions.
    top_ckt.layout().clear()
    all_x, all_y = [], []
    real_y_max = 0  # highest y of real circuit blocks (not chip rail virtual blocks)

    for bid, node_idx in bid_to_node_idx.items():
        placed = placed_by_id[bid]
        x_nm = um_to_nm(placed['main_bbox']['x_min'])
        y_nm = um_to_nm(placed['main_bbox']['y_min'])
        sub = db.subCkt(block_sub_ckt[bid])
        top_ckt.layout().insertLayout(sub.layout(), x_nm, y_nm, False)
        b = sub.layout().boundary()
        all_x += [x_nm + b.xLo, x_nm + b.xHi]
        all_y += [y_nm + b.yLo, y_nm + b.yHi]

        if bid <= max_real_bid:  # real device block (not chip rail virtual block)
            real_y_max = max(real_y_max, y_nm + b.yHi)
            if enable_block_fr and od_tech_idx >= 0:
                top_ckt.layout().insertRect(
                    od_tech_idx,
                    x_nm, y_nm, x_nm + (b.xHi - b.xLo), y_nm + b.yHi)

    # Dynamic top margin: extend boundary above chip rail by at least the circuit→rail gap.
    # This gives findOrigin() a larger design height → larger gridStep → chip rail pins
    # (which are just above the real circuit area) stay within the GR grid bounds.
    chip_rail_y_max = max(all_y)
    rail_gap = max(0, chip_rail_y_max - real_y_max)
    top_margin = MARGIN_NM + rail_gap

    top_xLo = min(all_x) - MARGIN_NM;  top_yLo = min(all_y) - MARGIN_NM
    top_xHi = max(all_x) + MARGIN_NM;  top_yHi = chip_rail_y_max + top_margin
    top_ckt.layout().setBoundary(top_xLo, top_yLo, top_xHi, top_yHi)
    print(f"[transponder201] Design boundary: "
          f"({nm_to_um(top_xLo):.2f},{nm_to_um(top_yLo):.2f}) → "
          f"({nm_to_um(top_xHi):.2f},{nm_to_um(top_yHi):.2f}) µm  "
          f"rail_gap={nm_to_um(rail_gap):.2f}µm top_margin={nm_to_um(top_margin):.2f}µm")

    return db, tDB, top_ckt_idx, bid_to_node_idx, block_sub_ckt


# =============================================================================
# 5. REQUIRED CONFIG FILES FOR ANAROUTE (dev_wmi branch)
# =============================================================================

def write_anaroute_logging_json(dirname: str, enable_gr: bool = False) -> str:
    """Write anaroute_logging.json to output dir and to ota1/ CWD (both required by dev_wmi)."""
    config = {
        "rrr_logging": {"enabled": True, "output_file": "."},
        "feature_toggles": {
            "enable_gr": enable_gr, "enable_fr": True, "enable_visualize": False,
            "correct_pin_loc": False, "use_gridless": False, "debug_print": False,
            "flatten_gds": False, "out_guide": "", "out_guide_gds": "",
        },
        "astar_params": {
            "dr": {
                "hor_cost": 1, "ver_cost": 1, "via_cost": 0,
                "factor_g": 1, "factor_h": 1, "guide_cost": -5000,
                "max_explore": 500000, "stacked_via_cost": 0,
                "drc_cost": 20000, "history_cost": 500, "legacy_routing": 0,
                "layer_dir_mode": 2, "wrong_dir_cost": 2000,
                "incompat_cost": 5000, "sens_radius": 1000,
                "z_effect_multiplier": 10.0, "allow_stacked_vias": 0,
                "max_iter": 15,
                "max_upper_routing_layer_idx_power": 6,
                "max_upper_routing_layer_idx_signal": 6,
                "center_only_acs": 1, "bend_penalty_pct": 5.0,
                "bend_penalty_cost": 1000,
            },
            "gr": {
                "hor_cost": 1, "ver_cost": 1, "via_cost": 10,
                "factor_g": 1, "factor_h": 1,
                "overflow_cost": 10, "layer_dir_mode": 2, "wrong_dir_cost": 100,
            },
        },
    }
    path = os.path.join(dirname, 'anaroute_logging.json')
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)
    ota1_path = '/install/MAGICAL/examples/ota1/anaroute_logging.json'
    try:
        with open(ota1_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[transponder201] WARNING: could not update {ota1_path}: {e} "
              f"(subprocess CWD=dirname means this is non-fatal)")
    return path


def write_route_json(dirname: str, circuit_name: str, json_data: dict,
                     signal_width_nm: int, power_width_nm: int) -> str:
    """Write <circuit>.route.json for dev_wmi PnR.runRoute() net-spec parsing."""
    # WIDTH UNIT: DATABASE MICRONS 2000 → 1 nm = 2 dbu
    sig_dbu = int(signal_width_nm * 2)
    pwr_dbu = int(power_width_nm  * 2)
    net_cfg = {}
    for net in json_data['netlist']['nets']:
        nid      = net['net_id']
        is_power = net.get('net_type') == 'power'
        if is_power:
            net_cfg[nid] = {
                "is_power": False, "min_width": pwr_dbu, "min_cuts": 4,
                "cuts_row": 2, "cuts_col": 2, "sens": 0.01, "aggr": 0.4,
                "routing_style": "P2T", "routing_info": "",
            }
        else:
            net_cfg[nid] = {
                "is_power": False, "min_width": sig_dbu, "min_cuts": 2,
                "cuts_row": 1, "cuts_col": 2, "sens": 0.9, "aggr": 0.05,
                "routing_style": "P2P", "routing_info": "",
            }
    path = os.path.join(dirname, circuit_name + '.route.json')
    with open(path, 'w') as f:
        json.dump({"net_config": net_cfg}, f, indent=2)
    return path


# =============================================================================
# 6. ROUTING SUBPROCESS HELPERS (called via --route-mode)
# =============================================================================

def _setup_pnr(db, tDB, top_ckt_idx, params, dirname):
    """Build and configure a PnR object from MagicalDB (extracted from repeated pattern)."""
    import PnR as PnRModule

    class _MDB:
        pass
    mdb          = _MDB()
    mdb.designDB = type('_D', (), {'db': db})()
    mdb.techDB   = tDB
    mdb.params   = params

    pnr               = PnRModule.PnR(mdb)
    pnr.cktIdx        = top_ckt_idx
    pnr.isTopLevel    = True
    pnr.dirname       = dirname if dirname.endswith('/') else dirname + '/'
    pnr.origin        = [10**9, 10**9]
    pnr.subShapeList  = []

    ckt = db.subCkt(top_ckt_idx)
    ckt.setTechDB(tDB)

    bbox     = ckt.layout().boundary()
    area_um2 = nm_to_um(bbox.xHi - bbox.xLo) * nm_to_um(bbox.yHi - bbox.yLo)
    pnr.isSmallModule = area_um2 < params.smallModuleAreaThreshold
    # Push sym axis far right so no net is mistakenly detected as self-symmetric
    pnr.symAxis = bbox.xHi + SYM_AXIS_MULT * (bbox.xHi - bbox.xLo)

    return pnr


def _load_params(cfg: dict):
    """Load MAGICAL Params from ota1.json and apply width overrides from cfg."""
    import Params as ParamsModule
    params = ParamsModule.Params()
    _ota1_path = '/install/MAGICAL/examples/ota1/ota1.json'
    params.load(_ota1_path)
    try:
        with open(_ota1_path) as _f:
            _ota1 = json.load(_f)
        _grid_keys = {k: v for k, v in _ota1.items()
                      if any(w in k.lower() for w in ('grid', 'cell', 'num', 'track', 'step', 'route'))}
        print(f"[ota1.json] grid-related keys: {_grid_keys}")
    except Exception as _e:
        print(f"[ota1.json] cannot read for diagnostics: {_e}")
    params.simple_tech_file = cfg['simple_tech_file']
    params.lef              = cfg['lef']
    params.techfile         = cfg['techfile']
    params.resultDir        = cfg['dirname']
    if cfg.get('signal_width_nm'):
        params.signalAnalogWireWidthTable = [[0, cfg['signal_width_nm'] / 1000.0]]
    if cfg.get('power_width_nm'):
        params.powerWireWidthTable = [[0, cfg['power_width_nm'] / 1000.0]]
    return params


def _run_combined_helper(cfg_path: str) -> None:
    """
    Subprocess entry: route all nets combined in one ANAROUTE call.
    Called as: python3 transponder201.py --route-mode combined-helper <cfg_path>
    """
    import magicalFlow
    import anaroutePy
    import subprocess as _sp

    with open(cfg_path) as f:
        cfg = json.load(f)

    json_data = json.load(open(cfg['input_json']))
    db, tDB, top_ckt_idx, _, _ = build_magical_db(
        json_data, cfg['simple_tech_file'],
        enable_block_fr=cfg.get('enable_block_fr', True))
    params = _load_params(cfg)
    pnr    = _setup_pnr(db, tDB, top_ckt_idx, params, cfg['dirname'])
    ckt    = db.subCkt(top_ckt_idx)
    num_nets = ckt.numNets()

    skip_nets = set(cfg.get('skip_nets', []))
    pnr.routerNets = list(range(num_nets))
    pnr.findOrigin(top_ckt_idx)
    print(f"[pnr] gridStep={pnr.gridStep} nm, origin={pnr.origin}")
    if skip_nets:
        pnr.routerNets = [i for i in range(num_nets) if ckt.net(i).name not in skip_nets]
        print(f'[combined_helper] Skipping nets: {sorted(skip_nets)}')

    adj_x = max(pnr.origin[0], pnr.gridStep * 10)
    adj_y = max(pnr.origin[1], pnr.gridStep * 10)

    router = anaroutePy.AnaroutePy()
    router.setCircuitName(ckt.name)
    router.parseLef(params.lef)
    router.parseTechfile(params.techfile)
    router.parseGds(cfg['place_file'])
    pnr.routeParsePin(router, top_ckt_idx,
                      cfg['dirname'] + ckt.name + '.gr')

    # Build net_spec CSV
    _csv_path        = cfg['dirname'] + ckt.name + '.net_spec_active.csv'
    _route_json_path = cfg['dirname'] + ckt.name + '.route.json'
    _script          = '/install/MAGICAL/anaroute/bin/route_json_to_csv.py'
    if os.path.isfile(_route_json_path) and os.path.isfile(_script):
        _sp.run([sys.executable, _script, _route_json_path, _csv_path], check=True)
        if skip_nets:
            with open(_csv_path) as rf:
                lines = rf.readlines()
            active = [l for l in lines[1:] if l.split(',')[0].strip() not in skip_nets]
            with open(_csv_path, 'w') as wf:
                wf.writelines([lines[0]] + active)
    else:
        sig_dbu = int(cfg.get('signal_width_nm', 200) * 2)
        pwr_dbu = int(cfg.get('power_width_nm',  500) * 2)
        pwr_ids = set(cfg.get('power_net_ids', []))
        hdr  = 'net,min_width,min_cuts,is_power,cuts_row,cuts_col,sens,aggr,routing_style,routing_info\n'
        rows = ''
        for i in pnr.routerNets:
            nm = ckt.net(i).name
            if nm in pwr_ids:
                rows += f"{nm},{pwr_dbu},4,0,2,2,0.01,0.4,P2T,\n"
            else:
                rows += f"{nm},{sig_dbu},2,0,1,2,0.9,0.05,P2P,\n"
        with open(_csv_path, 'w') as cf:
            cf.write(hdr + rows)

    try:
        router.parseNetCsv(_csv_path)
    except Exception as e:
        print(f'[combined_helper] parseNetCsv warning: {e}')

    router.setGridStep(2 * pnr.gridStep)
    router.setSymAxisX(2 * pnr.symAxis)
    router.setGridOffsetX(2 * (adj_x - pnr.gridStep * 10))
    router.setGridOffsetY(2 * (adj_y - pnr.gridStep * 10))
    router.parseSymNet(cfg['symnet_file'])
    if pnr.isTopLevel:
        for ni in pnr.routerNets:
            net = ckt.net(ni)
            if net.isIo():
                router.addIOPort(net.name)

    result = router.solve(False, pnr.enable_gr)
    # Write GDS BEFORE evaluate() — evaluate() can SIGSEGV; GDS must survive the crash
    try:
        router.writeLayoutGds(cfg['place_file'], cfg['route_file'], True)
        print(f'[combined_helper] GDS written → {cfg["route_file"]}')
    except Exception as e:
        print(f'[combined_helper] writeLayoutGds raised: {e}')
        sys.exit(1)
    try:
        router.evaluate()
    except Exception as e:
        print(f'[combined_helper] evaluate() warning (non-fatal): {e}')

    if result:
        print(f'[combined_helper] ROUTED all nets → {cfg["route_file"]}')
    else:
        print(f'[combined_helper] PARTIAL route (some nets unrouted) → {cfg["route_file"]}')
    sys.exit(0)


def _run_net_helper(cfg_path: str, net_idx: int, out_gds: str) -> None:
    """
    Subprocess entry: route a single net in isolation (no cumulative obstacles).
    Called as: python3 transponder201.py --route-mode net-helper <cfg> <net_idx> <out_gds>
    """
    import magicalFlow
    import anaroutePy

    with open(cfg_path) as f:
        cfg = json.load(f)

    json_data = json.load(open(cfg['input_json']))
    db, tDB, top_ckt_idx, _, _ = build_magical_db(
        json_data, cfg['simple_tech_file'],
        enable_block_fr=cfg.get('enable_block_fr', True))
    params = _load_params(cfg)

    # Per-net width: power nets get power_width even though all nets are analog
    ckt = db.subCkt(top_ckt_idx)
    if (net_idx < ckt.numNets() and
            ckt.net(net_idx).name in set(cfg.get('power_net_ids', [])) and
            cfg.get('power_width_nm')):
        params.signalAnalogWireWidthTable = [[0, cfg['power_width_nm'] / 1000.0]]

    pnr = _setup_pnr(db, tDB, top_ckt_idx, params, cfg['dirname'])

    pnr.routerNets = list(range(ckt.numNets()))
    pnr.findOrigin(top_ckt_idx)
    print(f"[pnr] gridStep={pnr.gridStep} nm, origin={pnr.origin}")
    adj_x = max(pnr.origin[0], pnr.gridStep * 10)
    adj_y = max(pnr.origin[1], pnr.gridStep * 10)

    router = anaroutePy.AnaroutePy()
    router.setCircuitName(ckt.name)
    router.parseLef(params.lef)
    router.parseTechfile(params.techfile)
    router.parseGds(cfg['place_file'])
    pnr.routerNets = [net_idx]
    pnr.routeParsePin(router, top_ckt_idx,
                      cfg['dirname'] + ckt.name + f'.gr_sub{net_idx}')
    router.setGridStep(2 * pnr.gridStep)
    router.setSymAxisX(2 * pnr.symAxis)
    router.setGridOffsetX(2 * (adj_x - pnr.gridStep * 10))
    router.setGridOffsetY(2 * (adj_y - pnr.gridStep * 10))
    net = ckt.net(net_idx)
    if net.isIo():
        router.addIOPort(net.name)
    router.parseSymNet(cfg['symnet_file'])
    # NOTE: parseNetCsv is NOT called for isolated single-net routing;
    # the CSV contains all nets and the C++ router throws at index access.

    result = router.solve(False, pnr.enable_gr)
    router.evaluate()
    if not result:
        print(f'[net_helper] solve() returned False for net {net.name}')
        sys.exit(1)
    router.writeLayoutGds(cfg['place_file'], out_gds, True)
    print(f'[net_helper] ROUTED {net.name} → {out_gds}')
    sys.exit(0)


# =============================================================================
# 7. ROUTING ORCHESTRATION
# =============================================================================

def run_routing(db, tDB, top_ckt_idx: int, json_data: dict, output_dir: str,
                params, mode: str,
                signal_width_nm: int, power_width_nm: int,
                input_json_path: str,
                enable_block_fr: bool = True) -> tuple:
    """
    Orchestrate ANAROUTE routing in combined or isolated mode.

    Returns (route_gds_path, per_net_gds: dict{net_name: gds_path}).
    per_net_gds is populated for isolated mode; for combined mode it is empty
    (shape attribution is done via flood-fill in extract_route_segments).
    """
    import magicalFlow

    os.makedirs(output_dir, exist_ok=True)
    top_ckt   = db.subCkt(top_ckt_idx)
    ckt_name  = top_ckt.name
    dirname   = output_dir if output_dir.endswith('/') else output_dir + '/'
    num_nets  = top_ckt.numNets()

    # Write placement GDS (base for routing)
    place_file = dirname + ckt_name + '.place.gds'
    magicalFlow.writeGdsLayout(top_ckt_idx, place_file, db, tDB)
    print(f"[transponder201] Placement GDS: {place_file} ({os.path.getsize(place_file)} bytes)")

    route_file  = dirname + ckt_name + '.route.gds'
    symnet_file = dirname + ckt_name + '.symnet'
    with open(symnet_file, 'w') as f:
        pass  # empty: no symmetry constraints for custom placement

    power_net_ids = [n['net_id'] for n in json_data['netlist']['nets']
                     if n.get('net_type') == 'power']

    # Shared config dict for all sub-process helpers
    base_cfg = {
        'input_json':       input_json_path,
        'simple_tech_file': params.simple_tech_file,
        'lef':              params.lef,
        'techfile':         params.techfile,
        'dirname':          dirname,
        'place_file':       place_file,
        'symnet_file':      symnet_file,
        'route_file':       route_file,
        'signal_width_nm':  signal_width_nm,
        'power_width_nm':   power_width_nm,
        'power_net_ids':    power_net_ids,
        'enable_block_fr':  enable_block_fr,
    }

    # Write routing config files required by dev_wmi
    # Combined mode uses GR (global router sees all nets); isolated uses DR only
    write_anaroute_logging_json(dirname, enable_gr=(mode == 'combined'))
    write_route_json(dirname, ckt_name, json_data, signal_width_nm, power_width_nm)

    this_script = os.path.abspath(__file__)
    per_net_gds = {}   # net_name → gds path (populated in isolated mode)

    # -----------------------------------------------------------------------
    # COMBINED MODE
    # -----------------------------------------------------------------------
    if mode == 'combined':
        print(f"\n[transponder201] Routing {num_nets} nets COMBINED ...")
        combined_skip = []
        succeeded     = False

        for attempt in range(MAX_COMBINED_RETRIES + 1):
            cfg = dict(base_cfg, skip_nets=combined_skip)
            cfg_path = dirname + '_combined_cfg.json'
            with open(cfg_path, 'w') as f:
                json.dump(cfg, f)

            t0   = time.time()
            proc = subprocess.run(
                [sys.executable, this_script, '--route-mode', 'combined-helper', cfg_path],
                timeout=900, capture_output=True, text=True,
                cwd=dirname,  # Anaroute reads anaroute_logging.json from CWD
            )
            elapsed = time.time() - t0
            for line in (proc.stdout + proc.stderr).splitlines():
                print('  ' + line)

            gds_written = os.path.exists(route_file) and os.path.getsize(route_file) > 100
            if gds_written:
                if proc.returncode != 0:
                    print(f'[transponder201] Combined helper exited {proc.returncode} '
                          f'but GDS was written — treating as success')
                succeeded = True
                # Check for DR-FAIL lines in output
                import re as _re
                dr_fails = _re.findall(r"\[DR-FAIL\] Net '([^']+)' permanently failed",
                                       proc.stdout + proc.stderr)
                for bad in dr_fails:
                    if bad not in combined_skip:
                        combined_skip.append(bad)
                print(f"[transponder201] Combined routing succeeded in {elapsed:.1f}s"
                      + (f", DR-FAILs: {dr_fails}" if dr_fails else ""))
                break

            # Identify crashing net and retry without it
            import re as _re
            failing = _re.findall(r'Route net (net_\w+)', proc.stdout + proc.stderr)
            if failing:
                bad = failing[-1]
                if bad not in combined_skip:
                    combined_skip.append(bad)
                    print(f"[transponder201] Retry {attempt+1}: excluding {bad}")
                    continue
            print(f"[transponder201] Combined routing FAILED (no new failing net) — "
                  f"falling back to isolated mode")
            break

        if succeeded:
            if combined_skip:
                print(f"[transponder201] Routing skipped nets {combined_skip} via isolated ...")
                _merge_skipped_nets_isolated(
                    combined_skip, base_cfg, dirname, ckt_name, place_file, route_file,
                    this_script, db, tDB, top_ckt_idx)
            top_ckt.setTechDB(tDB)
            top_ckt.parseGDS(route_file)
            pnr_stub = _make_pnr_stub(db, tDB, top_ckt_idx, params, dirname)
            pnr_stub.routerNets = list(range(num_nets))
            pnr_stub.upscaleBBox(pnr_stub.gridStep, top_ckt, pnr_stub.origin)
            return route_file, per_net_gds
        else:
            print("[transponder201] Combined failed, running isolated as fallback ...")
            write_anaroute_logging_json(dirname, enable_gr=False)
            mode = 'isolated'   # fall through

    # -----------------------------------------------------------------------
    # ISOLATED MODE (per-net, M1 only — also used as combined fallback)
    # -----------------------------------------------------------------------
    print(f"\n[transponder201] Routing {num_nets} nets ISOLATED (one subprocess per net) ...")

    def route_one_net(ni: int) -> str:
        """Route net ni in isolation; retry with 2× pin expansion if ACS fails."""
        net_name = db.subCkt(top_ckt_idx).net(ni).name
        out_gds  = dirname + f'{ckt_name}.route_{net_name}.gds'
        cfg_path = dirname + f'_iso_cfg_{ni}.json'
        with open(cfg_path, 'w') as f:
            json.dump(base_cfg, f)
        proc = subprocess.run(
            [sys.executable, this_script, '--route-mode', 'net-helper',
             cfg_path, str(ni), out_gds],
            timeout=120, capture_output=True, text=True,
            cwd=dirname,  # Anaroute reads anaroute_logging.json from CWD
        )
        if proc.returncode == 0 and os.path.exists(out_gds):
            return out_gds
        print(f"[transponder201] Net {net_name} failed (exit {proc.returncode})")
        return None

    import gdspy as _gdspy

    def _gds_shapes(path):
        lib = _gdspy.GdsLibrary()
        lib.read_gds(path)
        cells = lib.top_level()
        shapes = []
        if cells:
            for poly in cells[0].polygons:
                for i, pts in enumerate(poly.polygons):
                    shapes.append((poly.layers[i], poly.datatypes[i], pts))
        return shapes

    def _shape_key(layer, dtype, pts):
        return (layer, dtype, tuple(sorted((round(float(x), 1), round(float(y), 1))
                                           for x, y in pts)))

    base_shapes   = _gds_shapes(place_file)
    base_keys     = {_shape_key(l, d, p) for l, d, p in base_shapes}
    merged_extras = []   # routing wires from all nets

    for ni in range(num_nets):
        net_name = db.subCkt(top_ckt_idx).net(ni).name
        gds_path = route_one_net(ni)
        if gds_path:
            per_net_gds[net_name] = gds_path
            net_shapes = _gds_shapes(gds_path)
            new_shapes = [(l, d, p) for l, d, p in net_shapes
                          if _shape_key(l, d, p) not in base_keys]
            merged_extras.extend(new_shapes)
            print(f"[transponder201] {net_name}: {len(new_shapes)} new routing shapes")
        else:
            print(f"[transponder201] {net_name}: UNROUTED")

    # Merge all per-net routing wires into final route.gds
    base_lib = _gdspy.GdsLibrary()
    base_lib.read_gds(place_file)
    if base_lib.name is None:
        base_lib.name = 'CustomDesign'
    base_cell = base_lib.top_level()[0]
    for l, d, pts in merged_extras:
        base_cell.add(_gdspy.Polygon(pts, layer=l, datatype=d))
    base_lib.write_gds(route_file)
    print(f"[transponder201] Merged route.gds: {route_file} "
          f"({os.path.getsize(route_file)} bytes)")

    return route_file, per_net_gds


def _merge_skipped_nets_isolated(skip_list, base_cfg, dirname, ckt_name,
                                  place_file, route_file, this_script,
                                  db, tDB, top_ckt_idx):
    """Route skipped combined-mode nets via isolated and merge into route.gds."""
    import gdspy as _gdspy

    def _gds_shapes(path):
        lib = _gdspy.GdsLibrary(); lib.read_gds(path)
        cells = lib.top_level()
        shapes = []
        if cells:
            for poly in cells[0].polygons:
                for i, pts in enumerate(poly.polygons):
                    shapes.append((poly.layers[i], poly.datatypes[i], pts))
        return shapes

    def _sk(l, d, pts):
        return (l, d, tuple(sorted((round(float(x), 1), round(float(y), 1)) for x, y in pts)))

    ckt         = db.subCkt(top_ckt_idx)
    base_keys   = {_sk(l, d, p) for l, d, p in _gds_shapes(place_file)}
    combined_shapes = _gds_shapes(route_file)
    combined_extra  = [(l, d, p) for l, d, p in combined_shapes if _sk(l, d, p) not in base_keys]

    # Find net index by name
    name_to_idx = {ckt.net(i).name: i for i in range(ckt.numNets())}

    for net_name in skip_list:
        ni = name_to_idx.get(net_name)
        if ni is None:
            continue
        out_gds  = dirname + f'{ckt_name}.route_{net_name}.gds'
        cfg_path = dirname + f'_iso_cfg_skip_{ni}.json'
        with open(cfg_path, 'w') as f:
            json.dump(base_cfg, f)
        proc = subprocess.run(
            [sys.executable, this_script, '--route-mode', 'net-helper',
             cfg_path, str(ni), out_gds],
            timeout=120, capture_output=True, text=True,
            cwd=dirname,  # Anaroute reads anaroute_logging.json from CWD
        )
        if proc.returncode == 0 and os.path.exists(out_gds):
            net_shapes = _gds_shapes(out_gds)
            for l, d, p in net_shapes:
                if _sk(l, d, p) not in base_keys:
                    combined_extra.append((l, d, p))
            print(f"[transponder201] Skipped net {net_name}: ROUTED (isolated)")
        else:
            print(f"[transponder201] Skipped net {net_name}: FAILED")

    base_lib  = _gdspy.GdsLibrary(); base_lib.read_gds(place_file)
    if base_lib.name is None:
        base_lib.name = 'CustomDesign'
    cell = base_lib.top_level()[0]
    for l, d, p in combined_extra:
        cell.add(_gdspy.Polygon(p, layer=l, datatype=d))
    base_lib.write_gds(route_file)


def _make_pnr_stub(db, tDB, top_ckt_idx, params, dirname):
    """Create a minimal PnR object for upscaleBBox after combined routing."""
    import PnR as PnRModule

    class _MDB:
        pass
    mdb          = _MDB()
    mdb.designDB = type('_D', (), {'db': db})()
    mdb.techDB   = tDB
    mdb.params   = params

    pnr              = PnRModule.PnR(mdb)
    pnr.isTopLevel   = True
    pnr.dirname      = dirname if dirname.endswith('/') else dirname + '/'
    pnr.origin       = [10**9, 10**9]
    pnr.subShapeList = []
    ckt = db.subCkt(top_ckt_idx)
    ckt.setTechDB(tDB)
    bbox = ckt.layout().boundary()
    pnr.symAxis       = bbox.xHi + SYM_AXIS_MULT * (bbox.xHi - bbox.xLo)
    pnr.isSmallModule = False
    pnr.routerNets    = list(range(ckt.numNets()))
    pnr.findOrigin(top_ckt_idx)
    return pnr


# =============================================================================
# 8. GDS → JSON ROUTE SEGMENT EXTRACTION
# =============================================================================

def _poly_bbox_um(points) -> dict:
    """Convert polygon vertex array (µm floats) to axis-aligned bbox dict."""
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return {"x_min": min(xs), "y_min": min(ys), "x_max": max(xs), "y_max": max(ys)}


def _bboxes_touch(a: dict, b: dict, tol: float = 0.001) -> bool:
    return (a['x_min'] <= b['x_max'] + tol and a['x_max'] >= b['x_min'] - tol and
            a['y_min'] <= b['y_max'] + tol and a['y_max'] >= b['y_min'] - tol)


def extract_route_segments(route_gds: str, place_gds: str,
                            json_data: dict, per_net_gds: dict) -> dict:
    """
    Extract per-net routing segments from the GDS output.

    Isolated mode: reads per_net_gds files directly (exact per-net shapes).
    Combined mode: flood-fills route.gds shapes using pin rect seeds.

    Returns dict {net_id: {"status": str, "segments": [{"layer", "x_min", ...}]}}
    """
    import gdspy as _gdspy

    def _read_shapes(path):
        """Return list of {"layer_name": str, "bbox": dict} for routing layers."""
        lib = _gdspy.GdsLibrary(); lib.read_gds(path)
        cells = lib.top_level()
        shapes = []
        if cells:
            for poly in cells[0].polygons:
                for i, pts in enumerate(poly.polygons):
                    lname = GDS_LAYER_TO_NAME.get(poly.layers[i])
                    if lname:
                        shapes.append({"layer_name": lname, "bbox": _poly_bbox_um(pts)})
        return shapes

    def _shape_key_str(s):
        b = s['bbox']
        return (s['layer_name'],
                round(b['x_min'], 3), round(b['y_min'], 3),
                round(b['x_max'], 3), round(b['y_max'], 3))

    netlist       = json_data['netlist']
    placed_blocks = {pb['block_id']: pb for pb in json_data['placed_blocks']}
    net_result    = {}

    # Build net_id → list of known pin rects (M1 shapes with net assignment)
    net_pin_rects = {}
    for net_data in netlist['nets']:
        nid = net_data['net_id']
        net_pin_rects[nid] = []
        for pin_ref in net_data['pins']:
            parts  = pin_ref.split('_P')
            bid    = int(parts[0][1:])
            pin_k  = int(parts[1])
            placed = placed_blocks.get(bid)
            if placed is None:
                continue
            pkey  = f'B{bid}_P{pin_k}'
            prect = placed['pin_rects'].get(pkey)
            if prect:
                net_pin_rects[nid].append({"layer_name": "M1", "bbox": prect})

    # -----------------------------------------------------------------------
    # Isolated mode: read each per-net GDS directly
    # -----------------------------------------------------------------------
    if per_net_gds:
        place_shapes_set = {_shape_key_str(s) for s in _read_shapes(place_gds)}

        for net_data in netlist['nets']:
            nid = net_data['net_id']
            if nid in per_net_gds:
                net_shapes = _read_shapes(per_net_gds[nid])
                segments   = [{"layer": s["layer_name"], **s["bbox"]}
                               for s in net_shapes
                               if _shape_key_str(s) not in place_shapes_set]
                net_result[nid] = {"status": "routed", "segments": segments}
            else:
                net_result[nid] = {"status": "unrouted", "segments": []}
        return net_result

    # -----------------------------------------------------------------------
    # Combined mode: flood-fill routing shapes to nets via pin rect seeds
    # -----------------------------------------------------------------------
    place_shapes_set = {_shape_key_str(s) for s in _read_shapes(place_gds)}
    all_route_shapes = _read_shapes(route_gds)
    routing_shapes   = [s for s in all_route_shapes
                        if _shape_key_str(s) not in place_shapes_set]

    N           = len(routing_shapes)
    shape_net   = [None] * N

    def _connected(si, sj) -> bool:
        if si['layer_name'] == sj['layer_name']:
            return _bboxes_touch(si['bbox'], sj['bbox'])
        for via, (lo, hi) in VIA_CONNECTS.items():
            if si['layer_name'] == via and sj['layer_name'] in (lo, hi):
                return _bboxes_touch(si['bbox'], sj['bbox'])
            if sj['layer_name'] == via and si['layer_name'] in (lo, hi):
                return _bboxes_touch(si['bbox'], sj['bbox'])
        return False

    # Seed BFS from known pin rects
    queue = deque()
    for nid, pins in net_pin_rects.items():
        for pin in pins:
            for i, rs in enumerate(routing_shapes):
                if (rs['layer_name'] == pin['layer_name'] and
                        _bboxes_touch(rs['bbox'], pin['bbox'])):
                    if shape_net[i] is None:
                        shape_net[i] = nid
                        queue.append(i)

    while queue:
        i  = queue.popleft()
        si = routing_shapes[i]
        for j, sj in enumerate(routing_shapes):
            if shape_net[j] is None and _connected(si, sj):
                shape_net[j] = shape_net[i]
                queue.append(j)

    # Collect segments per net
    for net_data in netlist['nets']:
        nid = net_data['net_id']
        net_result[nid] = {"status": "unknown", "segments": []}

    for i, rs in enumerate(routing_shapes):
        if shape_net[i] is None:
            continue
        nid = shape_net[i]
        if nid in net_result:
            net_result[nid]["segments"].append({"layer": rs["layer_name"], **rs["bbox"]})

    for nid in net_result:
        if net_result[nid]["segments"]:
            net_result[nid]["status"] = "routed"
        else:
            net_result[nid]["status"] = "unrouted"

    return net_result


# =============================================================================
# 9. MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="py201 JSON → MAGICAL → ANAROUTE routing")

    # Sub-process routing modes (crash isolation)
    parser.add_argument('--route-mode', choices=['combined-helper', 'net-helper'],
                        help="Internal sub-process routing mode (do not call directly)")

    # Normal mode arguments
    parser.add_argument('--input',           required=False, help="Path to MAGICAL-ready JSON")
    parser.add_argument('--output',          default='/workspace/output_route/',
                        help="Output directory inside container")
    parser.add_argument('--techdir',         default='/workspace/generated_tech/',
                        help="Directory with techfile.simple, myPDK.lef, myPDK.techfile")
    parser.add_argument('--routing-mode',    default='combined',
                        choices=['combined', 'isolated'])
    parser.add_argument('--signal-width-nm', type=int, default=200)
    parser.add_argument('--power-width-nm',  type=int, default=500)
    _fr_group = parser.add_mutually_exclusive_group()
    _fr_group.add_argument('--enable-block-fr',    dest='enable_block_fr',
                           action='store_true',  default=True,
                           help="Add OD blockage shapes so FR enforcement avoids block interiors")
    _fr_group.add_argument('--no-enable-block-fr', dest='enable_block_fr',
                           action='store_false',
                           help="Disable OD blockage shapes (routing may pass through blocks)")

    args, extra = parser.parse_known_args()

    # -----------------------------------------------------------------------
    # Sub-process routing entry points
    # -----------------------------------------------------------------------
    if args.route_mode == 'combined-helper':
        _run_combined_helper(extra[0])
        return

    if args.route_mode == 'net-helper':
        _run_net_helper(extra[0], int(extra[1]), extra[2])
        return

    # -----------------------------------------------------------------------
    # Normal mode
    # -----------------------------------------------------------------------
    if not args.input:
        parser.error("--input is required in normal mode")

    input_json = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    techdir    = args.techdir.rstrip('/') + '/'
    os.makedirs(output_dir, exist_ok=True)

    with open(input_json) as f:
        json_data = json.load(f)

    simple_tech_file = techdir + 'techfile.simple'
    lef_file         = techdir + 'myPDK.lef'
    tech_file        = techdir + 'myPDK.techfile'

    for p in (simple_tech_file, lef_file, tech_file):
        if not os.path.exists(p):
            print(f"[transponder201] ERROR: required tech file not found: {p}")
            sys.exit(1)

    print(f"[transponder201] Building MagicalDB ...")
    db, tDB, top_ckt_idx, _, _ = build_magical_db(
        json_data, simple_tech_file, enable_block_fr=args.enable_block_fr)

    import Params as ParamsModule
    params = ParamsModule.Params()
    params.load('/install/MAGICAL/examples/ota1/ota1.json')
    params.simple_tech_file = simple_tech_file
    params.lef              = lef_file
    params.techfile         = tech_file
    params.resultDir        = output_dir
    params.signalAnalogWireWidthTable = [[0, args.signal_width_nm / 1000.0]]
    params.powerWireWidthTable        = [[0, args.power_width_nm  / 1000.0]]

    t0 = time.time()
    route_gds, per_net_gds = run_routing(
        db, tDB, top_ckt_idx, json_data, output_dir, params,
        mode=args.routing_mode,
        signal_width_nm=args.signal_width_nm,
        power_width_nm=args.power_width_nm,
        input_json_path=input_json,
        enable_block_fr=args.enable_block_fr,
    )
    t_routing = time.time() - t0

    place_gds = os.path.join(output_dir,
                             db.subCkt(top_ckt_idx).name + '.place.gds')

    print(f"\n[transponder201] Extracting per-net route segments ...")
    net_segments = extract_route_segments(route_gds, place_gds, json_data, per_net_gds)

    # Build route_data.json
    route_data = {
        "routing_mode": args.routing_mode,
        "t_routing_ms": round(t_routing * 1000),
        "nets": [],
    }
    routed_count   = 0
    unrouted_count = 0
    for net_data in json_data['netlist']['nets']:
        nid    = net_data['net_id']
        result = net_segments.get(nid, {"status": "unrouted", "segments": []})
        route_data["nets"].append({
            "net_id":   nid,
            "net_type": net_data.get("net_type", "signal"),
            "status":   result["status"],
            "segments": result["segments"],
        })
        if result["status"] != "unrouted":
            routed_count += 1
        else:
            unrouted_count += 1

    route_data["routed"]   = routed_count
    route_data["unrouted"] = unrouted_count

    route_data_path = os.path.join(output_dir, 'route_data.json')
    with open(route_data_path, 'w') as f:
        json.dump(route_data, f, indent=2)

    print(f"\n[transponder201] Done: {routed_count} routed, {unrouted_count} unrouted")
    print(f"  GDS:        {route_gds}")
    print(f"  route_data: {route_data_path}")


if __name__ == '__main__':
    main()
