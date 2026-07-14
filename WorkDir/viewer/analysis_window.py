"""Analysis tool — cost-over-time graphing, driven from the viewer's Tools menu."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QAbstractItemView,
    QDoubleSpinBox, QFileDialog, QMessageBox,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import cost_trace_plot as ctp

_TRACES_DIR = Path(__file__).parent.parent / "traces"


class AnalysisWindow(QMainWindow):
    """
    Toggle cost-over-time logging on/off, load a session's manifest + trace
    files, adjust the chart (which runs, legend, line width, title), and
    export PNG (matches the preview) or CSV (raw underlying rows).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analysis")
        self.resize(950, 650)

        self._session: ctp.Session | None = None

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        controls = QVBoxLayout()

        self._cb_enabled = QCheckBox("Log cost-over-time on next run")
        self._cb_enabled.setToolTip(
            "Turn this on before running a simulation (Tools > Simulate Circuit) "
            "to record cost-vs-time for every optimizer/warmup run."
        )
        self._cb_enabled.setChecked(QSettings().value("cost_trace/enabled", False, type=bool))
        self._cb_enabled.toggled.connect(self._on_toggle_enabled)
        controls.addWidget(self._cb_enabled)

        load_btn = QPushButton("Load Latest Session")
        load_btn.clicked.connect(self._load_latest)
        controls.addWidget(load_btn)

        browse_btn = QPushButton("Browse Session…")
        browse_btn.clicked.connect(self._browse_session)
        controls.addWidget(browse_btn)

        controls.addWidget(QLabel("Runs:"))
        self._run_list = QListWidget()
        self._run_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._run_list.itemChanged.connect(self._redraw)
        controls.addWidget(self._run_list, 1)

        self._cb_legend = QCheckBox("Show legend")
        self._cb_legend.setChecked(True)
        self._cb_legend.toggled.connect(self._redraw)
        controls.addWidget(self._cb_legend)

        self._cb_log_scale = QCheckBox("Log10 y-axis")
        self._cb_log_scale.setToolTip(
            "Plot cost on a log10 scale — makes small changes near the end "
            "of a run easier to see than on a linear axis."
        )
        self._cb_log_scale.toggled.connect(self._redraw)
        controls.addWidget(self._cb_log_scale)

        lw_row = QHBoxLayout()
        lw_row.addWidget(QLabel("Line width:"))
        self._sp_linewidth = QDoubleSpinBox()
        self._sp_linewidth.setRange(0.5, 6.0)
        self._sp_linewidth.setSingleStep(0.5)
        self._sp_linewidth.setValue(1.5)
        self._sp_linewidth.valueChanged.connect(self._redraw)
        lw_row.addWidget(self._sp_linewidth)
        controls.addLayout(lw_row)

        controls.addWidget(QLabel("Title:"))
        self._title_edit = QLineEdit()
        self._title_edit.textChanged.connect(self._redraw)
        controls.addWidget(self._title_edit)

        export_row = QHBoxLayout()
        png_btn = QPushButton("Export PNG…")
        png_btn.clicked.connect(self._export_png)
        export_row.addWidget(png_btn)
        csv_btn = QPushButton("Export CSV…")
        csv_btn.clicked.connect(self._export_csv)
        export_row.addWidget(csv_btn)
        controls.addLayout(export_row)

        controls.addStretch(1)

        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls_widget.setFixedWidth(260)
        root.addWidget(controls_widget)

        self._canvas = FigureCanvasQTAgg(Figure(figsize=(8, 5)))
        root.addWidget(self._canvas, 1)

    # ------------------------------------------------------------------
    def _on_toggle_enabled(self, checked: bool) -> None:
        QSettings().setValue("cost_trace/enabled", checked)

    def _load_latest(self) -> None:
        session_dir = ctp.latest_session_dir(_TRACES_DIR)
        if session_dir is None:
            QMessageBox.warning(
                self, "Analysis",
                "No cost-trace sessions found under WorkDir/traces/.\n"
                "Turn logging on above, then run a simulation first.",
            )
            return
        self._load_session_dir(session_dir)

    def _browse_session(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select session directory", str(_TRACES_DIR))
        if d:
            self._load_session_dir(Path(d))

    def _load_session_dir(self, session_dir: Path) -> None:
        try:
            self._session = ctp.load_session(session_dir)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Analysis", f"Could not load session:\n{exc}")
            return

        # Block signals on both widgets while populating — otherwise
        # setText()/addItem() fire a premature _redraw() before the run
        # list has any items (empty selection → matplotlib legend warning).
        self._title_edit.blockSignals(True)
        self._title_edit.setText(ctp.default_title(self._session))
        self._title_edit.blockSignals(False)

        self._run_list.blockSignals(True)
        self._run_list.clear()
        for run in self._session.runs:
            item = QListWidgetItem(run.label)
            item.setData(Qt.ItemDataRole.UserRole, run.run_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self._run_list.addItem(item)
        self._run_list.blockSignals(False)

        self._redraw()

    def _selected_run_ids(self) -> list[str]:
        ids: list[str] = []
        for i in range(self._run_list.count()):
            item = self._run_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _redraw(self) -> None:
        if self._session is None:
            return
        ctp.build_figure(
            self._session,
            run_ids     = self._selected_run_ids(),
            title       = self._title_edit.text(),
            show_legend = self._cb_legend.isChecked(),
            linewidth   = self._sp_linewidth.value(),
            log_scale   = self._cb_log_scale.isChecked(),
            fig         = self._canvas.figure,
        )
        self._canvas.draw()

    def _export_png(self) -> None:
        if self._session is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG Image (*.png)")
        if path:
            ctp.export_png(self._canvas.figure, path)

    def _export_csv(self) -> None:
        if self._session is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV (*.csv)")
        if path:
            ctp.export_csv(self._session, path, run_ids=self._selected_run_ids())
