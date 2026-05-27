"""Main application window: tab-per-block layout + placement tab, with right info panel."""
from __future__ import annotations
import dataclasses
import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QGraphicsView,
    QFrame, QTabWidget, QStatusBar, QToolBar, QApplication,
    QComboBox, QDoubleSpinBox, QCheckBox, QScrollArea, QGroupBox,
    QGridLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QToolButton, QMenu, QWidgetAction, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QMessageBox,
)
from PyQt6.QtGui import (
    QAction, QKeySequence, QWheelEvent, QMouseEvent, QPainter,
    QColor, QPixmap, QIcon, QPen, QCursor, QBrush,
)
from PyQt6.QtCore import Qt, QPointF, QLineF, pyqtSignal

import json_loader
from layer_manager import LayerManager, LayerDef
from scene import BlockScene
from placement_scene import PlacementScene
from drc_checker import load_rules, run_drc, DRCViolation, DRC_CATEGORY_COLORS
from simulation_window import SimulationWindow


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


def _swatch(color: QColor, size: int = 14) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(color)
    return QIcon(pix)


def _abbrev_run_id(run_id: str) -> str:
    """Shorten a run_id like 'BStarTopology+SimulatedAnnealingOptimizer' → 'BStar+SA'."""
    subs = [
        ("SimulatedAnnealing", "SA"),
        ("SequencePair", "SP"),
        ("Topology", ""),
        ("Optimizer", ""),
    ]
    result = run_id
    for old, new in subs:
        result = result.replace(old, new)
    parts = [p for p in result.split("+") if p]
    # Deduplicate consecutive identical parts (e.g. ILP+ILP → ILP)
    dedup: list[str] = []
    for p in parts:
        if not dedup or p != dedup[-1]:
            dedup.append(p)
    return "+".join(dedup)


# -----------------------------------------------------------------------
# Canvas view with pan/zoom and grid
# -----------------------------------------------------------------------
class CanvasView(QGraphicsView):
    """
    Pan/zoom canvas.
    - Scroll wheel: zoom centered on cursor
    - Middle-click or right-click drag: pan
    - Right-click without drag: emits right_clicked(scene_pos)
    - No Qt item selection (no white selection rectangles)
    - Configurable background grid starting at scene origin
    """
    mouse_moved   = pyqtSignal(float, float)
    right_clicked = pyqtSignal(QPointF)   # right-click with no drag

    _ZOOM = 1.15

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self._panning = False
        self._pan_start = QPointF()
        self._pan_dist  = 0.0   # accumulated drag distance for right-button

        # Grid settings (scene units = µm)
        self._grid_visible = True
        self._grid_small = 1.0
        self._grid_main = 5.0
        self._origin = (0.0, 0.0)   # scene position of the (0,0) origin cross
        self._y_up_height = 0.0     # 0 = Y-down (default); > 0 = Y-up mode

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setBackgroundBrush(QColor("#1A1A1A"))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    # ---- grid ---------------------------------------------------------------

    def set_y_up(self, height: float) -> None:
        """Enable Y-up mode: origin cross at (0, height), mouse Y emitted as height-y."""
        self._y_up_height = height
        self._origin = (0.0, height)
        self.viewport().update()

    def set_grid(self, small: float, main: float, visible: bool) -> None:
        self._grid_small = max(small, 0.0)
        self._grid_main = max(main, 0.0)
        self._grid_visible = visible
        self.viewport().update()

    def drawBackground(self, painter: QPainter, rect) -> None:
        super().drawBackground(painter, rect)
        if not self._grid_visible:
            return

        scale = abs(self.transform().m11())  # pixels per scene unit

        def _draw_grid(step: float, color: QColor) -> None:
            if step <= 0:
                return
            if step * scale < 2.0:   # less than 2 screen pixels → too dense, skip
                return
            pen = QPen(color)
            pen.setCosmetic(True)
            painter.setPen(pen)

            x_start = math.floor(rect.left() / step) * step
            y_start = math.floor(rect.top() / step) * step

            lines: list[QLineF] = []
            x = x_start
            while x <= rect.right() + step:
                lines.append(QLineF(x, rect.top(), x, rect.bottom()))
                x += step
                if len(lines) > 600:   # safety cap
                    break

            y = y_start
            while y <= rect.bottom() + step:
                lines.append(QLineF(rect.left(), y, rect.right(), y))
                y += step
                if len(lines) > 1200:
                    break

            painter.drawLines(lines)

        _draw_grid(self._grid_small, QColor(48, 48, 48))
        _draw_grid(self._grid_main,  QColor(72, 72, 72))

        # Origin cross — always shown at self._origin
        cross = self._grid_main if self._grid_main > 0 else self._grid_small
        if cross > 0:
            ox, oy = self._origin
            op = QPen(QColor(100, 100, 100))
            op.setCosmetic(True)
            op.setWidthF(1.5)
            painter.setPen(op)
            painter.drawLine(QLineF(ox - cross * 0.4, oy, ox + cross * 0.4, oy))
            painter.drawLine(QLineF(ox, oy - cross * 0.4, ox, oy + cross * 0.4))

    # ---- interaction --------------------------------------------------------

    def fit(self) -> None:
        r = self.scene().itemsBoundingRect()
        if not r.isNull():
            pad = max(r.width(), r.height()) * 0.12
            r.adjust(-pad, -pad, pad, pad)
            self.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:
        f = self._ZOOM if event.angleDelta().y() > 0 else 1 / self._ZOOM
        self.scale(f, f)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = True
            self._pan_start = event.position()
            self._pan_dist  = 0.0
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            d = event.position() - self._pan_start
            self._pan_dist += abs(d.x()) + abs(d.y())
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - d.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - d.y()))
        else:
            sp = self.mapToScene(event.position().toPoint())
            y = self._y_up_height - sp.y() if self._y_up_height > 0 else sp.y()
            self.mouse_moved.emit(sp.x(), y)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            was_right_click = (
                event.button() == Qt.MouseButton.RightButton
                and self._pan_dist < 5.0
            )
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if was_right_click:
                sp = self.mapToScene(event.position().toPoint())
                self.right_clicked.emit(sp)
        else:
            super().mouseReleaseEvent(event)


# -----------------------------------------------------------------------
# Left: layers panel
# -----------------------------------------------------------------------
class LayersPanel(QWidget):
    nets_toggled = pyqtSignal(bool)

    def __init__(self, lm: LayerManager, parent=None) -> None:
        super().__init__(parent)
        self.lm = lm
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("<b>Layers</b>"))

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        layout.addWidget(self._tree)

        for ld in lm.all_layers():
            item = QTreeWidgetItem(self._tree, [ld.display_name])
            item.setData(0, Qt.ItemDataRole.UserRole, ld.name)
            item.setIcon(0, _swatch(ld.color))
            item.setCheckState(
                0,
                Qt.CheckState.Checked if ld.visible else Qt.CheckState.Unchecked,
            )

        self._tree.itemChanged.connect(self._on_changed)

        layout.addWidget(_separator())
        self._nets_check = QCheckBox("Show nets")
        self._nets_check.setChecked(True)
        self._nets_check.toggled.connect(self.nets_toggled)
        layout.addWidget(self._nets_check)

        self.setMinimumWidth(195)
        self.setMaximumWidth(230)

    def _on_changed(self, item: QTreeWidgetItem, _col: int) -> None:
        layer = item.data(0, Qt.ItemDataRole.UserRole)
        if layer:
            self.lm.set_visible(layer, item.checkState(0) == Qt.CheckState.Checked)


# -----------------------------------------------------------------------
# Grid settings widget (lives in toolbar popup)
# -----------------------------------------------------------------------
class GridSettingsWidget(QWidget):
    grid_changed = pyqtSignal(float, float, bool)  # small, main, visible

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Main step (µm):"), 0, 0)
        self._main_step = QDoubleSpinBox()
        self._main_step.setRange(0.1, 10000.0)
        self._main_step.setValue(5.0)
        self._main_step.setSingleStep(0.5)
        self._main_step.setDecimals(2)
        layout.addWidget(self._main_step, 0, 1)

        layout.addWidget(QLabel("Small step (µm):"), 1, 0)
        self._small_step = QDoubleSpinBox()
        self._small_step.setRange(0.05, 1000.0)
        self._small_step.setValue(1.0)
        self._small_step.setSingleStep(0.1)
        self._small_step.setDecimals(2)
        layout.addWidget(self._small_step, 1, 1)

        self._grid_check = QCheckBox("Show grid")
        self._grid_check.setChecked(True)
        layout.addWidget(self._grid_check, 2, 0, 1, 2)

        self._main_step.valueChanged.connect(self._emit)
        self._small_step.valueChanged.connect(self._emit)
        self._grid_check.toggled.connect(self._emit)

    def _emit(self, *_) -> None:
        self.grid_changed.emit(
            self._small_step.value(),
            self._main_step.value(),
            self._grid_check.isChecked(),
        )

    def current_grid(self) -> tuple[float, float, bool]:
        return (
            self._small_step.value(),
            self._main_step.value(),
            self._grid_check.isChecked(),
        )


# -----------------------------------------------------------------------
# Right: block info panel (shown for individual block tabs)
# -----------------------------------------------------------------------
class BlockInfoPanel(QWidget):
    """Shows block metadata, variant picker, and pin list."""
    variant_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._block: json_loader.Block | None = None
        self._data:  json_loader.PlacementData | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        scroll.setWidget(container)

        # --- Block info -------------------------------------------------------
        self._title = QLabel("<b>No block selected</b>")
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._info = QLabel("")
        self._info.setWordWrap(True)
        self._info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._info)

        layout.addWidget(_separator())

        # --- Variant ----------------------------------------------------------
        layout.addWidget(QLabel("<b>Variant</b>"))
        self._variant_combo = QComboBox()
        self._variant_combo.currentIndexChanged.connect(self._on_variant_changed)
        layout.addWidget(self._variant_combo)

        layout.addWidget(_separator())

        # --- Pins -------------------------------------------------------------
        layout.addWidget(QLabel("<b>Pins</b>"))
        self._pins = QLabel("")
        self._pins.setWordWrap(True)
        self._pins.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._pins)

        layout.addStretch()

        self.setMinimumWidth(210)
        self.setMaximumWidth(260)

    # ---- public API ---------------------------------------------------------

    def update_block(self, block: json_loader.Block, data: json_loader.PlacementData) -> None:
        self._block = block
        self._data  = data
        p = block.parameters

        self._title.setText(
            f"<b>Block {block.block_id}</b><br>{block.device_type}"
        )
        rows = [
            f"W = {p.get('width','?')} µm",
            f"L = {p.get('length','?')} µm",
            f"M = {p.get('multiplier','?')}",
            f"NF = {p.get('num_fingers','?')}",
            f"Total fingers: {p.get('total_fingers','?')}",
            f"Power rail: {block.power_rail or '—'}",
        ]
        self._info.setText("\n".join(rows))

        self._variant_combo.blockSignals(True)
        self._variant_combo.clear()
        active = data.active_variant(block)
        for v in block.variants:
            tag = " ✓" if v.is_used else ""
            self._variant_combo.addItem(
                f"v{v.index}: {v.rows}×{v.cols}  AR={v.aspect_ratio:.2f}{tag}"
            )
        self._variant_combo.setCurrentIndex(active.index)
        self._variant_combo.blockSignals(False)

        self._refresh_pins(block, data, active.index)

    def _refresh_pins(
        self,
        block: json_loader.Block,
        data:  json_loader.PlacementData,
        variant_index: int,
    ) -> None:
        pin_to_net: dict[str, json_loader.Net] = {}
        for net in data.nets:
            for pin_ref in net.pins:
                ps = pin_ref.split("_", 1)
                if int(ps[0][1:]) == block.block_id:
                    pin_to_net[ps[1]] = net

        variant = block.variants[variant_index]
        lines: list[str] = []
        for pin in variant.pins:
            net = pin_to_net.get(pin.name)
            if net:
                others = sorted({
                    f"B{int(pr.split('_')[0][1:])}"
                    for pr in net.pins
                    if int(pr.split("_")[0][1:]) != block.block_id
                })
                others_str = f"  ({', '.join(others)})" if others else ""
                lines.append(f"{pin.name} → {net.net_id}{others_str}")
            else:
                lines.append(f"{pin.name} → —")

        self._pins.setText("\n".join(lines) if lines else "—")

    # ---- slots --------------------------------------------------------------

    def _on_variant_changed(self, index: int) -> None:
        if self._block and self._data:
            self._refresh_pins(self._block, self._data, index)
        self.variant_changed.emit(index)


# -----------------------------------------------------------------------
# Right: placement info panel (shown for Placement tab)
# -----------------------------------------------------------------------
class PlacementInfoPanel(QWidget):
    """Shows optimization metrics and info for the block selected in the placement view."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        scroll.setWidget(container)

        layout.addWidget(QLabel("<b>Placement Results</b>"))

        # --- Best run metrics ------------------------------------------------
        metrics_gb = QGroupBox("Best Run")
        mg = QGridLayout(metrics_gb)
        mg.setContentsMargins(4, 4, 4, 4)
        mg.setSpacing(3)
        self._metric_labels: dict[str, QLabel] = {}
        rows_def = [
            ("topology", "Topology:"),
            ("optimizer", "Optimizer:"),
            ("cost",     "Cost:"),
            ("area",     "Area (µm²):"),
            ("hpwl",     "HPWL (µm):"),
            ("ar",       "Aspect ratio:"),
            ("iter",     "Iterations:"),
            ("time",     "Time (ms):"),
            ("blocks",   "Blocks placed:"),
        ]
        for i, (key, lbl_text) in enumerate(rows_def):
            mg.addWidget(QLabel(lbl_text), i, 0)
            val = QLabel("—")
            val.setWordWrap(True)
            self._metric_labels[key] = val
            mg.addWidget(val, i, 1)
        layout.addWidget(metrics_gb)

        layout.addWidget(_separator())

        # --- All runs table --------------------------------------------------
        layout.addWidget(QLabel("<b>All Runs</b>"))
        self._runs_table = QTableWidget(0, 5)
        self._runs_table.setHorizontalHeaderLabels(
            ["Topology", "Cost", "Area", "HPWL", "AR"]
        )
        self._runs_table.horizontalHeader().setStretchLastSection(True)
        self._runs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._runs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._runs_table.setAlternatingRowColors(True)
        self._runs_table.verticalHeader().setVisible(False)
        self._runs_table.setMaximumHeight(110)
        layout.addWidget(self._runs_table)

        layout.addWidget(_separator())

        # --- Selected block --------------------------------------------------
        sel_gb = QGroupBox("Selected Block")
        sel_layout = QVBoxLayout(sel_gb)
        sel_layout.setContentsMargins(6, 6, 6, 6)
        sel_layout.setSpacing(4)

        self._sel_title = QLabel("<i>Click a block in the view</i>")
        self._sel_title.setWordWrap(True)
        sel_layout.addWidget(self._sel_title)

        self._sel_info = QLabel("")
        self._sel_info.setWordWrap(True)
        self._sel_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sel_layout.addWidget(self._sel_info)

        self._sel_variant_sep = _separator()
        self._sel_variant_sep.setVisible(False)
        sel_layout.addWidget(self._sel_variant_sep)

        self._sel_variant = QLabel("")
        self._sel_variant.setWordWrap(True)
        sel_layout.addWidget(self._sel_variant)

        self._sel_pins_sep = _separator()
        self._sel_pins_sep.setVisible(False)
        sel_layout.addWidget(self._sel_pins_sep)

        self._sel_pins_header = QLabel("<b>Pins</b>")
        self._sel_pins_header.setVisible(False)
        sel_layout.addWidget(self._sel_pins_header)

        self._sel_pins = QLabel("")
        self._sel_pins.setWordWrap(True)
        self._sel_pins.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sel_layout.addWidget(self._sel_pins)

        layout.addWidget(sel_gb)
        layout.addStretch()

        self.setMinimumWidth(210)
        self.setMaximumWidth(260)

    # ---- public API ---------------------------------------------------------

    def update_placement(self, data: json_loader.PlacementData) -> None:
        pr = data.placement_result
        if not pr:
            return

        topo = pr.topology.replace("Topology", "")
        opt  = pr.optimizer.replace("Optimizer", "").replace("SimulatedAnnealing", "SA")

        self._metric_labels["topology"].setText(topo)
        self._metric_labels["optimizer"].setText(opt)
        self._metric_labels["cost"].setText(f"{pr.final_cost:.4f}")
        self._metric_labels["area"].setText(f"{pr.area_um2:.2f}")
        self._metric_labels["hpwl"].setText(f"{pr.hpwl_um:.2f}")
        self._metric_labels["ar"].setText(f"{pr.aspect_ratio:.4f}")
        self._metric_labels["iter"].setText(str(pr.n_iterations))
        self._metric_labels["time"].setText(f"{pr.t_total_ms:.1f}")
        self._metric_labels["blocks"].setText(
            f"{len(pr.placed_blocks)} / {len(data.blocks)}"
        )

        self._runs_table.setRowCount(len(pr.all_runs))
        for row, run in enumerate(pr.all_runs):
            vals = [
                run.get("topology", "?").replace("Topology", ""),
                f"{run.get('final_cost', 0):.4f}",
                f"{run.get('area_um2', 0):.1f}",
                f"{run.get('hpwl_um', 0):.1f}",
                f"{run.get('aspect_ratio', 0):.3f}",
            ]
            for col, val in enumerate(vals):
                self._runs_table.setItem(row, col, QTableWidgetItem(val))
        self._runs_table.resizeColumnsToContents()

    def update_selected_block(
        self, block: json_loader.Block, data: json_loader.PlacementData
    ) -> None:
        p = block.parameters
        self._sel_title.setText(
            f"<b>Block {block.block_id}</b> — {block.device_type}"
        )
        rows = [
            f"W = {p.get('width', '?')} µm",
            f"L = {p.get('length', '?')} µm",
            f"M = {p.get('multiplier', '?')}",
            f"NF = {p.get('num_fingers', '?')}",
            f"Total fingers: {p.get('total_fingers', '?')}",
            f"Power rail: {block.power_rail or '—'}",
        ]
        self._sel_info.setText("\n".join(rows))

        active = data.active_variant(block)
        self._sel_variant.setText(
            f"v{active.index}: {active.rows}×{active.cols}  AR={active.aspect_ratio:.2f} ✓"
        )

        pin_to_net: dict[str, json_loader.Net] = {}
        for net in data.nets:
            for pin_ref in net.pins:
                ps = pin_ref.split("_", 1)
                if int(ps[0][1:]) == block.block_id:
                    pin_to_net[ps[1]] = net

        lines: list[str] = []
        for pin in active.pins:
            net = pin_to_net.get(pin.name)
            if net:
                others = sorted({
                    f"B{int(pr.split('_')[0][1:])}"
                    for pr in net.pins
                    if int(pr.split("_")[0][1:]) != block.block_id
                })
                others_str = f"  ({', '.join(others)})" if others else ""
                lines.append(f"{pin.name} → {net.net_id}{others_str}")
            else:
                lines.append(f"{pin.name} → —")

        self._sel_pins.setText("\n".join(lines) if lines else "—")
        self._sel_variant_sep.setVisible(True)
        self._sel_pins_sep.setVisible(True)
        self._sel_pins_header.setVisible(True)

    def clear_selection(self) -> None:
        self._sel_title.setText("<i>Click a block in the view</i>")
        self._sel_info.setText("")
        self._sel_variant.setText("")
        self._sel_pins.setText("")
        self._sel_variant_sep.setVisible(False)
        self._sel_pins_sep.setVisible(False)
        self._sel_pins_header.setVisible(False)


# -----------------------------------------------------------------------
# Standalone block detail window (opened from placement right-click menu)
# -----------------------------------------------------------------------
class BlockDetailWindow(QMainWindow):
    """Floating window showing a single block's layout and metadata."""

    def __init__(
        self,
        block: json_loader.Block,
        data:  json_loader.PlacementData,
        lm:    LayerManager,
        grid_settings: tuple[float, float, bool],
        parent=None,
    ) -> None:
        super().__init__(parent)
        short = block.device_type.replace("_nat", "")
        self.setWindowTitle(f"Block Blueprint  —  B{block.block_id}  {short}")
        self.resize(900, 680)

        scene = BlockScene(block, data, lm)
        self._view = CanvasView(scene)
        self._scene = scene

        variant = data.active_variant(block)
        self._view.set_y_up(variant.bbox[3] - variant.bbox[1])
        small, main, vis = grid_settings
        self._view.set_grid(small, main, vis)

        info = BlockInfoPanel()
        info.update_block(block, data)
        info.variant_changed.connect(
            lambda idx, b=block: self._on_variant_changed(b, idx)
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._view)
        splitter.addWidget(info)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([660, 230])
        self.setCentralWidget(splitter)

        self._view.fit()
        self._block = block

    def _on_variant_changed(self, block: json_loader.Block, idx: int) -> None:
        self._scene.switch_variant(idx)
        variant = block.variants[idx]
        self._view.set_y_up(variant.bbox[3] - variant.bbox[1])
        self._view.fit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self._view.fit()
        else:
            super().keyPressEvent(event)


# -----------------------------------------------------------------------
# DRC window
# -----------------------------------------------------------------------
class DRCWindow(QMainWindow):
    """Floating DRC check panel — similar to Cadence Virtuoso's DRC results window."""

    def __init__(
        self,
        data: json_loader.PlacementData,
        scene: PlacementScene,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._scene = scene
        self._violations: list[DRCViolation] = []

        default_pdk = Path(__file__).parent.parent / "myPDK" / "gpdk090_device_rules.json"
        self.setWindowTitle("DRC Check")
        self.resize(600, 560)
        self._build_ui(str(default_pdk))

    def _build_ui(self, default_pdk_path: str) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # PDK file row
        pdk_row = QHBoxLayout()
        pdk_row.addWidget(QLabel("PDK Rules:"))
        self._pdk_path = QLineEdit(default_pdk_path)
        pdk_row.addWidget(self._pdk_path, stretch=1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_pdk)
        pdk_row.addWidget(browse_btn)
        layout.addLayout(pdk_row)

        # Run DRC row
        run_row = QHBoxLayout()
        run_btn = QPushButton("Run DRC")
        run_btn.clicked.connect(self._run_drc)
        run_row.addWidget(run_btn)
        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        run_row.addWidget(self._status_label, stretch=1)
        layout.addLayout(run_row)

        layout.addWidget(QLabel("Violations:"))

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_violation_selected)
        layout.addWidget(self._list, stretch=1)

        # Bottom options row
        options_row = QHBoxLayout()
        self._show_all = QCheckBox("Show All Errors")
        self._show_all.toggled.connect(self._on_show_all_toggled)
        options_row.addWidget(self._show_all)
        options_row.addStretch()
        clear_btn = QPushButton("Clear Highlights")
        clear_btn.clicked.connect(self._on_clear_highlights)
        options_row.addWidget(clear_btn)
        layout.addLayout(options_row)

    # ---- slots -------------------------------------------------------------

    def _browse_pdk(self) -> None:
        start = str(Path(__file__).parent.parent / "myPDK")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDK Rules JSON", start, "JSON files (*.json)"
        )
        if path:
            self._pdk_path.setText(path)

    def _run_drc(self) -> None:
        pdk_path = self._pdk_path.text().strip()
        try:
            rules = load_rules(pdk_path)
        except (FileNotFoundError, ValueError) as exc:
            self._status_label.setText(f"Error: {exc}")
            return

        self._violations = run_drc(self._data, rules)
        self._populate_list()
        self._scene.clear_drc()

        count = len(self._violations)
        if count == 0:
            self._status_label.setText("No violations")
            QMessageBox.information(self, "DRC Check", "No DRC violations found.")
        else:
            self._status_label.setText(f"{count} violation{'s' if count != 1 else ''} found")

        if self._show_all.isChecked() and self._violations:
            self._scene.highlight_drc(self._violations)

    def _populate_list(self) -> None:
        self._list.clear()
        for v in self._violations:
            item = QListWidgetItem(v.display_str)
            hex_color, _ = DRC_CATEGORY_COLORS.get(v.category, ("#FF4444", 80))
            item.setForeground(QBrush(QColor(hex_color)))
            self._list.addItem(item)

    def _on_violation_selected(self, item: QListWidgetItem) -> None:
        idx = self._list.row(item)
        if 0 <= idx < len(self._violations):
            self._scene.clear_drc()
            self._scene.highlight_drc([self._violations[idx]])

    def _on_show_all_toggled(self, checked: bool) -> None:
        self._scene.clear_drc()
        if checked and self._violations:
            self._scene.highlight_drc(self._violations)

    def _on_clear_highlights(self) -> None:
        self._scene.clear_drc()

    def closeEvent(self, event) -> None:
        self._scene.clear_drc()
        super().closeEvent(event)


# -----------------------------------------------------------------------
# Right: exhaustive compare panel (shown when mode == "exhaustive")
# -----------------------------------------------------------------------
class ExhaustiveComparePanel(QWidget):
    """Comparison table of all exhaustive runs + selected-block info."""

    _HIGHLIGHT_BG = QColor("#4A3800")
    _HIGHLIGHT_FG = QColor("#FFD700")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[json_loader.PlacementResult] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        scroll.setWidget(container)

        layout.addWidget(QLabel("<b>Run Comparison</b>"))
        sub = QLabel("Sorted: best → worst  (norm. cost)")
        sub.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(sub)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Run", "N.Cost", "Area", "HPWL", "AR", "ms"]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumHeight(80)
        layout.addWidget(self._table)

        layout.addWidget(_separator())

        sel_gb = QGroupBox("Selected Block")
        sel_layout = QVBoxLayout(sel_gb)
        sel_layout.setContentsMargins(6, 6, 6, 6)
        sel_layout.setSpacing(4)
        self._sel_title = QLabel("<i>Click a block in the view</i>")
        self._sel_title.setWordWrap(True)
        sel_layout.addWidget(self._sel_title)
        self._sel_info = QLabel("")
        self._sel_info.setWordWrap(True)
        self._sel_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sel_layout.addWidget(self._sel_info)
        layout.addWidget(sel_gb)

        layout.addStretch()
        self.setMinimumWidth(210)
        self.setMaximumWidth(280)

    # ---- public API ---------------------------------------------------------

    def update_runs(self, results: list[json_loader.PlacementResult]) -> None:
        self._results = results
        self._table.setRowCount(len(results))
        for row, pr in enumerate(results):
            vals = [
                _abbrev_run_id(pr.run_id),
                f"{pr.renorm_cost:.4f}",
                f"{pr.area_um2:.1f}",
                f"{pr.hpwl_um:.1f}",
                f"{pr.aspect_ratio:.3f}",
                f"{pr.t_optimize_ms:.0f}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setToolTip(pr.run_id)
                self._table.setItem(row, col, item)
        self._table.resizeColumnsToContents()

    def highlight_run(self, run_id: str) -> None:
        for row, pr in enumerate(self._results):
            is_cur = pr.run_id == run_id
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item:
                    if is_cur:
                        item.setBackground(QBrush(self._HIGHLIGHT_BG))
                        item.setForeground(QBrush(self._HIGHLIGHT_FG))
                    else:
                        item.setData(Qt.ItemDataRole.BackgroundRole, None)
                        item.setData(Qt.ItemDataRole.ForegroundRole, None)
            if is_cur and self._table.item(row, 0):
                self._table.scrollToItem(self._table.item(row, 0))

    def update_selected_block(
        self, block: json_loader.Block, data: json_loader.PlacementData
    ) -> None:
        p = block.parameters
        self._sel_title.setText(
            f"<b>Block {block.block_id}</b> — {block.device_type}"
        )
        self._sel_info.setText(
            f"W={p.get('width','?')} µm  L={p.get('length','?')} µm\n"
            f"M={p.get('multiplier','?')}  NF={p.get('num_fingers','?')}\n"
            f"Rail: {block.power_rail or '—'}"
        )

    def clear_selection(self) -> None:
        self._sel_title.setText("<i>Click a block in the view</i>")
        self._sel_info.setText("")


# -----------------------------------------------------------------------
# Main window
# -----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ALDA Placement Viewer")
        self.resize(1500, 880)

        self.lm = LayerManager()
        self._scenes: list[BlockScene] = []
        self._views:  list[CanvasView] = []
        self._data:   json_loader.PlacementData | None = None

        self._placement_scene: PlacementScene | None = None
        self._placement_view:  CanvasView | None = None
        self._placement_tab_idx: int = -1
        self._detail_windows: list[BlockDetailWindow] = []
        self._drc_window: DRCWindow | None = None
        self._drc_action: QAction | None = None
        self._sim_window: SimulationWindow | None = None

        # Exhaustive mode state
        self._exhaustive_mode: bool = False
        self._exhaustive_scenes: list[PlacementScene] = []
        self._exhaustive_views: list[CanvasView] = []
        self._exhaustive_data: list[json_loader.PlacementData] = []
        self._exhaustive_tab_start: int = -1

        self._build_ui()
        self._build_menus()
        self._build_toolbar()

    # -----------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        hbox = QHBoxLayout(central)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: layers panel
        self._layers_panel = LayersPanel(self.lm)
        self._layers_panel.nets_toggled.connect(self._on_nets_toggled)
        splitter.addWidget(self._layers_panel)

        # Center: tab widget (one tab per block + optional placement tab)
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(False)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self._tabs)

        # Right: stacked panel (block info | placement info)
        self._right_stack = QStackedWidget()

        self._info_panel = BlockInfoPanel()
        self._info_panel.variant_changed.connect(self._on_variant_changed)
        self._right_stack.addWidget(self._info_panel)        # index 0

        self._placement_info_panel = PlacementInfoPanel()
        self._right_stack.addWidget(self._placement_info_panel)  # index 1

        self._exhaustive_compare_panel = ExhaustiveComparePanel()
        self._right_stack.addWidget(self._exhaustive_compare_panel)  # index 2

        splitter.addWidget(self._right_stack)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([215, 1100, 230])

        hbox.addWidget(splitter)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._coord_label = QLabel("(—, —)")
        self._mode_label  = QLabel("")
        self._status.addWidget(self._coord_label)
        self._status.addPermanentWidget(self._mode_label)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        fm = mb.addMenu("&File")
        oa = QAction("&Open JSON…", self)
        oa.setShortcut(QKeySequence.StandardKey.Open)
        oa.triggered.connect(self._open_file)
        fm.addAction(oa)
        fm.addSeparator()
        qa = QAction("&Quit", self)
        qa.setShortcut(QKeySequence.StandardKey.Quit)
        qa.triggered.connect(QApplication.quit)
        fm.addAction(qa)

        vm = mb.addMenu("&View")
        fa = QAction("&Fit  [F]", self)
        fa.setShortcut(QKeySequence("F"))
        fa.triggered.connect(self._fit_current)
        vm.addAction(fa)

        faa = QAction("Fit &all tabs", self)
        faa.triggered.connect(self._fit_all)
        vm.addAction(faa)

        zi = QAction("Zoom &In", self)
        zi.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zi.triggered.connect(lambda: self._current_view() and self._current_view().scale(1.2, 1.2))
        vm.addAction(zi)

        zo = QAction("Zoom &Out", self)
        zo.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zo.triggered.connect(lambda: self._current_view() and self._current_view().scale(1/1.2, 1/1.2))
        vm.addAction(zo)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        ob = QAction("Open", self)
        ob.triggered.connect(self._open_file)
        tb.addAction(ob)

        fb = QAction("Fit [F]", self)
        fb.triggered.connect(self._fit_current)
        tb.addAction(fb)

        tb.addSeparator()

        grid_btn = QToolButton()
        grid_btn.setText("Grid…")
        grid_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        grid_menu = QMenu(grid_btn)
        grid_action = QWidgetAction(grid_menu)
        self._grid_widget = GridSettingsWidget()
        self._grid_widget.grid_changed.connect(self._on_grid_changed)
        grid_action.setDefaultWidget(self._grid_widget)
        grid_menu.addAction(grid_action)
        grid_btn.setMenu(grid_menu)
        tb.addWidget(grid_btn)

        tb.addSeparator()
        self._drc_action = QAction("DRC", self)
        self._drc_action.setToolTip("Run Design Rule Check (requires loaded placement)")
        self._drc_action.setEnabled(False)
        self._drc_action.triggered.connect(self._open_drc_window)
        tb.addAction(self._drc_action)

        self._sim_action = QAction("Simulate", self)
        self._sim_action.setToolTip("Run placement optimizer with custom settings")
        self._sim_action.triggered.connect(self._open_sim_window)
        tb.addAction(self._sim_action)

    # -----------------------------------------------------------------------
    def _current_view(self) -> CanvasView | None:
        idx = self._tabs.currentIndex()
        if self._exhaustive_mode:
            et_end = self._exhaustive_tab_start + len(self._exhaustive_views)
            if self._exhaustive_tab_start <= idx < et_end:
                return self._exhaustive_views[idx - self._exhaustive_tab_start]
        if idx == self._placement_tab_idx and self._placement_view is not None:
            return self._placement_view
        return self._views[idx] if 0 <= idx < len(self._views) else None

    def _current_scene(self) -> BlockScene | None:
        idx = self._tabs.currentIndex()
        return self._scenes[idx] if 0 <= idx < len(self._scenes) else None

    def _fit_current(self) -> None:
        v = self._current_view()
        if v:
            v.fit()

    def _fit_all(self) -> None:
        for v in self._views:
            v.fit()
        for v in self._exhaustive_views:
            v.fit()
        if not self._exhaustive_mode and self._placement_view:
            self._placement_view.fit()

    # -----------------------------------------------------------------------
    def _open_file(self) -> None:
        start = str(Path(__file__).parent.parent / "json_files")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open placement JSON", start, "JSON files (*.json)"
        )
        if not path:
            return
        try:
            data = json_loader.load(path)
        except Exception as exc:
            self._status.showMessage(f"Error: {exc}", 5000)
            return
        self._load_data(data, Path(path).name)

    def _load_data(self, data: json_loader.PlacementData, title: str = "") -> None:
        # Close any open detail windows from a previous file
        for w in self._detail_windows:
            w.close()
        self._detail_windows.clear()

        self._data = data
        self._scenes.clear()
        self._views.clear()
        self.lm._callbacks.clear()
        self._placement_scene = None
        self._placement_view = None
        self._placement_tab_idx = -1
        self._exhaustive_mode = False
        self._exhaustive_scenes.clear()
        self._exhaustive_views.clear()
        self._exhaustive_data.clear()
        self._exhaustive_tab_start = -1

        while self._tabs.count():
            self._tabs.removeTab(0)

        small, main, vis = self._grid_widget.current_grid()

        if data.placement_mode == "exhaustive" and data.all_placement_results:
            # Exhaustive mode: one tab per run, sorted by renorm_cost (best → worst)
            self._exhaustive_mode = True
            self._exhaustive_tab_start = self._tabs.count()   # == 0
            for pr in data.all_placement_results:
                run_data = dataclasses.replace(
                    data, placement_result=pr, all_placement_results=[], placement_mode=""
                )
                ps = PlacementScene(run_data, self.lm)
                pv = CanvasView(ps)
                pv.set_y_up(ps._H)
                pv.set_grid(small, main, vis)
                pv.mouse_moved.connect(self._on_mouse_moved)
                pv.right_clicked.connect(self._on_placement_right_click)
                ps.block_selected.connect(self._on_placement_block_selected)
                self._exhaustive_scenes.append(ps)
                self._exhaustive_views.append(pv)
                self._exhaustive_data.append(run_data)
                self._tabs.addTab(pv, _abbrev_run_id(pr.run_id))
            # First tab = lowest renorm_cost
            self._placement_scene = self._exhaustive_scenes[0]
            self._placement_view = self._exhaustive_views[0]
            self._placement_tab_idx = self._exhaustive_tab_start
            self._exhaustive_compare_panel.update_runs(data.all_placement_results)
            self._exhaustive_compare_panel.highlight_run(data.all_placement_results[0].run_id)
            self._exhaustive_compare_panel.clear_selection()
            self._right_stack.setCurrentIndex(2)
            for pv in self._exhaustive_views:
                pv.fit()

        elif data.has_placement and data.placement_result:
            # Single-run placement mode: one Placement tab
            ps = PlacementScene(data, self.lm)
            pv = CanvasView(ps)
            pv.set_y_up(ps._H)
            pv.set_grid(small, main, vis)
            pv.mouse_moved.connect(self._on_mouse_moved)
            pv.right_clicked.connect(self._on_placement_right_click)
            ps.block_selected.connect(self._on_placement_block_selected)
            self._placement_scene = ps
            self._placement_view = pv
            self._placement_tab_idx = self._tabs.count()   # == 0
            self._tabs.addTab(pv, "Placement")
            pv.fit()
            self._placement_info_panel.update_placement(data)
            self._placement_info_panel.clear_selection()
            self._right_stack.setCurrentIndex(1)

        else:
            # Browser mode: one tab per block, no placement tab
            for block in data.blocks:
                scene = BlockScene(block, data, self.lm)
                view  = CanvasView(scene)
                variant = data.active_variant(block)
                view.set_y_up(variant.bbox[3] - variant.bbox[1])
                view.set_grid(small, main, vis)
                view.mouse_moved.connect(self._on_mouse_moved)

                self._scenes.append(scene)
                self._views.append(view)

                short = block.device_type.replace("_nat", "")
                self._tabs.addTab(view, f"B{block.block_id} {short}")

            for view in self._views:
                view.fit()

            if data.blocks:
                self._info_panel.update_block(data.blocks[0], data)
            self._right_stack.setCurrentIndex(0)

        if self._exhaustive_mode:
            mode = f"Exhaustive ({len(data.all_placement_results)} runs)"
        else:
            mode = "Placed" if data.has_placement else "Browser"
        self.setWindowTitle(f"ALDA Placement Viewer — {title}")
        self._mode_label.setText(f"Mode: {mode}  |  Blocks: {len(data.blocks)}")
        self._status.showMessage(f"Loaded {title}  ({len(data.blocks)} blocks)", 3000)

        if self._drc_window is not None:
            self._drc_window.close()
            self._drc_window = None
        if self._drc_action:
            self._drc_action.setEnabled(
                bool(self._exhaustive_scenes) or
                (data.has_placement and data.placement_result is not None)
            )

    # -----------------------------------------------------------------------
    def _on_tab_changed(self, idx: int) -> None:
        if self._exhaustive_mode:
            et_end = self._exhaustive_tab_start + len(self._exhaustive_scenes)
            if self._exhaustive_tab_start <= idx < et_end:
                run_idx = idx - self._exhaustive_tab_start
                self._placement_scene = self._exhaustive_scenes[run_idx]
                self._placement_view = self._exhaustive_views[run_idx]
                self._placement_tab_idx = idx
                self._right_stack.setCurrentIndex(2)
                run_id = self._data.all_placement_results[run_idx].run_id
                self._exhaustive_compare_panel.highlight_run(run_id)
                # Close DRC window when switching runs (it was tied to the old scene)
                if self._drc_window is not None:
                    self._drc_window.close()
                    self._drc_window = None
                return

        if idx == self._placement_tab_idx:
            self._right_stack.setCurrentIndex(1)
        elif self._data and 0 <= idx < len(self._scenes):
            self._right_stack.setCurrentIndex(0)
            block = self._scenes[idx].block
            self._info_panel.update_block(block, self._data)

    def _on_variant_changed(self, variant_index: int) -> None:
        sc = self._current_scene()
        if sc:
            sc.switch_variant(variant_index)
            idx = self._tabs.currentIndex()
            if 0 <= idx < len(self._views):
                v = self._views[idx]
                variant = sc.block.variants[variant_index]
                v.set_y_up(variant.bbox[3] - variant.bbox[1])
                v.fit()

    def _on_grid_changed(self, small: float, main: float, visible: bool) -> None:
        for view in self._views:
            view.set_grid(small, main, visible)
        for view in self._exhaustive_views:
            view.set_grid(small, main, visible)
        if not self._exhaustive_mode and self._placement_view:
            self._placement_view.set_grid(small, main, visible)

    def _on_nets_toggled(self, visible: bool) -> None:
        targets = (
            self._exhaustive_scenes if self._exhaustive_mode
            else ([self._placement_scene] if self._placement_scene else [])
        )
        for ps in targets:
            ps.set_nets_visible(visible)

    def _open_drc_window(self) -> None:
        if not self._placement_scene:
            return
        if self._drc_window is not None and self._drc_window.isVisible():
            self._drc_window.raise_()
            self._drc_window.activateWindow()
            return
        if self._exhaustive_mode:
            run_idx = self._tabs.currentIndex() - self._exhaustive_tab_start
            if not (0 <= run_idx < len(self._exhaustive_data)):
                return
            drc_data = self._exhaustive_data[run_idx]
        else:
            if not self._data:
                return
            drc_data = self._data
        self._drc_window = DRCWindow(drc_data, self._placement_scene, parent=self)
        self._drc_window.show()

    def _open_sim_window(self) -> None:
        if self._sim_window is not None and self._sim_window.isVisible():
            self._sim_window.raise_()
            self._sim_window.activateWindow()
            return
        self._sim_window = SimulationWindow(parent=self)
        self._sim_window.result_ready.connect(self._load_simulation_result)
        self._sim_window.show()

    def _load_simulation_result(self, path: Path) -> None:
        data = json_loader.load(path)
        self._load_data(data, path.name)

    def _on_placement_block_selected(self, bid) -> None:
        if bid is None:
            if self._exhaustive_mode:
                self._exhaustive_compare_panel.clear_selection()
            else:
                self._placement_info_panel.clear_selection()
        elif self._data:
            block = self._data.block_by_id(bid)
            if block:
                if self._exhaustive_mode:
                    self._exhaustive_compare_panel.update_selected_block(block, self._data)
                else:
                    self._placement_info_panel.update_selected_block(block, self._data)

    def _on_placement_right_click(self, scene_pos: QPointF) -> None:
        if not self._placement_scene or not self._data:
            return
        bid = None
        for item in self._placement_scene.items(scene_pos):
            d = item.data(0)
            if isinstance(d, int):
                bid = d
                break
        if bid is None:
            return
        block = self._data.block_by_id(bid)
        if not block:
            return
        short = block.device_type.replace("_nat", "")
        menu = QMenu(self)
        action = menu.addAction(f"Open Block Blueprint  —  B{bid} {short}")
        action.triggered.connect(lambda: self._open_block_detail(bid))
        menu.exec(QCursor.pos())

    def _open_block_detail(self, bid: int) -> None:
        if not self._data:
            return
        block = self._data.block_by_id(bid)
        if not block:
            return
        w = BlockDetailWindow(
            block, self._data, self.lm, self._grid_widget.current_grid()
        )
        w.show()
        self._detail_windows.append(w)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._coord_label.setText(f"({x:.3f} µm,  {y:.3f} µm)")

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self._fit_current()
        else:
            super().keyPressEvent(event)
