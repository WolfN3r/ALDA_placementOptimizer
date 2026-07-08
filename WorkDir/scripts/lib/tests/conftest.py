"""
Test bootstrap: scripts/lib modules are flat files imported by bare name
(e.g. `import cost_evaluator`), not a package — mirrors the sys.path setup
already used by scripts/101_placementOptimizer.py.
"""
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1]
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))
