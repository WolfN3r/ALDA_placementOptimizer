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
    route_segments: list[dict] = field(default_factory=list)  # [{layer,x_min,y_min,x_max,y_max}]
    route_status: str = ""  # "routed" | "unrouted" | ""


_COMPOSITE_ID_BASE = 10_000  # block_id threshold: IDs >= this value are composite group blocks


@dataclass
class PlacedBlockInfo:
    block_id: int
    main_bbox: tuple[float, float, float, float]   # x_min, y_min, x_max, y_max (absolute)
    pins: dict[str, dict]   # pin_name -> {x,y} (old) or {layer,side,x_min,y_min,x_max,y_max} (new)
    # Composite group fields — populated only when block_id >= _COMPOSITE_ID_BASE
    is_composite: bool = False
    group_id: int = 0
    topology_type: str = ""
    matching_variant: dict = field(default_factory=dict)
    sub_blocks: dict = field(default_factory=dict)   # str(member_bid) -> PlacedBlockInfo


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
    chip_power_rails: list[dict] = field(default_factory=list)  # VDD/VSS M1 chip rails


@dataclass
class PlacementData:
    file_path: str
    generation_params: dict
    technology: str
    blocks: list[Block]
    nets: list[Net]
    symmetry_constraints: dict  # keys: groups, passive_clusters, symmetric_net_pairs, self_symmetric_nets, cascode_proximity_pairs, tail_cm_pairs, compound_blocks
    groups: list  # hierarchy groups from py011/py101 JSON top-level groups[] key
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


def _extract_chip_rails(pb_raw: dict) -> list[dict]:
    """Return chip power rail dicts stored under '__chip_*' keys."""
    return [
        v for k, v in pb_raw.items()
        if k.startswith("__chip_") and isinstance(v, dict) and "layer" in v
    ]


def _parse_pins(raw_pins: dict) -> dict[str, dict]:
    pins: dict[str, dict] = {}
    for pname, ppos in raw_pins.items():
        if isinstance(ppos, dict):
            if "x_min" in ppos:
                pins[pname] = {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in ppos.items()}
            else:
                pins[pname] = {"x": float(ppos["x"]), "y": float(ppos["y"])}
        else:
            pins[pname] = {"x": float(ppos[0]), "y": float(ppos[1])}
    return pins


def _parse_bbox(b) -> tuple[float, float, float, float]:
    if isinstance(b, dict):
        return (float(b["x_min"]), float(b["y_min"]), float(b["x_max"]), float(b["y_max"]))
    return (float(b[0]), float(b[1]), float(b[2]), float(b[3]))


def _parse_placed_blocks(pb_raw: dict) -> dict[int, PlacedBlockInfo]:
    placed_blocks: dict[int, PlacedBlockInfo] = {}
    for bid_str, pb in pb_raw.items():
        if bid_str.startswith("__"):
            continue  # skip special entries (chip power rails, etc.)
        try:
            bid = int(bid_str)
        except ValueError:
            continue
        bbox = _parse_bbox(pb["main_bbox"])
        pins = _parse_pins(pb.get("pins", {}))

        if bid >= _COMPOSITE_ID_BASE:
            # Composite group block — parse sub_blocks and group metadata
            raw_sub = pb.get("sub_blocks", {})
            sub: dict[int, PlacedBlockInfo] = {}
            for mbid_str, mpb in raw_sub.items():
                try:
                    mbid = int(mbid_str)
                except ValueError:
                    continue
                sub[mbid] = PlacedBlockInfo(
                    block_id=mbid,
                    main_bbox=_parse_bbox(mpb["main_bbox"]),
                    pins=_parse_pins(mpb.get("pins", {})),
                )
            placed_blocks[bid] = PlacedBlockInfo(
                block_id=bid,
                main_bbox=bbox,
                pins=pins,
                is_composite=True,
                group_id=int(pb.get("group_id", bid - _COMPOSITE_ID_BASE)),
                topology_type=str(pb.get("topology_type", "")),
                matching_variant=dict(pb.get("matching_variant", {})),
                sub_blocks=sub,
            )
        else:
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
            route_segments=list(rn.get("route_segments", [])),
            route_status=str(rn.get("route_status", "")),
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
                _pb_raw = run_raw["placed_blocks"]
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
                    placed_blocks=_parse_placed_blocks(_pb_raw),
                    all_runs=[],
                    renorm_cost=float(run_raw.get("renorm_cost", 0.0)),
                    t_optimize_ms=float(run_raw.get("t_optimize_ms", 0.0)),
                    chip_power_rails=_extract_chip_rails(_pb_raw),
                ))
            parsed_runs.sort(key=lambda r: r.renorm_cost)
            all_placement_results = parsed_runs
            best_id = raw_placement.get("best_run_id", "")
            placement_result = next((r for r in parsed_runs if r.run_id == best_id), None)
            if placement_result is None and parsed_runs:
                placement_result = parsed_runs[0]
        elif "placed_blocks" in raw_placement:
            _pb_raw2 = raw_placement["placed_blocks"]
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
                placed_blocks=_parse_placed_blocks(_pb_raw2),
                all_runs=list(raw_placement.get("all_runs", [])),
                chip_power_rails=_extract_chip_rails(_pb_raw2),
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
        groups=list(raw.get("groups", [])),
        has_placement=has_placement,
        placement_result=placement_result,
        placement_mode=placement_mode,
        all_placement_results=all_placement_results,
    )
