"""
Compact JSON tree for the PDK files (characterize.json, pdk.json). Every reader
expands a file to the plain dict the code works on; the characteriser writes
pdk.json through compress(). Stdlib only: runs on the host and inside KLayout.
Format reference: .claude/knowledge/pdk_files.md.

Rules (expand):
  "@refs": {name: value}       top level; a string "@name" anywhere is that value
  {"@use": name|[names], ...}  dict = deep merge of the refs, then its own keys
  family: a dict value holding "@members" -> one entry per member in the parent:
    "@name"    entry name template (default "{key}")
    "@members" {key: {var: value, ..., "@set": {...}}}
    "@vars"    {var: default} for members that do not set it (may use {key}, {name})
    "@when"    [{"@if": {var: value|[values]}, field: value, ...}] merged in order
    body       every other key; "{var}" in a string is the member's value
               (the whole string "{var}" keeps the value's type);
               vars: the member's, plus key and name
  deep merge: dicts recursively, anything else replaced; "key+": [..] appends

load(path)                  -> plain dict
expand(tree)                -> plain dict
compress(plain, refs, ...)  -> tree with expand(tree) == plain
dumps(obj)                  -> JSON text, small values on one line
"""
import copy
import json
import os
import re

# =============================================================================
# CONSTANTS
# =============================================================================
DEBUG = False

LINE_WIDTH = 110        # dumps(): a value that fits on one line stays on one line
INDENT = 2
HOIST_MIN_CHARS = 150   # compress(): repeated subtree at least this long (JSON) -> @refs;
                        # smaller ones save little and make the file harder to read
STRING_MIN_CHARS = 30   # compress(): repeated string at least this long -> @refs

_VAR = re.compile(r"\{(\w+)\}")

# =============================================================================
# ALGORITHM
# =============================================================================

# --- Expand ----------------------------------------------------------------------

def merge(base, over, refs: dict | None = None):
    """Deep merge (copies): dicts recursively, other values replaced, 'key+' appends to a list.
    A "@ref" in base that over changes in part is resolved first (needs refs); a "@ref"
    in over on a dict base too (hoist may turn a partial override into a ref)."""
    if _is_ref(base, refs) and isinstance(over, dict):
        base = _walk(base, refs)
    if _is_ref(over, refs) and isinstance(base, dict):
        over = _walk(over, refs)
    if not (isinstance(base, dict) and isinstance(over, dict)):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k.endswith("+"):
            cur = out.get(k[:-1], [])
            out[k[:-1]] = (_walk(cur, refs) if _is_ref(cur, refs) else cur) + copy.deepcopy(v)
        else:
            out[k] = merge(out[k], v, refs) if k in out else copy.deepcopy(v)
    return out


def _is_ref(v, refs) -> bool:
    """A "@name" that can be resolved now (not a "@{var}" template)."""
    return bool(refs) and isinstance(v, str) and v.startswith("@") and "{" not in v


def _sub(obj, var: dict):
    if isinstance(obj, str):
        m = _VAR.fullmatch(obj)
        if m:
            return copy.deepcopy(var[m.group(1)])
        return _VAR.sub(lambda m: str(var[m.group(1)]), obj)
    if isinstance(obj, list):
        return [_sub(x, var) for x in obj]
    if isinstance(obj, dict):
        return {_sub(k, var): _sub(v, var) for k, v in obj.items()}
    return obj


def _matches(var: dict, cond: dict) -> bool:
    return all(var.get(k) in (want if isinstance(want, list) else [want]) for k, want in cond.items())


def _family(fam: dict, refs: dict) -> list:
    """[(name, entry)] of a family node, vars substituted, refs not yet resolved."""
    body = {k: v for k, v in fam.items() if not k.startswith("@")}
    out = []
    for key, member in fam["@members"].items():
        var = {"key": key, **{k: v for k, v in member.items() if not k.startswith("@")}}
        var["name"] = _sub(fam.get("@name", "{key}"), var)
        for k, default in fam.get("@vars", {}).items():
            var.setdefault(k, _sub(default, var))
        entry = body
        for rule in fam.get("@when", []):
            if _matches(var, rule["@if"]):
                entry = merge(entry, {k: v for k, v in rule.items() if k != "@if"}, refs)
        entry = merge(entry, member.get("@set", {}), refs)
        out.append((var["name"], _sub(entry, var)))
    return out


def _walk(obj, refs: dict):
    if isinstance(obj, str) and obj.startswith("@"):
        if obj[1:] not in refs:
            raise KeyError(f"pdk_tree: unknown reference {obj!r}")
        return _walk(copy.deepcopy(refs[obj[1:]]), refs)
    if isinstance(obj, list):
        return [_walk(x, refs) for x in obj]
    if not isinstance(obj, dict):
        return obj
    if "@use" in obj:
        names = obj["@use"] if isinstance(obj["@use"], list) else [obj["@use"]]
        base: dict = {}
        for n in names:
            base = merge(base, _walk(f"@{n}", refs), refs)
        obj = merge(base, {k: v for k, v in obj.items() if k != "@use"}, refs)
    out: dict = {}
    for k, v in obj.items():
        items = _family(v, refs) if isinstance(v, dict) and "@members" in v else [(k, v)]
        for name, entry in items:
            if name in out:
                raise KeyError(f"pdk_tree: duplicate entry {name!r}")
            out[name] = _walk(entry, refs)
    return out


def expand(tree: dict) -> dict:
    return _walk({k: v for k, v in tree.items() if k != "@refs"}, tree.get("@refs", {}))


def load(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return expand(json.load(f))


# --- Compress --------------------------------------------------------------------

def _common(values: list):
    """Deep part shared by all values (dicts: keys in all, recursively), or a
    sentinel when there is none."""
    if all(isinstance(v, dict) for v in values):
        out = {}
        for k in values[0]:
            if all(k in v for v in values):
                c = _common([v[k] for v in values])
                if c is not _NONE:
                    out[k] = c
        return out
    return values[0] if all(v == values[0] for v in values) else _NONE


_NONE = object()


def _diff(value: dict, common: dict) -> dict:
    out = {}
    for k, v in value.items():
        if k not in common:
            out[k] = v
        elif isinstance(v, dict) and isinstance(common[k], dict):
            d = _diff(v, common[k])
            if d:
                out[k] = d
        elif v != common[k]:
            out[k] = v
    return out


def _templated(obj, name: str):
    """Strings equal to the entry name -> "{name}"."""
    if isinstance(obj, str):
        return "{name}" if obj == name else obj
    if isinstance(obj, list):
        return [_templated(x, name) for x in obj]
    if isinstance(obj, dict):
        return {k: _templated(v, name) for k, v in obj.items()}
    return obj


def factor(entries: dict, group_by: str | None = None) -> dict:
    """Entries -> families of the entries sharing entry[group_by] (all of them
    when None); groups of one stay plain. Members keep only what differs."""
    groups: dict = {}
    for name, e in entries.items():
        groups.setdefault(e.get(group_by) if group_by else "all", []).append(name)
    prefix = os.path.commonprefix(list(entries)) if len(entries) > 1 else ""
    prefix = prefix[:prefix.rfind("_") + 1] if "_" in prefix else ""
    out: dict = {}
    for gname, names in groups.items():
        if len(names) == 1:
            out[names[0]] = entries[names[0]]
            continue
        tmpl = {n: _templated(entries[n], n) for n in names}
        common = _common(list(tmpl.values()))
        fam = {"@name": prefix + "{key}" if prefix else "{key}",
               "@members": {n[len(prefix):]: ({"@set": d} if (d := _diff(tmpl[n], common)) else {})
                            for n in names}}
        out[str(gname)] = {**fam, **common}
    return out


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=False)


def _ref_name(path: list, value, taken: set) -> str:
    """'tool:rule' for a DRC message 'tool:text (rule)', else the key it sits
    under (parent.key, then #n when taken)."""
    if isinstance(value, str):
        m = re.match(r"(\w+):.*\(([^()]+)\)\s*$", value)
        cands = [f"{m.group(1)}:{m.group(2)}" if m else value[:24].strip()]
    else:
        cands = [str(path[-1]), ".".join(str(p) for p in path[-2:])]
    for c in cands:
        if c not in taken:
            return c
    i = 2
    while f"{cands[-1]}#{i}" in taken:
        i += 1
    return f"{cands[-1]}#{i}"


def _big(obj) -> bool:
    if isinstance(obj, str) and obj.startswith("@"):
        return False
    s = _json(obj)
    big = (isinstance(obj, (dict, list)) and len(s) >= HOIST_MIN_CHARS) or \
          (isinstance(obj, str) and len(s) >= STRING_MIN_CHARS)
    return big and not _VAR.search(s)    # refs are resolved after member vars: no templates inside


def _inner(obj, out: dict) -> dict:
    """Big subtrees strictly inside obj -> count."""
    kids = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    for x in kids:
        if _big(x):
            out[_json(x)] = out.get(_json(x), 0) + 1
        _inner(x, out)
    return out


def hoist(tree: dict, refs: dict) -> dict:
    """Repeated subtrees and long strings -> "@name" (added to refs); values
    equal to an existing ref -> that ref."""
    by_value = {_json(v): n for n, v in refs.items()}
    count: dict = {}
    first_path: dict = {}

    def scan(obj, path):
        if _big(obj):
            s = _json(obj)
            count[s] = count.get(s, 0) + 1
            first_path.setdefault(s, path)
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not k.startswith("@"):
                    scan(v, path + [k])
                elif k == "@members":           # a member's data is its @set (repl hoists there too)
                    for mk, mv in v.items():
                        for mk2, mv2 in mv.items():
                            if mk2 == "@set" or not mk2.startswith("@"):
                                scan(mv2, path + [mk])
        elif isinstance(obj, list):
            for x in obj:
                scan(x, path)

    scan(tree, [])
    taken = set(refs)
    for s in sorted(count, key=len, reverse=True):     # largest first
        n = count[s]
        if n > 1 and s not in by_value:
            name = _ref_name(first_path[s], json.loads(s), taken)
            taken.add(name)
            by_value[s] = name
            refs[name] = json.loads(s)
            for inner, k in _inner(json.loads(s), {}).items():
                if inner in count:                     # scan skips directive values (@name, ...)
                    count[inner] -= k * (n - 1)        # now written once, inside the ref

    def repl(obj, top=False):
        s = _json(obj)
        if not top and s in by_value and not (isinstance(obj, str) and obj.startswith("@")):
            return "@" + by_value[s]
        if isinstance(obj, dict):
            return {k: repl(v) if not k.startswith("@") or k == "@members" or k == "@set" else v
                    for k, v in obj.items()}
        if isinstance(obj, list):
            return [repl(x) for x in obj]
        return obj

    out = repl(tree, top=True)
    # refs may repeat each other's parts: hoist inside them too (never themselves)
    for name in list(refs):
        own = by_value.pop(_json(refs[name]))
        refs[name] = repl(refs[name], top=True)
        by_value[_json(json.loads(_json(refs[name])))] = own
    return out


def compress(plain: dict, refs: dict, factor_sections: dict) -> dict:
    """plain -> tree. refs: given names (e.g. layers) reused wherever their value
    occurs; factor_sections: {section: group_by key or None} turned into families.
    Raises if the tree does not expand back to plain."""
    tree = {k: (factor(v, factor_sections[k]) if k in factor_sections else v) for k, v in plain.items()}
    refs = copy.deepcopy(refs)
    tree = hoist(tree, refs)
    used = _used_refs(tree, refs)
    out = {"@refs": {n: v for n, v in refs.items() if n in used}, **tree} if used else tree
    if expand(out) != plain:
        raise AssertionError("pdk_tree.compress: tree does not expand back to the input")
    return out


def _used_refs(tree, refs: dict) -> set:
    used: set = set()

    def visit(obj):
        if isinstance(obj, str) and obj.startswith("@") and obj[1:] in refs and obj[1:] not in used:
            used.add(obj[1:])
            visit(refs[obj[1:]])
        elif isinstance(obj, dict):
            for v in obj.values():
                visit(v)
        elif isinstance(obj, list):
            for x in obj:
                visit(x)

    visit(tree)
    return used


# --- Output --------------------------------------------------------------------

def dumps(obj, indent: int = 0, lead: int = 0) -> str:
    """JSON with every value that fits in LINE_WIDTH on one line (lead: chars
    already on the line before the value)."""
    one = _json(obj)
    if lead + len(one) <= LINE_WIDTH or not isinstance(obj, (dict, list)) or not obj:
        return one
    ind = indent + INDENT
    pad = " " * ind
    if isinstance(obj, dict):
        items = [f"{pad}{_json(k)}: {dumps(v, ind, ind + len(_json(k)) + 2)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"
    items = [pad + dumps(x, ind, ind) for x in obj]
    return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
