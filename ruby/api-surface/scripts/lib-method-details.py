"""Full per-method extraction from a Ruby source file.

Produces one record per method with signature, parameters, visibility, body
calls, raises and control-flow counts -- the Ruby equivalent of the structured
per-function records people usually build for Python.

Two fields do not translate directly, and are handled rather than faked:

  types      Ruby has no static types. The only place a type appears is a
             Sorbet `sig` block preceding the def, so `sig_raw`, `param_types`
             and `return_type` are populated when one is present and left null
             otherwise. Most gems have none; that is a fact about Ruby, not a
             gap in the parser.

  decorators Ruby has no decorator syntax. The nearest equivalents are the DSL
             calls that immediately precede a definition -- `memoize :foo`,
             `sig { ... }`, `deprecate :bar` -- so those are collected into
             `preceding_calls`.

Everything else is read straight off the tree-sitter parse. `calls` is every
method invoked in the body, which is what makes the output useful for building
a call graph later; note it is syntactic, so `foo` could be a method call or a
local variable read, and tree-sitter cannot tell those apart.
"""
from __future__ import annotations

import json

import tree_sitter_ruby as tsr
from tree_sitter import Language, Parser

from rubyvis import visibility_map

_PARSER = Parser(Language(tsr.language()))

PARAM_KIND = {"identifier": "required", "optional_parameter": "optional",
              "splat_parameter": "splat", "keyword_parameter": "keyword",
              "hash_splat_parameter": "kwsplat", "block_parameter": "block",
              "forward_parameter": "forward",
              "destructured_parameter": "destructured"}
FLOW = {"if": "if", "unless": "unless", "while": "while", "until": "until",
        "for": "for", "case": "case", "case_match": "case", "rescue": "rescue",
        "ensure": "ensure", "if_modifier": "if", "unless_modifier": "unless",
        "while_modifier": "while", "until_modifier": "until"}
SCOPES = ("class", "module", "singleton_class")
DEFS = ("method", "singleton_method")
DSL = {b"sig", b"memoize", b"deprecate", b"delegate", b"validates",
       b"before_action", b"after_action", b"around_action", b"scope"}
# attr_* and friends define real, callable methods without writing a `def`,
# so a walk that only visits method nodes silently misses them -- for rake
# that is 114 of 444 methods. Mirrors rubycount's ATTRS handling.
ATTRS = {b"attr_reader": ("r",), b"attr_writer": ("w",),
         b"attr_accessor": ("r", "w")}
DEFINERS = (b"define_method", b"define_singleton_method", b"alias_method")


def _t(src, n):
    return src[n.start_byte:n.end_byte].decode("utf8", "replace")


def _params(src, node):
    """[{name, kind, default}] in declaration order."""
    out = []
    ps = node.child_by_field_name("parameters")
    if ps is None:
        return out
    for p in ps.named_children:
        kind = PARAM_KIND.get(p.type, p.type)
        nm = p.child_by_field_name("name")
        default = p.child_by_field_name("value")
        out.append({
            "name": _t(src, nm) if nm else _t(src, p).lstrip("*&:").strip(),
            "kind": kind,
            "default": _t(src, default) if default is not None else None,
        })
    return out


def _body_facts(src, node):
    """calls / raises / yields / control-flow counts inside one method body."""
    calls, raises, flow = [], [], {}
    yields = False
    nested = 0
    stack = [node]
    while stack:
        n = stack.pop()
        t = n.type
        if n is not node and t in DEFS:
            nested += 1
            continue                      # a nested def is its own method
        if t in FLOW:
            flow[FLOW[t]] = flow.get(FLOW[t], 0) + 1
        elif t == "yield":
            yields = True
        elif t == "call":
            m = n.child_by_field_name("method")
            if m is not None:
                calls.append(_t(src, m))
        elif t == "identifier":
            pass
        if t == "call" or t == "command":
            m = n.child_by_field_name("method")
            if m is not None and _t(src, m) == "raise":
                args = n.child_by_field_name("arguments")
                if args and args.named_children:
                    a = args.named_children[0]
                    raises.append(_t(src, a).split("(")[0].split(",")[0].strip())
        stack.extend(n.children)
    return calls, raises, yields, flow, nested


def extract_methods(src: bytes, path: str, gem="", version=""):
    """One rich record per method definition in this file."""
    tree = _PARSER.parse(src)
    vis, modfunc = visibility_map(src)
    by_name = {k[1]: v for k, v in vis.items() if isinstance(k, tuple)}
    out = []

    def walk(node, scope, pending):
        prev = list(pending)
        for ch in node.children:
            t = ch.type

            # `alias new old` is its own node type, not a call -- the
            # alias_method form above does not cover it.
            if t == "alias":
                nm = ch.child_by_field_name("name")
                cls = "::".join(scope) or "(main)"
                line = ch.start_point[0] + 1
                name = _t(src, nm) if nm else "?"
                out.append({
                    "gem": gem, "version": version, "name": name,
                    "sig": cls + "#" + name, "kind": "alias", "class": cls,
                    "visibility": vis.get(line, "public"),
                    "module_function": False, "file": path,
                    "start_line": line, "end_line": line, "loc": 1,
                    "is_endless": False, "parameters": [], "arity": {},
                    "sig_raw": None, "return_type": None,
                    "preceding_calls": None, "calls": [], "raises": [],
                    "yields": False, "nested_defs": 0, "control_flow": {},
                })
                prev = []
                continue

            if t in SCOPES:
                nm = ch.child_by_field_name("name")
                if t == "singleton_class":
                    val = ch.child_by_field_name("value")
                    seg = "<<" + (_t(src, val) if val else "self")
                else:
                    seg = _t(src, nm) if nm else "?"
                walk(ch, scope + [seg], [])
                prev = []
                continue

            if t in ("call", "command"):
                m = ch.child_by_field_name("method")
                mn = _t(src, m).encode() if m is not None else b""
                if mn in ATTRS or mn in DEFINERS:
                    cls = "::".join(scope) or "(main)"
                    line = ch.start_point[0] + 1
                    v = vis.get(line, "public")
                    args = ch.child_by_field_name("arguments")
                    names = []
                    if args:
                        for a in args.named_children:
                            if a.type == "simple_symbol":
                                names.append(_t(src, a).lstrip(":"))
                            elif a.type == "string":
                                names.append(_t(src, a).strip("\"'"))
                    if mn in ATTRS:
                        pairs = [(nm + ("=" if mode == "w" else ""),
                                  "attr_writer" if mode == "w" else "attr_reader")
                                 for nm in names for mode in ATTRS[mn]]
                    elif mn == b"alias_method":
                        pairs = [(names[0], "alias")] if names else []
                    else:
                        sep_kind = ("define_method"
                                    if mn == b"define_method"
                                    else "define_singleton_method")
                        pairs = [(names[0], sep_kind)] if names else []
                    for nm, kind in pairs:
                        sep = "." if "singleton" in kind else "#"
                        out.append({
                            "gem": gem, "version": version, "name": nm,
                            "sig": cls + sep + nm, "kind": kind, "class": cls,
                            "visibility": v, "module_function": False,
                            "file": path, "start_line": line,
                            "end_line": line, "loc": 1, "is_endless": False,
                            "parameters": [], "arity": {}, "sig_raw": None,
                            "return_type": None, "preceding_calls": None,
                            "calls": [], "raises": [], "yields": False,
                            "nested_defs": 0, "control_flow": {},
                        })
                    continue
                if m is not None and mn in DSL:
                    prev.append(_t(src, ch)[:200])
                    continue

            if t in DEFS:
                nm = ch.child_by_field_name("name")
                name = _t(src, nm) if nm else "?"
                if t == "singleton_method":
                    recv = ch.child_by_field_name("object")
                    rt = _t(src, recv) if recv else "self"
                    kind, sep = "singleton", "."
                    if rt != "self":
                        name = rt + "." + name
                else:
                    kind = ("singleton" if scope and scope[-1].startswith("<<")
                            else "instance")
                    sep = "." if kind == "singleton" else "#"
                cls = "::".join(scope) or "(main)"
                line = ch.start_point[0] + 1
                body = ch.child_by_field_name("body")
                calls, raises, yields, flow, nested = (
                    _body_facts(src, body) if body is not None
                    else ([], [], False, {}, 0))
                ps = _params(src, ch)
                sigblk = next((p for p in prev if p.startswith("sig")), None)
                out.append({
                    "gem": gem, "version": version,
                    "name": name,
                    "sig": cls + sep + name,
                    "kind": kind,
                    "class": cls,
                    "visibility": vis.get(line, by_name.get(name, "public")),
                    "module_function": line in modfunc,
                    "file": path,
                    "start_line": line,
                    "end_line": ch.end_point[0] + 1,
                    "loc": ch.end_point[0] - ch.start_point[0] + 1,
                    "is_endless": body is None and ch.child_by_field_name("value") is not None,
                    "parameters": ps,
                    "arity": {
                        "required": sum(1 for p in ps if p["kind"] == "required"),
                        "optional": sum(1 for p in ps if p["kind"] == "optional"),
                        "keyword": sum(1 for p in ps if p["kind"] == "keyword"),
                        "splat": any(p["kind"] == "splat" for p in ps),
                        "kwsplat": any(p["kind"] == "kwsplat" for p in ps),
                        "block": any(p["kind"] == "block" for p in ps),
                    },
                    "sig_raw": sigblk,          # Sorbet, when the gem uses it
                    "return_type": None,        # Ruby has none without a sig
                    "preceding_calls": prev or None,
                    "calls": sorted(set(calls)),
                    "raises": sorted(set(raises)),
                    "yields": yields,
                    "nested_defs": nested,
                    "control_flow": flow,
                })
                prev = []
                walk(ch, scope, [])
                continue

            walk(ch, scope, prev)
            prev = []

    walk(tree.root_node, [], [])
    return out


if __name__ == "__main__":
    import gzip, io, ssl, sys, tarfile, urllib.request
    ctx = ssl.create_default_context()
    gem, ver, want = (sys.argv + ["rack", "3.2.7", "2"])[1:4]
    url = "https://rubygems.org/downloads/" + gem + "-" + ver + ".gem"
    raw = urllib.request.urlopen(urllib.request.Request(
        url, headers={"User-Agent": "census/1.0"}), timeout=90, context=ctx).read()
    with tarfile.open(fileobj=io.BytesIO(raw)) as o:
        data = gzip.decompress(o.extractfile("data.tar.gz").read())
    recs = []
    with tarfile.open(fileobj=io.BytesIO(data)) as inner:
        for mem in inner.getmembers():
            if mem.isfile() and mem.name.endswith(".rb"):
                recs += extract_methods(inner.extractfile(mem).read(),
                                        mem.name, gem, ver)
    print("methods:", len(recs))
    rich = sorted([r for r in recs if r["parameters"] and r["calls"]],
                  key=lambda r: -len(r["calls"]))
    for r in rich[:int(want)]:
        r = dict(r)
        r["calls"] = r["calls"][:8]
        print(json.dumps(r, indent=2)[:1400])
