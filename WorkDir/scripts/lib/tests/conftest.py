"""
Test bootstrap: scripts/lib modules are flat files imported by bare name
(e.g. `import cost_evaluator`), not a package — mirrors the sys.path setup
already used by scripts/101_placementOptimizer.py.

Tests marked `corpus` (the long #Netlists placement run) are deselected unless
selected with `-m corpus`.
"""
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1]
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


def pytest_configure(config):
    config.addinivalue_line("markers", "corpus: rest of the #Netlists placement corpus (slow); run with -m corpus")


def pytest_collection_modifyitems(config, items):
    if "corpus" in (config.getoption("-m") or ""):
        return
    slow = [i for i in items if "corpus" in i.keywords]
    if slow:
        config.hook.pytest_deselected(items=slow)
        items[:] = [i for i in items if "corpus" not in i.keywords]
