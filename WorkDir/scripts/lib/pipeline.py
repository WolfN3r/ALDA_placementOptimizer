"""
Orchestration layer: CompatibilityRegistry, OptimizationPipeline, observer classes,
and PipelineResult.

OptimizationPipeline is the only component that simultaneously knows both the
topology class and the optimizer class. All other components see only ABCs.
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Type

from topology_base import TopologyBase, SAMixin, GAMixin
from cost_evaluator import CostEvaluator, CostWeights
from sa_optimizer import (
    SimulatedAnnealingOptimizer, SAConfig, SAResult, NullObserver,
    calibrate_initial_temperature,
)


# =============================================================================
# CONSTANTS
# =============================================================================
_SUPPORTED     = "SUPPORTED"
_EXPERIMENTAL  = "EXPERIMENTAL"
_UNSUPPORTED   = "UNSUPPORTED"


# =============================================================================
# ERRORS
# =============================================================================

class IncompatibleCombinationError(Exception):
    """Raised when an UNSUPPORTED (topology, optimizer) pair is used."""


# =============================================================================
# COMPATIBILITY REGISTRY
# =============================================================================

class CompatibilityRegistry:
    """
    Explicit compatibility table. Not inferred from class hierarchy.
    Some pairs are architecturally possible but not yet validated.
    """

    def __init__(self) -> None:
        # Keys are (topology_cls.__name__, optimizer_cls.__name__)
        self._table: dict[tuple[str, str], str] = {}

    def register(
        self, topology_cls: Type, optimizer_cls: Type, status: str
    ) -> None:
        self._table[(topology_cls.__name__, optimizer_cls.__name__)] = status

    def status(self, topology_cls: Type, optimizer_cls: Type) -> str:
        return self._table.get(
            (topology_cls.__name__, optimizer_cls.__name__), _UNSUPPORTED
        )

    def supported_pairs(self) -> list[tuple[Type, Type]]:
        """Return all (topology_cls, optimizer_cls) pairs with status SUPPORTED."""
        from bstar_topology    import BStarTopology
        from seqpair_topology  import SequencePairTopology
        from ilp_topology      import ILPTopology
        from ilp_optimizer     import ILPOptimizer
        cls_map = {
            "BStarTopology":               BStarTopology,
            "SequencePairTopology":        SequencePairTopology,
            "SimulatedAnnealingOptimizer": SimulatedAnnealingOptimizer,
            "ILPTopology":                 ILPTopology,
            "ILPOptimizer":                ILPOptimizer,
        }
        pairs = []
        for (t_name, o_name), st in self._table.items():
            if st == _SUPPORTED and t_name in cls_map and o_name in cls_map:
                pairs.append((cls_map[t_name], cls_map[o_name]))
        return pairs


def build_default_registry() -> CompatibilityRegistry:
    """Build the default compatibility table as specified in the architecture."""
    from bstar_topology   import BStarTopology
    from seqpair_topology import SequencePairTopology
    from ilp_topology     import ILPTopology
    from ilp_optimizer    import ILPOptimizer

    reg = CompatibilityRegistry()
    reg.register(BStarTopology,          SimulatedAnnealingOptimizer, _SUPPORTED)
    reg.register(SequencePairTopology,   SimulatedAnnealingOptimizer, _SUPPORTED)
    reg.register(ILPTopology,            ILPOptimizer,                _SUPPORTED)
    # GeneticOptimizer not yet implemented — stubs only
    # reg.register(SequencePairTopology, GeneticOptimizer, _SUPPORTED)
    # reg.register(BStarTopology,        GeneticOptimizer, _EXPERIMENTAL)
    return reg


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class PipelineResult:
    run_id:           str
    topology:         str
    optimizer:        str
    status:           str                          # "success" | "failed" | "timeout" | "incompatible"
    final_cost:       float           = 0.0
    area_um2:         float           = 0.0
    hpwl_um:          float           = 0.0
    aspect_ratio:     float           = 0.0
    n_iterations:     int             = 0
    positions:        dict            = field(default_factory=dict)
    placed_blocks:    dict            = field(default_factory=dict)
    t_seed_ms:        float           = 0.0
    t_first_decode_ms: float          = 0.0
    t_optimize_ms:    float           = 0.0
    t_total_ms:       float           = 0.0
    error_message:    str             = ""

    def to_dict(self) -> dict:
        return {
            "run_id":    self.run_id,
            "topology":  self.topology,
            "optimizer": self.optimizer,
            "status":    self.status,
            "metrics": {
                "final_cost":       self.final_cost,
                "area_um2":         self.area_um2,
                "hpwl_um":          self.hpwl_um,
                "aspect_ratio":     self.aspect_ratio,
                "n_iterations":     self.n_iterations,
                "t_seed_ms":        self.t_seed_ms,
                "t_first_decode_ms": self.t_first_decode_ms,
                "t_optimize_ms":    self.t_optimize_ms,
                "t_total_ms":       self.t_total_ms,
            },
            "positions": {
                bid: list(xy) for bid, xy in self.positions.items()
            },
            "error_message": self.error_message,
        }


# =============================================================================
# PIPELINE
# =============================================================================

class OptimizationPipeline:
    """
    Constructs and runs one (topology, optimizer) pair.
    The only place in the system that simultaneously imports both.
    """

    def __init__(
        self,
        topology_cls:  Type,
        optimizer_cls: Type,
        sa_config:     SAConfig | None      = None,
        weights:       CostWeights | None   = None,
        registry:      CompatibilityRegistry | None = None,
        observer:      Any                  = None,
        auto_calibrate: bool                = True,
        sym_groups:    list | None          = None,
    ) -> None:
        self._topology_cls  = topology_cls
        self._optimizer_cls = optimizer_cls
        self._sa_config     = sa_config or SAConfig()
        self._weights       = weights   or CostWeights()
        self._registry      = registry  or build_default_registry()
        self._observer      = observer  or NullObserver()
        self._auto_calibrate = auto_calibrate
        self._sym_groups     = sym_groups or []

        # Check compatibility at construction — not at run time
        st = self._registry.status(topology_cls, optimizer_cls)
        if st == _UNSUPPORTED:
            raise IncompatibleCombinationError(
                f"{topology_cls.__name__} + {optimizer_cls.__name__} is UNSUPPORTED"
            )
        if st == _EXPERIMENTAL:
            warnings.warn(
                f"{topology_cls.__name__} + {optimizer_cls.__name__} is EXPERIMENTAL",
                stacklevel=2,
            )

    def run(
        self,
        blocks: dict,
        nets:   list,
        seed_mode: str = "random",
        run_id:    str = "",
    ) -> PipelineResult:
        t_wall = time.perf_counter()

        topo_name = self._topology_cls.__name__
        opt_name  = self._optimizer_cls.__name__
        result = PipelineResult(
            run_id    = run_id or f"{topo_name}+{opt_name}",
            topology  = topo_name,
            optimizer = opt_name,
            status    = "failed",
        )

        try:
            # Step 3: construct + seed topology
            topology = self._topology_cls(blocks, nets, sym_groups=self._sym_groups)
            topology.seed(blocks, mode=seed_mode)
            result.t_seed_ms = (time.perf_counter() - t_wall) * 1000

            # Step 4: first decode to capture reference values
            t_decode_start = time.perf_counter()
            ref_positions  = topology.decode()
            result.t_first_decode_ms = (time.perf_counter() - t_decode_start) * 1000

            init_area = _bbox_area(ref_positions, blocks)
            init_wl   = _hpwl(ref_positions, blocks, nets)

            # Step 5: construct evaluator
            evaluator = CostEvaluator(blocks, nets, max(init_area, 1e-9), max(init_wl, 0.0), self._weights)

            # Step 6: auto-calibrate SA initial temperature if needed
            cfg = SAConfig(**self._sa_config.__dict__)
            if self._auto_calibrate and cfg.initial_temp <= 0.0 and isinstance(topology, SAMixin):
                cfg.initial_temp = calibrate_initial_temperature(topology, evaluator)

            n_blocks = len([b for b in blocks.values() if "error" not in b])
            if cfg.epoch_size == 0:
                cfg.epoch_size = max(n_blocks * 8, 50)
            if cfg.max_iterations == 0:
                cfg.max_iterations = cfg.epoch_size * 200

            # Step 7: run optimizer
            optimizer = self._optimizer_cls(topology, evaluator, cfg, observer=self._observer)
            t_opt_start = time.perf_counter()
            opt_result  = optimizer.run()
            result.t_optimize_ms = (time.perf_counter() - t_opt_start) * 1000

            # Step 8: restore best state and decode final positions
            topology.restore_state(opt_result.best_state)
            final_positions = topology.decode()

            variant_map = topology.get_variant_map()

            result.status       = "success"
            result.final_cost   = opt_result.best_cost
            result.n_iterations = opt_result.n_iterations
            result.positions    = final_positions
            result.placed_blocks = _compute_placed_blocks(final_positions, blocks, variant_map)
            result.area_um2     = _bbox_area(final_positions, blocks)
            result.hpwl_um      = _hpwl(final_positions, blocks, nets)
            result.aspect_ratio = _aspect_ratio(final_positions, blocks)

        except IncompatibleCombinationError as exc:
            result.status        = "incompatible"
            result.error_message = str(exc)
        except Exception as exc:
            result.status        = "failed"
            result.error_message = str(exc)

        result.t_total_ms = (time.perf_counter() - t_wall) * 1000
        return result


# =============================================================================
# GEOMETRY HELPERS (duplicated from CostEvaluator for pipeline-level use)
# =============================================================================

def _active_variant(block: dict) -> dict:
    for v in block.get("variants", []):
        if v.get("is_used"):
            return v
    variants = block.get("variants", [])
    return variants[0] if variants else {}


def _bbox_area(positions: dict, blocks: dict) -> float:
    if not positions:
        return 0.0
    xs, ys, xe, ye = [], [], [], []
    for bid, (bx, by) in positions.items():
        v = _active_variant(blocks.get(bid, {}))
        w = v.get("main_bbox", {}).get("x_max", 0.0)
        h = v.get("main_bbox", {}).get("y_max", 0.0)
        xs.append(bx);      ys.append(by)
        xe.append(bx + w);  ye.append(by + h)
    return max(0.0, max(xe) - min(xs)) * max(0.0, max(ye) - min(ys))


def _hpwl(positions: dict, blocks: dict, nets: list) -> float:
    pin_pos: dict[str, tuple[float, float]] = {}
    for bid, (bx, by) in positions.items():
        v = _active_variant(blocks.get(bid, {}))
        for pname, pcoord in v.get("pin_positions", {}).items():
            pin_pos[f"B{bid}_{pname}"] = (bx + pcoord["x"], by + pcoord["y"])
    total = 0.0
    for net in nets:
        pins = net.get("pins", [])
        xs = [pin_pos[p][0] for p in pins if p in pin_pos]
        ys = [pin_pos[p][1] for p in pins if p in pin_pos]
        if len(xs) >= 2:
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def _aspect_ratio(positions: dict, blocks: dict) -> float:
    if not positions:
        return 1.0
    xs, ys, xe, ye = [], [], [], []
    for bid, (bx, by) in positions.items():
        v = _active_variant(blocks.get(bid, {}))
        w = v.get("main_bbox", {}).get("x_max", 0.0)
        h = v.get("main_bbox", {}).get("y_max", 0.0)
        xs.append(bx);      ys.append(by)
        xe.append(bx + w);  ye.append(by + h)
    width  = max(xe) - min(xs)
    height = max(ye) - min(ys)
    return width / height if height > 0.0 else float("inf")


def _compute_placed_blocks(
    positions:   dict[str, tuple[float, float]],
    blocks:      dict,
    variant_map: dict[str, int],
) -> dict:
    """
    Build absolute placed geometry for every block in positions.
    Uses variant_map to select the correct variant (as chosen by the optimizer).
    Returns {block_id: {"x", "y", "main_bbox": {x_min,y_min,x_max,y_max}, "pins": {name: {x,y}}}}.
    """
    placed = {}
    for bid, (bx, by) in positions.items():
        block    = blocks.get(bid, {})
        variants = block.get("variants", [])
        vidx     = variant_map.get(bid, 0)
        v        = variants[vidx] if vidx < len(variants) else (variants[0] if variants else {})
        bb       = v.get("main_bbox", {})
        w        = bb.get("x_max", 0.0)
        h        = bb.get("y_max", 0.0)
        abs_pins = {
            pname: {"x": round(bx + pc["x"], 6), "y": round(by + pc["y"], 6)}
            for pname, pc in v.get("pin_positions", {}).items()
        }
        placed[bid] = {
            "main_bbox": {
                "x_min": round(bx,     6),
                "y_min": round(by,     6),
                "x_max": round(bx + w, 6),
                "y_max": round(by + h, 6),
            },
            "pins": abs_pins,
        }
    return placed
