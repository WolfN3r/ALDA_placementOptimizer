"""Main application window: tab-per-block layout + placement tab, with right info panel."""
from __future__ import annotations
import dataclasses
import json
import math
import subprocess
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent as _xml_indent

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QGraphicsView,
    QFrame, QTabWidget, QStatusBar, QToolBar, QApplication,
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QScrollArea, QGroupBox,
    QGridLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QToolButton, QMenu, QWidgetAction, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QMessageBox, QHeaderView,
    QDialog, QColorDialog, QSlider, QPlainTextEdit,
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
from routing_window import RoutingWindow
import tikz_exporter as _tikz


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


_RUN_ID_OVERRIDES: dict[str, str] = {
    "BStarTopology+SimulatedAnnealingOptimizer": "B* SA",
    "ILPTopology+PSOILPOptimizer":              "PSO+ILP",
    "ILPTopology+BStarILPOptimizer":            "B*+ILP",
}


def _abbrev_run_id(run_id: str) -> str:
    """Shorten a run_id like 'SequencePairTopology+SimulatedAnnealingOptimizer' → 'SP+SA'."""
    if run_id in _RUN_ID_OVERRIDES:
        return _RUN_ID_OVERRIDES[run_id]
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
    dedup: list[str] = []
    for p in parts:
        if not dedup or p != dedup[-1]:
            dedup.append(p)
    return "+".join(dedup)


def _get_block_symmetry_info(block_id: int, sc: dict) -> str:
    """Return a multi-line string describing which symmetry groups block_id belongs to."""
    if not sc:
        return ""
    lines: list[str] = []
    for g in sc.get("groups", []):
        cid = g.get("compound_id", "?")
        tag = str(g.get("topology_tag", ""))
        emv = bool(g.get("enforce_matching_variants", False))
        tag_str = f"[{tag}]" if tag else "[—]"
        # Check symmetric pairs
        for p in g.get("pairs", []):
            if isinstance(p, dict):
                a, b = int(p["block_a"]), int(p["block_b"])
            else:
                a, b = int(p[0]), int(p[1])
            if block_id == a:
                lines.append(f"Group {cid} {tag_str}")
                lines.append(f"  Pair with B{b}" + ("  [enforce variants]" if emv else ""))
                break
            elif block_id == b:
                lines.append(f"Group {cid} {tag_str}")
                lines.append(f"  Pair with B{a}" + ("  [enforce variants]" if emv else ""))
                break
        # Check self-symmetric
        for s in g.get("self_symmetric", []):
            if int(s) == block_id:
                lines.append(f"Group {cid} {tag_str}")
                lines.append(f"  Self-symmetric" + ("  [enforce variants]" if emv else ""))
                break
    for entry in sc.get("cascode_proximity_pairs", []):
        u, l = int(entry[0]), int(entry[1])
        if block_id == u:
            lines.append(f"Cascode proximity: upper (B{l})")
        elif block_id == l:
            lines.append(f"Cascode proximity: lower (B{u})")
    for entry in sc.get("tail_cm_pairs", []):
        t, m = int(entry[0]), int(entry[1])
        if block_id == t:
            lines.append(f"Tail-CM: tail (of B{m})")
        elif block_id == m:
            lines.append(f"Tail-CM: mirror ref (of B{t})")
    return "\n".join(lines)


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

            ox, oy = self._origin
            x_start = math.floor((rect.left() - ox) / step) * step + ox
            y_start = math.floor((rect.top()  - oy) / step) * step + oy

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
# Grid settings widget (kept as utility class; used inside dialogs)
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
# Grid settings dialog  (Options > Grid Settings…)
# -----------------------------------------------------------------------
class GridSettingsDialog(QDialog):
    """Standalone dialog for major/minor grid with Cancel / Apply / OK."""

    applied = pyqtSignal(float, float, bool)   # small, main, visible

    def __init__(self, small: float, main: float, visible: bool, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Grid Settings")
        self.setFixedWidth(310)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._saved = (small, main, visible)
        self._build_ui(small, main, visible)

    def _build_ui(self, small: float, main: float, visible: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)

        form.addWidget(QLabel("Major grid step (µm):"), 0, 0)
        self._main = QDoubleSpinBox()
        self._main.setRange(0.1, 10000.0)
        self._main.setValue(main)
        self._main.setSingleStep(0.5)
        self._main.setDecimals(2)
        form.addWidget(self._main, 0, 1)

        form.addWidget(QLabel("Minor grid step (µm):"), 1, 0)
        self._small = QDoubleSpinBox()
        self._small.setRange(0.05, 1000.0)
        self._small.setValue(small)
        self._small.setSingleStep(0.1)
        self._small.setDecimals(2)
        form.addWidget(self._small, 1, 1)

        self._vis = QCheckBox("Show grid")
        self._vis.setChecked(visible)
        form.addWidget(self._vis, 2, 0, 1, 2)

        layout.addLayout(form)
        layout.addWidget(_separator())

        btns = QHBoxLayout()
        btns.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._cancel)
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._ok)
        btns.addWidget(apply_btn)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _values(self) -> tuple[float, float, bool]:
        return self._small.value(), self._main.value(), self._vis.isChecked()

    def _apply(self) -> None:
        v = self._values()
        self._saved = v
        self.applied.emit(*v)

    def _ok(self) -> None:
        self._apply()
        self.accept()

    def _cancel(self) -> None:
        self.applied.emit(*self._saved)   # restore original
        self.reject()


# -----------------------------------------------------------------------
# Block rendering settings dialog  (Options > Block Rendering…)
# -----------------------------------------------------------------------
class BlockRenderingDialog(QDialog):
    """Dialog for block border width and per-device-type fill/border colors."""

    def __init__(self, lm: LayerManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Block Rendering Settings")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self._lm = lm
        self._saved_fill   = {dt: lm.get_device_fill_rgba(dt)  for dt in lm.device_types()}
        self._saved_border = {dt: lm.get_device_border_rgb(dt) for dt in lm.device_types()}
        self._saved_width  = lm.border_width
        self._fill_btns:   dict[str, QPushButton] = {}
        self._border_btns: dict[str, QPushButton] = {}
        self._build_ui()

    # ---- color button helpers -----------------------------------------------

    def _make_color_btn(self, color: QColor, alpha: bool) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(80, 22)
        btn._color = color    # type: ignore[attr-defined]
        btn._alpha = alpha    # type: ignore[attr-defined]
        self._refresh_btn_style(btn, color)
        btn.clicked.connect(lambda _checked, b=btn: self._pick_color(b))
        return btn

    @staticmethod
    def _refresh_btn_style(btn: QPushButton, color: QColor) -> None:
        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        lum = r * 0.299 + g * 0.587 + b * 0.114
        txt = "#fff" if lum < 128 else "#000"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: rgba({r},{g},{b},{a}); "
            f"border: 1px solid #888; color: {txt}; }}"
        )
        btn.setText(f"#{r:02X}{g:02X}{b:02X}")

    def _pick_color(self, btn: QPushButton) -> None:
        opts = (
            QColorDialog.ColorDialogOption.ShowAlphaChannel
            if btn._alpha  # type: ignore[attr-defined]
            else QColorDialog.ColorDialogOption(0)
        )
        c = QColorDialog.getColor(
            btn._color, self, options=opts   # type: ignore[attr-defined]
        )
        if c.isValid():
            btn._color = c   # type: ignore[attr-defined]
            self._refresh_btn_style(btn, c)

    # ---- UI -----------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Border width
        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("Border line width (µm):"))
        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(0.001, 2.0)
        self._width_spin.setValue(self._lm.border_width)
        self._width_spin.setSingleStep(0.01)
        self._width_spin.setDecimals(3)
        w_row.addWidget(self._width_spin)
        w_row.addStretch()
        layout.addLayout(w_row)

        layout.addWidget(_separator())
        layout.addWidget(QLabel("<b>Device block colors:</b>"))

        tbl = QGridLayout()
        tbl.setSpacing(4)
        tbl.addWidget(QLabel("Device Type"),  0, 0)
        tbl.addWidget(QLabel("Fill"),         0, 1)
        tbl.addWidget(QLabel("Border"),       0, 2)

        for row_idx, dt in enumerate(self._lm.device_types(), start=1):
            r, g, b, a = self._lm.get_device_fill_rgba(dt)
            br, bg, bb = self._lm.get_device_border_rgb(dt)
            fill_btn   = self._make_color_btn(QColor(r, g, b, a), alpha=True)
            border_btn = self._make_color_btn(QColor(br, bg, bb),  alpha=False)
            self._fill_btns[dt]   = fill_btn
            self._border_btns[dt] = border_btn
            tbl.addWidget(QLabel(dt),   row_idx, 0)
            tbl.addWidget(fill_btn,     row_idx, 1)
            tbl.addWidget(border_btn,   row_idx, 2)

        layout.addLayout(tbl)
        layout.addWidget(_separator())

        btns = QHBoxLayout()
        btns.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._cancel)
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._ok)
        btns.addWidget(apply_btn)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    # ---- slots --------------------------------------------------------------

    def _apply(self) -> None:
        self._lm.set_border_width(self._width_spin.value())
        for dt, btn in self._fill_btns.items():
            c: QColor = btn._color  # type: ignore[attr-defined]
            self._lm.set_device_fill(dt, c.red(), c.green(), c.blue(), c.alpha())
        for dt, btn in self._border_btns.items():
            c = btn._color  # type: ignore[attr-defined]
            self._lm.set_device_border(dt, c.red(), c.green(), c.blue())
        # Update saved baseline
        self._saved_fill   = {dt: self._lm.get_device_fill_rgba(dt)  for dt in self._lm.device_types()}
        self._saved_border = {dt: self._lm.get_device_border_rgb(dt) for dt in self._lm.device_types()}
        self._saved_width  = self._lm.border_width
        self._lm.apply_render_settings()

    def _ok(self) -> None:
        self._apply()
        self.accept()

    def _cancel(self) -> None:
        self._lm.set_border_width(self._saved_width)
        for dt, rgba in self._saved_fill.items():
            self._lm.set_device_fill(dt, *rgba)
        for dt, rgb in self._saved_border.items():
            self._lm.set_device_border(dt, *rgb)
        self._lm.apply_render_settings()
        self.reject()


# -----------------------------------------------------------------------
# TikZ export — result viewer  (shows generated LaTeX code)
# -----------------------------------------------------------------------
class TikZResultWindow(QDialog):
    """Displays generated TikZ code with Copy-to-clipboard and Save-as-file actions."""

    def __init__(self, tex_text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("TikZ Export — Generated Code")
        self.resize(820, 600)
        self._tex = tex_text
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Info bar
        n_lines = self._tex.count("\n") + 1
        n_chars = len(self._tex)
        info = QLabel(f"{n_lines} lines  ·  {n_chars} characters")
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)

        # Code editor (read-only)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(self._tex)
        from PyQt6.QtGui import QFont as _QFont
        font = _QFont("Courier New", 9)
        font.setFixedPitch(True)
        editor.setFont(font)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(editor)

        # Buttons
        btn_row = QHBoxLayout()
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.setMinimumWidth(150)
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_save = QPushButton("Save as .tex…")
        btn_save.setMinimumWidth(130)
        btn_save.clicked.connect(self._save_as_file)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_copy)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self._tex)
        # Brief visual feedback via window title
        orig = self.windowTitle()
        self.setWindowTitle("TikZ Export — Copied!")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.setWindowTitle(orig))

    def _save_as_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save TikZ File", "placement.tex",
            "LaTeX files (*.tex);;All files (*)",
        )
        if path:
            try:
                from pathlib import Path as _Path
                _Path(path).write_text(self._tex, encoding="utf-8")
            except OSError as exc:
                QMessageBox.critical(self, "Save Error", str(exc))


# -----------------------------------------------------------------------
# TikZ export — settings dialog  (Tools > Export TikZ…)
# -----------------------------------------------------------------------
class TikZExportWindow(QMainWindow):
    """Settings dialog for TikZ figure export."""

    def __init__(
        self,
        data: json_loader.PlacementData,
        lm: LayerManager,
        drc_violations=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export TikZ")
        self.resize(480, 680)
        self._data = data
        self._lm = lm
        self._drc_violations = drc_violations

        # Collect device types present in this design
        self._present_dtypes: list[str] = sorted({
            b.device_type for b in data.blocks
        })

        self._layer_checks: dict[str, QCheckBox] = {}
        self._dtype_checks: dict[str, QCheckBox] = {}
        self._scale_slider: QSlider | None = None
        self._scale_spin: QSpinBox | None = None
        self._scale_label: QLabel | None = None
        self._result_window: TikZResultWindow | None = None

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scroll area for all settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        pane = QWidget()
        pane_layout = QVBoxLayout(pane)
        pane_layout.setContentsMargins(10, 10, 10, 10)
        pane_layout.setSpacing(8)
        scroll.setWidget(pane)
        outer.addWidget(scroll, 1)

        self._build_layers_group(pane_layout)
        self._build_dtypes_group(pane_layout)
        self._build_scale_group(pane_layout)
        self._build_labels_group(pane_layout)
        self._build_scalebar_group(pane_layout)
        self._build_legend_group(pane_layout)
        pane_layout.addStretch()

        # Generate button in a non-scrolling footer
        footer = QWidget()
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(10, 6, 10, 10)
        gen_btn = QPushButton("Generate TikZ")
        gen_btn.setMinimumHeight(32)
        gen_btn.setMinimumWidth(160)
        gen_btn.clicked.connect(self._generate)
        footer_row.addStretch()
        footer_row.addWidget(gen_btn)
        footer_row.addStretch()
        outer.addWidget(footer)

        self._update_scale_label(100)

    # ── UI builders ──────────────────────────────────────────────────────

    def _make_swatch(self, color: "QColor") -> QLabel:
        swatch = QLabel()
        swatch.setFixedSize(14, 14)
        swatch.setStyleSheet(
            f"background-color: rgb({color.red()},{color.green()},{color.blue()});"
            "border: 1px solid #555; border-radius: 2px;"
        )
        return swatch

    def _build_layers_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Layers")
        grid = QGridLayout(box)
        grid.setSpacing(3)
        for row_idx, ld in enumerate(self._lm.all_layers()):
            chk = QCheckBox(ld.display_name)
            chk.setChecked(ld.name != "drc_overlay")
            self._layer_checks[ld.name] = chk
            swatch = self._make_swatch(ld.color)
            grid.addWidget(swatch, row_idx, 0)
            grid.addWidget(chk, row_idx, 1)
        parent_layout.addWidget(box)

    def _build_dtypes_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Device Types")
        grid = QGridLayout(box)
        grid.setSpacing(3)
        for row_idx, dt in enumerate(self._present_dtypes):
            chk = QCheckBox(dt)
            chk.setChecked(True)
            self._dtype_checks[dt] = chk
            fill_c = self._lm.block_fill(dt)
            border_c = self._lm.block_border(dt)
            fill_sw = self._make_swatch(fill_c)
            border_sw = self._make_swatch(border_c)
            lbl = QLabel("fill / border")
            lbl.setStyleSheet("color: #888; font-size: 10px;")
            row = QHBoxLayout()
            row.setSpacing(3)
            row.addWidget(fill_sw)
            row.addWidget(border_sw)
            row.addWidget(lbl)
            row.addStretch()
            w = QWidget()
            w.setLayout(row)
            grid.addWidget(chk, row_idx, 0)
            grid.addWidget(w, row_idx, 1)
        if not self._present_dtypes:
            grid.addWidget(QLabel("(no device types detected)"), 0, 0)
        parent_layout.addWidget(box)

    def _build_scale_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Scale && Geometry")
        vlayout = QVBoxLayout(box)
        vlayout.setSpacing(6)

        # Slider row
        slider_row = QHBoxLayout()
        lbl_min = QLabel("50%")
        lbl_min.setStyleSheet("color: #888; font-size: 10px;")
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(50, 500)
        self._scale_slider.setValue(100)
        self._scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._scale_slider.setTickInterval(50)
        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(50, 500)
        self._scale_spin.setValue(100)
        self._scale_spin.setSuffix(" %")
        self._scale_spin.setFixedWidth(75)
        lbl_max = QLabel("500%")
        lbl_max.setStyleSheet("color: #888; font-size: 10px;")
        slider_row.addWidget(lbl_min)
        slider_row.addWidget(self._scale_slider, 1)
        slider_row.addWidget(lbl_max)
        slider_row.addWidget(self._scale_spin)
        vlayout.addLayout(slider_row)

        # Live size preview
        self._scale_label = QLabel()
        self._scale_label.setStyleSheet("color: #aaa; font-size: 11px;")
        vlayout.addWidget(self._scale_label)

        self._scale_slider.valueChanged.connect(self._on_scale_changed)
        self._scale_spin.valueChanged.connect(self._on_scale_changed)

        # Line width
        lw_row = QHBoxLayout()
        lw_row.addWidget(QLabel("Border line width:"))
        self._lw_spin = QDoubleSpinBox()
        self._lw_spin.setRange(0.05, 5.0)
        self._lw_spin.setValue(0.4)
        self._lw_spin.setSingleStep(0.05)
        self._lw_spin.setDecimals(2)
        self._lw_spin.setSuffix(" pt")
        self._lw_spin.setFixedWidth(90)
        lw_row.addWidget(self._lw_spin)
        lw_row.addStretch()
        vlayout.addLayout(lw_row)

        # White background
        self._bg_check = QCheckBox("White background")
        self._bg_check.setChecked(True)
        vlayout.addWidget(self._bg_check)

        parent_layout.addWidget(box)

    def _build_labels_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Labels")
        vlayout = QVBoxLayout(box)
        self._show_labels_check = QCheckBox("Show block labels (B0, B1, …)")
        self._show_labels_check.setChecked(True)
        vlayout.addWidget(self._show_labels_check)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Label font size:"))
        self._font_combo = QComboBox()
        self._font_combo.addItems(["tiny", "scriptsize", "footnotesize", "small"])
        font_row.addWidget(self._font_combo)
        font_row.addStretch()
        vlayout.addLayout(font_row)

        self._net_labels_check = QCheckBox("Show net labels near ratsnest centroid")
        self._net_labels_check.setChecked(False)
        vlayout.addWidget(self._net_labels_check)

        parent_layout.addWidget(box)

    def _build_scalebar_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Scale Bar")
        vlayout = QVBoxLayout(box)

        self._scalebar_check = QCheckBox("Show scale bar")
        self._scalebar_check.setChecked(True)
        vlayout.addWidget(self._scalebar_check)

        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Bar length (µm):"))
        self._bar_len_spin = QDoubleSpinBox()
        self._bar_len_spin.setRange(0.0, 10000.0)
        self._bar_len_spin.setValue(0.0)
        self._bar_len_spin.setSingleStep(1.0)
        self._bar_len_spin.setDecimals(1)
        self._bar_len_spin.setSpecialValueText("auto")
        self._bar_len_spin.setFixedWidth(100)
        len_row.addWidget(self._bar_len_spin)
        len_row.addStretch()
        vlayout.addLayout(len_row)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Position:"))
        self._bar_pos_combo = QComboBox()
        self._bar_pos_combo.addItems(["bottom-left", "bottom-right"])
        pos_row.addWidget(self._bar_pos_combo)
        pos_row.addStretch()
        vlayout.addLayout(pos_row)

        parent_layout.addWidget(box)

    def _build_legend_group(self, parent_layout: QVBoxLayout) -> None:
        box = QGroupBox("Legend && Extras")
        vlayout = QVBoxLayout(box)

        self._legend_check = QCheckBox("Show color legend")
        self._legend_check.setChecked(True)
        vlayout.addWidget(self._legend_check)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Comment / name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("my_placement  (shown in header comment)")
        name_row.addWidget(self._name_edit)
        vlayout.addLayout(name_row)

        parent_layout.addWidget(box)

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_scale_changed(self, value: int) -> None:
        self._scale_slider.blockSignals(True)
        self._scale_spin.blockSignals(True)
        self._scale_slider.setValue(value)
        self._scale_spin.setValue(value)
        self._scale_slider.blockSignals(False)
        self._scale_spin.blockSignals(False)
        self._update_scale_label(value)

    def _update_scale_label(self, scale_pct: int) -> None:
        if self._scale_label is None:
            return
        pr = self._data.placement_result
        if not pr or not pr.placed_blocks:
            self._scale_label.setText("→ no placement data loaded")
            return
        flat_bbs = [pb.main_bbox for pb in pr.placed_blocks.values()]
        chip_w = max(b[2] for b in flat_bbs) - min(b[0] for b in flat_bbs)
        chip_h = max(b[3] for b in flat_bbs) - min(b[1] for b in flat_bbs)
        S = scale_pct / 100.0
        self._scale_label.setText(
            f"→ {chip_w*S:.1f} × {chip_h*S:.1f} mm on paper"
            f"  (1 µm = {S:.2f} mm)"
        )

    def _collect_settings(self) -> "_tikz.TikZExportSettings":
        enabled_layers = {
            name for name, chk in self._layer_checks.items()
            if chk.isChecked()
        }
        enabled_dtypes = {
            dt for dt, chk in self._dtype_checks.items()
            if chk.isChecked()
        }
        return _tikz.TikZExportSettings(
            scale_pct=float(self._scale_spin.value()),
            enabled_layers=enabled_layers,
            enabled_device_types=enabled_dtypes,
            show_labels=self._show_labels_check.isChecked(),
            label_font_size=self._font_combo.currentText(),
            line_width_pt=self._lw_spin.value(),
            background_white=self._bg_check.isChecked(),
            show_scale_bar=self._scalebar_check.isChecked(),
            scale_bar_length_um=self._bar_len_spin.value(),
            scale_bar_position=self._bar_pos_combo.currentText(),
            show_legend=self._legend_check.isChecked(),
            show_net_labels=self._net_labels_check.isChecked(),
            comment_name=self._name_edit.text().strip(),
        )

    def _generate(self) -> None:
        settings = self._collect_settings()
        try:
            tex = _tikz.generate(self._data, self._lm, settings, self._drc_violations)
        except Exception as exc:
            QMessageBox.critical(self, "TikZ Export Error", str(exc))
            return
        self._result_window = TikZResultWindow(tex, parent=self)
        self._result_window.show()
        self._result_window.raise_()


# -----------------------------------------------------------------------
# GDS Export window  (Tools > Export GDS…)
# -----------------------------------------------------------------------
class GDSExportWindow(QMainWindow):
    """Export placement to GDS-II with configurable layer assignments and KLayout (WSL) integration."""

    _PDK_LAYERS_PATH = Path(__file__).parent.parent / "myPDK" / "gpdk090_gds_layers.json"

    _DEFAULT_ACTIVE: dict[str, str] = {
        "nmos_hvt": "OD_25", "pmos_hvt": "OD_25",
        "nmos_rvt": "OD",    "nmos_lvt": "OD",
        "pmos_rvt": "OD",    "pmos_lvt": "OD",
        "res_poly": "RPO",   "cap_mom":  "M1",
    }
    _DEFAULT_GATE = "PO"

    # Layer → color used in generated .lyp files
    _LYP_COLORS: dict[str, str] = {
        "NW": "#aa44aa", "OD": "#44cc44", "OD_25": "#88dd44",
        "PO": "#dddd00", "PP": "#cc4488", "NP": "#4488cc",
        "RPO": "#cc8844", "CO": "#aaaaaa", "M1": "#4488ff",
        "M2": "#ff8844", "M3": "#44ffff", "M4": "#ff44ff",
        "M5": "#ffcc44", "M6": "#44ccff", "ANN": "#666666",
    }

    def __init__(self, data: json_loader.PlacementData, parent=None) -> None:
        super().__init__(parent)
        self._data = data
        self._pdk_layers: dict[str, int] = {}
        self._layer_names: list[str] = []
        self._active_combos: dict[str, QComboBox] = {}
        self._gate_combos:   dict[str, QComboBox] = {}
        self._pin_combo: QComboBox | None = None

        self.setWindowTitle("Export GDS")
        self.resize(720, 580)
        self._load_pdk()
        self._build_ui()

    # ---- PDK loading --------------------------------------------------------

    def _load_pdk(self) -> None:
        try:
            raw = json.loads(self._PDK_LAYERS_PATH.read_text(encoding="utf-8"))
            self._pdk_layers = {name: info["layer"] for name, info in raw["layers"].items()}
            self._layer_names = sorted(self._pdk_layers.keys(), key=lambda n: self._pdk_layers[n])
        except Exception:
            self._pdk_layers = {"OD": 6, "PO": 17, "OD_25": 18, "RPO": 29, "M1": 31, "ANN": 100}
            self._layer_names = list(self._pdk_layers.keys())

    def _layer_items(self) -> list[str]:
        return [f"{n}  ({self._pdk_layers[n]})" for n in self._layer_names]

    def _layer_idx(self, name: str) -> int:
        try:
            return self._layer_names.index(name)
        except ValueError:
            return 0

    # ---- UI -----------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Layer assignments
        la_group = QGroupBox("Layer Assignments")
        la_layout = QVBoxLayout(la_group)

        layer_items = self._layer_items()
        tbl = QGridLayout()
        tbl.setSpacing(4)
        tbl.addWidget(QLabel("<b>Device Type</b>"),  0, 0)
        tbl.addWidget(QLabel("<b>Active Layer</b>"), 0, 1)
        tbl.addWidget(QLabel("<b>Gate Layer</b>"),   0, 2)

        dt_present = sorted({b.device_type for b in self._data.blocks})
        for row, dt in enumerate(dt_present, start=1):
            tbl.addWidget(QLabel(dt), row, 0)

            active_cb = QComboBox()
            active_cb.addItems(layer_items)
            active_cb.setCurrentIndex(self._layer_idx(self._DEFAULT_ACTIVE.get(dt, "OD")))
            tbl.addWidget(active_cb, row, 1)
            self._active_combos[dt] = active_cb

            gate_cb = QComboBox()
            gate_cb.addItems(layer_items)
            gate_cb.setCurrentIndex(self._layer_idx(self._DEFAULT_GATE))
            tbl.addWidget(gate_cb, row, 2)
            self._gate_combos[dt] = gate_cb

        pin_row = len(dt_present) + 1
        tbl.addWidget(QLabel("Pins / Power Rails"), pin_row, 0)
        self._pin_combo = QComboBox()
        self._pin_combo.addItems(layer_items)
        self._pin_combo.setCurrentIndex(self._layer_idx("M1"))
        tbl.addWidget(self._pin_combo, pin_row, 1)
        tbl.addWidget(QLabel("—"), pin_row, 2)

        la_layout.addLayout(tbl)
        layout.addWidget(la_group)

        # Output file
        out_group = QGroupBox("Output File")
        out_layout = QHBoxLayout(out_group)
        out_layout.addWidget(QLabel("Path:"))
        self._out_path = QLineEdit()
        default_out = str(Path(__file__).parent.parent / "output.gds")
        self._out_path.setText(default_out)
        out_layout.addWidget(self._out_path, stretch=1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_output)
        out_layout.addWidget(browse_btn)
        layout.addWidget(out_group)

        # Export button + status
        exp_row = QHBoxLayout()
        export_btn = QPushButton("Export GDS")
        export_btn.setMinimumWidth(130)
        export_btn.clicked.connect(self._export)
        exp_row.addWidget(export_btn)
        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        exp_row.addWidget(self._status_label, stretch=1)
        layout.addLayout(exp_row)

        layout.addWidget(_separator())

        # KLayout options
        kl_group = QGroupBox("KLayout (WSL) Options")
        kl_layout = QVBoxLayout(kl_group)

        self._kl_open_check = QCheckBox("Open in KLayout (WSL) after export")
        kl_layout.addWidget(self._kl_open_check)

        # Layer design source
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Layer design:"))
        self._kl_lyp_source = QComboBox()
        _builtin = Path(__file__).parent.parent / "lib" / "alda_layers.lyp"
        _items = []
        if _builtin.exists():
            _items.append("Built-in ALDA design")
        _items += ["Auto-generate from assignments", "Custom file…", "None (no .lyp)"]
        self._kl_lyp_source.addItems(_items)
        self._kl_lyp_source.currentIndexChanged.connect(self._on_lyp_source_changed)
        src_row.addWidget(self._kl_lyp_source)
        src_row.addStretch()
        kl_layout.addLayout(src_row)

        # Custom file path row (shown only when "Custom file…" selected)
        self._kl_custom_row = QWidget()
        cr = QHBoxLayout(self._kl_custom_row)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.addWidget(QLabel("Custom .lyp:"))
        self._kl_custom_path = QLineEdit()
        self._kl_custom_path.setPlaceholderText("Path to .lyp file…")
        cr.addWidget(self._kl_custom_path, stretch=1)
        kl_browse = QPushButton("Browse…")
        kl_browse.clicked.connect(self._browse_lyp)
        cr.addWidget(kl_browse)
        kl_layout.addWidget(self._kl_custom_row)
        self._kl_custom_row.setVisible(False)

        # Auto-generate options (shown only when "Auto-generate" selected)
        self._kl_autogen_row = QWidget()
        ar = QHBoxLayout(self._kl_autogen_row)
        ar.setContentsMargins(0, 0, 0, 0)
        ar.addWidget(QLabel("Include layers:"))
        self._kl_display_combo = QComboBox()
        self._kl_display_combo.addItems(["All PDK layers", "Active device layers only"])
        ar.addWidget(self._kl_display_combo)
        ar.addStretch()
        kl_layout.addWidget(self._kl_autogen_row)
        self._kl_autogen_row.setVisible(False)

        wsl_row = QHBoxLayout()
        wsl_row.addWidget(QLabel("WSL KLayout command:"))
        self._kl_cmd = QLineEdit("wsl klayout")
        self._kl_cmd.setToolTip(
            "Command used to launch KLayout via WSL, e.g. 'wsl klayout' or 'wsl /usr/bin/klayout'"
        )
        wsl_row.addWidget(self._kl_cmd, stretch=1)
        kl_layout.addLayout(wsl_row)

        layout.addWidget(kl_group)
        layout.addStretch()

        # Trigger initial visibility
        self._on_lyp_source_changed(0)

    # ---- slots --------------------------------------------------------------

    def _on_lyp_source_changed(self, _idx: int) -> None:
        label = self._kl_lyp_source.currentText()
        self._kl_custom_row.setVisible(label == "Custom file…")
        self._kl_autogen_row.setVisible(label == "Auto-generate from assignments")

    def _browse_output(self) -> None:
        start_dir = str(Path(__file__).parent.parent)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save GDS file", start_dir, "GDS files (*.gds);;All files (*)"
        )
        if path:
            self._out_path.setText(path)

    def _browse_lyp(self) -> None:
        start_dir = str(Path(__file__).parent.parent / "lib")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select KLayout layer properties", start_dir,
            "KLayout layer properties (*.lyp);;All files (*)"
        )
        if path:
            self._kl_custom_path.setText(path)

    def _get_layer_overrides(self) -> dict[str, list[int]]:
        overrides: dict[str, list[int]] = {}
        for dt, active_cb in self._active_combos.items():
            active_num = self._pdk_layers[self._layer_names[active_cb.currentIndex()]]
            gate_num   = self._pdk_layers[self._layer_names[self._gate_combos[dt].currentIndex()]]
            overrides[dt] = [active_num, gate_num]
        return overrides

    def _export(self) -> None:
        out_path = self._out_path.text().strip()
        if not out_path:
            self._status_label.setText("Error: no output path specified")
            return

        assert self._pin_combo is not None
        pin_layer_num = self._pdk_layers[self._layer_names[self._pin_combo.currentIndex()]]
        layer_overrides = self._get_layer_overrides()

        try:
            from gds_exporter import export as gds_export
            gds_export(
                self._data, out_path,
                layer_overrides=layer_overrides,
                pin_layer=pin_layer_num,
            )
            self._status_label.setText(f"Exported: {Path(out_path).name}")
        except Exception as exc:
            self._status_label.setText(f"Error: {exc}")
            QMessageBox.critical(self, "GDS Export Error", str(exc))
            return

        if self._kl_open_check.isChecked():
            self._open_in_klayout(out_path)

    @staticmethod
    def _to_wsl(p: str) -> str:
        import re
        m = re.match(r'^([A-Za-z]):[/\\](.*)', p)
        if m:
            drive = m.group(1).lower()
            rest  = m.group(2).replace("\\", "/")
            return f"/mnt/{drive}/{rest}"
        return p.replace("\\", "/")

    def _resolve_lyp(self, gds_path: str) -> str | None:
        """Return the .lyp path to pass to KLayout, or None to skip."""
        label = self._kl_lyp_source.currentText()

        if label == "None (no .lyp)":
            return None

        if label == "Built-in ALDA design":
            builtin = Path(__file__).parent.parent / "lib" / "alda_layers.lyp"
            if builtin.exists():
                return str(builtin)
            QMessageBox.warning(self, "Layer Design Missing",
                                f"Built-in file not found:\n{builtin}")
            return None

        if label == "Custom file…":
            custom = self._kl_custom_path.text().strip()
            if not custom:
                QMessageBox.warning(self, "No Custom File",
                                    "Enter a path to a .lyp file or pick a different source.")
                return None
            if not Path(custom).exists():
                QMessageBox.warning(self, "File Not Found",
                                    f"Custom .lyp file not found:\n{custom}")
                return None
            return custom

        # "Auto-generate from assignments"
        lyp_path = str(Path(gds_path).with_suffix(".lyp"))
        try:
            self._generate_lyp(lyp_path)
            return lyp_path
        except Exception as exc:
            QMessageBox.warning(self, "LYP Generation Error",
                                f"Could not generate .lyp file:\n{exc}")
            return None

    def _open_in_klayout(self, gds_path: str) -> None:
        wsl_gds  = self._to_wsl(gds_path)
        cmd_base = self._kl_cmd.text().strip().split()
        cmd      = cmd_base + [wsl_gds]

        lyp_path = self._resolve_lyp(gds_path)
        if lyp_path:
            cmd += ["-l", self._to_wsl(lyp_path)]

        try:
            subprocess.Popen(cmd)
            self._status_label.setText(f"KLayout launched — {Path(gds_path).name}")
        except Exception as exc:
            QMessageBox.warning(
                self, "KLayout Launch Error",
                f"Could not launch KLayout:\n{exc}\n\nCommand: {' '.join(cmd)}"
            )

    def _generate_lyp(self, lyp_path: str) -> None:
        """Auto-generate a KLayout .lyp file from the current layer assignments."""
        active_only = self._kl_display_combo.currentIndex() == 1

        if active_only:
            assert self._pin_combo is not None
            used: set[str] = set()
            for cb in self._active_combos.values():
                used.add(self._layer_names[cb.currentIndex()])
            for cb in self._gate_combos.values():
                used.add(self._layer_names[cb.currentIndex()])
            used.add(self._layer_names[self._pin_combo.currentIndex()])
            used.add("ANN")
            layers_to_write = {n: self._pdk_layers[n] for n in used if n in self._pdk_layers}
        else:
            layers_to_write = self._pdk_layers

        root = Element("layer-properties")
        for name, lnum in sorted(layers_to_write.items(), key=lambda x: x[1]):
            prop = SubElement(root, "properties")
            color = self._LYP_COLORS.get(name, "#888888")
            SubElement(prop, "frame-color").text = color
            SubElement(prop, "fill-color").text = color
            SubElement(prop, "frame-brightness").text = "0"
            SubElement(prop, "fill-brightness").text = "0"
            SubElement(prop, "dither-pattern").text = "I5"
            SubElement(prop, "line-style").text = "I0"
            SubElement(prop, "valid").text = "true"
            SubElement(prop, "visible").text = "true"
            SubElement(prop, "transparent").text = "false"
            SubElement(prop, "width").text = "1"
            SubElement(prop, "marked").text = "false"
            SubElement(prop, "xfill").text = "false"
            SubElement(prop, "animation").text = "0"
            SubElement(prop, "n").text = f"{name} ({lnum}/0)"
            SubElement(prop, "source").text = f"{lnum}/0@1"

        tree = ElementTree(root)
        _xml_indent(tree, space=" ")
        tree.write(lyp_path, xml_declaration=True, encoding="utf-8")


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

        layout.addWidget(_separator())

        # --- Symmetry ---------------------------------------------------------
        layout.addWidget(QLabel("<b>Symmetry</b>"))
        self._sym_info = QLabel("—")
        self._sym_info.setWordWrap(True)
        self._sym_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._sym_info)

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
        sym_text = _get_block_symmetry_info(block.block_id, data.symmetry_constraints)
        self._sym_info.setText(sym_text if sym_text else "—")

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

    group_highlight_requested = pyqtSignal(list)  # emits list[int] of block IDs to highlight

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sym_groups: list = []
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

        # --- Symmetry groups -------------------------------------------------
        sym_gb = QGroupBox("Symmetry Groups")
        sym_layout = QVBoxLayout(sym_gb)
        sym_layout.setContentsMargins(4, 4, 4, 4)
        sym_layout.setSpacing(2)
        self._sym_table = QTableWidget(0, 4)
        self._sym_table.setHorizontalHeaderLabels(["ID", "Type", "Blocks", "Variants"])
        self._sym_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sym_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._sym_table.setAlternatingRowColors(True)
        self._sym_table.verticalHeader().setVisible(False)
        self._sym_table.setMaximumHeight(110)
        self._sym_table.horizontalHeader().setStretchLastSection(True)
        self._sym_table.itemSelectionChanged.connect(self._on_sym_group_selected)
        sym_layout.addWidget(self._sym_table)
        layout.addWidget(sym_gb)

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

        self._sel_sym_sep = _separator()
        self._sel_sym_sep.setVisible(False)
        sel_layout.addWidget(self._sel_sym_sep)

        self._sel_sym_header = QLabel("<b>Symmetry</b>")
        self._sel_sym_header.setVisible(False)
        sel_layout.addWidget(self._sel_sym_header)

        self._sel_sym_info = QLabel("")
        self._sel_sym_info.setWordWrap(True)
        self._sel_sym_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sel_layout.addWidget(self._sel_sym_info)

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

    def update_symmetry_groups(self, groups: list) -> None:
        """Populate the Topology Groups table from the top-level groups list."""
        self._sym_groups = groups or []
        self._sym_table.setRowCount(len(self._sym_groups))
        for row, g in enumerate(self._sym_groups):
            vals = [
                str(g.get("group_id", "?")),
                str(g.get("topology_type", "—")),
                str(len(g.get("block_ids", []))),
                str(len(g.get("matching_variants", []))),
            ]
            for col, val in enumerate(vals):
                self._sym_table.setItem(row, col, QTableWidgetItem(val))
        self._sym_table.resizeColumnsToContents()

    def _on_sym_group_selected(self) -> None:
        rows = {idx.row() for idx in self._sym_table.selectedIndexes()}
        if not rows:
            self.group_highlight_requested.emit([])
            return
        row = next(iter(rows))
        if row >= len(self._sym_groups):
            return
        g = self._sym_groups[row]
        block_ids = [int(bid) for bid in g.get("block_ids", [])]
        self.group_highlight_requested.emit(block_ids)

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
        sym_text = _get_block_symmetry_info(block.block_id, data.symmetry_constraints)
        self._sel_sym_info.setText(sym_text if sym_text else "—")
        self._sel_variant_sep.setVisible(True)
        self._sel_pins_sep.setVisible(True)
        self._sel_pins_header.setVisible(True)
        self._sel_sym_sep.setVisible(True)
        self._sel_sym_header.setVisible(True)

    def clear_selection(self) -> None:
        self._sel_title.setText("<i>Click a block in the view</i>")
        self._sel_info.setText("")
        self._sel_variant.setText("")
        self._sel_pins.setText("")
        self._sel_sym_info.setText("")
        self._sel_variant_sep.setVisible(False)
        self._sel_pins_sep.setVisible(False)
        self._sel_pins_header.setVisible(False)
        self._sel_sym_sep.setVisible(False)
        self._sel_sym_header.setVisible(False)


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
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
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
        self.setMinimumWidth(300)

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
        self._drc_window:  DRCWindow | None = None
        self._drc_action:    QAction  | None = None
        self._sim_action:    QAction  | None = None
        self._gds_action:    QAction  | None = None
        self._tikz_action:   QAction  | None = None
        self._route_action:  QAction  | None = None
        self._warmup_action: QAction  | None = None
        self._sim_window:   SimulationWindow | None = None
        self._gds_window:   GDSExportWindow  | None = None
        self._tikz_window:  TikZExportWindow | None = None
        self._route_window: RoutingWindow    | None = None
        self._current_path: Path | None = None

        # Grid settings (backing values — updated by GridSettingsDialog)
        self._grid_small:   float = 1.0
        self._grid_main:    float = 5.0
        self._grid_visible: bool  = True

        # Exhaustive mode state
        self._exhaustive_mode: bool = False
        self._exhaustive_scenes: list[PlacementScene] = []
        self._exhaustive_views: list[CanvasView] = []
        self._exhaustive_data: list[json_loader.PlacementData] = []
        self._exhaustive_tab_start: int = -1

        self._build_ui()
        self._build_menus()

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
        splitter.setSizes([215, 1000, 360])

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

        # ---- File -----------------------------------------------------------
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

        # ---- View -----------------------------------------------------------
        vm = mb.addMenu("&View")
        fa = QAction("&Fit  [F]", self)
        fa.setShortcut(QKeySequence("F"))
        fa.triggered.connect(self._fit_current)
        vm.addAction(fa)

        faa = QAction("Fit &all tabs", self)
        faa.triggered.connect(self._fit_all)
        vm.addAction(faa)

        vm.addSeparator()
        zi = QAction("Zoom &In", self)
        zi.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zi.triggered.connect(
            lambda: self._current_view() and self._current_view().scale(1.2, 1.2)
        )
        vm.addAction(zi)

        zo = QAction("Zoom &Out", self)
        zo.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zo.triggered.connect(
            lambda: self._current_view() and self._current_view().scale(1 / 1.2, 1 / 1.2)
        )
        vm.addAction(zo)

        # ---- Options --------------------------------------------------------
        om = mb.addMenu("&Options")
        grid_act = QAction("&Grid Settings…", self)
        grid_act.triggered.connect(self._open_grid_dialog)
        om.addAction(grid_act)

        render_act = QAction("&Block Rendering…", self)
        render_act.triggered.connect(self._open_block_rendering)
        om.addAction(render_act)

        # ---- Tools ----------------------------------------------------------
        tm = mb.addMenu("&Tools")
        self._drc_action = QAction("&DRC Check", self)
        self._drc_action.setToolTip("Run Design Rule Check (requires loaded placement)")
        self._drc_action.setEnabled(False)
        self._drc_action.triggered.connect(self._open_drc_window)
        tm.addAction(self._drc_action)

        self._sim_action = QAction("&Simulate Circuit…", self)
        self._sim_action.setToolTip("Run placement optimizer with custom settings")
        self._sim_action.triggered.connect(self._open_sim_window)
        tm.addAction(self._sim_action)

        self._route_action = QAction("&Route Placement…", self)
        self._route_action.setToolTip("Run router on a placed py101 JSON file")
        self._route_action.setEnabled(False)
        self._route_action.triggered.connect(self._open_routing_window)
        tm.addAction(self._route_action)

        self._warmup_action = QAction("&Warmup Runs…", self)
        self._warmup_action.setToolTip("View all warmup placements from the last ILP run")
        self._warmup_action.setEnabled(False)
        self._warmup_action.triggered.connect(self._on_view_warmup_runs)
        tm.addAction(self._warmup_action)

        tm.addSeparator()
        self._gds_action = QAction("&Export GDS…", self)
        self._gds_action.setToolTip("Export placement to GDS-II file")
        self._gds_action.setEnabled(False)
        self._gds_action.triggered.connect(self._open_gds_window)
        tm.addAction(self._gds_action)

        self._tikz_action = QAction("Export &TikZ…", self)
        self._tikz_action.setToolTip("Export placement as TikZ/LaTeX figure")
        self._tikz_action.setEnabled(False)
        self._tikz_action.triggered.connect(self._open_tikz_window)
        tm.addAction(self._tikz_action)

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
        self._current_path = Path(path)
        self._load_data(data, Path(path).name)

    def _load_data(self, data: json_loader.PlacementData, title: str = "") -> None:
        # Close any open detail / tool windows from a previous file
        for w in self._detail_windows:
            w.close()
        self._detail_windows.clear()

        if self._drc_window is not None:
            self._drc_window.close()
            self._drc_window = None
        if self._gds_window is not None:
            self._gds_window.close()
            self._gds_window = None
        if self._tikz_window is not None:
            self._tikz_window.close()
            self._tikz_window = None

        self._data = data
        self._scenes.clear()
        self._views.clear()
        self.lm._callbacks.clear()
        self.lm._render_callbacks.clear()
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

        small, main, vis = self._grid_small, self._grid_main, self._grid_visible

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
            self._placement_info_panel.update_symmetry_groups(data.groups)
            self._placement_info_panel.clear_selection()
            try:
                self._placement_info_panel.group_highlight_requested.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._placement_info_panel.group_highlight_requested.connect(ps.highlight_group_blocks)
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
        has_routing = any(n.route_segments for n in data.nets)
        routed_tag = "  |  Routed" if has_routing else ""
        self.setWindowTitle(f"ALDA Placement Viewer — {title}")
        self._mode_label.setText(f"Mode: {mode}  |  Blocks: {len(data.blocks)}{routed_tag}")
        self._status.showMessage(f"Loaded {title}  ({len(data.blocks)} blocks)", 3000)

        # Update action enable/disable states
        has_placement = (
            bool(self._exhaustive_scenes) or
            (data.has_placement and data.placement_result is not None)
        )
        if self._drc_action:
            self._drc_action.setEnabled(has_placement)
        if self._route_action:
            self._route_action.setEnabled(has_placement)
        if self._gds_action:
            self._gds_action.setEnabled(True)  # available for any loaded data
        if self._tikz_action:
            self._tikz_action.setEnabled(True)
        if self._warmup_action:
            has_warmup = (
                data.placement_result is not None
                and bool(data.placement_result.warmup_runs)
            )
            self._warmup_action.setEnabled(has_warmup)

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
        self._grid_small   = small
        self._grid_main    = main
        self._grid_visible = visible
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
        self._current_path = path
        data = json_loader.load(path)
        self._load_data(data, path.name)
        # Auto-open warmup visualizer if warmup_runs were saved
        if (
            data.placement_result is not None
            and data.placement_result.warmup_runs
        ):
            self._open_warmup_view(data.placement_result.warmup_runs)

    def _open_warmup_view(self, warmup_runs: list) -> None:
        from warmup_view import WarmupViewDialog
        dlg = WarmupViewDialog(warmup_runs, parent=self)
        dlg.show()

    def _on_view_warmup_runs(self) -> None:
        if (
            self._data is not None
            and self._data.placement_result is not None
            and self._data.placement_result.warmup_runs
        ):
            self._open_warmup_view(self._data.placement_result.warmup_runs)

    def _open_routing_window(self) -> None:
        if self._route_window is not None and self._route_window.isVisible():
            self._route_window.raise_()
            self._route_window.activateWindow()
            return
        self._route_window = RoutingWindow(prefill_path=self._current_path, parent=self)
        self._route_window.result_ready.connect(self._load_routing_result)
        self._route_window.show()

    def _load_routing_result(self, path: Path) -> None:
        self._current_path = path
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
            block, self._data, self.lm,
            (self._grid_small, self._grid_main, self._grid_visible),
        )
        w.show()
        self._detail_windows.append(w)

    def _on_mouse_moved(self, x: float, y: float) -> None:
        self._coord_label.setText(f"({x:.3f} µm,  {y:.3f} µm)")

    # ---- new tool methods ---------------------------------------------------

    def _open_grid_dialog(self) -> None:
        dlg = GridSettingsDialog(
            self._grid_small, self._grid_main, self._grid_visible, parent=self
        )
        dlg.applied.connect(self._on_grid_changed)
        dlg.exec()

    def _open_block_rendering(self) -> None:
        dlg = BlockRenderingDialog(self.lm, parent=self)
        dlg.exec()

    def _open_gds_window(self) -> None:
        if self._gds_window is not None and self._gds_window.isVisible():
            self._gds_window.raise_()
            self._gds_window.activateWindow()
            return
        if not self._data:
            return
        self._gds_window = GDSExportWindow(self._data, parent=self)
        self._gds_window.show()

    def _open_tikz_window(self) -> None:
        if self._tikz_window is not None and self._tikz_window.isVisible():
            self._tikz_window.raise_()
            self._tikz_window.activateWindow()
            return
        if not self._data:
            return
        drc_viols = (
            self._drc_window._violations
            if self._drc_window is not None and self._drc_window.isVisible()
            else None
        )
        self._tikz_window = TikZExportWindow(
            self._data, self.lm, drc_viols, parent=self
        )
        self._tikz_window.show()

    # -----------------------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F:
            self._fit_current()
        else:
            super().keyPressEvent(event)
