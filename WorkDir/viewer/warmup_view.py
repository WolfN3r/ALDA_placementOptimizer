"""
WarmupViewDialog — side-by-side grid of N warmup placement mini-views.

Each cell shows a simple block-rectangle rendering of one warmup run,
its cost value, and which one was selected (highlighted with a green border).

Accepts warmup_runs as loaded from the placement JSON
(placement.warmup_runs[]).  Each entry has the format:
    {
        "run_index":   int,
        "strategy":    str,
        "seed":        int,
        "cost":        float,
        "is_selected": bool,
        "positions":   {bid: [x_bl, y_bl, w, h], ...}
    }

Self-contained: does not depend on PlacementScene, LayerManager, or DRC.
"""
from __future__ import annotations

import math

from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QBrush, QColor, QPen, QFont, QPainter
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGraphicsRectItem, QGraphicsScene,
    QGraphicsTextItem, QGraphicsView, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)


class _AutoFitView(QGraphicsView):
    """QGraphicsView that fits the full scene rect once the widget is shown."""
    def showEvent(self, event):
        super().showEvent(event)
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


# =============================================================================
# DEVICE-TYPE COLOUR PALETTE (simple, self-contained)
# =============================================================================

_DT_COLORS: dict[str, QColor] = {
    "nmos1v_nat": QColor("#4A7FB5"),
    "nmos2v_nat": QColor("#2E5C8A"),
    "pmos1v_nat": QColor("#B55A4A"),
    "pmos2v_nat": QColor("#8A2E2E"),
}
_DEFAULT_BLOCK_COLOR = QColor("#607080")
_SELECTED_BORDER     = QColor("#00FF88")
_NORMAL_BORDER       = QColor("#404040")
_BACKGROUND          = QColor("#1E1E1E")
_TEXT_COLOR          = QColor("#CCCCCC")
_SELECTED_TEXT       = QColor("#00FF88")


def _block_color(device_type: str) -> QColor:
    for key, col in _DT_COLORS.items():
        if key in device_type:
            return col
    return _DEFAULT_BLOCK_COLOR


# =============================================================================
# MINI SCENE — just block rectangles, Y-flipped
# =============================================================================

class WarmupMiniScene(QGraphicsScene):
    """
    Minimal scene for one warmup run.  Draws only block rectangles, no nets,
    no DRC, no routing — just enough to see the spatial arrangement.

    positions: {bid: [x_bl, y_bl, w, h]}   (list or tuple, 4 elements)
    """

    def __init__(
        self,
        positions:   dict[str, list],
        is_selected: bool,
    ) -> None:
        super().__init__()
        self.setBackgroundBrush(QBrush(_BACKGROUND))
        self._build(positions, is_selected)

    def _build(self, positions: dict[str, list], is_selected: bool) -> None:
        if not positions:
            return

        # Find total bounding box for Y-flip
        total_h = max(v[1] + v[3] for v in positions.values())
        total_h = max(total_h, 1e-6)

        block_pen = QPen(QColor("#888888"), 0.05)

        for bid, v in positions.items():
            x_bl, y_bl, w, h = float(v[0]), float(v[1]), float(v[2]), float(v[3])
            if w < 1e-9 or h < 1e-9:
                continue

            # Qt Y-axis is top-down; JSON is Y-up → flip
            qt_y = total_h - y_bl - h

            col  = _block_color("")   # no device_type in warmup positions; use default
            rect = QGraphicsRectItem(x_bl, qt_y, w, h)
            rect.setPen(block_pen)
            rect.setBrush(QBrush(col))
            self.addItem(rect)

        # Glow border around the entire scene rect for the selected run
        if is_selected:
            br        = self.itemsBoundingRect()
            sel_rect  = QGraphicsRectItem(br.adjusted(-0.1, -0.1, 0.1, 0.1))
            sel_pen   = QPen(_SELECTED_BORDER, 0.3)
            sel_rect.setPen(sel_pen)
            sel_rect.setBrush(QBrush(Qt.GlobalColor.transparent))
            sel_rect.setZValue(200)
            self.addItem(sel_rect)

        self.setSceneRect(self.itemsBoundingRect().adjusted(-0.5, -0.5, 0.5, 0.5))


# =============================================================================
# CELL WIDGET — mini-view + cost label + selected badge
# =============================================================================

class WarmupCellWidget(QWidget):
    """One cell in the grid: a small QGraphicsView + labels underneath."""

    _CELL_W = 220
    _CELL_H = 180

    def __init__(
        self,
        run:         dict,
        run_display: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        is_selected = bool(run.get("is_selected", False))
        positions   = run.get("positions", {})
        cost        = float(run.get("cost", 0.0))
        seed        = int(run.get("seed", 0))
        strategy    = str(run.get("strategy", ""))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Border frame — green for selected, dark grey otherwise
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setLineWidth(2 if is_selected else 1)
        border_color = _SELECTED_BORDER.name() if is_selected else _NORMAL_BORDER.name()
        frame.setStyleSheet(f"QFrame {{ border: {2 if is_selected else 1}px solid {border_color}; }}")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)

        # Mini QGraphicsView — fitInView happens in showEvent once the viewport has a real size
        scene = WarmupMiniScene(positions, is_selected)
        view  = _AutoFitView(scene)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setFixedSize(self._CELL_W - 12, self._CELL_H - 50)
        frame_layout.addWidget(view)
        layout.addWidget(frame)

        # Cost / seed label
        lbl_color = _SELECTED_TEXT.name() if is_selected else _TEXT_COLOR.name()
        info_lbl  = QLabel(f"Run {run_display} · seed {seed}\ncost: {cost:.4f}")
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_lbl.setStyleSheet(f"color: {lbl_color}; font-size: 10px;")
        layout.addWidget(info_lbl)

        if is_selected:
            badge = QLabel("◀ SELECTED")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"color: {_SELECTED_BORDER.name()}; font-weight: bold; font-size: 10px;"
            )
            layout.addWidget(badge)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedWidth(self._CELL_W)


# =============================================================================
# DIALOG
# =============================================================================

class WarmupViewDialog(QDialog):
    """
    Grid of N warmup result mini-views, one per warmup run.

    warmup_runs: list of run dicts from placement JSON (placement.warmup_runs).
    Sorted by cost before display so the cheapest runs appear first.
    """

    _MAX_COLS = 3

    def __init__(
        self,
        warmup_runs: list[dict],
        parent=None,
    ) -> None:
        super().__init__(parent)
        strategy  = warmup_runs[0].get("strategy", "?") if warmup_runs else "?"
        n         = len(warmup_runs)
        self.setWindowTitle(f"Warmup Results — strategy: {strategy}  N={n}")
        self.setModal(False)
        self._build_ui(warmup_runs)

    def _build_ui(self, warmup_runs: list[dict]) -> None:
        # Sort by cost so cheapest appears top-left (selected highlighted wherever it lands)
        sorted_runs = sorted(warmup_runs, key=lambda r: float(r.get("cost", 0.0)))
        n    = len(sorted_runs)
        cols = min(n, self._MAX_COLS)
        rows = math.ceil(n / cols)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # Title
        title = QLabel(f"Warmup placements sorted by cost (cheapest first).")
        title.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        root.addWidget(title)

        # Grid of cells
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, run in enumerate(sorted_runs):
            cell = WarmupCellWidget(run, run_display=i, parent=self)
            grid.addWidget(cell, i // cols, i % cols)
        root.addLayout(grid)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(80)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Size hint based on content
        cell_w = WarmupCellWidget._CELL_W + 6
        cell_h = WarmupCellWidget._CELL_H + 6
        self.resize(cols * cell_w + 32, rows * cell_h + 80)
