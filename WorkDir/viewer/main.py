"""Entry point for the ALDA Placement Viewer / DRC CLI."""
import sys
import os
import argparse
from pathlib import Path
from collections import Counter

# Ensure the viewer directory is on the path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _resolve(path_str: str) -> Path:
    """Resolve a file path argument robustly.

    Tried in order:
      1. As-is (relative to CWD or absolute)
      2. Relative to WorkDir  (parent of viewer/)
      3. Relative to project root (parent of WorkDir/)

    This lets users call the script from any directory and pass paths
    relative to the project root, e.g.:
        python WorkDir/viewer/main.py --input WorkDir/json_files/s42_n10_py001_v01.json
    """
    p = Path(path_str)
    if p.exists():
        return p.resolve()

    viewer_dir = Path(__file__).parent
    for base in (viewer_dir.parent, viewer_dir.parent.parent):
        candidate = base / p
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        f"Cannot find '{path_str}'. Tried relative to CWD, WorkDir, and project root."
    )


# ---------------------------------------------------------------------------
# CLI mode — no Qt, pure terminal output
# ---------------------------------------------------------------------------

def run_cli(input_path: Path, pdk_path: Path) -> int:
    """Run DRC check without a GUI. Returns exit code (0=clean, 1=violations, 2=error)."""
    import json_loader
    from drc_checker import load_rules, run_drc

    # Ensure µ and other Unicode characters render correctly on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Load placement JSON
    try:
        data = json_loader.load(input_path)
    except Exception as exc:
        print(f"[ERROR] Could not load placement file: {exc}", file=sys.stderr)
        return 2

    if not data.has_placement or data.placement_result is None:
        print("[ERROR] Placement file contains no placement result. Run the optimizer first.")
        return 2

    # Load PDK rules
    try:
        rules = load_rules(pdk_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    # Run DRC
    violations = run_drc(data, rules)

    n_blocks = len(data.placement_result.placed_blocks)
    print(f"Input   : {input_path}")
    print(f"PDK     : {pdk_path}")
    print(f"Blocks  : {n_blocks} placed")
    print()

    if not violations:
        print("DRC result: CLEAN — no violations found.")
        return 0

    # Print each violation (same text as the app's list widget)
    print(f"DRC result: {len(violations)} violation(s) found")
    print("-" * 72)
    for v in violations:
        print(f"  {v.display_str}")
    print("-" * 72)

    # Summary by category
    counts = Counter(v.category for v in violations)
    print("Summary:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {cat}")

    return 1


# ---------------------------------------------------------------------------
# GUI mode
# ---------------------------------------------------------------------------

def run_gui(input_arg: str | None) -> None:
    """Launch the graphical viewer."""
    from PyQt6.QtWidgets import QApplication
    from app_window import MainWindow

    # Pass only the program name to Qt so it doesn't choke on our --input/--drc args
    app = QApplication(sys.argv[:1])
    app.setApplicationName("ALDA Placement Viewer")
    app.setOrganizationName("ALDA")

    window = MainWindow()

    if input_arg:
        import json_loader
        try:
            resolved = _resolve(input_arg)
            data = json_loader.load(resolved)
            window._load_data(data, resolved.name)
        except Exception as exc:
            print(f"Warning: could not load '{input_arg}': {exc}", file=sys.stderr)

    window.show()
    sys.exit(app.exec())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="ALDA Placement Viewer / DRC Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  Launch viewer (empty):
      python WorkDir/viewer/main.py

  Open a placement file in the viewer:
      python WorkDir/viewer/main.py --input WorkDir/json_files/s42_n10_py001_v01.json

  Run DRC check in CLI mode (no GUI):
      python WorkDir/viewer/main.py \\
          --input  WorkDir/json_files/s42_n10_py001_v01.json \\
          --drc    WorkDir/myPDK/gpdk090_device_rules.json

Exit codes (CLI mode only):
  0  DRC clean
  1  DRC violations found
  2  Error (bad file path, invalid PDK, no placement result, etc.)
""",
    )
    parser.add_argument(
        "--input", metavar="JSON",
        help="Placement JSON file to open / check",
    )
    parser.add_argument(
        "--drc", metavar="PDK_JSON",
        help="PDK rules JSON file; activates CLI DRC mode (no GUI is opened)",
    )
    # Keep backward-compat: bare positional arg still opens the viewer
    parser.add_argument("positional", nargs="?", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # --input wins over the legacy positional argument
    input_arg = args.input or args.positional

    if args.drc:
        # CLI mode — Qt is never imported
        if not input_arg:
            parser.error("--drc requires --input <placement.json>")
        try:
            input_path = _resolve(input_arg)
            pdk_path   = _resolve(args.drc)
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(2)
        sys.exit(run_cli(input_path, pdk_path))
    else:
        run_gui(input_arg)


if __name__ == "__main__":
    main()
