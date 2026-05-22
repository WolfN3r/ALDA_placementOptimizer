"""Parse placement JSON files into typed dataclasses."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PinPos:
    name: str
    x: float
    y: float


@dataclass
class Variant:
    index: int
    rows: int
    cols: int
    aspect_ratio: float
    bbox: tuple[float, float, float, float]  # x_min, y_min, x_max, y_max
    pins: list[PinPos]
    is_used: bool
    rotation_deg: int  # 0 or 90


@dataclass
class Block:
    block_id: int
    device_type: str   # nmos1v_nat | nmos2v_nat | pmos1v_nat | pmos2v_nat
    parameters: dict
    variants: list[Variant]
    power_rail: str | None   # VDD | VSS | None
    placed: dict | None = None  # {x, y, rotation_deg, variant_index, ...} when placed


@dataclass
class Net:
    net_id: str
    net_type: str   # power | signal
    pins: list[str]  # ["B0_P1", "B3_P0", ...]


@dataclass
class PlacedBlockInfo:
    block_id: int
    main_bbox: tuple[float, float, float, float]   # x_min, y_min, x_max, y_max (absolute)
    pins: dict[str, tuple[float, float]]           # pin_name -> (abs_x, abs_y)


@dataclass
class PlacementResult:
    run_id: str
    topology: str
    optimizer: str
    final_cost: float
    area_um2: float
    hpwl_um: float
    aspect_ratio: float
    n_iterations: int
    t_total_ms: float
    placed_blocks: dict[int, PlacedBlockInfo]
    all_runs: list[dict]
    renorm_cost: float = 0.0
    t_optimize_ms: float = 0.0


@dataclass
class PlacementData:
    file_path: str
    generation_params: dict
    technology: str
    blocks: list[Block]
    nets: list[Net]
    symmetry_constraints: dict
    has_placement: bool
    placement_result: PlacementResult | None = None
    placement_mode: str = ""
    all_placement_results: list[PlacementResult] = field(default_factory=list)

    def block_by_id(self, block_id: int) -> Block | None:
        for b in self.blocks:
            if b.block_id == block_id:
                return b
        return None

    def nets_for_block(self, block_id: int) -> list[Net]:
        prefix = f"B{block_id}_"
        return [n for n in self.nets if any(p.startswith(prefix) for p in n.pins)]

    def active_variant(self, block: Block) -> Variant:
        """Return the placed variant if placed, else the is_used=True variant, else variant 0."""
        if block.placed and "variant_index" in block.placed:
            idx = block.placed["variant_index"]
            if 0 <= idx < len(block.variants):
                return block.variants[idx]
        for v in block.variants:
            if v.is_used:
                return v
        return block.variants[0]


def _parse_placed_blocks(pb_raw: dict) -> dict[int, PlacedBlockInfo]:
    placed_blocks: dict[int, PlacedBlockInfo] = {}
    for bid_str, pb in pb_raw.items():
        bid = int(bid_str)
        b = pb["main_bbox"]
        if isinstance(b, dict):
            bbox = (float(b["x_min"]), float(b["y_min"]), float(b["x_max"]), float(b["y_max"]))
        else:
            bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
        pins: dict[str, tuple[float, float]] = {}
        for pname, ppos in pb.get("pins", {}).items():
            if isinstance(ppos, dict):
                pins[pname] = (float(ppos["x"]), float(ppos["y"]))
            else:
                pins[pname] = (float(ppos[0]), float(ppos[1]))
        placed_blocks[bid] = PlacedBlockInfo(block_id=bid, main_bbox=bbox, pins=pins)
    return placed_blocks


def _parse_variant(idx: int, raw: dict) -> Variant:
    layout = raw.get("layout", {})
    bbox_raw = raw["main_bbox"]
    # Support both dict {"x_min":...} and list [x_min, y_min, x_max, y_max] formats
    if isinstance(bbox_raw, dict):
        bbox = (
            float(bbox_raw["x_min"]),
            float(bbox_raw["y_min"]),
            float(bbox_raw["x_max"]),
            float(bbox_raw["y_max"]),
        )
    else:
        bbox = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))

    # Support both {"x":...,"y":...} dict and [x,y] list for pin positions
    pins = []
    for k, v in raw.get("pin_positions", {}).items():
        if isinstance(v, dict):
            pins.append(PinPos(name=k, x=float(v["x"]), y=float(v["y"])))
        else:
            pins.append(PinPos(name=k, x=float(v[0]), y=float(v[1])))

    return Variant(
        index=idx,
        rows=int(layout.get("rows", 1)),
        cols=int(layout.get("cols", 1)),
        aspect_ratio=float(layout.get("aspect_ratio", 1.0)),
        bbox=bbox,
        pins=pins,
        is_used=bool(raw.get("is_used", False)),
        rotation_deg=int(raw.get("rotation_deg", 0)),
    )


def load(path: str | Path) -> PlacementData:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    # n8n-format files wrap the payload in a list of scenarios; unwrap the first one
    if isinstance(raw, list):
        raw = raw[0]

    blocks: list[Block] = []
    for rb in raw.get("blocks", []):
        variants = [_parse_variant(i, v) for i, v in enumerate(rb.get("variants", []))]
        placed = rb.get("placed", None)
        # only treat as placed if it carries real coordinates
        if placed and "x" not in placed and "y" not in placed:
            placed = None
        blocks.append(Block(
            block_id=int(rb["block_id"]),
            device_type=str(rb["device_type"]),
            parameters=rb.get("parameters", {}),
            variants=variants,
            power_rail=rb.get("power_rail"),
            placed=placed,
        ))

    nets: list[Net] = []
    for rn in raw.get("netlist", {}).get("nets", []):
        nets.append(Net(
            net_id=str(rn["net_id"]),
            net_type=str(rn["net_type"]),
            pins=list(rn.get("pins", [])),
        ))

    # Parse placement section (supports single-run and exhaustive modes)
    placement_result = None
    placement_mode = ""
    all_placement_results: list[PlacementResult] = []
    raw_placement = raw.get("placement", {})
    if isinstance(raw_placement, dict):
        placement_mode = str(raw_placement.get("mode", ""))
        if placement_mode == "exhaustive" and "runs" in raw_placement:
            parsed_runs: list[PlacementResult] = []
            for run_raw in raw_placement.get("runs", []):
                if run_raw.get("status") != "success" or not run_raw.get("placed_blocks"):
                    continue
                parsed_runs.append(PlacementResult(
                    run_id=str(run_raw.get("run_id", "")),
                    topology=str(run_raw.get("topology", "")),
                    optimizer=str(run_raw.get("optimizer", "")),
                    final_cost=float(run_raw.get("final_cost", 0.0)),
                    area_um2=float(run_raw.get("area_um2", 0.0)),
                    hpwl_um=float(run_raw.get("hpwl_um", 0.0)),
                    aspect_ratio=float(run_raw.get("aspect_ratio", 1.0)),
                    n_iterations=int(run_raw.get("n_iterations", 0)),
                    t_total_ms=float(run_raw.get("t_total_ms", 0.0)),
                    placed_blocks=_parse_placed_blocks(run_raw["placed_blocks"]),
                    all_runs=[],
                    renorm_cost=float(run_raw.get("renorm_cost", 0.0)),
                    t_optimize_ms=float(run_raw.get("t_optimize_ms", 0.0)),
                ))
            parsed_runs.sort(key=lambda r: r.renorm_cost)
            all_placement_results = parsed_runs
            best_id = raw_placement.get("best_run_id", "")
            placement_result = next((r for r in parsed_runs if r.run_id == best_id), None)
            if placement_result is None and parsed_runs:
                placement_result = parsed_runs[0]
        elif "placed_blocks" in raw_placement:
            placement_result = PlacementResult(
                run_id=str(raw_placement.get("run_id", "")),
                topology=str(raw_placement.get("topology", "")),
                optimizer=str(raw_placement.get("optimizer", "")),
                final_cost=float(raw_placement.get("final_cost", 0.0)),
                area_um2=float(raw_placement.get("area_um2", 0.0)),
                hpwl_um=float(raw_placement.get("hpwl_um", 0.0)),
                aspect_ratio=float(raw_placement.get("aspect_ratio", 1.0)),
                n_iterations=int(raw_placement.get("n_iterations", 0)),
                t_total_ms=float(raw_placement.get("t_total_ms", 0.0)),
                placed_blocks=_parse_placed_blocks(raw_placement["placed_blocks"]),
                all_runs=list(raw_placement.get("all_runs", [])),
            )

    has_placement = bool(
        (placement_result and placement_result.placed_blocks)
        or any(b.placed and "x" in b.placed and "y" in b.placed for b in blocks)
    )

    return PlacementData(
        file_path=str(path),
        generation_params=raw.get("generation_params", {}),
        technology=str(raw.get("technology", "")),
        blocks=blocks,
        nets=nets,
        symmetry_constraints=raw.get("symmetry_constraints", {}),
        has_placement=has_placement,
        placement_result=placement_result,
        placement_mode=placement_mode,
        all_placement_results=all_placement_results,
    )
