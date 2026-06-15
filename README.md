# ALDA Placement Optimizer

Analog-IC block placement engine for the `gpdk090` (90 nm) technology.
Generates blocks (random or from a SPICE netlist), then optimizes their 2D arrangement
(`B*-tree` / `Sequence Pair` topologies, Simulated Annealing, ILP, PSO) under symmetry constraints.
Includes a PyQt6 viewer with DRC checking, routing via MAGICAL Anaroute, and GDS export.

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Python 3.9+. Gurobi (free academic licence) is required for ILP-based optimizers — all other topologies work without it.

## Run the optimizer

```bash
cd WorkDir/scripts

# Default — try every topology/optimizer combo and rank results
python main.py

# From a SPICE netlist
python main.py --netlist "../#Netlists/a11_five_transistor_ota.sp" --seed 42

# Single topology/optimizer pair
python main.py --run-mode user --topology BStarTopology --optimizer SimulatedAnnealingOptimizer

# Skip the Anaroute routing stage
python main.py --no-routing
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--seed INT` | `42` | Random seed passed to every pipeline stage |
| `--num-blocks INT` | `15` | Number of transistor blocks to generate (ignored when `--netlist` is set) |
| `--netlist PATH` | — | Path to a SPICE `.sp` netlist; activates netlist-driven block generation (stage 011) instead of random generation (stage 001) |
| `--run-mode` | `exhaustive` | `random` — one random combo; `exhaustive` — all combos ranked; `user` — specify topology + optimizer explicitly |
| `--topology CLASS` | — | Required when `--run-mode user`. Available: `BStarTopology`, `SequencePairTopology`, `ILPTopology`, `PSOTopology` |
| `--optimizer CLASS` | — | Required when `--run-mode user`. Available: `SimulatedAnnealingOptimizer`, `ILPOptimizer`, `PSOOptimizer`, `BStarILPOptimizer`, `PSOILPOptimizer` |
| `--version TAG` | `v01` | Version suffix appended to all output JSON filenames |
| `--no-routing` | false | Skip stage 201 (Anaroute) even when `RUN_ROUTING = True` in the config block |

Output JSON → `WorkDir/json_files/`, logs → `WorkDir/logs/`.

## Viewer

The viewer is a PyQt6 GUI for inspecting placements, running simulations, checking DRC, routing, and exporting GDS.

### Launch

```bash
# Empty viewer
python WorkDir/viewer/main.py

# Open a placement file directly
python WorkDir/viewer/main.py --input WorkDir/json_files/s42_n15_py101_v01.json

# Headless DRC check — no GUI (exit 0 = clean, 1 = violations, 2 = error)
python WorkDir/viewer/main.py \
    --input WorkDir/json_files/s42_n15_py101_v01.json \
    --drc   WorkDir/myPDK/gpdk090_device_rules.json
```

### Run a simulation — Tools → Simulate Circuit

1. Open the viewer (**without** a file, or with an existing one for reference).
2. Choose **Tools → Simulate Circuit**.
3. Set the seed, number of blocks (or point to a netlist), run mode, and topology/optimizer combination.
4. Click **Run** — the optimizer executes and the resulting placement loads automatically into the viewer.

### Check DRC — Tools → DRC Check

1. Load a placement JSON that contains a placement result (stage 101 or later).
2. Open **Tools → DRC Check**.
3. Confirm the PDK rules path (`WorkDir/myPDK/gpdk090_device_rules.json`) and click **Run DRC**.
4. Violations appear in the list and are highlighted on the canvas; click any entry to zoom to it.

### Run routing — Tools → Route Placement

Requires the MAGICAL Docker image (`magical_szaboga1_dev_wmi:latest`) to be running locally.

1. Load a placed py101 JSON.
2. Open **Tools → Route Placement** — Anaroute runs in the background and the routed result (py201) loads automatically.

### Export GDS — Tools → Export GDS

1. Load any placement JSON (routing is not required).
2. Open **Tools → Export GDS**.
3. Adjust GDS layer assignments if needed, set the output path, and click **Export GDS**.
4. Enable **Open in KLayout (WSL)** to preview the layout immediately after export.

## Project layout

| Path | Contents |
|------|----------|
| `WorkDir/scripts/` | Placement engine — see its `README.md` for module details |
| `WorkDir/viewer/` | PyQt6 viewer (simulate, DRC, route, GDS export) |
| `WorkDir/#Netlists/` | 47 analog netlists (ALIGN / MAGICAL SPICE format) |
| `WorkDir/myPDK/` | gpdk090 device rules, GDS layers, tech config |
| `WorkDir/json_files/` | Optimizer output (generated at runtime) |
| `WorkDir/testFiles/` | Sample placement JSONs for quick testing |

> **Docker / n8n:** Container-based workflow automation is planned as a future add-on and is not yet available.
