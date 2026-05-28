#!/usr/bin/env python3
"""
Placement optimizer hub — run pipeline scripts and optionally save their output.

Edit the CONFIGURATION block below, then run:
    python main.py

CLI usage (used by the viewer's Simulate dialog):
    python main.py --seed 42 --num-blocks 15 --run-mode random
    python main.py --seed 7  --num-blocks 10 --run-mode user \
                   --topology BStarTopology --optimizer SimulatedAnnealingOptimizer
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION  (edit here — CLI args override these when provided)
# =============================================================================
SEED       =  42    # random seed passed to every script
NUM_BLOCKS = 15    # number of transistor blocks to generate

SAVE_FILES = True  # False → run without writing any files to disk
VERSION    = "v01" # json structure version tag (see testFiles_naming.md)

_OUTPUT_DIR = Path(__file__).parent.parent / "json_files"

# =============================================================================
# HELPERS
# =============================================================================

def _load_script(filename: str):
    """Import a same-directory script by filename (names may start with digits)."""
    path = Path(__file__).parent / filename
    spec = importlib.util.spec_from_file_location(filename, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _save(data: dict, script_id: str, version: str = VERSION) -> None:
    """Save data to json_files/ using the project naming convention."""
    n  = data["generation_params"]["num_of_blocks"]
    s  = data["generation_params"]["seed"]
    _OUTPUT_DIR.mkdir(exist_ok=True)
    out = _OUTPUT_DIR / f"s{s}_n{n}_py{script_id}_{version}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out}", file=sys.stderr)

# =============================================================================
# PIPELINE
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALDA placement optimizer hub")
    parser.add_argument("--seed",       type=int, default=SEED,       help="Random seed (default: %(default)s)")
    parser.add_argument("--num-blocks", type=int, default=NUM_BLOCKS, help="Number of transistor blocks, ignored when --netlist is given (default: %(default)s)")
    parser.add_argument("--netlist",    default="",  help="Path to a SPICE .sp netlist; activates netlist-driven block generation (011)")
    parser.add_argument("--run-mode",   default="exhaustive",         choices=["random", "exhaustive", "user"],
                        help="Solver selection mode (default: %(default)s)")
    parser.add_argument("--topology",   default="",  help="Topology class name (required when --run-mode user)")
    parser.add_argument("--optimizer",  default="",  help="Optimizer class name (required when --run-mode user)")
    parser.add_argument("--version",    default=VERSION, help="Output version tag (default: %(default)s)")
    args = parser.parse_args()

    seed       = args.seed
    num_blocks = args.num_blocks
    version    = args.version

    # --- Stage 1: block generation ---
    if args.netlist:
        gen = _load_script("011_netlisBlocksGenerator.py")
        blocks_data: dict = gen.run(args.netlist, seed)
        script_id_gen = "011"
    else:
        gen = _load_script("001_L1blocksGenerator.py")
        blocks_data: dict = gen.run(num_blocks, seed)
        script_id_gen = "001"

    if SAVE_FILES:
        _save(blocks_data, script_id_gen, version)

    # --- Stage 2: Placement optimization ---
    opt = _load_script("101_placementOptimizer.py")

    # Override module constants so the optimizer uses the CLI-specified mode
    opt.RUN_MODE  = args.run_mode if args.run_mode != "user" else "exhaustive"
    opt.TOPOLOGY  = args.topology if args.run_mode == "user" else ""
    opt.OPTIMIZER = args.optimizer if args.run_mode == "user" else ""

    placement_data: dict = opt.run(blocks_data)

    if SAVE_FILES:
        _save(placement_data, "101", version)
