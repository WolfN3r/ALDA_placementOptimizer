#!/usr/bin/env python3
"""
Placement optimizer hub — run pipeline scripts and optionally save their output.

Edit the CONFIGURATION block below, then run:
    python main.py
"""

import importlib.util
import json
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION  (edit here)
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


def _save(data: dict, script_id: str) -> None:
    """Save data to json_files/ using the project naming convention."""
    n  = data["generation_params"]["num_of_blocks"]
    s  = data["generation_params"]["seed"]
    _OUTPUT_DIR.mkdir(exist_ok=True)
    out = _OUTPUT_DIR / f"s{s}_n{n}_py{script_id}_{VERSION}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out}", file=sys.stderr)

# =============================================================================
# PIPELINE
# =============================================================================

if __name__ == "__main__":
    # --- Stage 1: L1 block generation ---
    gen = _load_script("001_L1blocksGenerator.py")
    blocks_data: dict = gen.run(NUM_BLOCKS, SEED)

    if SAVE_FILES:
        _save(blocks_data, "001")

    # --- Stage 1, Script 01: Placement optimization ---
    opt = _load_script("101_placementOptimizer.py")
    placement_data: dict = opt.run(blocks_data)

    if SAVE_FILES:
        _save(placement_data, "101")
