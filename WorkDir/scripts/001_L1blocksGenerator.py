#!/usr/bin/env python3
"""
Generate random transistor blocks from gpdk090 PDK and save as placement-ready JSON.

Standalone:  python 001_L1blocksGenerator.py <num_blocks> <seed>
             Writes WorkDir/json_files/s{seed}_n{num_blocks}.json
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import copy
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_PDK_DIR = Path(__file__).parent.parent / "myPDK"

DEVICE_TYPES = ["nmos1v_nat", "nmos2v_nat", "pmos1v_nat", "pmos2v_nat"]

# Minimum centre-to-centre distance between any two pins on the same bbox edge.
# 0.5 um pin square + 0.12 um M1 min_spacing (gpdk090 DRM).
_PIN_MIN_PITCH = 0.62

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)

# =============================================================================
# 4. ALGORITHM
# =============================================================================

def snap_to_grid(value: float, grid: float) -> float:
    return round(round(value / grid) * grid, 6)


def snap_to_step(value: float, step: float) -> float:
    return round(round(value / step) * step, 6)


def center_pin_positions(num_pins: int, W: float, H: float, grid: float) -> dict:
    """Return num_pins positions all at the bbox centre. Will be adjusted later."""
    cx = snap_to_grid(W / 2, grid)
    cy = snap_to_grid(H / 2, grid)
    return {f"P{i}": {"x": cx, "y": cy} for i in range(num_pins)}


def rotate_variant_90cw(v: dict, grid: float) -> dict:
    """Return a 90 CW rotated copy: bbox W x H becomes H x W, pins re-centred."""
    bb = v["main_bbox"]
    W, H     = bb["x_max"], bb["y_max"]
    W_new, H_new = H, W
    num_pins = len(v["pin_positions"])
    ar_new   = round(W_new / H_new, 3) if H_new > 0 else 0
    return {
        "layout": {
            "rows": v["layout"]["cols"],
            "cols": v["layout"]["rows"],
            "aspect_ratio": ar_new,
        },
        "main_bbox": {"x_min": 0.0, "y_min": 0.0, "x_max": W_new, "y_max": H_new},
        "pin_positions": center_pin_positions(num_pins, W_new, H_new, grid),
        "is_used": False,
        "rotation_deg": 90,
    }


def append_rotation_90(variants: list, rotation_cfg: dict, grid: float) -> None:
    """Extend variants in-place with a 90 CW copy per rotation_cfg probability."""
    if not rotation_cfg:
        return
    prob_90 = rotation_cfg.get("prob_90", 0.0)
    dedup   = rotation_cfg.get("deduplicate_square", True)

    for base in list(variants):
        W, H = base["main_bbox"]["x_max"], base["main_bbox"]["y_max"]
        if dedup and abs(W - H) < grid:
            continue
        if random.random() < prob_90:
            variants.append(rotate_variant_90cw(base, grid))


def wmi_generate_transistor_block(
    tech_file: dict,
    width: float, length: float,
    multiplier: int, num_fingers: int,
    min_aspect: float, max_aspect: float,
    device_type: str,
    num_pins: int,
) -> dict:
    """Generate all valid layout variants for one transistor block."""
    grid = tech_file["technology_info"]["manufacturing_grid"]

    device = tech_file["device_constraints"][device_type]
    assert device["L"]["min"] <= length <= device["L"]["max"], \
        f"Length {length} outside [{device['L']['min']}, {device['L']['max']}]"
    assert device["W"]["min"] <= width <= device["W"]["max"], \
        f"Width {width} outside [{device['W']['min']}, {device['W']['max']}]"

    rules          = tech_file["physical_design_rules"]
    poly_width     = rules["poly"]["min_width"]
    poly_spacing   = rules["poly"]["min_spacing"]
    active_spacing = rules["active"]["min_spacing"]
    contact_size   = rules["contact"]["size"]
    contact_enc    = rules["contact"]["enclosure_by_active"]

    w_finger  = width / num_fingers
    finger_wc = w_finger + 2 * (contact_enc + contact_size)
    f_pitch   = finger_wc + poly_width + poly_spacing

    total_fingers = multiplier * num_fingers
    variants: list = []

    for n_rows in range(1, total_fingers + 1):
        if total_fingers % n_rows != 0:
            continue
        n_cols = total_fingers // n_rows

        block_W = snap_to_grid(n_cols * f_pitch - poly_spacing, grid)
        block_H = snap_to_grid(n_rows * (w_finger + active_spacing) - active_spacing, grid)

        if block_H == 0:
            continue
        ar = block_W / block_H
        if not (min_aspect <= ar <= max_aspect):
            continue

        variants.append({
            "layout": {"rows": n_rows, "cols": n_cols, "aspect_ratio": round(ar, 3)},
            "main_bbox": {"x_min": 0.0, "y_min": 0.0, "x_max": block_W, "y_max": block_H},
            "pin_positions": center_pin_positions(num_pins, block_W, block_H, grid),
            "is_used": False,
            "rotation_deg": 0,
        })

    return {
        "device_type": device_type,
        "parameters": {
            "width": width, "length": length,
            "multiplier": multiplier, "num_fingers": num_fingers,
            "total_fingers": total_fingers,
        },
        "variants": variants,
    }


def _shift_power_pin(pins: dict, moved_key: str, W: float, H: float, grid: float) -> None:
    """Push any pin within _PIN_MIN_PITCH of the power pin away along its edge."""
    pwr = pins[moved_key]
    for key, pos in list(pins.items()):
        if key == moved_key:
            continue
        dx   = pos["x"] - pwr["x"]
        dy   = pos["y"] - pwr["y"]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < _PIN_MIN_PITCH - grid:
            on_horizontal = pwr["y"] == 0.0 or abs(pwr["y"] - H) < grid
            if on_horizontal:
                direction = 1 if pos["x"] >= pwr["x"] else -1
                nx = snap_to_grid(pwr["x"] + direction * _PIN_MIN_PITCH, grid)
                pins[key] = {"x": max(0.0, min(snap_to_grid(W, grid), nx)), "y": pos["y"]}
            else:
                direction = 1 if pos["y"] >= pwr["y"] else -1
                ny = snap_to_grid(pwr["y"] + direction * _PIN_MIN_PITCH, grid)
                pins[key] = {"x": pos["x"], "y": max(0.0, min(snap_to_grid(H, grid), ny))}


def wmi_adjust_power_pin_positions(blocks: list, grid: float) -> None:
    """Move P0 of VDD blocks to top edge, VSS blocks to bottom edge."""
    for block in blocks:
        if "error" in block:
            continue
        rail = block.get("power_rail")
        if rail is None:
            continue
        for variant in block.get("variants", []):
            pins = variant.get("pin_positions", {})
            if "P0" not in pins:
                continue
            bb  = variant["main_bbox"]
            W   = snap_to_grid(bb["x_max"] - bb["x_min"], grid)
            H   = snap_to_grid(bb["y_max"] - bb["y_min"], grid)
            p0x = pins["P0"]["x"]
            pins["P0"] = {"x": p0x, "y": H if rail == "VDD" else 0.0}
            _shift_power_pin(pins, "P0", W, H, grid)


def wmi_decide_symmetry_roles(num_blocks: int, config: dict, seed: int) -> dict:
    """
    Pre-assign device types and symmetry roles before generation.
    Uses an independent RNG (seed+7777) so symmetry decisions do not disturb
    the main block-generation RNG sequence.
    """
    rng = random.Random(seed + 7777)
    sym_cfg   = config.get("symmetry", {})
    pair_prob = sym_cfg.get("pair_probability", 0.4)
    self_prob = sym_cfg.get("self_sym_probability", 0.15)

    device_type_map = {i: rng.choice(DEVICE_TYPES) for i in range(num_blocks)}

    by_type: dict = {}
    for idx, dt in device_type_map.items():
        by_type.setdefault(dt, []).append(idx)

    all_pairs: list    = []
    all_self_sym: list = []
    groups: list       = []

    for dt, indices in by_type.items():
        rng.shuffle(indices)
        pairs: list    = []
        self_sym: list = []
        i = 0
        while i + 1 < len(indices):
            if rng.random() < pair_prob:
                a, b = sorted((indices[i], indices[i + 1]))
                pairs.append((a, b))
                i += 2
            else:
                i += 1
        while i < len(indices):
            if rng.random() < self_prob:
                self_sym.append(indices[i])
            i += 1

        all_pairs.extend(pairs)
        all_self_sym.extend(self_sym)
        if pairs or self_sym:
            groups.append({
                "device_type":     dt,
                "pair_indices":    pairs,
                "self_sym_indices": self_sym,
            })

    return {
        "pairs":           all_pairs,
        "self_symmetric":  all_self_sym,
        "device_type_map": device_type_map,
        "groups":          groups,
    }


def wmi_assign_power_nets(
    valid_blocks: list, power_config: dict, paired_blocks: list
) -> dict:
    """Assign VDD or VSS to >= coverage_min fraction of blocks."""
    b_set    = {b for _, b in paired_blocks}
    eligible = [b for b in valid_blocks if b["block_id"] not in b_set]
    cov_min  = power_config.get("coverage_min", 0.6)
    n_pwr    = min(math.ceil(cov_min * len(valid_blocks)), len(eligible))
    sampled  = random.sample(eligible, n_pwr)
    assign   = {b["block_id"]: random.choice(["VDD", "VSS"]) for b in sampled}
    # block_b inherits block_a's rail so symmetric pairs share the same power net
    for a_id, b_id in paired_blocks:
        if a_id in assign:
            assign[b_id] = assign[a_id]
    return assign


def wmi_generate_symmetry_aware_netlist(
    blocks: list, sym_roles: dict, config: dict, seed: int
) -> tuple:
    """Build power + signal nets with symmetry awareness. Returns (netlist, sym_pairs, self_sym_nets)."""
    random.seed(seed + 1111)

    nl_cfg  = config["netlist"]
    density = nl_cfg["density"]

    valid    = [b for b in blocks if "error" not in b]
    n_blocks = len(valid)
    bmap     = {b["block_id"]: b for b in valid}

    paired_set   = {idx for pair in sym_roles["pairs"] for idx in pair}
    self_sym_set = set(sym_roles["self_symmetric"])

    power_assign = wmi_assign_power_nets(
        valid, config.get("power_nets", {}), sym_roles["pairs"]
    )
    vdd_pins: list = []
    vss_pins: list = []
    for b in valid:
        bid  = b["block_id"]
        rail = power_assign.get(bid)
        b["power_rail"] = rail
        if rail == "VDD":
            vdd_pins.append(f"B{bid}_P0")
        elif rail == "VSS":
            vss_pins.append(f"B{bid}_P0")

    nets: list = []
    if vdd_pins:
        nets.append({"net_id": "VDD", "net_type": "power", "pins": vdd_pins})
    if vss_pins:
        nets.append({"net_id": "VSS", "net_type": "power", "pins": vss_pins})
    n_power = len(nets)

    net_ctr = 0
    sym_net_pairs: list = []
    self_sym_nets: list = []

    for a, b in sym_roles["pairs"]:
        if a not in bmap or b not in bmap:
            continue
        start = 1 if a in power_assign else 0
        for k in range(start, bmap[a]["num_pins"]):
            xid = f"net_{net_ctr}"
            yid = f"net_{net_ctr + 1}"
            nets.append({"net_id": xid, "net_type": "signal", "pins": [f"B{a}_P{k}"]})
            nets.append({"net_id": yid, "net_type": "signal", "pins": [f"B{b}_P{k}"]})
            sym_net_pairs.append({
                "net_a": xid, "net_b": yid,
                "block_pair": [a, b], "pin_index": k,
            })
            net_ctr += 2

    for s in sym_roles["self_symmetric"]:
        if s not in bmap:
            continue
        start = 1 if s in power_assign else 0
        for k in range(start, bmap[s]["num_pins"]):
            nid = f"net_{net_ctr}"
            nets.append({"net_id": nid, "net_type": "signal", "pins": [f"B{s}_P{k}"]})
            self_sym_nets.append(nid)
            net_ctr += 1

    free_pins: list = []
    for b in valid:
        bid = b["block_id"]
        if bid in paired_set or bid in self_sym_set:
            continue
        start = 1 if bid in power_assign else 0
        for k in range(start, b["num_pins"]):
            free_pins.append({"block_id": bid, "pin_name": f"B{bid}_P{k}"})
    random.shuffle(free_pins)

    fp_idx = 0
    for snp in sym_net_pairs:
        if fp_idx + 1 >= len(free_pins):
            break
        next(n for n in nets if n["net_id"] == snp["net_a"])["pins"].append(
            free_pins[fp_idx]["pin_name"])
        next(n for n in nets if n["net_id"] == snp["net_b"])["pins"].append(
            free_pins[fp_idx + 1]["pin_name"])
        fp_idx += 2

    for sn_id in self_sym_nets:
        if fp_idx >= len(free_pins):
            break
        next(n for n in nets if n["net_id"] == sn_id)["pins"].append(
            free_pins[fp_idx]["pin_name"])
        fp_idx += 1

    remaining = free_pins[fp_idx:]
    used: set  = set()
    target_sig = max(2, int(density * n_blocks))
    cur_sig    = sum(1 for n in nets if n["net_type"] == "signal")

    avail = [p for p in remaining if p["pin_name"] not in used]
    while cur_sig < target_sig and len(avail) >= 2:
        size     = min(random.randint(2, 4), len(avail))
        cluster: list = []
        bids: set    = set()
        for pin in avail:
            if len(cluster) >= size:
                break
            if pin["block_id"] not in bids or not cluster:
                cluster.append(pin)
                bids.add(pin["block_id"])
        if len(bids) >= 2:
            nid = f"net_{net_ctr}"
            nets.append({
                "net_id": nid, "net_type": "signal",
                "pins": [p["pin_name"] for p in cluster],
            })
            net_ctr += 1
            cur_sig += 1
            for p in cluster:
                used.add(p["pin_name"])
        else:
            for p in cluster:
                used.add(p["pin_name"])
        avail = [p for p in remaining if p["pin_name"] not in used]

    all_sig = [n for n in nets if n["net_type"] == "signal"]
    for pin in [p for p in remaining if p["pin_name"] not in used]:
        if all_sig:
            random.choice(all_sig)["pins"].append(pin["pin_name"])

    n_sig    = len(nets) - n_power
    tot_pins = sum(b["num_pins"] for b in valid)
    netlist = {
        "num_nets":        len(nets),
        "num_power_nets":  n_power,
        "num_signal_nets": n_sig,
        "num_pins":        tot_pins,
        "density":         round(n_sig / n_blocks, 2) if n_blocks > 0 else 0,
        "power_coverage":  round(len(power_assign) / n_blocks, 2) if n_blocks > 0 else 0,
        "nets":            nets,
    }
    return netlist, sym_net_pairs, self_sym_nets


def wmi_build_symmetry_output(
    sym_roles: dict, sym_net_pairs: list, self_sym_nets: list
) -> dict:
    groups = [
        {
            "group_id":       gid,
            "device_type":    g["device_type"],
            "pairs":          [{"block_a": a, "block_b": b} for a, b in g["pair_indices"]],
            "self_symmetric": list(g["self_sym_indices"]),
        }
        for gid, g in enumerate(sym_roles["groups"])
    ]
    return {
        "symmetry_axis":       "vertical",
        "groups":              groups,
        "symmetric_net_pairs": sym_net_pairs,
        "self_symmetric_nets": self_sym_nets,
    }


def wmi_generate_random_blocks(
    tech_file: dict, config: dict, num_blocks: int, seed: int
) -> dict:
    """Top-level generator: create all blocks, netlist, and symmetry constraints."""
    grid     = tech_file["technology_info"]["manufacturing_grid"]
    gen_p    = config["generation_params"]
    L_step   = gen_p["length_range"]["step"]
    W_step   = gen_p["width_range"]["step"]
    M_min    = gen_p["multiplier_range"]["min"]
    M_max    = gen_p["multiplier_range"]["max"]
    NF_min   = gen_p["num_fingers_range"]["min"]
    NF_max   = gen_p["num_fingers_range"]["max"]
    ar_cfg   = gen_p["aspect_ratio"]
    design_c = config["design_constraints"]
    rot_cfg  = config.get("rotation_variants")
    pins_min = config["netlist"]["pins_per_block_min"]
    pins_max = config["netlist"]["pins_per_block_max"]
    max_att  = config["validation"]["max_generation_attempts"]

    sym_roles = wmi_decide_symmetry_roles(num_blocks, config, seed)
    pair_b2a  = {b: a for a, b in sym_roles["pairs"]}
    self_sym  = set(sym_roles["self_symmetric"])

    random.seed(seed)

    blocks: list    = []
    gen_cache: dict = {}

    for i in range(num_blocks):
        device_type = sym_roles["device_type_map"][i]
        block = None

        if i in pair_b2a:
            a_idx = pair_b2a[i]
            ab    = gen_cache[a_idx]
            if "error" not in ab:
                block = {
                    "device_type":         ab["device_type"],
                    "block_id":            i,
                    "parameters":          copy.deepcopy(ab["parameters"]),
                    "variants":            copy.deepcopy(ab["variants"]),
                    "num_pins":            ab["num_pins"],
                    "generation_attempts": 1,
                }
            else:
                block = {
                    "block_id": i,
                    "error":    f"Pair partner {a_idx} failed generation",
                    "generation_attempts": 0,
                }
        else:
            num_pins = random.randint(pins_min, pins_max)
            dc = design_c[device_type]

            for attempt in range(max_att):
                try:
                    L  = snap_to_step(random.uniform(dc["L"]["min"], dc["L"]["max"]), L_step)
                    W  = snap_to_step(random.uniform(dc["W"]["min"], dc["W"]["max"]), W_step)
                    M  = random.randrange(M_min, M_max + 1, 2)
                    NF = random.randint(NF_min, NF_max)
                    min_ar = round(random.uniform(ar_cfg["min_aspect_min"], ar_cfg["min_aspect_max"]), 2)
                    max_ar = round(random.uniform(ar_cfg["max_aspect_min"], ar_cfg["max_aspect_max"]), 2)

                    tb = wmi_generate_transistor_block(
                        tech_file, W, L, M, NF, min_ar, max_ar, device_type, num_pins
                    )

                    if tb["variants"]:
                        append_rotation_90(tb["variants"], rot_cfg, grid)
                        block = {
                            "device_type":         tb["device_type"],
                            "block_id":            i,
                            "parameters":          tb["parameters"],
                            "variants":            tb["variants"],
                            "num_pins":            num_pins,
                            "generation_attempts": attempt + 1,
                        }
                        logger.debug("Block %d (%s): %d variant(s), attempt %d",
                                     i, device_type, len(block["variants"]), attempt + 1)
                        break

                except Exception as exc:
                    logger.debug("Block %d attempt %d: %s", i, attempt, exc)
                    if attempt == max_att - 1:
                        block = {
                            "block_id":            i,
                            "error":               str(exc),
                            "generation_attempts": max_att,
                        }

            if block is None:
                block = {
                    "block_id":            i,
                    "error":               "No valid variants found",
                    "generation_attempts": max_att,
                }
                logger.warning("Block %d (%s): failed after %d attempts",
                               i, device_type, max_att)

        # Self-symmetric blocks may only use 0 deg rotation (vertical axis constraint)
        if i in self_sym and "error" not in block:
            block["variants"] = [v for v in block["variants"] if v.get("rotation_deg", 0) == 0]

        # Mark the first variant as the default selected layout
        if "error" not in block and block.get("variants"):
            block["variants"][0]["is_used"] = True

        blocks.append(block)
        gen_cache[i] = block

    netlist, sym_pairs, self_sym_nets = wmi_generate_symmetry_aware_netlist(
        blocks, sym_roles, config, seed
    )
    wmi_adjust_power_pin_positions(blocks, grid)
    sym_constraints = wmi_build_symmetry_output(sym_roles, sym_pairs, self_sym_nets)

    logger.info("Generated %d blocks, %d nets (%d power, %d signal)",
                num_blocks, netlist["num_nets"],
                netlist["num_power_nets"], netlist["num_signal_nets"])

    return {
        "generation_params": {"num_of_blocks": num_blocks, "seed": seed},
        "technology":        tech_file["technology_info"]["name"],
        "blocks":            blocks,
        "netlist":           netlist,
        "symmetry_constraints": sym_constraints,
    }

# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(num_blocks: int, seed: int) -> dict:
    """Load PDK, generate blocks, and return the result dict. File saving is handled by main.py."""
    with open(_PDK_DIR / "gpdk090_tech_simple.json", encoding="utf-8") as f:
        tech_data = json.load(f)
    with open(_PDK_DIR / "gpdk090_device_rules.json", encoding="utf-8") as f:
        device_rules = json.load(f)
    tech_file = {**tech_data, **device_rules}

    with open(_PDK_DIR / "generation_config.json", encoding="utf-8") as f:
        config = json.load(f)

    return wmi_generate_random_blocks(tech_file, config, num_blocks, seed)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        try:
            run(int(sys.argv[1]), int(sys.argv[2]))
        except ValueError:
            logger.error("Arguments must be integers: <num_blocks> <seed>")
            sys.exit(1)
    else:
        logger.error("Usage: 001_L1blocksGenerator.py <num_blocks> <seed>")
        sys.exit(1)
