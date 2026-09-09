"""Which Ruby methods are public, private or protected.

Visibility in Ruby is not a property of a definition, it is a mode the class
body is in when the definition is reached:

    class Foo
      def a; end      # mode is public
      private         # <- flips the mode
      def b; end      # private
      def c; end      # still private, the mode is sticky
    end               # mode resets in the next class body

So it cannot be read off a method node. The body has to be walked in order,
carrying the mode, resetting at every class/module/singleton_class boundary.

The trap: a bare `private` on its own line parses as an **identifier**, not a
call -- tree-sitter emits `identifier 'private'` sitting between two `method`
nodes. A scan that only inspects call nodes therefore finds almost nothing and
reports a confident ~1.5% private, when the real figure across real gems is
~29%. Both node shapes have to be handled.

Four forms exist, all static:

    private                 bare identifier, flips the mode
    private :name           call with arguments, marks those names only
    private def x; end      call wrapping a method definition
    module_function         like private, but also makes a module-level copy

Rather than re-deriving method names, this returns a line -> visibility map to
be joined against rubycount.extract()'s records, which are already validated.
Two definitions on one line would collide; that is rare enough to accept, and
attr_accessor / define_method inherit the mode at their own line, which is the
correct Ruby semantics.
"""
from __future__ import annotations

import tree_sitter_ruby as tsr
from tree_sitter import Language, Parser

_PARSER = Parser(Language(tsr.language()))

MODES = {b"private": "private", b"protected": "protected", b"public": "public"}
SCOPES = ("class", "module", "singleton_class")
DEFS = ("method", "singleton_method")
# calls that create methods -- they take the mode in force where they appear
GENERATORS = (b"attr_reader", b"attr_writer", b"attr_accessor",
              b"define_method", b"define_singleton_method", b"alias_method")


def visibility_map(src: bytes):
    """{line: visibility} for every definition site, plus module_function lines."""
    tree = _PARSER.parse(src)
    vis, modfunc = {}, set()

    def txt(n):
        return src[n.start_byte:n.end_byte]

    def walk(node, mode, in_modfunc):
        cur, mf = mode, in_modfunc
        for ch in node.children:
            t = ch.type

            # bare `private` / `module_function` -- an identifier, not a call
            if t == "identifier":
                raw = txt(ch)
                if raw in MODES:
                    cur = MODES[raw]
                    continue
                if raw == b"module_function":
                    mf = True
                    continue

            if t == "call":
                mname = ch.child_by_field_name("method")
                nm = txt(mname) if mname else b""
                args = ch.child_by_field_name("arguments")
                has_args = bool(args and args.named_children)

                if nm in MODES and not has_args:
                    cur = MODES[nm]
                    continue
                if nm == b"module_function" and not has_args:
                    mf = True
                    continue
                # private :a, :b  /  private def x; end
                if nm in (b"private", b"protected", b"public") and has_args:
                    for a in args.named_children:
                        if a.type in DEFS:
                            vis[a.start_point[0] + 1] = MODES[nm]
                        elif a.type == "simple_symbol":
                            vis.setdefault(("sym", txt(a).lstrip(b":").decode(
                                "utf8", "replace")), MODES[nm])
                    continue
                if nm in GENERATORS:
                    vis[ch.start_point[0] + 1] = cur
                    continue

            if t in DEFS:
                line = ch.start_point[0] + 1
                vis.setdefault(line, cur)
                if mf:
                    modfunc.add(line)
                walk(ch, "public", False)       # nested defs start fresh
                continue

            if t in SCOPES:
                walk(ch, "public", False)       # mode resets per body
                continue

            walk(ch, cur, mf)

    walk(tree.root_node, "public", False)
    return vis, modfunc


def annotate(funcs, src: bytes):
    """Add a 'visibility' key to rubycount.extract() records, in place."""
    vis, modfunc = visibility_map(src)
    by_name = {k[1]: v for k, v in vis.items() if isinstance(k, tuple)}
    for f in funcs:
        v = vis.get(f.get("line"))
        if v is None:
            v = by_name.get(f.get("name"), "public")
        f["visibility"] = v
        f["module_function"] = f.get("line") in modfunc
    return funcs


if __name__ == "__main__":
    import collections
    import gzip
    import io
    import ssl
    import sys
    import tarfile
    import urllib.request

    sys.path.append(r"c:\Users\agraw\OneDrive\Desktop\experiment\ruby-fn-census")
    from rubycount import extract
    ctx = ssl.create_default_context()

    for gem, ver in [("rake", "13.4.2"), ("rack", "3.2.7"),
                     ("bundler", "4.0.20"), ("aws-sdk-core", "3.254.1")]:
        url = "https://rubygems.org/downloads/" + gem + "-" + ver + ".gem"
        raw = urllib.request.urlopen(urllib.request.Request(
            url, headers={"User-Agent": "census/1.0"}), timeout=90,
            context=ctx).read()
        with tarfile.open(fileobj=io.BytesIO(raw)) as o:
            data = gzip.decompress(o.extractfile("data.tar.gz").read())
        c = collections.Counter()
        with tarfile.open(fileobj=io.BytesIO(data)) as inner:
            for mem in inner.getmembers():
                if mem.isfile() and mem.name.endswith(".rb"):
                    src = inner.extractfile(mem).read()
                    for f in annotate(extract(src, mem.name)[0], src):
                        c[f["visibility"]] += 1
        tot = sum(c.values())
        print(gem.ljust(15), dict(c),
              " non-public", round(100 * (tot - c["public"]) / tot, 1), "%")
