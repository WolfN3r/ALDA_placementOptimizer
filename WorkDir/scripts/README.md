# ALDA Placement Optimizer — Scripts

Analog IC block placement engine for gpdk090 technology.
Separates **topology**, **optimizer**, and **cost evaluation** into independent layers so any combination can be compared with a single run.

---

## Quick Start

```bash
# Run the full pipeline (block generation → placement optimization)
cd WorkDir/scripts
python main.py
```

Output JSON files land in `WorkDir/json_files/`.
Log files land in `WorkDir/logs/`.

### Run the optimizer standalone on an existing block JSON

```bash
python 101_placementOptimizer.py ../json_files/s42_n10_py001_v01.json
# writes → ../json_files/s42_n10_py101_v01.json
```

---

## Prerequisites

- Python 3.9+
- No external packages required — stdlib only (`json`, `math`, `random`, `abc`, `dataclasses`, `collections`)

---

## File Naming Convention

Scripts follow the pattern `{stage}{index}_nameOfScript.py`:

| Prefix | Stage | Meaning |
|--------|-------|---------|
| `001`  | Stage 0, Script 01 | Block generation (pre-placement) |
| `101`  | Stage 1, Script 01 | Placement optimizer |

Output JSON files: `s{seed}_n{n_blocks}_py{prefix}_{version}.json`

---

## Scripts

### `main.py` — Pipeline Hub

Runs all stages in sequence. Edit the configuration block at the top:

| Constant | Default | Effect |
|----------|---------|--------|
| `SEED` | `42` | RNG seed for block generation |
| `NUM_BLOCKS` | `10` | Number of transistor blocks to generate |
| `SAVE_FILES` | `True` | `False` → dry run, no files written |
| `VERSION` | `"v01"` | Version tag in output filenames |

---

### `001_L1blocksGenerator.py` — Block Generator

Generates random transistor blocks from the gpdk090 PDK with symmetry constraints and a netlist. Produces the input JSON for stage 1.

**Reads from:** `WorkDir/myPDK/`
**Outputs:** `{blocks[], netlist{}, symmetry_constraints{}, generation_params{}}`

---

### `101_placementOptimizer.py` — Placement Optimizer ✅ Ready to run

Runs the placement optimization on a block+netlist JSON.
Tries multiple (topology, optimizer) combinations and reports which produced the best result.

**Configuration constants** (edit section 2 of the script):

| Constant | Default | Effect |
|----------|---------|--------|
| `RUN_MODE` | `"exhaustive"` | `"exhaustive"` runs all supported combinations; `"random"` picks one at random |
| `SEED_MODE` | `"random"` | Initial topology seed strategy: `"random"` or `"ordered"` |
| `SA_INITIAL_TEMP` | `0.0` | SA starting temperature. `0.0` → auto-calibrated from the netlist |
| `SA_FINAL_TEMP` | `1e-4` | SA stopping temperature |
| `SA_MAX_ITER` | `0` | `0` → computed as `epoch_size × 200` |
| `SA_EPOCH_SIZE` | `0` | `0` → computed as `max(n_blocks × 8, 50)` |
| `SA_STAGNATION` | `15` | Epochs without improvement before reheating |
| `W_AREA` | `0.6` | Cost weight for bounding-box area |
| `W_WL` | `0.1` | Cost weight for half-perimeter wirelength |
| `W_AR` | `0.3` | Cost weight for aspect-ratio penalty |
| `TARGET_AR` | `1.0` | Target aspect ratio (width/height) for the full placement |
| `DEBUG` | `False` | `True` → prints debug messages to stderr |

**Output JSON structure:**
```json
{
  "generation_params": { ... },
  "technology": "gpdk090_simple_tech",
  "netlist": { ... },
  "symmetry_constraints": { ... },
  "placement_results": {
    "netlist_id": "s42_n10",
    "runs": [
      {
        "run_id": "BStarTopology+SimulatedAnnealingOptimizer",
        "topology": "BStarTopology",
        "optimizer": "SimulatedAnnealingOptimizer",
        "status": "success",
        "metrics": {
          "final_cost": 0.523,
          "area_um2": 1250.0,
          "hpwl_um": 340.0,
          "aspect_ratio": 1.12,
          "n_iterations": 85000,
          "t_seed_ms": 2.1,
          "t_optimize_ms": 4180.0,
          "t_total_ms": 4200.0
        },
        "positions": { "0": [10.5, 20.0], "1": [34.2, 20.0] }
      }
    ],
    "summary": {
      "best_cost_run": "SequencePairTopology+SimulatedAnnealingOptimizer",
      "fastest_run": "BStarTopology+SimulatedAnnealingOptimizer",
      "rank_by_cost": [ ... ],
      "rank_by_runtime": [ ... ],
      "failed_runs": []
    }
  }
}
```

---

## Library Modules (`lib/`)

| File | What it does |
|------|-------------|
| `log_setup.py` | Shared logger — always writes to `logs/`, mirrors to stderr when `DEBUG=True` |
| `spacing.py` | `compute_block_spacing(a, b) → SpacingResult` — DRC clearance between two blocks, backed by `gpdk090_device_rules.json` |
| `topology_base.py` | Abstract base classes: `TopologyBase`, `SAMixin`, `GAMixin` — the interface that optimizers program against |
| `cost_evaluator.py` | `CostEvaluator.evaluate(positions)` — normalized area + HPWL + aspect-ratio cost, topology-agnostic |
| `sa_optimizer.py` | `SimulatedAnnealingOptimizer` — Huang 1986 adaptive cooling, undo-closure loop, auto-calibration |
| `bstar_topology.py` | `BStarTopology` — B\*-tree with typed contour DFS decode, 4 SA operators (rotate/swap/move/variant), GA crossover via OX+binary encoding |
| `seqpair_topology.py` | `SequencePairTopology` — H/V-DAG longest-path decode, M1/M2/M3 SA operators, PMX GA crossover |
| `pipeline.py` | `OptimizationPipeline` — wires topology + optimizer together; checks compatibility at construction; times each phase |
| `solver_picker.py` | `SolverPicker` — selects combinations (random/exhaustive/ML); `ResultLog` — appends results to `logs/result_log.jsonl` |

---

## Supported Combinations

| Topology | Optimizer | Status |
|----------|-----------|--------|
| `BStarTopology` | `SimulatedAnnealingOptimizer` | ✅ Supported |
| `SequencePairTopology` | `SimulatedAnnealingOptimizer` | ✅ Supported |
| `SequencePairTopology` | `GeneticOptimizer` | 🔲 Planned |
| `BStarTopology` | `GeneticOptimizer` | 🔬 Experimental (planned) |

---

## What Is Implemented vs. Stub

### ✅ Fully implemented and runnable
- B\*-tree topology: `seed()`, `decode()` with typed contour, all 4 SA operators with correct undo closures, `copy_state()` / `restore_state()`
- Sequence-pair topology: `seed()`, `decode()` with H/V-DAG longest-path, M1/M2/M3 SA operators, PMX crossover
- SA optimizer: Metropolis loop, Huang 1986 adaptive cooling, reheating, temperature auto-calibration
- Cost evaluator: normalized area, HPWL, aspect-ratio penalty
- Compatibility registry + pipeline orchestration with per-phase timing
- Exhaustive mode: runs all supported combinations, ranks by cost and runtime
- Result log: appends every run (including failures) to `logs/result_log.jsonl`
- GA crossover infrastructure: OX+binary encoding for B\*-tree, PMX for sequence pair

### 🔲 Planned (architecture designed, not yet coded)
- `GeneticOptimizer` loop (population, selection, replacement)
- Symmetry super-blocks (step 13 in implementation order)
- `ConsoleObserver` / `TraceObserver` (step 14) — `NullObserver` is the default
- Cython acceleration of `decode()` inner loop (step 15, requires profiling first)
- ML solver picker — data collection runs now; model training is future work

---

## Architecture Reference

The full design specification is at:
`.claude/plans/universal_optimizer_architecture.md`

Key design rule: **`topology.decode()` is the only path from topology state to block coordinates.** The optimizer never imports topology-specific logic.

---

## Logs and Traces

| Path | Content |
|------|---------|
| `WorkDir/logs/<script>.log` | Full debug log for each script run (always written) |
| `WorkDir/logs/result_log.jsonl` | One JSON line per exhaustive run — all combinations including failures |
| `WorkDir/traces/` | Per-run improvement traces (opt-in, disabled by default) |
