"""Floating Simulate panel — launch the placement optimizer from the viewer."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QRadioButton, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget,
)

# Paths
_VIEWER_DIR   = Path(__file__).parent
_SCRIPTS_DIR  = _VIEWER_DIR.parent / "scripts"
_MAIN_PY      = _SCRIPTS_DIR / "main.py"
_PIPELINE_PY  = _SCRIPTS_DIR / "lib" / "pipeline.py"
_OUTPUT_DIR   = _VIEWER_DIR.parent / "json_files"
_NETLISTS_DIR = _VIEWER_DIR.parent / "#Netlists"

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


class SimulationWindow(QMainWindow):
    """Floating window for configuring and running the placement optimizer."""

    result_ready = pyqtSignal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Simulation")
        self.resize(560, 620)
        self._process: QProcess | None = None
        self._pairs: list[tuple[str, str]] = _load_supported_pairs()
        self._netlist_mode: bool = False
        self._run_seed: int = 42
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

        return box

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_source_toggled(self, netlist_active: bool) -> None:
        self._netlist_combo.setEnabled(netlist_active)
        self._blocks_spin.setEnabled(not netlist_active)

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
            "--seed",     str(seed),
            "--run-mode", mode,
        ]

        if self._rb_src_netlist.isChecked():
            netlist_name = self._netlist_combo.currentText()
            args += ["--netlist", str(_NETLISTS_DIR / netlist_name)]
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

        self._status_label.setText("Done")
        self._log.append(f"\n[viewer] Loading: {out.name}")
        self.result_ready.emit(out)

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        super().closeEvent(event)
