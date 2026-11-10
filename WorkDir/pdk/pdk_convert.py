#!/usr/bin/env python3
"""
PDK converter: <pdk_dir>/convert.json (hand-written recipe) -> <pdk_dir>/characterize.json,
optionally -> pdk.json (characterize_pdk.py). How a PDK was converted is the recipe;
a new PDK = a copy of an existing recipe with the PDK-specific parts adjusted.
Format and procedure: .claude/knowledge/pdk_files.md.

1. Discover (in the PDK container, KLayout): for every PCell a recipe family names,
   its type parameter and choices; per choice the coerced minimum of every number
   parameter (all set to 0) and the layers it draws at its defaults. Layer names
   from the PDK's .lyp; model pins and .param values from its SPICE library.
2. Compose (host): the recipe's "spec" (everything characterize.json holds besides
   devices) + one pdk_tree family per recipe family, one member per PCell type
   choice that matches the family's "types" regex. Member vars come from the
   family's "derive" (Python expressions over the facts, in order, each seeing the
   previous ones); None / False vars are left out. Every "@layer" used anywhere
   gets its value from the .lyp. Families must not produce the same model twice.

Facts in a derive expression: pcell, type (PCell type choice), name (netlist model
name, from the family's "model" expression, default type), mins (coerced minima),
drawn (names of the layers drawn), pins (model .subckt pins, lowercase), mparams
(model .param values), plus implants(drawn) (the recipe's implant layers drawn,
as "@name", in recipe order) and num("0p69") -> 0.69.

Input:   <pdk_dir>/convert.json
Output:  <pdk_dir>/characterize.json (written only when composition succeeds),
         <pdk_dir>/discovery.json (the facts, for review), report on the log
Usage:   .venv/bin/python WorkDir/pdk/pdk_convert.py WorkDir/pdk/sky130/convert.json [--characterize]
Inside:  klayout -b -rm <pcell_macro> -r pdk_convert.py -rd recipe=<convert.json> -rd out=<discovery.json>
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import glob
import json
import logging
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import pya                      # only inside KLayout
    sys.path.insert(0, "/tmp/alda_conv")   # = _CONTAINER_DIR: pdk_tree.py is copied next to this script
except ImportError:
    pya = None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdk_tree

# =============================================================================
# 2. CONSTANTS
# =============================================================================
DEBUG = False

_CONTAINER_DIR = "/tmp/alda_conv"
_SKIP_NUMBERS = ("area", "perim", "cap_value", "res_value")    # PCell read-outs, not inputs
_LYP_RE = re.compile(r"^(.*?)\s+-\s+(\d+)/(\d+)$")              # "met1.drawing - 68/20"
_SUBCKT_RE = re.compile(r"^\.subckt\s+(\S+)\s*(.*)$", re.IGNORECASE)
_PARAM_RE = re.compile(r"(\w+)\s*=\s*(\{[^}]*\}|[^\s]+)")
_ROUND = 6

# =============================================================================
# 3. LOGGING
# =============================================================================
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
logger = logging.getLogger("pdk_convert")

# =============================================================================
# 4. ALGORITHM
# =============================================================================

# --- 4a. Discovery (container) ---------------------------------------------------

def discover_pcells(library: str, technology, names: list) -> dict:
    """{pcell: {"type_param", "types": {choice: {"mins", "drawn", "bbox"}}}} (KLayout)."""
    lib = (pya.Library.library_by_name(library, technology) if technology
           else pya.Library.library_by_name(library))
    if lib is None:
        raise RuntimeError(f"PCell library {library!r} not loaded (pcell_macro?)")
    ly, work = lib.layout(), pya.Layout()
    num = (pya.PCellParameterDeclaration.TypeDouble, pya.PCellParameterDeclaration.TypeInt)
    out = {}
    for name in names:
        decl = ly.pcell_declaration(name)
        if decl is None:
            raise KeyError(f"PCell {name!r} not in library {library!r}")
        ps = decl.get_parameters()
        tp = next(p for p in ps if p.name.lower() == "type" and p.choice_values())
        types = {}
        for choice in (str(c) for c in tp.choice_values()):
            if choice.endswith(".cdl"):         # fixed-cell PCells list netlist files next to the GDS
                continue
            base = {p.name: p.default for p in ps}
            base[tp.name] = choice
            zero = {p.name: (0 if p.type in num and not p.hidden and p.name not in _SKIP_NUMBERS else base[p.name])
                    for p in ps}
            co = decl.coerce_parameters(ly, [zero[p.name] for p in ps])
            mins = {p.name: c for p, c in zip(ps, co) if p.type in num and not p.hidden and p.name not in _SKIP_NUMBERS}
            cell = work.cell(work.add_pcell_variant(lib, ly.pcell_id(name), base))
            drawn = sorted({f"{work.get_info(li).layer}/{work.get_info(li).datatype}"
                            for li in work.layer_indexes() if not cell.bbox_per_layer(li).empty()})
            bb = cell.dbbox()
            types[choice] = {"mins": mins, "drawn": drawn, "bbox": [round(bb.width(), 4), round(bb.height(), 4)]}
        out[name] = {"type_param": tp.name, "types": types}
    return out


def read_lyp(path: str) -> dict:
    """{name: [layer, datatype]}: 'x.drawing' as 'x', every other purpose as 'x.purpose'."""
    out = {}
    for p in ET.parse(path).getroot().iter("properties"):
        m = _LYP_RE.match((p.findtext("name") or "").strip())
        if m:
            n = m.group(1)[:-len(".drawing")] if m.group(1).endswith(".drawing") else m.group(1)
            out.setdefault(n, [int(m.group(2)), int(m.group(3))])
    return out


def _logical(text: str) -> list:
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("+") and lines:
            lines[-1] += " " + s[1:]
        elif s and not s.startswith("*"):
            lines.append(s)
    return lines


def _value(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def read_models(patterns: list) -> dict:
    """{model (lowercase): {"pins": [...], "params": {...}}} from every .subckt of the
    SPICE files; params = the subckt line's defaults and its .param lines. First
    definition wins."""
    out: dict = {}
    for pat in patterns:
        for f in sorted(glob.glob(os.path.expandvars(pat), recursive=True)):
            cur = None
            for line in _logical(Path(f).read_text(encoding="utf-8", errors="replace")):
                m = _SUBCKT_RE.match(line)
                if m:
                    name = m.group(1).lower()
                    rest = m.group(2).split()
                    cur = None if name in out else name
                    if cur:
                        out[cur] = {"pins": [t.lower() for t in rest if "=" not in t and t.lower() != "params:"],
                                    "params": {k: _value(v) for k, v in _PARAM_RE.findall(m.group(2))}}
                elif cur and line.lower().startswith(".param"):
                    out[cur]["params"].update({k: _value(v) for k, v in _PARAM_RE.findall(line[6:])})
                elif line.lower().startswith(".ends"):
                    cur = None
    return out


def discover(recipe: dict) -> dict:
    src = recipe["sources"]
    names = sorted({p for f in recipe["families"].values() for p in f["pcells"]})
    return {"pcells": discover_pcells(recipe["spec"]["library"], recipe["spec"].get("technology"), names),
            "layers": read_lyp(os.path.expandvars(src["lyp"])),
            "models": read_models(src["models"])}


# --- 4b. Composition (host) ------------------------------------------------------

def _eval(expr: str, env: dict):
    """A recipe expression; env as globals so comprehensions see it too."""
    return eval(expr, {"__builtins__": {}, **env})


def num(s: str) -> float:
    """'0p69' -> 0.69 (sky130 size tags)."""
    return float(s.replace("p", "."))


def _layer_names(layers: dict, renames: dict) -> dict:
    """{name used in the recipe: [l, d]}; renames: recipe name -> .lyp name."""
    out = dict(layers)
    for new, old in renames.items():
        out[new] = layers[old]
    return out


def _refs_used(obj, out: set) -> set:
    if isinstance(obj, str) and obj.startswith("@") and "{" not in obj:
        out.add(obj[1:])
    elif isinstance(obj, dict):
        for v in obj.values():
            _refs_used(v, out)
    elif isinstance(obj, list):
        for x in obj:
            _refs_used(x, out)
    return out


def family_node(fname: str, fam: dict, disc: dict, names: dict, implants: list, report: list,
                pins_of: dict) -> dict:
    """One pdk_tree family: @name, @members (derived vars), the recipe body."""
    by_gds = {tuple(v): k for k, v in names.items()}
    prefix = fam["@name"].split("{key}")[0]
    members: dict = {}
    for pcell in fam["pcells"]:
        for choice, f in disc["pcells"][pcell]["types"].items():
            tname = Path(choice).stem if "/" in choice else choice
            if not re.fullmatch(fam.get("types", ".*"), tname):
                continue
            drawn = [by_gds.get(tuple(int(x) for x in g.split("/")), g) for g in f["drawn"]]
            env = {"pcell": pcell, "type_param": disc["pcells"][pcell]["type_param"],
                   "type": choice, "tname": tname, "mins": f["mins"], "drawn": drawn,
                   "implants": lambda d: [f"@{n}" for n in implants if n in d], "num": num,
                   "round": round, "max": max, "min": min, "len": len, "math": math}
            env["name"] = _eval(fam.get("model", "tname"), env)
            model = disc["models"].get(env["name"].lower())
            need = fam.get("require_model", True)
            if model is None and (_eval(need, env) if isinstance(need, str) else need):
                report.append(f"{fname}: {tname} skipped, no model {env['name']} in the SPICE library")
                continue
            env["pins"], env["mparams"] = (model or {}).get("pins", []), (model or {}).get("params", {})
            var = {} if choice == env["name"] else {"type": choice}    # default: @vars type = {name}
            for k, expr in fam.get("derive", {}).items():
                env[k] = _eval(expr, env)
                if env[k] is not None and env[k] is not False:
                    var[k] = round(env[k], _ROUND) if isinstance(env[k], float) else env[k]
            if not env["name"].startswith(prefix):
                raise ValueError(f"{fname}: model {env['name']} does not match @name {fam['@name']}")
            members[env["name"][len(prefix):]] = var
            if model is not None:
                pins_of[env["name"]] = env["pins"]
    if not members:
        raise ValueError(f"{fname}: no PCell type matches {fam.get('types')!r}")
    report.append(f"{fname}: {len(members)} models")
    return {"@name": fam["@name"], "@vars": {"type": "{name}"}, "@members": members, **fam["body"]}


def compose(recipe: dict, disc: dict) -> tuple:
    """(characterize.json tree, report lines)."""
    names = _layer_names(disc["layers"], recipe.get("layer_renames", {}))
    report: list = []
    pins_of: dict = {}
    devices = {fname: family_node(fname, fam, disc, names, recipe["implants"], report, pins_of)
               for fname, fam in recipe["families"].items()}
    spec = dict(recipe["spec"])
    refs = dict(spec.pop("@refs", {}))
    tree = {**spec, "devices": devices}
    for n in sorted(_refs_used(tree, set()) | _refs_used(refs, set())):
        if n not in refs:
            if n not in names:
                raise KeyError(f"layer @{n}: not in the .lyp (add it to layer_renames)")
            refs[n] = names[n]
    tree = {"@refs": dict(sorted(refs.items(), key=lambda kv: (not isinstance(kv[1], list), kv[0]))), **tree}
    flat = pdk_tree.expand(tree)                     # raises on an unknown ref or duplicate model
    bad = {m: (d["terminals"], pins_of[m]) for m, d in flat["devices"].items()
           if m in pins_of and len(d["terminals"]) != len(pins_of[m])}
    if bad:
        raise ValueError(f"terminal count differs from the model .subckt pins: {bad}")
    report.append(f"total: {len(flat['devices'])} models")
    return tree, report


# =============================================================================
# 5. ENTRY POINT
# =============================================================================

def run(recipe: dict, disc: dict) -> tuple:
    for key in ("spec", "sources", "families", "implants"):
        if key not in recipe:
            raise KeyError(f"run: recipe missing {key!r}")
    return compose(recipe, disc)


def main_container(recipe_path: str, out_path: str) -> None:
    recipe = json.loads(Path(recipe_path).read_text(encoding="utf-8"))
    Path(out_path).write_text(json.dumps(discover(recipe), indent=1, default=str), encoding="utf-8")


def main_host() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit("usage: pdk_convert.py <pdk_dir>/convert.json [--characterize]")
    recipe_path = Path(args[0]).resolve()
    pdk_dir = recipe_path.parent
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    c = recipe["spec"]["container"]["name"]
    subprocess.run(["docker", "exec", c, "mkdir", "-p", _CONTAINER_DIR], check=True)
    for f in (Path(__file__).resolve(), Path(__file__).resolve().parent / "pdk_tree.py", recipe_path):
        subprocess.run(["docker", "cp", str(f), f"{c}:{_CONTAINER_DIR}/{f.name}"], check=True)
    inner = (f"cd {_CONTAINER_DIR} && klayout -b -rm {recipe['spec']['container']['pcell_macro']} "
             f"-r {_CONTAINER_DIR}/{Path(__file__).name} "
             f"-rd recipe={_CONTAINER_DIR}/{recipe_path.name} -rd out={_CONTAINER_DIR}/discovery.json")
    subprocess.run(["docker", "exec", c, "bash", "-lc", inner], check=True)
    subprocess.run(["docker", "cp", f"{c}:{_CONTAINER_DIR}/discovery.json", str(pdk_dir / "discovery.json")], check=True)
    disc = json.loads((pdk_dir / "discovery.json").read_text(encoding="utf-8"))
    tree, report = run(recipe, disc)
    for line in report:
        logger.info("%s", line)
    (pdk_dir / "characterize.json").write_text(pdk_tree.dumps(tree) + "\n", encoding="utf-8")
    logger.info("wrote %s", pdk_dir / "characterize.json")
    if "--characterize" in sys.argv:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "characterize_pdk.py"),
                        str(pdk_dir / "characterize.json")], check=True)


if pya is None:
    if __name__ == "__main__":
        main_host()
else:
    main_container(globals()["recipe"], globals()["out"])
