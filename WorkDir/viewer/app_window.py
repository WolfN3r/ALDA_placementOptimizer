"""Main application window: tab-per-block layout with right info panel and canvas grid."""
from __future__ import annotations
import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QGraphicsView,
    QFrame, QTabWidget, QStatusBar, QToolBar, QApplication,
    QComboBox, QDoubleSpinBox, QCheckBox, QScrollArea, QGroupBox,
    QGridLayout,
)
from PyQt6.QtGui import (
    QAction, QKeySequence, QWheelEvent, QMouseEvent, QPainter,
    QColor, QPixmap, QIcon, QPen,
)
from PyQt6.QtCore import Qt, QPointF, QLineF, pyqtSignal

import json_loader
from layer_manager import LayerManager, LayerDef
from scene import BlockScene


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


# -----------------------------------------------------------------------
# Canvas view with pan/zoom and grid
# -----------------------------------------------------------------------
class CanvasView(QGraphicsView):
    """
    Pan/zoom canvas.
    - Scroll wheel: zoom centered on cursor
    - Middle-click or right-click drag: pan
    - No Qt item selection (no white selection rectangles)
    - Configurable background grid starting at scene origin
    """
    mouse_moved = pyqtSignal(float, float)

    _ZOOM = 1.15

    def __init__(self, scene: BlockScene, parent=None) -> None:
        super().__init__(scene, parent)
        self._panning = False
        self._pan_start = QPointF()

        # Grid settings (scene units = µm)
        self._grid_visible = True
        self._grid_small = 1.0
        self._grid_main = 5.0

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

        # Origin cross — always shown
        cross = self._grid_main if self._grid_main > 0 else self._grid_small
        if cross > 0:
            op = QPen(QColor(100, 100, 100))
            op.setCosmetic(True)
            op.setWidthF(1.5)
            painter.setPen(op)
            painter.drawLine(QLineF(-cross * 0.4, 0, cross * 0.4, 0))
            painter.drawLine(QLineF(0, -cross * 0.4, 0, cross * 0.4))

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
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            d = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - d.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - d.y()))
        else:
            sp = self.mapToScene(event.position().toPoint())
            self.mouse_moved.emit(sp.x(), sp.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)


# -----------------------------------------------------------------------
# Left: layers panel
# -----------------------------------------------------------------------
class LayersPanel(QWidget):
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
        self.setMinimumWidth(195)
        self.setMaximumWidth(230)

    def _on_changed(self, item: QTreeWidgetItem, _col: int) -> None:
        layer = item.data(0, Qt.ItemDataRole.UserRole)
        if layer:
            self.lm.set_visible(layer, item.checkState(0) == Qt.CheckState.Checked)


# -----------------------------------------------------------------------
# Right: block info panel
# -----------------------------------------------------------------------
class BlockInfoPanel(QWidget):
    """
    Shows block metadata, variant picker, pin list, and grid controls.
    Emits signals so MainWindow can forward them to the active scene/view.
    """
    variant_changed = pyqtSignal(int)            # variant_index
    grid_changed    = pyqtSignal(float, float, bool)  # small, main, visible

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._block: json_loader.Block | None = None
        self._data:  json_loader.PlacementData | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scroll area so content is accessible even when panel is narrow
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

        layout.addWidget(_separator())

        # --- Grid -------------------------------------------------------------
        gb = QGroupBox("Grid")
        gl = QGridLayout(gb)
        gl.setContentsMargins(4, 4, 4, 4)
        gl.setSpacing(4)

        gl.addWidget(QLabel("Main step (µm):"), 0, 0)
        self._main_step = QDoubleSpinBox()
        self._main_step.setRange(0.1, 10000.0)
        self._main_step.setValue(5.0)
        self._main_step.setSingleStep(0.5)
        self._main_step.setDecimals(2)
        gl.addWidget(self._main_step, 0, 1)

        gl.addWidget(QLabel("Small step (µm):"), 1, 0)
        self._small_step = QDoubleSpinBox()
        self._small_step.setRange(0.05, 1000.0)
        self._small_step.setValue(1.0)
        self._small_step.setSingleStep(0.1)
        self._small_step.setDecimals(2)
        gl.addWidget(self._small_step, 1, 1)

        self._grid_check = QCheckBox("Show grid")
        self._grid_check.setChecked(True)
        gl.addWidget(self._grid_check, 2, 0, 1, 2)

        layout.addWidget(gb)
        layout.addStretch()

        # Connect grid controls
        self._main_step.valueChanged.connect(self._emit_grid)
        self._small_step.valueChanged.connect(self._emit_grid)
        self._grid_check.toggled.connect(self._emit_grid)

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

        # Variants
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

    def current_grid(self) -> tuple[float, float, bool]:
        return (
            self._small_step.value(),
            self._main_step.value(),
            self._grid_check.isChecked(),
        )

    # ---- slots --------------------------------------------------------------

    def _on_variant_changed(self, index: int) -> None:
        if self._block and self._data:
            self._refresh_pins(self._block, self._data, index)
        self.variant_changed.emit(index)

    def _emit_grid(self, *_) -> None:
        self.grid_changed.emit(
            self._small_step.value(),
            self._main_step.value(),
            self._grid_check.isChecked(),
        )


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
        splitter.addWidget(self._layers_panel)

        # Center: tab widget (one tab per block)
        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(False)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self._tabs)

        # Right: block info panel
        self._info_panel = BlockInfoPanel()
        self._info_panel.variant_changed.connect(self._on_variant_changed)
        self._info_panel.grid_changed.connect(self._on_grid_changed)
        splitter.addWidget(self._info_panel)

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

    # -----------------------------------------------------------------------
    def _current_view(self) -> CanvasView | None:
        idx = self._tabs.currentIndex()
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
        self._data = data
        self._scenes.clear()
        self._views.clear()
        self.lm._callbacks.clear()

        while self._tabs.count():
            self._tabs.removeTab(0)

        small, main, vis = self._info_panel.current_grid()

        for block in data.blocks:
            scene = BlockScene(block, data, self.lm)
            view  = CanvasView(scene)
            view.set_grid(small, main, vis)
            view.mouse_moved.connect(self._on_mouse_moved)

            self._scenes.append(scene)
            self._views.append(view)

            short = block.device_type.replace("_nat", "")
            self._tabs.addTab(view, f"B{block.block_id} {short}")

        for view in self._views:
            view.fit()

        mode = "Placed" if data.has_placement else "Browser"
        self.setWindowTitle(f"ALDA Placement Viewer — {title}")
        self._mode_label.setText(f"Mode: {mode}  |  Blocks: {len(data.blocks)}")
        self._status.showMessage(f"Loaded {title}  ({len(data.blocks)} blocks)", 3000)

        # Show info for first block
        if data.blocks:
            self._info_panel.update_block(data.blocks[0], data)

    # -----------------------------------------------------------------------
    def _on_tab_changed(self, idx: int) -> None:
        if self._data and 0 <= idx < len(self._scenes):
            block = self._scenes[idx].block
            self._info_panel.update_block(block, self._data)

    def _on_variant_changed(self, variant_index: int) -> None:
        sc = self._current_scene()
        if sc:
            sc.switch_variant(variant_index)
            v = self._current_view()
            if v:
                v.fit()

    def _on_grid_changed(self, small: float, main: float, visible: bool) -> None:
        for view in self._views:
            view.set_grid(small, main, visible)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._coord_label.setText(f"({x:.3f} µm,  {y:.3f} µm)")

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self._fit_current()
        else:
            super().keyPressEvent(event)
