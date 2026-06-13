# ALDA Placement Optimizer

Analog-IC block placement engine for the `gpdk090` (90 nm) technology.
Generates blocks (random or from a SPICE netlist), then optimizes their 2D placement
(`B*-tree` / `Sequence Pair` topologies, Simulated Annealing) under symmetry constraints.
Includes a PyQt6 viewer with DRC checking and GDS export.

## Requirements

```bash
pip install -r requirements.txt   # numpy, matplotlib, imageio, imageio-ffmpeg
pip install PyQt6                  # for the viewer
```

Python 3.9+. The Docker path additionally needs Docker + Docker Compose.

## Run the optimizer

```bash
cd WorkDir/scripts

# Full pipeline, default settings (all topology/optimizer combos, ranked)
python main.py

# From a real netlist
python main.py --netlist "../#Netlists/a11_five_transistor_ota.sp" --seed 42

# Pick a single combination
python main.py --run-mode user --topology BStarTopology --optimizer SimulatedAnnealingOptimizer
```

Output → `WorkDir/json_files/`, logs → `WorkDir/logs/`.
Run `python main.py --help` for all flags (`--seed`, `--num-blocks`, `--run-mode`, …).

## View / check a placement

```bash
# Open in the GUI
python WorkDir/viewer/main.py --input WorkDir/testFiles/s13_n9_py14_v01.json

# Headless DRC (exit 0 = clean, 1 = violations)
python WorkDir/viewer/main.py \
    --input WorkDir/testFiles/s13_n9_py14_v01.json \
    --drc   WorkDir/myPDK/gpdk090_device_rules.json
```

## Run via Docker + n8n

```bash
make init     # build image
make up        # start → http://localhost:5678
make logs      # tail logs   (make down to stop, make help for all targets)
```

## Layout

| Path | |
|------|--|
| `WorkDir/scripts/` | placement engine — see its README for module details |
| `WorkDir/viewer/` | PyQt6 viewer (DRC, simulate, GDS export) |
| `WorkDir/#Netlists/` | 47 analog netlists (ALIGN/MAGICAL SPICE) |
| `WorkDir/myPDK/` | gpdk090 device rules, GDS layers, tech config |
| `WorkDir/testFiles/` | sample placement JSONs |
| `n8n/` | n8n workflows |
