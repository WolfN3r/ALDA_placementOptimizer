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
from cost_evaluator import CostEvaluator, CostWeights, _VDD_NET_IDS, _VSS_NET_IDS
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
        from pso_topology      import PSOTopology
        from pso_optimizer     import PSOOptimizer
        from pso_ilp_optimizer   import PSOILPOptimizer
        from bstar_ilp_optimizer import BStarILPOptimizer
        cls_map = {
            "BStarTopology":               BStarTopology,
            "SequencePairTopology":        SequencePairTopology,
            "SimulatedAnnealingOptimizer": SimulatedAnnealingOptimizer,
            "ILPTopology":                 ILPTopology,
            "ILPOptimizer":                ILPOptimizer,
            "PSOTopology":                 PSOTopology,
            "PSOOptimizer":                PSOOptimizer,
            "PSOILPOptimizer":             PSOILPOptimizer,
            "BStarILPOptimizer":           BStarILPOptimizer,
        }
        pairs = []
        for (t_name, o_name), st in self._table.items():
            if st == _SUPPORTED and t_name in cls_map and o_name in cls_map:
                pairs.append((cls_map[t_name], cls_map[o_name]))
        return pairs


def build_default_registry() -> CompatibilityRegistry:
    """Build the default compatibility table as specified in the architecture."""
    from bstar_topology    import BStarTopology
    from seqpair_topology  import SequencePairTopology
    from ilp_topology      import ILPTopology
    from ilp_optimizer     import ILPOptimizer
    from pso_topology      import PSOTopology
    from pso_optimizer     import PSOOptimizer
    from pso_ilp_optimizer   import PSOILPOptimizer
    from bstar_ilp_optimizer import BStarILPOptimizer

    reg = CompatibilityRegistry()
    reg.register(BStarTopology,          SimulatedAnnealingOptimizer, _SUPPORTED)
    reg.register(SequencePairTopology,   SimulatedAnnealingOptimizer, _SUPPORTED)
    reg.register(ILPTopology,            ILPOptimizer,                _SUPPORTED)
    reg.register(PSOTopology,            PSOOptimizer,                _SUPPORTED)
    reg.register(ILPTopology,            PSOILPOptimizer,             _SUPPORTED)
    reg.register(ILPTopology,            BStarILPOptimizer,           _SUPPORTED)
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
    variant_map:      dict            = field(default_factory=dict)
    power_rails:      dict            = field(default_factory=dict)
    t_seed_ms:        float           = 0.0
    t_first_decode_ms: float          = 0.0
    t_optimize_ms:    float           = 0.0
    t_total_ms:       float           = 0.0
    error_message:    str             = ""
    warmup_runs:      list            = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
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
            "power_rails":   self.power_rails,
            "error_message": self.error_message,
        }
        if self.warmup_runs:
            d["warmup_runs"] = self.warmup_runs
        return d


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
        topology_cls:     Type,
        optimizer_cls:    Type,
        sa_config:        SAConfig | None             = None,
        weights:          CostWeights | None          = None,
        registry:         CompatibilityRegistry | None = None,
        observer:         Any                         = None,
        auto_calibrate:   bool                        = True,
        sym_groups:       list | None                 = None,
        optimizer_kwargs: dict | None                 = None,
        use_power_rails:  bool                        = False,
    ) -> None:
        self._topology_cls     = topology_cls
        self._optimizer_cls    = optimizer_cls
        self._sa_config        = sa_config or SAConfig()
        self._weights          = weights   or CostWeights()
        self._registry         = registry  or build_default_registry()
        self._observer         = observer  or NullObserver()
        self._auto_calibrate   = auto_calibrate
        self._sym_groups       = sym_groups or []
        self._optimizer_kwargs = optimizer_kwargs or {}
        self._use_power_rails  = use_power_rails

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
            init_wl   = _hpwl(ref_positions, blocks, nets, use_power_rails=self._use_power_rails)

            # Step 5: construct evaluator
            evaluator = CostEvaluator(
                blocks, nets,
                max(init_area, 1e-9), max(init_wl, 0.0),
                self._weights,
                use_power_rails=self._use_power_rails,
            )

            # Step 5b: multi-warmup start (optional — ILP only, keyed by warmup_config)
            warmup_positions:    dict | None = None
            warmup_variant_map:  dict        = {}
            warmup_runs_data:    list        = []
            warmup_cfg = self._optimizer_kwargs.get("warmup_config")
            if warmup_cfg is not None:
                from warmup_manager import WarmupManager
                mgr = WarmupManager(warmup_cfg)
                warmup_positions, warmup_results, warmup_variant_map = mgr.run(blocks, nets, init_area, init_wl)
                if warmup_cfg.visualize:
                    warmup_runs_data = [
                        {
                            "run_index":   r.run_index,
                            "strategy":    r.strategy,
                            "seed":        r.seed,
                            "cost":        round(r.cost, 6),
                            "is_selected": r.is_selected,
                            "positions": {
                                bid: [round(v[0], 6), round(v[1], 6), round(v[2], 6), round(v[3], 6)]
                                for bid, v in r.positions.items()
                            },
                        }
                        for r in warmup_results
                    ]

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
            # In exhaustive-ILP mode: run one ILP pass per warmup result (serial).
            # In default mode: run one ILP pass with the selected warmup positions.
            base_kwargs = dict(self._optimizer_kwargs)
            base_kwargs.pop("warmup_config", None)  # consumed above; not a valid optimizer kwarg

            if (
                warmup_cfg is not None
                and warmup_cfg.exhaustive_ilp
                and warmup_results
            ):
                # --- Exhaustive-ILP: N serial ILP runs, one per warmup result ---
                ilp_entries: list[dict] = []
                best_ilp_positions    = None
                best_ilp_opt_result   = None
                best_ilp_cost         = float("inf")
                best_ilp_variant_map  = {}

                for wu_r in warmup_results:
                    wp_2d = {bid: (v[0], v[1]) for bid, v in wu_r.positions.items()}
                    kwargs_i = {**base_kwargs, "initial_warm_positions": wp_2d,
                                "initial_variant_map": wu_r.variant_map}
                    opt_i = self._optimizer_cls(
                        topology, evaluator, cfg, observer=self._observer, **kwargs_i
                    )
                    t_i = time.perf_counter()
                    res_i = opt_i.run()
                    t_i_ms = (time.perf_counter() - t_i) * 1000

                    topology.restore_state(res_i.best_state)
                    pos_i   = topology.decode()
                    vm_i    = topology.get_variant_map()
                    cost_i  = evaluator.evaluate(pos_i)

                    # Collect block dims for viewer (same format as warmup positions)
                    positions_with_dims = {
                        bid: [
                            round(pos_i[bid][0], 6), round(pos_i[bid][1], 6),
                            round(
                                _active_variant(blocks.get(bid, {})).get("main_bbox", {}).get("x_max", 0.0), 6
                            ),
                            round(
                                _active_variant(blocks.get(bid, {})).get("main_bbox", {}).get("y_max", 0.0), 6
                            ),
                        ]
                        for bid in pos_i
                    }
                    ilp_entries.append({
                        "run_index":    wu_r.run_index,
                        "strategy":     wu_r.strategy,
                        "seed":         wu_r.seed,
                        "cost":         round(cost_i, 6),
                        "warmup_cost":  round(wu_r.cost, 6),
                        "is_selected":  False,
                        "t_optimize_ms": round(t_i_ms, 1),
                        "positions":    positions_with_dims,
                    })

                    if cost_i < best_ilp_cost:
                        best_ilp_cost        = cost_i
                        best_ilp_positions   = pos_i
                        best_ilp_opt_result  = res_i
                        best_ilp_variant_map = vm_i

                # Mark the best entry as selected
                if ilp_entries:
                    best_entry = min(ilp_entries, key=lambda e: e["cost"])
                    best_entry["is_selected"] = True

                if best_ilp_opt_result is None:
                    raise RuntimeError("All exhaustive-ILP runs failed — no valid placement produced")

                ilp_entries.sort(key=lambda e: e["cost"])
                warmup_runs_data    = ilp_entries
                opt_result          = best_ilp_opt_result
                final_positions     = best_ilp_positions
                variant_map         = best_ilp_variant_map
                result.t_optimize_ms = sum(e["t_optimize_ms"] for e in ilp_entries)

            else:
                # --- Default mode: single ILP run with selected warmup positions ---
                effective_kwargs = dict(base_kwargs)
                if warmup_positions is not None:
                    effective_kwargs["initial_warm_positions"] = warmup_positions
                    effective_kwargs["initial_variant_map"]    = warmup_variant_map
                optimizer = self._optimizer_cls(
                    topology, evaluator, cfg, observer=self._observer, **effective_kwargs
                )
                t_opt_start = time.perf_counter()
                opt_result  = optimizer.run()
                result.t_optimize_ms = (time.perf_counter() - t_opt_start) * 1000

                # Step 8: restore best state and decode final positions
                topology.restore_state(opt_result.best_state)
                final_positions = topology.decode()
                variant_map     = topology.get_variant_map()

            n_ilp_runs = len(warmup_runs_data) if (warmup_cfg and warmup_cfg.exhaustive_ilp) else 1
            result.status        = "success"
            result.final_cost    = evaluator.evaluate(final_positions) if final_positions else 0.0
            result.n_iterations  = n_ilp_runs
            result.positions     = final_positions
            result.variant_map   = variant_map
            placed = _compute_placed_blocks(final_positions, blocks, variant_map)
            try:
                from pin_optimizer import optimize_pin_positions
                placed = optimize_pin_positions(placed, nets, blocks)
            except Exception as _pin_exc:
                warnings.warn(f"pin_optimizer skipped: {_pin_exc}")
            result.placed_blocks = placed
            result.area_um2      = _bbox_area(final_positions, blocks)
            result.hpwl_um       = _hpwl(final_positions, blocks, nets, use_power_rails=self._use_power_rails)
            result.aspect_ratio  = _aspect_ratio(final_positions, blocks)
            result.power_rails   = _compute_power_rails(final_positions, blocks)
            result.warmup_runs   = warmup_runs_data

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


def _hpwl(positions: dict, blocks: dict, nets: list, use_power_rails: bool = False) -> float:
    pin_pos: dict[str, tuple[float, float]] = {}
    for bid, (bx, by) in positions.items():
        v = _active_variant(blocks.get(bid, {}))
        for pname, pcoord in v.get("pin_positions", {}).items():
            pin_pos[f"B{bid}_{pname}"] = (bx + pcoord["x"], by + pcoord["y"])
    if use_power_rails and positions:
        y_top = max(
            by + _active_variant(blocks.get(bid, {})).get("main_bbox", {}).get("y_max", 0.0)
            for bid, (_, by) in positions.items()
        )
        y_bot = min(by for _, (_, by) in positions.items())
    total = 0.0
    for net in nets:
        pins = net.get("pins", [])
        xs = [pin_pos[p][0] for p in pins if p in pin_pos]
        ys = [pin_pos[p][1] for p in pins if p in pin_pos]
        if use_power_rails and xs:
            nid = net.get("net_id", "").upper()
            if nid in _VDD_NET_IDS:
                ys.append(y_top)
            elif nid in _VSS_NET_IDS:
                ys.append(y_bot)
        if len(xs) >= 2:
            total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def _compute_power_rails(positions: dict, blocks: dict) -> dict:
    if not positions:
        return {}
    xs_all, y_tops, y_bots = [], [], []
    for bid, (bx, by) in positions.items():
        v = _active_variant(blocks.get(bid, {}))
        h = v.get("main_bbox", {}).get("y_max", 0.0)
        w = v.get("main_bbox", {}).get("x_max", 0.0)
        y_tops.append(by + h)
        y_bots.append(by)
        xs_all += [bx, bx + w]
    return {
        "VDD": {"y": max(y_tops), "x_min": min(xs_all), "x_max": max(xs_all)},
        "VSS": {"y": min(y_bots), "x_min": min(xs_all), "x_max": max(xs_all)},
    }


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
