#!/usr/bin/env python3
"""
Graph-based symmetry detection for analog netlists — SSFG method of
Eick et al., "Comprehensive Generation of Hierarchical Placement Rules for
Analog Integrated Circuits", IEEE TCAD 2011.

Pipeline:
  0. Logical devices     — series stacks (same gate, private internal net) collapsed
  1. Building blocks     — ccm → scm → ls → xcpl → digital → dp → t (Eick Fig. 5 + a
                           digital library; a larger or more specific pattern claims a
                           device first)
  2. SSFG                — one sub-SSFG per building block; power nets carry no signal
  3. Symmetry assignment — BFS from dp input pairs (S1–S4). Ambiguous successors are
                           resolved by backtracking; the first assignment with the
                           fewest V2 violations wins (Eick §III-C-1b)
  4. Device symmetry     — dp/xcpl pairs, bank-internal drain pairs, then the
                           terminal mapping φ (net → symmetric partner)
  5. Compounds           — one per connected propagation (one common axis); pairs are
                           ordered [L, R]: the seeding dp's first gate is side L and every
                           derived pair keeps the orientation of the pair it came from

Every device ends in at most one pair; there are no self-symmetric devices
(a tail belongs to the current mirror that feeds it). Decisions and tests:
.claude/plans/eick_symmetry_detection_rewrite.md,
lib/tests/test_symmetry_detection_eick.py.

Public API (called from 011_netlisBlocksGenerator.py):
  detect_symmetries(devices, port_nets, power_nets) -> dict
  find_passive_arrays(devices)                      -> list
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
from collections import defaultdict
from itertools import permutations, product
from typing import Dict, List, Set, Tuple

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from log_setup import get_logger

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG  = False

_MOSFET_GROUPS  = frozenset({"LV", "HV"})
_PASSIVE_GROUPS = frozenset({"passive"})

# Backtracking limits: an ambiguity with more successors than this is resolved
# in sorted order only, and after this many explored branches every remaining
# ambiguity takes its first permutation.
_MAX_PERMUTED  = 4
_SEARCH_BUDGET = 2000

# Digital proximity block types (mixed N/P, matched as one placement unit only).
_DIGITAL = ("inv", "nand2", "nor2", "tg")

# Building-block type → topology tag used by hierarchy_builder / topology_library.
_TAG_OF: Dict[str, str] = {
    "dp":      "diff_pair",
    "xcpl":    "cross_coupled",
    "ccm":     "cascode_current_mirror",
    "scm":     "current_mirror",
    "ls":      "level_shifter",
    "inv":     "inverter",
    "nand2":   "nand2",
    "nor2":    "nor2",
    "tg":      "transmission_gate",
    "t":       "paired_symmetric",
    "passive": "passive",
}
_TAG_PRIORITY: Dict[str, int] = {
    "diff_pair":              6,
    "cross_coupled":          5,
    "cascode_current_mirror": 4,
    "current_mirror":         3,
    "level_shifter":          3,
    "paired_symmetric":       2,
    "inverter":               1,
    "nand2":                  1,
    "nor2":                   1,
    "transmission_gate":      1,
    "passive":                1,
}

# =============================================================================
# 3. LOGGING
# =============================================================================
logger = get_logger(__name__, DEBUG)


# =============================================================================
# 4. ALGORITHM
# =============================================================================

# ── Device accessors ──────────────────────────────────────────────────────────

def _is_mosfet(dev: dict) -> bool:
    return dev.get("device_group") in _MOSFET_GROUPS


def _is_passive(dev: dict) -> bool:
    return dev.get("device_group") in _PASSIVE_GROUPS


def _gate(dev: dict) -> str:
    return dev["terminals"].get("gate", "")


def _drain(dev: dict) -> str:
    return dev["terminals"].get("drain", "")


def _source(dev: dict) -> str:
    return dev["terminals"].get("source", "")


def _passive_nets(dev: dict) -> frozenset:
    return frozenset(
        v for k, v in dev["terminals"].items()
        if k not in ("substrate", "bulk")
    )


def _terminal_nets(dev: dict) -> Dict[str, str]:
    return {k: v for k, v in dev["terminals"].items()
            if k not in ("bulk", "substrate") and v}


def _polarity(L: dict) -> str:
    """device_class (PDK-generic, set by 012) wins; gpdk090 names carry "pmos"."""
    if L.get("device_class"):
        return "p" if L["device_class"] == "pmos" else "n"
    return "p" if "pmos" in L["pdk_type"].lower() else "n"


# ── Phase 0 — logical devices (series stacks) ─────────────────────────────────

def _logical_devices(devices: list, port_nets: set, power_nets: set) -> List[dict]:
    """
    One entry per schematic-level device: {"members", "pdk_type", "mos", "d", "g", "s"}
    for MOSFETs (members ordered from the drain side), {"members", "pdk_type",
    "mos": False, "nets"} for passives.
    """
    conn: Dict[str, int] = defaultdict(int)
    for d in devices:
        for net in _terminal_nets(d).values():
            conn[net] += 1

    mos = [d for d in devices if _is_mosfet(d)]
    by_drain: Dict[str, list] = defaultdict(list)
    for d in mos:
        by_drain[_drain(d)].append(d)

    lower_of: Dict[int, dict] = {}
    for u in mos:
        n = _source(u)
        if not n or n in power_nets or n in port_nets or conn[n] != 2:
            continue
        cands = [l for l in by_drain.get(n, [])
                 if l is not u and l["pdk_type"] == u["pdk_type"] and _gate(l) == _gate(u)]
        if len(cands) == 1:
            lower_of[u["block_id"]] = cands[0]
    has_upper = {l["block_id"] for l in lower_of.values()}

    logical: List[dict] = []
    for d in mos:
        if d["block_id"] in has_upper:
            continue
        chain = [d]
        while chain[-1]["block_id"] in lower_of:
            chain.append(lower_of[chain[-1]["block_id"]])
        logical.append({
            "members":  [c["block_id"] for c in chain],
            "pdk_type": d["pdk_type"],
            "device_class": d.get("device_class"),
            "mos":      True,
            "d": _drain(chain[0]), "g": _gate(d), "s": _source(chain[-1]),
        })
        if len(chain) > 1:
            logger.info("Series stack: %s", [c["inst"] for c in chain])
    for d in devices:
        if _is_passive(d):
            logical.append({"members": [d["block_id"]], "pdk_type": d["pdk_type"],
                            "mos": False, "nets": _passive_nets(d)})
    for i, L in enumerate(logical):
        L["id"] = i
    return logical


# ── Phase 1 — building blocks ─────────────────────────────────────────────────

def _recognize_building_blocks(logical: List[dict], power_nets: set) -> Tuple[List[dict], Dict[int, str]]:
    """
    Returns (building_blocks, type_of). Each block: {"type", "devices", "reference"}
    (+ "stacks" for ccm, "outputs" for ls) over logical ids; type_of maps every
    MOSFET logical id to its block type ("t" when unclaimed).
    """
    mos = [L for L in logical if L["mos"]]
    claimed: Set[int] = set()
    bbs: List[dict] = []

    fam: Dict[tuple, list] = defaultdict(list)
    by_src: Dict[tuple, list] = defaultdict(list)
    for L in mos:
        if L["g"] and L["g"] not in power_nets:
            fam[(L["pdk_type"], L["g"])].append(L)
        by_src[(L["pdk_type"], L["s"])].append(L)

    def _claim(kind: str, devs: list, ref: list, **extra) -> None:
        bbs.append({"type": kind, "devices": [L["id"] for L in devs],
                    "reference": [L["id"] for L in ref], **extra})
        claimed.update(L["id"] for L in devs)

    # 1. Cascode current mirror (Eick Fig. 5d): lower pair on g_l with common
    #    source, upper pair on g_u stacked on the lower drains, diode across the
    #    reference stack (g_l == upper drain) or on both levels.
    for (pdk, g_l), lowers in fam.items():
        by_s: Dict[str, list] = defaultdict(list)
        for l in lowers:
            by_s[l["s"]].append(l)
        for low in by_s.values():
            stacks = []
            for l in low:
                if l["id"] in claimed:
                    continue
                ups = [u for u in by_src.get((pdk, l["d"]), [])
                       if u["id"] not in claimed and u is not l
                       and u["g"] and u["g"] not in power_nets and u["g"] != g_l]
                if len(ups) == 1:
                    stacks.append((ups[0], l))
            by_gu: Dict[str, list] = defaultdict(list)
            for u, l in stacks:
                by_gu[u["g"]].append((u, l))
            for g_u, st in by_gu.items():
                if len(st) < 2:
                    continue
                refs = [(u, l) for u, l in st
                        if u["d"] == g_l or (u["d"] == g_u and l["d"] == g_l)]
                if not refs or any(x["id"] in claimed for u, l in st for x in (u, l)):
                    continue
                _claim("ccm", [x for u, l in st for x in (u, l)],
                       [x for u, l in refs for x in (u, l)],
                       stacks=[(u["id"], l["id"]) for u, l in st])
                logger.info("Cascode mirror: gates %s/%s, %d stacks", g_u, g_l, len(st))

    # 2. Simple current mirror bank (Fig. 5c): diode + common source.
    for (pdk, g), ms in fam.items():
        for diode in [L for L in ms if L["d"] == g]:
            group = [L for L in ms if L["id"] not in claimed and L["s"] == diode["s"]]
            if len(group) >= 2:
                _claim("scm", group, [L for L in group if L["d"] == g])
                logger.info("Current mirror: gate=%s, n=%d", g, len(group))

    # 3. Level-shifter bank (Fig. 5b): diode reference, outputs on other sources.
    #    The reference may already sit in an scm of the same gate net; it then
    #    stays there and is only named as this block's reference.
    for (pdk, g), ms in fam.items():
        diodes = [L for L in ms if L["d"] == g]
        if not diodes:
            continue
        ref = diodes[0]
        outs = [L for L in ms if L["id"] not in claimed and L["s"] != ref["s"]]
        if not outs:
            continue
        devs = ([ref] if ref["id"] not in claimed else []) + outs
        _claim("ls", devs, [ref], outputs=[L["id"] for L in outs])
        logger.info("Level shifter: gate=%s, %d output(s)", g, len(outs))

    # 4. Cross-coupled latch [ext]: before dp, because a latch on a common
    #    signal source also matches the dp pattern (corpus a10).
    for pdk in sorted({L["pdk_type"] for L in mos}):
        free = [L for L in mos if L["pdk_type"] == pdk and L["id"] not in claimed]
        for i, a in enumerate(free):
            if a["id"] in claimed or not a["g"] or a["g"] in power_nets or a["d"] in power_nets:
                continue
            for b in free[i + 1:]:
                if b["id"] in claimed:
                    continue
                if a["g"] == b["d"] and b["g"] == a["d"] and a["g"] != a["d"]:
                    _claim("xcpl", [a, b], [])
                    logger.info("Cross-coupled pair: logical %d/%d", a["id"], b["id"])
                    break

    # 5. Digital proximity blocks (not in Eick): N and P devices of one logic gate.
    _recognize_digital(mos, power_nets, claimed, _claim)

    # 6. Differential pair (Fig. 5a): exactly two devices on a non-power source.
    for (pdk, src), ms in by_src.items():
        if not src or src in power_nets:
            continue
        free = [L for L in ms if L["id"] not in claimed]
        if len(free) == 2 and free[0]["g"] != free[1]["g"] \
                and not {free[0]["g"], free[1]["g"]} & power_nets:
            _claim("dp", free, [])
            logger.info("Diff pair on source %s", src)
        elif len(free) > 2 and len({L["g"] for L in free}) > 1:
            logger.warning("Ambiguous source %s: %d devices, no diff pair", src, len(free))

    type_of: Dict[int, str] = {L["id"]: "t" for L in mos}
    for bb in bbs:
        for lid in bb["devices"]:
            type_of[lid] = bb["type"]
    return bbs, type_of


def _recognize_digital(mos: List[dict], power_nets: set, claimed: Set[int], claim) -> None:
    """
    Digital library (proximity blocks, devices role-ordered for pairing):
      nand2 / nor2 — two series devices of one polarity (different gates) from the
                     output to a rail + two parallel devices of the other polarity
                     on the same gates: (series_top, series_bottom, par_top_gate, par_bottom_gate)
      inv          — N + P, same gate and drain, sources on the rails: (n, p)
      tg           — N + P across the same two nets, different gates: (n, p)
    Runs after the analog blocks, so a cross-coupled inverter pair stays a latch.
    """
    free = lambda L: L["id"] not in claimed
    nmos = [L for L in mos if _polarity(L) == "n"]
    pmos = [L for L in mos if _polarity(L) == "p"]

    for kind, series, parallel in (("nand2", nmos, pmos), ("nor2", pmos, nmos)):
        for top in series:
            for bot in series:
                if not (free(top) and free(bot)) or top is bot or top["s"] != bot["d"] \
                        or top["g"] == bot["g"] or bot["s"] not in power_nets \
                        or top["d"] in power_nets or top["s"] in power_nets:
                    continue
                par = {g: [L for L in parallel if free(L) and L["d"] == top["d"]
                           and L["g"] == g and L["s"] in power_nets]
                       for g in (top["g"], bot["g"])}
                if all(par.values()):
                    claim(kind, [top, bot, par[top["g"]][0], par[bot["g"]][0]], [])
                    logger.info("%s gate: output %s", kind, top["d"])

    for n in nmos:
        for p in pmos:
            if free(n) and free(p) and n["g"] == p["g"] and n["d"] == p["d"] \
                    and n["g"] not in power_nets and n["d"] not in power_nets \
                    and n["s"] in power_nets and p["s"] in power_nets:
                claim("inv", [n, p], [])
                logger.info("Inverter: %s → %s", n["g"], n["d"])

    for n in nmos:
        for p in pmos:
            if free(n) and free(p) and {n["d"], n["s"]} == {p["d"], p["s"]} \
                    and n["g"] != p["g"] and not {n["d"], n["s"]} & power_nets:
                claim("tg", [n, p], [])
                logger.info("Transmission gate: %s ↔ %s", n["d"], n["s"])


# ── Phase 2 — SSFG construction ───────────────────────────────────────────────

def _build_ssfg(
    bbs: List[dict], logical: List[dict], type_of: Dict[int, str], power_nets: set,
) -> Dict[str, List[Tuple[str, tuple]]]:
    """
    Out-adjacency net → [(dst, (bb_type, pin_a, pin_b))], power nets omitted.
    Each bb also gets bb["edges"] = its own sub-SSFG, used for bb-level symmetry.
    """
    out_adj: Dict[str, List[Tuple[str, tuple]]] = defaultdict(list)
    seen: Set[tuple] = set()
    sink: list = []

    def _add(src: str, dst: str, attr: tuple) -> None:
        if not src or not dst or src == dst or src in power_nets or dst in power_nets:
            return
        sink.append((src, dst, attr))
        if (src, dst, attr) in seen:
            return
        seen.add((src, dst, attr))
        out_adj[src].append((dst, attr))

    L = logical
    for bb in bbs:
        sink = bb["edges"] = []
        pol = _polarity(L[bb["devices"][0] if bb["devices"] else bb["reference"][0]])
        kind = bb["type"]
        if kind in ("dp", "xcpl"):
            bbt = f"{pol}-{kind}"
            for lid in bb["devices"]:
                _add(L[lid]["g"], L[lid]["d"], (bbt, "a", "b"))
                _add(L[lid]["s"], L[lid]["d"], (bbt, "c", "b"))
        elif kind == "scm":
            ref = set(bb["reference"])
            g = L[bb["devices"][0]]["g"]
            for lid in bb["devices"]:
                if lid not in ref:
                    _add(g, L[lid]["d"], (f"{pol}-scm", "a", "b"))
        elif kind == "ccm":
            # Eick: the cascode mirror's sub-SSFG equals the simple mirror's.
            ref_stack = next(st for st in bb["stacks"] if st[0] in bb["reference"])
            p_a = L[ref_stack[0]]["d"]
            for u, _ in bb["stacks"]:
                if (u, _) != ref_stack:
                    _add(p_a, L[u]["d"], (f"{pol}-ccm", "a", "b"))
        elif kind == "ls":
            bbt = f"{pol}-ls"
            r = L[bb["reference"][0]]
            p_a, p_c = r["d"], r["s"]
            _add(p_a, p_c, (bbt, "a", "c"))
            _add(p_c, p_a, (bbt, "c", "a"))
            for lid in bb["outputs"]:
                p_b, p_d = L[lid]["d"], L[lid]["s"]
                _add(p_b, p_d, (bbt, "b", "d"))
                _add(p_d, p_b, (bbt, "d", "b"))
                _add(p_a, p_b, (bbt, "a", "b"))
                _add(p_a, p_d, (bbt, "a", "d"))
                _add(p_c, p_b, (bbt, "c", "b"))
                _add(p_c, p_d, (bbt, "c", "d"))
        elif kind in ("inv", "nand2", "nor2"):
            out = L[bb["devices"][0]]["d"]
            for pin, lid in zip("ab", bb["devices"][:2] if kind != "inv" else bb["devices"][:1]):
                _add(L[lid]["g"], out, (kind, pin, "o"))
        elif kind == "tg":
            n = L[bb["devices"][0]]
            _add(n["d"], n["s"], ("tg", "a", "b"))
            _add(n["s"], n["d"], ("tg", "b", "a"))
    sink = []
    for lid, kind in type_of.items():
        if kind == "t":
            # Channel conducts both ways (like Eick's ls p_b↔p_d): s↔d lets the
            # propagation climb from a DP's outputs into a cascode load (corpus a30).
            bbt = f"{_polarity(L[lid])}-t"
            _add(L[lid]["g"], L[lid]["d"], (bbt, "g", "d"))
            _add(L[lid]["s"], L[lid]["d"], (bbt, "s", "d"))
            _add(L[lid]["d"], L[lid]["s"], (bbt, "d", "s"))
    logger.debug("SSFG: %d source nodes, %d edges", len(out_adj), len(seen))
    return out_adj


# ── Phase 3 — symmetry assignment with backtracking ───────────────────────────

class _Assignment:
    """Symmetric net pairs found so far + compound bookkeeping (cheap to copy)."""

    def __init__(self) -> None:
        self.partner:  Dict[str, str] = {}
        self.comp:     Dict[str, int] = {}     # net → compound id
        self.uf:       Dict[int, int] = {}
        self.self_net: Set[str]       = set()
        self.terminal: Set[tuple]     = set()  # pairs ended by a self-symmetric edge
        self.side:     Dict[str, str] = {}     # net → "L" | "R"
        self.conflicts = 0

    def copy(self) -> "_Assignment":
        c = _Assignment()
        c.partner, c.comp, c.uf = dict(self.partner), dict(self.comp), dict(self.uf)
        c.self_net, c.terminal, c.side = set(self.self_net), set(self.terminal), dict(self.side)
        c.conflicts = self.conflicts
        return c

    def find(self, x: int) -> int:
        while self.uf.get(x, x) != x:
            x = self.uf[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.uf[ra] = rb


def _key(a: str, b: str) -> tuple:
    return (a, b) if a <= b else (b, a)


def _link(st: _Assignment, queue: list, a: str, b: str, comp: int) -> None:
    if a == b:
        st.self_net.add(a)                     # two symmetric edges converge
        return
    pa, pb = st.partner.get(a), st.partner.get(b)
    if pa == b:
        st.union(st.comp[a], comp)
        return
    if pa is not None or pb is not None:
        st.conflicts += 1
        return
    st.partner[a], st.partner[b] = b, a
    st.comp[a] = st.comp[b] = comp
    # Queued pairs keep their orientation: the first net always descends from the
    # seeding dp's first gate (side L).
    st.side[a], st.side[b] = "L", "R"
    queue.append((a, b))


def _successor_groups(out_adj: dict, n: str, m: str) -> List[Tuple[list, list]]:
    by_n: Dict[tuple, list] = defaultdict(list)
    by_m: Dict[tuple, list] = defaultdict(list)
    for dst, attr in out_adj.get(n, []):
        by_n[attr].append(dst)
    for dst, attr in out_adj.get(m, []):
        by_m[attr].append(dst)
    groups = []
    for attr in sorted(set(by_n) & set(by_m)):
        A, B = sorted(by_n[attr]), sorted(by_m[attr])
        if len(A) == len(B):
            groups.append((A, B))
    return groups


def _connected(out_adj: dict, n: str, m: str) -> bool:
    """
    Self-symmetric edge (Eick Def. 4): an edge n→m without an opposite edge of
    the same attribute. A latch's crossn→crossp + crossp→crossn are a symmetric
    edge pair instead and do not end the search.
    """
    nm = {a for d, a in out_adj.get(n, []) if d == m}
    mn = {a for d, a in out_adj.get(m, []) if d == n}
    return bool(nm ^ mn)


def _violations(out_adj: dict, st: _Assignment) -> int:
    """Eick V2: every edge leaving n needs a symmetric edge leaving n' (and vice versa)."""
    v = st.conflicts
    for n, m in {_key(a, b) for a, b in st.partner.items()}:
        if (n, m) in st.terminal:
            continue
        by_n: Dict[tuple, Set[str]] = defaultdict(set)
        by_m: Dict[tuple, Set[str]] = defaultdict(set)
        for dst, attr in out_adj.get(n, []):
            by_n[attr].add(dst)
        for dst, attr in out_adj.get(m, []):
            by_m[attr].add(dst)
        for attr in set(by_n) | set(by_m):
            A, B = by_n.get(attr, set()), by_m.get(attr, set())
            v += sum(1 for x in A if st.partner.get(x, x) not in B)
            v += sum(1 for x in B if st.partner.get(x, x) not in A)
    return v


def _assign_symmetry(out_adj: dict, seeds: List[Tuple[str, str]]) -> _Assignment:
    """
    Eick Fig. 8 (S1 seeds, S2/S4 propagation, S3 self-symmetric edge ends the
    search) with the backtracking of §III-C-1b: every ambiguous successor
    matching is tried in sorted order; the first complete assignment with the
    fewest V2 violations is returned (0 → stop, as Eick stops at the first
    valid solution).
    """
    best: List = [None]
    budget = [_SEARCH_BUDGET]

    def run(st: _Assignment, queue: list) -> bool:
        while queue:
            n, m = queue.pop(0)
            if _connected(out_adj, n, m):
                st.terminal.add(_key(n, m))
                continue
            comp = st.comp[n]
            choices = []
            for A, B in _successor_groups(out_adj, n, m):
                if len(A) == 1 or len(A) > _MAX_PERMUTED:
                    choices.append([list(zip(A, B))])
                else:
                    choices.append([list(zip(A, p)) for p in permutations(B)])
            combos = list(product(*choices))
            if len(combos) <= 1 or budget[0] <= 0:
                for links in (combos[0] if combos else ()):
                    for a, b in links:
                        _link(st, queue, a, b, comp)
                continue
            for combo in combos:
                budget[0] -= 1
                st2, q2 = st.copy(), list(queue)
                for links in combo:
                    for a, b in links:
                        _link(st2, q2, a, b, comp)
                if run(st2, q2):
                    return True
            return False
        v = _violations(out_adj, st)
        if best[0] is None or v < best[0][0]:
            best[0] = (v, st)
        return v == 0

    st0, q0 = _Assignment(), []
    for i, (a, b) in enumerate(seeds):
        st0.uf[i] = i
        _link(st0, q0, a, b, i)
    run(st0, q0)
    v, st = best[0]
    if v:
        logger.info("Symmetry assignment: %d V2 violation(s) remain (best of search)", v)
    return st


# ── Phase 4 — device symmetry ─────────────────────────────────────────────────

def _device_pairs(
    logical: List[dict], bbs: List[dict], type_of: Dict[int, str], st: _Assignment,
) -> List[Tuple[int, int, str]]:
    """Logical-device pairs (a, b, bb_type); every device in at most one pair."""
    L = logical
    phi = lambda net: st.partner.get(net, net)
    paired: Set[int] = set()
    pairs: List[Tuple[int, int, str]] = []

    def _pair(a: int, b: int, kind: str) -> None:
        pairs.append((a, b, kind))
        paired.update((a, b))

    # dp and latch: the block itself is symmetric (Eick §III-C-2, self-symmetric bb).
    for bb in bbs:
        if bb["type"] in ("dp", "xcpl"):
            _pair(*bb["devices"], bb["type"])

    # Banks (scm, ls, ccm), Eick §III-C-2/3: a bank whose edges map onto
    # themselves under φ is self-symmetric (scm3 → (N3, N4); bank outputs on a
    # differential pair); two banks of one type whose edges map onto each other
    # are symmetric (scm1 ↔ scm2 → (P1, P2), (P3, P4)). Units are then matched
    # by their drain, a cascode stack as one unit. Units of banks without a
    # symmetric partner fall back to a unique drain match of the same type.
    # Digital blocks take part as one unit each (role-ordered devices, keyed by
    # the output net), so two symmetric inverters pair N↔N and P↔P.
    banks = [i for i, bb in enumerate(bbs) if bb["type"] in ("scm", "ls", "ccm") + _DIGITAL]
    units: Dict[int, List[Tuple[str, tuple]]] = {}
    for i in banks:
        bb = bbs[i]
        if bb["type"] == "ccm":
            units[i] = [(L[u]["d"], (u, l)) for u, l in bb["stacks"]]
        elif bb["type"] in _DIGITAL:
            units[i] = [(L[bb["devices"][0]]["d"], tuple(bb["devices"]))]
        else:
            units[i] = [(L[lid]["d"], (lid,)) for lid in bb["devices"]]

    def _img(e: tuple) -> tuple:
        return (phi(e[0]), phi(e[1]), e[2])

    def _pair_units(src: List[tuple], dst: List[tuple], kind: str) -> None:
        for d, u in src:
            if phi(d) == d or u[0] in paired:
                continue
            cands = [v for dv, v in dst if dv == phi(d) and v != u and v[0] not in paired]
            if len(cands) == 1 and len(cands[0]) == len(u):
                for a, b in zip(u, cands[0]):
                    _pair(a, b, kind)

    partner_bb: Dict[int, int] = {}
    for i in banks:
        edges = set(bbs[i]["edges"])
        if not edges:
            continue
        if all(_img(e) in edges or (_img(e)[1], _img(e)[0]) == e[:2] for e in edges):
            partner_bb[i] = i
            continue
        img = {_img(e) for e in edges}
        sym = [j for j in banks if j != i and bbs[j]["type"] == bbs[i]["type"]
               and set(bbs[j]["edges"]) == img]
        if len(sym) == 1:
            partner_bb[i] = sym[0]
    for i, j in partner_bb.items():
        if i <= j:
            _pair_units(units[i], units[j], bbs[i]["type"])
    for i in banks:
        same_type = [u for j in banks if bbs[j]["type"] == bbs[i]["type"] for u in units[j]]
        _pair_units(units[i], same_type, bbs[i]["type"])

    # Terminal mapping φ for everything else (symmetric bbs, single transistors,
    # passives [ext]): partner must be unique, same pdk_type and block type.
    def _sig(lg: dict, f) -> tuple:
        if lg["mos"]:
            return (lg["pdk_type"], type_of[lg["id"]], f(lg["d"]), f(lg["g"]), f(lg["s"]))
        return (lg["pdk_type"], "passive", frozenset(f(n) for n in lg["nets"]))

    by_sig: Dict[tuple, list] = defaultdict(list)
    for lg in L:
        by_sig[_sig(lg, lambda n: n)].append(lg["id"])
    for lg in L:
        if lg["id"] in paired:
            continue
        own, image = _sig(lg, lambda n: n), _sig(lg, phi)
        if image == own:
            continue
        cands = [c for c in by_sig.get(image, []) if c != lg["id"] and c not in paired]
        if len(cands) == 1:
            _pair(lg["id"], cands[0], type_of.get(lg["id"], "passive"))
    return pairs


# ── Phase 5 — compounds ───────────────────────────────────────────────────────

def _pair_nets(lg: dict) -> List[str]:
    return [lg["d"], lg["g"], lg["s"]] if lg["mos"] else sorted(lg["nets"])


def _pair_side(lg: dict, st: _Assignment) -> str | None:
    """Side of a paired device: its drain's side, else the first side among its nets."""
    for net in _pair_nets(lg):
        if net in st.side:
            return st.side[net]
    return None


def _assemble_groups(
    logical: List[dict], pairs: List[Tuple[int, int, str]], bbs: List[dict], st: _Assignment,
) -> list:
    L = logical
    next_id = max(st.uf, default=-1) + 1
    pair_comp: List[int] = []
    for a, b, _ in pairs:
        comps = {st.find(st.comp[n]) for n in _pair_nets(L[a]) if n in st.comp}
        if not comps:
            st.uf[next_id] = next_id
            comps = {next_id}
            next_id += 1
        root, *rest = sorted(comps)
        for c in rest:
            st.union(c, root)
        pair_comp.append(root)

    data: Dict[int, dict] = {}
    for (a, b, kind), c in zip(pairs, pair_comp):
        e = data.setdefault(st.find(c), {"pairs": [], "tags": set(), "core": set()})
        ma, mb = L[a]["members"], L[b]["members"]
        if len(ma) != len(mb):
            logger.warning("Paired stacks of unequal length %s / %s — skipped", ma, mb)
            continue
        if _pair_side(L[a], st) == "R" or _pair_side(L[b], st) == "L":
            ma, mb = mb, ma
        e["pairs"].extend([x, y] for x, y in zip(ma, mb))
        e["tags"].add(_TAG_OF[kind])
    for bb in bbs:
        if bb["type"] != "dp":
            continue
        a = L[bb["devices"][0]]
        c = st.find(st.comp[a["g"]]) if a["g"] in st.comp else None
        if c in data:
            for lid in bb["devices"]:
                data[c]["core"].update((L[lid]["d"], L[lid]["s"]))

    groups = []
    for cid, e in sorted(data.items()):
        if not e["pairs"]:
            continue
        groups.append({
            "compound_id":               cid,
            "axis":                      "vertical",
            "topology_tag":              max(e["tags"], key=lambda t: _TAG_PRIORITY.get(t, 0)),
            "pairs":                     e["pairs"],
            "self_symmetric":            [],
            "core_nets":                 sorted(e["core"]),
            "enforce_matching_variants": True,
        })
    return groups


# ── Symmetric net-pair annotations (schema unchanged) ─────────────────────────

def _build_sym_net_pairs(devices: list, pairs: list) -> list:
    id_to_dev: Dict[int, dict] = {d["block_id"]: d for d in devices}
    result: list = []
    for a, b in pairs:
        da, db = id_to_dev.get(a), id_to_dev.get(b)
        if da is None or db is None:
            continue
        ta, tb = da["terminals"], db["terminals"]
        for term in [t for t in ta if t in tb and t != "bulk"]:
            if ta[term] != tb[term]:
                result.append({"net_a": ta[term], "net_b": tb[term],
                               "block_pair": [a, b], "terminal": term})
    return result


def find_passive_arrays(devices: list) -> list:
    """Identical passives across the same nets → one parallel cluster each."""
    by_key: Dict[tuple, List[int]] = defaultdict(list)
    for d in devices:
        if _is_passive(d):
            by_key[(d["pdk_type"], _passive_nets(d))].append(d["block_id"])
    return [{"members": ids, "topology": "parallel", "representative_block_id": ids[0]}
            for ids in by_key.values()]


# =============================================================================
# 5. PUBLIC ENTRY POINT
# =============================================================================

def detect_symmetries(devices: list, port_nets: set, power_nets: set) -> dict:
    """
    Returns:
      building_blocks         — [{"type", "devices", "reference"}] (block ids)
      logical_devices         — [[block ids]] per MOSFET, series stacks merged
      groups                  — one per compound: pairs, self_symmetric ([]), core_nets
                                (DP drain/source nets), topology_tag
      symmetric_net_pairs     — per-terminal cross-net annotations of each pair
      self_symmetric_nets     — nets where symmetric edges converge
      cascode_proximity_pairs — [[upper_id, lower_id], ...] of cascode-mirror stacks
    """
    logical = _logical_devices(devices, port_nets, power_nets)
    bbs, type_of = _recognize_building_blocks(logical, power_nets)
    out_adj = _build_ssfg(bbs, logical, type_of, power_nets)

    seeds = [(logical[bb["devices"][0]]["g"], logical[bb["devices"][1]]["g"])
             for bb in bbs if bb["type"] == "dp"]
    # A gate net seeded with two different partners is a reference, not a
    # differential input (CMFB amplifier: (vref, outm), (vref, outp), corpus
    # m02); such seeds are discarded, their DPs stay matched building blocks.
    partners: Dict[str, Set[str]] = defaultdict(set)
    for a, b in seeds:
        partners[a].add(b)
        partners[b].add(a)
    dropped = [s for s in seeds if len(partners[s[0]]) > 1 or len(partners[s[1]]) > 1]
    if dropped:
        logger.info("Seeds dropped (shared reference gate): %s", dropped)
    st = _assign_symmetry(out_adj, [s for s in seeds if s not in dropped])

    pairs = _device_pairs(logical, bbs, type_of, st)
    groups = _assemble_groups(logical, pairs, bbs, st)

    phys = lambda lids: [b for lid in lids for b in logical[lid]["members"]]
    building_blocks = [{"type": bb["type"], "devices": phys(bb["devices"]),
                        "reference": phys(bb["reference"])} for bb in bbs]
    cascode_prox = [[logical[u]["members"][-1], logical[l]["members"][0]]
                    for bb in bbs if bb["type"] == "ccm" for u, l in bb["stacks"]]
    all_pairs = [p for g in groups for p in g["pairs"]]

    logger.info(
        "Symmetry: %d building blocks, %d compounds, %d device pairs",
        len(bbs), len(groups), len(all_pairs),
    )
    return {
        "building_blocks":         building_blocks,
        "logical_devices":         [L["members"] for L in logical if L["mos"]],
        "groups":                  groups,
        "symmetric_net_pairs":     _build_sym_net_pairs(devices, all_pairs),
        "self_symmetric_nets":     sorted(st.self_net),
        "cascode_proximity_pairs": cascode_prox,
    }
