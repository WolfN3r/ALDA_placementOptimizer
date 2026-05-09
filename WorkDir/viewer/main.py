"""Entry point for the ALDA Placement Viewer."""
import sys
import os
from pathlib import Path

# Ensure the viewer directory is on the path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from app_window import MainWindow


def _resolve(path_str: str) -> Path:
    """
    Resolve a JSON path argument robustly.

    Tried in order:
      1. As-is (relative to CWD or absolute)
      2. Relative to WorkDir  (parent of viewer/)
      3. Relative to project root (parent of WorkDir/)

    This lets users call the script from any directory and pass paths
    relative to the project root, e.g.:
        python WorkDir/viewer/main.py WorkDir/json_files/s42_n10_py001_v01.json
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


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("ALDA Placement Viewer")
    app.setOrganizationName("ALDA")

    window = MainWindow()

    if len(sys.argv) > 1:
        import json_loader
        try:
            resolved = _resolve(sys.argv[1])
            data = json_loader.load(resolved)
            window._load_data(data, resolved.name)
        except Exception as exc:
            print(f"Warning: could not load '{sys.argv[1]}': {exc}", file=sys.stderr)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
