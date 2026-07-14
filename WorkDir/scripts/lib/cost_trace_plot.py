"""
Cost-over-time plotting — pure logic, no Qt. Shared by the viewer's Analysis
window (WorkDir/viewer/analysis_window.py) so the on-screen preview and any
exported PNG/CSV always come from the exact same code path.

Loads a session's manifest.json + per-run JSONL trace files (written by
101_placementOptimizer.py when SAVE_COST_TRACE=True) and renormalizes every
sample with the same shared-cost formula 101_placementOptimizer.py already
uses to rank exhaustive-mode runs by their *final* cost
(_renormalize_costs/_shared_cost) — applied here to every sample instead of
just the last one, so run curves plotted together are directly comparable
even though each run's own CostEvaluator normalizes against its own
init_area/init_wl.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from math import log10
from pathlib import Path
from typing import TYPE_CHECKING

from run_labels import display_label

if TYPE_CHECKING:
    from matplotlib.figure import Figure


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RunTrace:
    run_id: str
    label:  str
    samples: list[dict] = field(default_factory=list)  # each sample also carries "renorm_cost"


@dataclass
class Session:
    session_id:    str
    netlist_id:    str
    symmetry_mode: str
    runs:          list[RunTrace] = field(default_factory=list)


# =============================================================================
# LOADING + RENORMALIZATION
# =============================================================================

def _make_shared_cost_fn(entries: list[dict], weights: dict):
    """Same formula as 101_placementOptimizer.py::_renormalize_costs, built
    once from every run's *final* metrics so it can be applied per-sample."""
    ref_area = min((e["area_um2"] for e in entries if e.get("area_um2", 0.0) > 0.0), default=1.0)
    ref_hpwl = min((e["hpwl_um"]  for e in entries if e.get("hpwl_um", 0.0)  > 0.0), default=1.0)

    w_a       = weights.get("area_weight", 1.0)
    w_wl      = weights.get("wirelength_weight", 1.0)
    w_ar      = weights.get("aspect_ratio_weight", 1.0)
    target_ar = weights.get("target_aspect_ratio", 1.0)

    def shared_cost(area_um2: float, hpwl_um: float, aspect_ratio: float) -> float:
        area_term = w_a  * (area_um2 / ref_area) if ref_area > 0.0 else 0.0
        hpwl_term = w_wl * (hpwl_um  / ref_hpwl) if ref_hpwl > 0.0 else 0.0
        ar_term   = w_ar * (aspect_ratio - target_ar) ** 2
        return area_term + hpwl_term + ar_term

    return shared_cost


def load_session(session_dir: str | Path) -> Session:
    """Read manifest.json + every referenced run's JSONL trace file."""
    session_dir = Path(session_dir)
    with open(session_dir / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    entries = manifest.get("runs", [])
    shared_cost = _make_shared_cost_fn(entries, manifest.get("weights", {}))

    final_shared = [
        shared_cost(e["area_um2"], e["hpwl_um"], e["aspect_ratio"])
        for e in entries if e.get("area_um2") is not None
    ]
    min_shared = min(final_shared) if final_shared else 1.0
    denom      = min_shared if min_shared > 0.0 else 1.0

    runs: list[RunTrace] = []
    for e in entries:
        trace_path = Path(e["trace_file"]) if e.get("trace_file") else None
        if trace_path is None or not trace_path.exists():
            continue

        samples: list[dict] = []
        with open(trace_path, encoding="utf-8") as tf:
            for line in tf:
                line = line.strip()
                if not line:
                    continue
                s = json.loads(line)
                s["renorm_cost"] = round(
                    shared_cost(s["area_um2"], s["hpwl_um"], s["aspect_ratio"]) / denom, 6
                )
                samples.append(s)

        runs.append(RunTrace(
            run_id  = e["run_id"],
            label   = display_label(e["run_id"], e.get("warmup_strategy") or None),
            samples = samples,
        ))

    return Session(
        session_id    = manifest.get("session_id", ""),
        netlist_id    = manifest.get("netlist_id", ""),
        symmetry_mode = manifest.get("symmetry_mode", ""),
        runs          = runs,
    )


def latest_session_dir(traces_root: str | Path) -> Path | None:
    """Most recently modified session directory under WorkDir/traces/, or None."""
    traces_root = Path(traces_root)
    if not traces_root.is_dir():
        return None
    sessions = [d for d in traces_root.iterdir() if d.is_dir() and (d / "manifest.json").exists()]
    if not sessions:
        return None
    return max(sessions, key=lambda d: d.stat().st_mtime)


def default_title(session: Session) -> str:
    mode = session.symmetry_mode or "none"
    return f"{session.netlist_id} — {mode}"


# =============================================================================
# PLOTTING
# =============================================================================

def build_figure(
    session:     Session,
    run_ids:     list[str] | None = None,
    title:       str  = "",
    show_legend: bool  = True,
    linewidth:   float = 1.5,
    log_scale:   bool  = False,
    fig:         "Figure | None" = None,
) -> "Figure":
    """
    Build a normalized-cost-vs-time Figure for the selected runs (all, if
    run_ids is None). If `fig` is given, it is cleared and reused in place
    (preserving its current on-screen size) instead of allocating a new
    default-sized Figure — callers redrawing into an existing canvas should
    always pass their canvas's figure here.
    """
    if fig is None:
        from matplotlib.figure import Figure
        fig = Figure(figsize=(8, 5))
    else:
        fig.clear()
    ax = fig.add_subplot(111)

    selected = session.runs if run_ids is None else [r for r in session.runs if r.run_id in run_ids]
    for run in selected:
        if log_scale:
            # log10 is undefined at/below 0 — drop those samples rather than
            # feeding NaN/-inf to matplotlib.
            xs, ys = [], []
            for s in run.samples:
                if s["renorm_cost"] > 0.0:
                    xs.append(s["t_rel"])
                    ys.append(log10(s["renorm_cost"]))
        else:
            xs = [s["t_rel"] for s in run.samples]
            ys = [s["renorm_cost"] for s in run.samples]
        ax.plot(xs, ys, label=run.label, linewidth=linewidth)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("log10(normalized cost)" if log_scale else "Normalized cost (best = 1.0)")
    ax.set_title(title or default_title(session))
    if show_legend:
        ax.legend()
    fig.tight_layout()
    return fig


# =============================================================================
# EXPORT
# =============================================================================

def export_png(fig: "Figure", path: str | Path) -> None:
    fig.savefig(str(path), dpi=150)


def export_csv(session: Session, path: str | Path, run_ids: list[str] | None = None) -> None:
    """Flatten the selected runs' raw samples (including renorm_cost) to one CSV."""
    selected = session.runs if run_ids is None else [r for r in session.runs if r.run_id in run_ids]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run_id", "label", "iteration", "t_rel",
            "area_um2", "hpwl_um", "aspect_ratio", "cost", "renorm_cost",
        ])
        for run in selected:
            for s in run.samples:
                writer.writerow([
                    run.run_id, run.label, s["iteration"], s["t_rel"],
                    s["area_um2"], s["hpwl_um"], s["aspect_ratio"], s["cost"], s["renorm_cost"],
                ])
