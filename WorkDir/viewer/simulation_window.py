"""Floating Simulate panel — launch the placement optimizer from the viewer."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QRadioButton, QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from routing_window import RoutingSettingsDialog, find_routing_output

try:
    import winsound as _winsound
except ImportError:
    _winsound = None

# Paths
_VIEWER_DIR    = Path(__file__).parent
_SCRIPTS_DIR   = _VIEWER_DIR.parent / "scripts"
_MAIN_PY       = _SCRIPTS_DIR / "main.py"
_PIPELINE_PY   = _SCRIPTS_DIR / "lib" / "pipeline.py"
_OUTPUT_DIR    = _VIEWER_DIR.parent / "json_files"
_NETLISTS_DIR  = _VIEWER_DIR.parent / "#Netlists"
_ROUTER_SCRIPT       = _SCRIPTS_DIR / "201_routingOptimizer.py"
_VIEWER_SETTINGS_PATH = _VIEWER_DIR / "viewer_settings.json"

_PAIR_RE = re.compile(
    r'reg\.register\(\s*(\w+)\s*,\s*(\w+)\s*,\s*_SUPPORTED'
)


def _load_supported_pairs() -> list[tuple[str, str]]:
    """Parse pipeline.py to discover all SUPPORTED (topology, optimizer) pairs."""
    try:
        text = _PIPELINE_PY.read_text(encoding="utf-8")
        return _PAIR_RE.findall(text)  # list of ("TopoName", "OptName")
    except OSError:
        return []


def _load_netlist_files() -> list[str]:
    """Return sorted list of .sp filenames from the #Netlists folder."""
    if not _NETLISTS_DIR.exists():
        return []
    return sorted(p.name for p in _NETLISTS_DIR.glob("*.sp"))


_PAIR_LABEL_OVERRIDES: dict[tuple[str, str], str] = {
    ("ILP", "ILP"):       "ILP",
    ("PSO", "PSO"):       "PSO",
    ("ILP", "PSOILP"):   "PSO + ILP",
    ("ILP", "BStarILP"): "B* tree + ILP",
}


def _pair_label(topo: str, opt: str) -> str:
    short_topo = topo.replace("Topology", "")
    short_opt  = opt.replace("Optimizer", "")
    override = _PAIR_LABEL_OVERRIDES.get((short_topo, short_opt))
    if override is not None:
        return override
    return f"{short_topo}  +  {short_opt}"


def _load_viewer_settings() -> dict:
    try:
        return json.loads(_VIEWER_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_viewer_settings(settings: dict) -> None:
    _VIEWER_SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2), encoding="utf-8"
    )


class OptimizerFilterDialog(QDialog):
    """Dialog for selecting which optimizer pairs appear in the simulation window."""

    def __init__(
        self,
        all_pairs: list[tuple[str, str]],
        enabled_pairs: set[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Optimizers")
        self.resize(360, 280)

        self._checkboxes: list[tuple[QCheckBox, tuple[str, str]]] = []

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(6)
        scroll_layout.setContentsMargins(4, 4, 4, 4)

        for pair in all_pairs:
            topo, opt = pair
            cb = QCheckBox(_pair_label(topo, opt))
            cb.setChecked(pair in enabled_pairs)
            scroll_layout.addWidget(cb)
            self._checkboxes.append((cb, pair))

        scroll_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Select which optimizers appear in the simulation window:"))
        root.addWidget(scroll, stretch=1)
        root.addWidget(buttons)

    def _on_save(self) -> None:
        _save_viewer_settings({"enabled_pairs": self.selected_pairs()})
        self.accept()

    def selected_pairs(self) -> list[tuple[str, str]]:
        return [pair for cb, pair in self._checkboxes if cb.isChecked()]


class SimulationWindow(QMainWindow):
    """Floating window for configuring and running the placement optimizer."""

    result_ready = pyqtSignal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Simulation")
        self.resize(560, 620)
        self._process: QProcess | None = None
        self._router_process: QProcess | None = None
        self._placement_out: Path | None = None
        self._all_pairs: list[tuple[str, str]] = _load_supported_pairs()
        self._pairs: list[tuple[str, str]] = self._apply_pair_filter(self._all_pairs)
        self._netlist_mode: bool = False
        self._run_seed: int = 42
        self._routing_settings: dict = {
            "routing_mode":    "combined",
            "signal_width_nm": 120,
            "power_width_nm":  200,
            "fallback_isolated": False,
            "output_format":   "json",
        }
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_source_group())
        root.addWidget(self._build_config_group())
        root.addWidget(self._build_mode_group())
        root.addWidget(self._build_warmup_group())
        root.addWidget(self._build_routing_group())

        # Run button + status
        run_row = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._run_btn.setFixedHeight(28)
        self._run_btn.clicked.connect(self._on_run)
        run_row.addWidget(self._run_btn)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedHeight(28)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        run_row.addWidget(self._stop_btn)
        self._beep_chk = QCheckBox("Beep on finish")
        run_row.addWidget(self._beep_chk)
        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        run_row.addWidget(self._status_label, stretch=1)
        root.addLayout(run_row)

        root.addWidget(QLabel("Output log:"))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        mono = QFont("Courier New", 9)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._log.setFont(mono)
        root.addWidget(self._log, stretch=1)

    def _build_source_group(self) -> QGroupBox:
        box = QGroupBox("Block Source")
        vbox = QVBoxLayout(box)
        vbox.setSpacing(4)

        self._src_btn_group = QButtonGroup(self)
        self._rb_src_random  = QRadioButton("Generate randomly")
        self._rb_src_netlist = QRadioButton("From SPICE netlist")
        self._rb_src_random.setChecked(True)

        self._src_btn_group.addButton(self._rb_src_random,  0)
        self._src_btn_group.addButton(self._rb_src_netlist, 1)

        vbox.addWidget(self._rb_src_random)
        vbox.addWidget(self._rb_src_netlist)

        netlist_row = QHBoxLayout()
        netlist_row.addSpacing(20)
        self._netlist_combo = QComboBox()
        self._netlist_combo.setEnabled(False)
        for name in _load_netlist_files():
            self._netlist_combo.addItem(name)
        if self._netlist_combo.count() == 0:
            self._netlist_combo.addItem("(no .sp files found)")
        netlist_row.addWidget(self._netlist_combo, stretch=1)
        vbox.addLayout(netlist_row)

        self._rb_src_netlist.toggled.connect(self._on_source_toggled)

        return box

    def _build_config_group(self) -> QGroupBox:
        box = QGroupBox("Configuration")
        form = QFormLayout(box)
        form.setSpacing(6)

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(1, 99999)
        self._seed_spin.setValue(42)
        form.addRow("Seed:", self._seed_spin)

        self._blocks_spin = QSpinBox()
        self._blocks_spin.setRange(2, 30)
        self._blocks_spin.setValue(15)
        form.addRow("Num Blocks:", self._blocks_spin)

        self._sym_mode_combo = QComboBox()
        self._sym_mode_combo.addItem("Aggressive  (all groups)", userData="aggressive")
        self._sym_mode_combo.addItem("Moderate  (diff pairs + mirrors + tail-CM)", userData="moderate")
        self._sym_mode_combo.addItem("None  (no constraints)", userData="none")
        self._sym_mode_combo.setEnabled(False)  # enabled only in netlist mode
        self._sym_mode_combo.setToolTip(
            "Symmetry aggressiveness — only applies when using a SPICE netlist.\n"
            "  Aggressive: all detected symmetry groups (default)\n"
            "  Moderate:   diff pairs + current mirrors + tail-CM pairs\n"
            "  None:       no symmetry constraints"
        )
        form.addRow("Sym mode:", self._sym_mode_combo)

        return box

    def _build_mode_group(self) -> QGroupBox:
        box = QGroupBox("Design Mode")
        vbox = QVBoxLayout(box)
        vbox.setSpacing(4)

        self._btn_group = QButtonGroup(self)

        self._rb_random = QRadioButton("Random  (one randomly chosen solver pair)")
        self._rb_exhaustive = QRadioButton("Exhaustive  (all supported solver pairs)")
        self._rb_user = QRadioButton("User Selected")

        self._btn_group.addButton(self._rb_random,     0)
        self._btn_group.addButton(self._rb_exhaustive, 1)
        self._btn_group.addButton(self._rb_user,       2)

        self._rb_exhaustive.setChecked(True)

        vbox.addWidget(self._rb_random)
        vbox.addWidget(self._rb_exhaustive)
        vbox.addWidget(self._rb_user)

        # Combo for user-selected pair
        pair_row = QHBoxLayout()
        pair_row.addSpacing(20)
        self._pair_combo = QComboBox()
        self._pair_combo.setEnabled(False)
        for topo, opt in self._pairs:
            self._pair_combo.addItem(_pair_label(topo, opt), userData=(topo, opt))
        if not self._pairs:
            self._pair_combo.addItem("(no pairs found — check pipeline.py)")
        pair_row.addWidget(self._pair_combo, stretch=1)
        vbox.addLayout(pair_row)

        self._rb_user.toggled.connect(self._pair_combo.setEnabled)

        # Manage which pairs are shown
        manage_row = QHBoxLayout()
        manage_row.addSpacing(20)
        self._manage_btn = QPushButton("⚙  Manage Optimizers…")
        self._manage_btn.setFlat(True)
        self._manage_btn.setFixedHeight(22)
        self._manage_btn.clicked.connect(self._open_optimizer_settings)
        manage_row.addWidget(self._manage_btn)
        manage_row.addStretch()
        vbox.addLayout(manage_row)

        return box

    def _build_warmup_group(self) -> QGroupBox:
        box = QGroupBox("Warmup (ILP only)")
        form = QFormLayout(box)
        form.setSpacing(6)

        self._warmup_strategy_combo = QComboBox()
        for label, key in [
            ("CORP (default)",       "corp"),
            ("Contour placer",       "contour"),
            ("Spring / FDGD (paper)", "spring"),
            ("SPSA",                  "spsa"),
        ]:
            self._warmup_strategy_combo.addItem(label, userData=key)
        form.addRow("Strategy:", self._warmup_strategy_combo)

        self._warmup_n_runs_spin = QSpinBox()
        self._warmup_n_runs_spin.setRange(1, 16)
        self._warmup_n_runs_spin.setValue(3)
        self._warmup_n_runs_spin.setToolTip(
            "Number of parallel warmup runs; the median-cost result is passed to ILP"
        )
        form.addRow("Parallel runs:", self._warmup_n_runs_spin)

        self._cb_warmup_viz = QCheckBox("Save warmup placements for viewer")
        self._cb_warmup_viz.setToolTip(
            "When checked, all warmup placements are saved to JSON so you can "
            "inspect them in the viewer after the run."
        )
        form.addRow("", self._cb_warmup_viz)

        return box

    def _build_routing_group(self) -> QGroupBox:
        box = QGroupBox("Router")
        row = QHBoxLayout(box)
        row.setSpacing(8)

        self._cb_routing = QCheckBox("Run router after placement")
        self._btn_routing_opts = QPushButton("Options…")
        self._btn_routing_opts.setFixedWidth(90)
        self._btn_routing_opts.setEnabled(False)
        self._cb_routing.toggled.connect(self._btn_routing_opts.setEnabled)
        self._btn_routing_opts.clicked.connect(self._open_routing_options)

        row.addWidget(self._cb_routing)
        row.addWidget(self._btn_routing_opts)
        row.addStretch()

        return box

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _open_routing_options(self) -> None:
        dlg = RoutingSettingsDialog(self._routing_settings, parent=self)
        if dlg.exec():
            self._routing_settings = dlg.get_settings()

    @staticmethod
    def _apply_pair_filter(all_pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
        settings = _load_viewer_settings()
        enabled = settings.get("enabled_pairs")
        if not enabled:
            return list(all_pairs)
        enabled_set = {tuple(p) for p in enabled}
        filtered = [p for p in all_pairs if p in enabled_set]
        return filtered if filtered else list(all_pairs)

    def _open_optimizer_settings(self) -> None:
        settings = _load_viewer_settings()
        raw_enabled = settings.get("enabled_pairs", self._all_pairs)
        enabled_set: set[tuple[str, str]] = {tuple(p) for p in raw_enabled}
        dlg = OptimizerFilterDialog(self._all_pairs, enabled_set, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            chosen = dlg.selected_pairs()
            self._pairs = chosen if chosen else list(self._all_pairs)
            self._pair_combo.clear()
            for topo, opt in self._pairs:
                self._pair_combo.addItem(_pair_label(topo, opt), userData=(topo, opt))

    def _on_source_toggled(self, netlist_active: bool) -> None:
        self._netlist_combo.setEnabled(netlist_active)
        self._blocks_spin.setEnabled(not netlist_active)
        self._sym_mode_combo.setEnabled(netlist_active)

    def _on_run(self) -> None:
        self._log.clear()
        self._status_label.setText("Running…")
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        seed       = self._seed_spin.value()
        num_blocks = self._blocks_spin.value()

        if self._rb_random.isChecked():
            mode = "random"
        elif self._rb_exhaustive.isChecked():
            mode = "exhaustive"
        else:
            mode = "user"

        args = [
            str(_MAIN_PY),
            "--seed",       str(seed),
            "--run-mode",   mode,
            "--no-routing",          # routing is owned by the Router checkbox below
        ]

        # Warmup args (only override when the user actually changed from defaults)
        warmup_strategy = self._warmup_strategy_combo.currentData() or "corp"
        warmup_n_runs   = self._warmup_n_runs_spin.value()
        args += [
            "--warmup-strategy", warmup_strategy,
            "--warmup-n-runs",   str(warmup_n_runs),
        ]
        if self._cb_warmup_viz.isChecked():
            args.append("--warmup-visualize")

        if self._rb_src_netlist.isChecked():
            netlist_name = self._netlist_combo.currentText()
            sym_mode = self._sym_mode_combo.currentData() or "aggressive"
            args += ["--netlist", str(_NETLISTS_DIR / netlist_name),
                     "--sym-mode", sym_mode]
            self._netlist_mode = True
        else:
            args += ["--num-blocks", str(num_blocks)]
            self._netlist_mode = False
            self._expected_output = _OUTPUT_DIR / f"s{seed}_n{num_blocks}_py101_v01.json"

        self._run_seed = seed

        if mode == "user":
            data = self._pair_combo.currentData()
            if data is None:
                self._status_label.setText("Error: no pair selected")
                self._run_btn.setEnabled(True)
                self._stop_btn.setEnabled(False)
                return
            topo, opt = data
            args += ["--topology", topo, "--optimizer", opt]

        self._process = QProcess(self)
        self._process.setProgram(sys.executable)
        self._process.setArguments(args)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.start()

    def _on_stop(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        if self._router_process and self._router_process.state() != QProcess.ProcessState.NotRunning:
            self._router_process.kill()
        self._status_label.setText("Stopped")
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

    def _on_stdout(self) -> None:
        if self._process:
            text = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
            self._log.moveCursor(QTextCursor.MoveOperation.End)
            self._log.insertPlainText(text)

    def _on_stderr(self) -> None:
        if self._process:
            text = bytes(self._process.readAllStandardError()).decode(errors="replace")
            self._log.moveCursor(QTextCursor.MoveOperation.End)
            self._log.insertPlainText(text)

    def _on_finished(self, exit_code: int, exit_status) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if exit_code != 0:
            self._status_label.setText(f"Failed (exit {exit_code})")
            return

        if self._netlist_mode:
            matches = sorted(
                _OUTPUT_DIR.glob(f"s{self._run_seed}_n*_py101_v01.json"),
                key=lambda p: p.stat().st_mtime,
            )
            out = matches[-1] if matches else None
        else:
            out = self._expected_output

        if out is None or not out.exists():
            self._status_label.setText("Done — output file not found")
            self._log.append(f"\n[viewer] Expected output not found: {out}")
            return

        if self._cb_routing.isChecked():
            self._placement_out = out
            self._log.append(f"\n[viewer] Placement done: {out.name}  — starting router…")
            self._status_label.setText("Routing…")
            self._run_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._start_router(out)
            return

        self._status_label.setText("Done")
        self._log.append(f"\n[viewer] Loading: {out.name}")
        self._maybe_beep()
        self.result_ready.emit(out)

    def _start_router(self, py101_path: Path) -> None:
        s = self._routing_settings
        args = [
            str(_ROUTER_SCRIPT),
            str(py101_path),
            "--routing-mode",    s["routing_mode"],
            "--signal-width-nm", str(s["signal_width_nm"]),
            "--power-width-nm",  str(s["power_width_nm"]),
            "--output-format",   s["output_format"],
        ]
        if s["fallback_isolated"]:
            args.append("--fallback-isolated")

        self._log.append("\n--- Router ---\n")
        self._router_process = QProcess(self)
        self._router_process.setProgram(sys.executable)
        self._router_process.setArguments(args)
        self._router_process.readyReadStandardOutput.connect(self._on_router_stdout)
        self._router_process.readyReadStandardError.connect(self._on_router_stderr)
        self._router_process.finished.connect(self._on_router_finished)
        self._router_process.start()

    def _on_router_stdout(self) -> None:
        if self._router_process:
            text = bytes(self._router_process.readAllStandardOutput()).decode(errors="replace")
            self._log.moveCursor(QTextCursor.MoveOperation.End)
            self._log.insertPlainText(text)

    def _on_router_stderr(self) -> None:
        if self._router_process:
            text = bytes(self._router_process.readAllStandardError()).decode(errors="replace")
            self._log.moveCursor(QTextCursor.MoveOperation.End)
            self._log.insertPlainText(text)

    def _on_router_finished(self, exit_code: int, exit_status) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if self._placement_out is None:
            self._status_label.setText("Done — placement path lost")
            return

        out = find_routing_output(self._placement_out) if exit_code == 0 else None
        if out is not None:
            self._status_label.setText("Done (routed)")
            self._log.append(f"\n[viewer] Loading: {out.name}")
            self._maybe_beep()
            self.result_ready.emit(out)
        else:
            self._status_label.setText("Done (routing failed — loading placement)")
            self._log.append(f"\n[viewer] Router exit {exit_code}. Loading placement: {self._placement_out.name}")
            self._maybe_beep()
            self.result_ready.emit(self._placement_out)

    # ------------------------------------------------------------------

    def _maybe_beep(self) -> None:
        if self._beep_chk.isChecked() and _winsound is not None:
            _winsound.MessageBeep()

    def closeEvent(self, event) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        if self._router_process and self._router_process.state() != QProcess.ProcessState.NotRunning:
            self._router_process.kill()
        super().closeEvent(event)
