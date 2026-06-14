"""Routing launcher window and settings dialog for the ALDA placement viewer."""
from __future__ import annotations

import json as _json
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

_VIEWER_DIR    = Path(__file__).parent
_SCRIPTS_DIR   = _VIEWER_DIR.parent / "scripts"
_ROUTER_SCRIPT = _SCRIPTS_DIR / "201_routingOptimizer.py"
_OUTPUT_DIR    = _VIEWER_DIR.parent / "json_files"

_DEFAULT_SETTINGS: dict = {
    "routing_mode":    "combined",
    "signal_width_nm": 120,
    "power_width_nm":  200,
    "fallback_isolated": False,
    "output_format":   "json",
}


def find_routing_output(placement_path: Path) -> Path | None:
    """Find the routed output JSON by content rather than by filename pattern.

    Scans JSON files in the same directory as placement_path (excluding it),
    sorted newest-first, and returns the first one whose nets contain
    route_segments — i.e. proof that the router actually ran on it.
    Only considers files written after placement_path was last modified.
    """
    try:
        placement_mtime = placement_path.stat().st_mtime
    except OSError:
        return None

    candidates = sorted(
        placement_path.parent.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if candidate == placement_path:
            continue
        try:
            if candidate.stat().st_mtime < placement_mtime:
                break  # sorted desc — everything from here is older
            raw = _json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                raw = raw[0]
            if any(n.get("route_segments") for n in raw.get("netlist", {}).get("nets", [])):
                return candidate
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Reusable settings dialog (used by RoutingWindow inline and by SimulationWindow)
# ---------------------------------------------------------------------------

class RoutingSettingsDialog(QDialog):
    """Modal dialog for editing routing parameters."""

    def __init__(self, settings: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Router Options")
        self.setMinimumWidth(320)
        self._settings = dict(_DEFAULT_SETTINGS)
        if settings:
            self._settings.update(settings)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["combined", "isolated"])
        self._mode_combo.setCurrentText(self._settings["routing_mode"])
        form.addRow("Routing mode:", self._mode_combo)

        self._sig_spin = QSpinBox()
        self._sig_spin.setRange(10, 5000)
        self._sig_spin.setSuffix(" nm")
        self._sig_spin.setValue(self._settings["signal_width_nm"])
        form.addRow("Signal width:", self._sig_spin)

        self._pwr_spin = QSpinBox()
        self._pwr_spin.setRange(10, 5000)
        self._pwr_spin.setSuffix(" nm")
        self._pwr_spin.setValue(self._settings["power_width_nm"])
        form.addRow("Power width:", self._pwr_spin)

        self._fallback_cb = QCheckBox("Fallback to isolated on failure")
        self._fallback_cb.setChecked(self._settings["fallback_isolated"])
        form.addRow("", self._fallback_cb)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["json", "gds", "both"])
        self._fmt_combo.setCurrentText(self._settings["output_format"])
        form.addRow("Output format:", self._fmt_combo)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_settings(self) -> dict:
        return {
            "routing_mode":    self._mode_combo.currentText(),
            "signal_width_nm": self._sig_spin.value(),
            "power_width_nm":  self._pwr_spin.value(),
            "fallback_isolated": self._fallback_cb.isChecked(),
            "output_format":   self._fmt_combo.currentText(),
        }


# ---------------------------------------------------------------------------
# Standalone routing launcher window
# ---------------------------------------------------------------------------

class RoutingWindow(QMainWindow):
    """Floating window to run 201_routingOptimizer.py on a py101 JSON file."""

    result_ready = pyqtSignal(Path)

    def __init__(self, prefill_path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Run Router")
        self.resize(620, 680)
        self._process: QProcess | None = None
        self._input_path: Path | None = None
        self._prefill_path = prefill_path
        self._build_ui()
        if prefill_path:
            self._file_edit.setText(str(prefill_path))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(self._build_file_group())
        root.addWidget(self._build_settings_group())

        # Run / Stop / status row
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

    def _build_file_group(self) -> QGroupBox:
        box = QGroupBox("Input File  (py101 JSON)")
        row = QHBoxLayout(box)
        row.setSpacing(6)

        self._file_edit = QLineEdit()
        self._file_edit.setPlaceholderText("Path to *_py101_*.json …")
        row.addWidget(self._file_edit, stretch=1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._on_browse)
        row.addWidget(browse_btn)

        return box

    def _build_settings_group(self) -> QGroupBox:
        box = QGroupBox("Router Settings")
        form = QFormLayout(box)
        form.setSpacing(6)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["combined", "isolated"])
        form.addRow("Routing mode:", self._mode_combo)

        self._sig_spin = QSpinBox()
        self._sig_spin.setRange(10, 5000)
        self._sig_spin.setSuffix(" nm")
        self._sig_spin.setValue(120)
        form.addRow("Signal width:", self._sig_spin)

        self._pwr_spin = QSpinBox()
        self._pwr_spin.setRange(10, 5000)
        self._pwr_spin.setSuffix(" nm")
        self._pwr_spin.setValue(200)
        form.addRow("Power width:", self._pwr_spin)

        self._fallback_cb = QCheckBox("Fallback to isolated on failure")
        form.addRow("", self._fallback_cb)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["json", "gds", "both"])
        form.addRow("Output format:", self._fmt_combo)

        return box

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        start = str(
            self._prefill_path.parent if self._prefill_path else _OUTPUT_DIR
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Open py101 JSON", start, "JSON files (*.json)"
        )
        if path:
            self._file_edit.setText(path)

    def _on_run(self) -> None:
        raw = self._file_edit.text().strip()
        if not raw:
            self._status_label.setText("Error: no input file")
            return
        p = Path(raw)
        if not p.exists():
            self._status_label.setText("Error: file not found")
            return

        self._input_path = p
        self._log.clear()
        self._status_label.setText("Running…")
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        args = [
            str(_ROUTER_SCRIPT),
            str(p),
            "--routing-mode",    self._mode_combo.currentText(),
            "--signal-width-nm", str(self._sig_spin.value()),
            "--power-width-nm",  str(self._pwr_spin.value()),
            "--output-format",   self._fmt_combo.currentText(),
        ]
        if self._fallback_cb.isChecked():
            args.append("--fallback-isolated")

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

        if self._input_path is None:
            self._status_label.setText("Done — input path lost")
            return

        out = find_routing_output(self._input_path)
        if out is not None:
            self._status_label.setText("Done")
            self._log.append(f"\n[viewer] Loading: {out.name}")
            self.result_ready.emit(out)
        else:
            self._status_label.setText("Done — routed output not found")
            self._log.append(f"\n[viewer] No routed JSON found in {self._input_path.parent}")

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        super().closeEvent(event)
