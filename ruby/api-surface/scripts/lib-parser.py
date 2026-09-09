"""Count Ruby functions + lines from a real AST (tree-sitter), not regex."""
import re, tree_sitter_ruby as tsr
from tree_sitter import Language, Parser

LANG = Language(tsr.language())
_parser = Parser(LANG)

# call-sites that generate real, callable methods
ATTRS = {"attr_reader": ("r",), "attr_writer": ("w",), "attr_accessor": ("r", "w")}
SCOPE_NODES = {"class", "module", "singleton_class"}


def _txt(src, n):
    return src[n.start_byte:n.end_byte].decode("utf8", "replace") if n else "?"


def _sym_args(src, call):
    """Symbol literals passed to a call: attr_accessor :a, :b -> ['a','b']"""
    args = call.child_by_field_name("arguments")
    out = []
    if not args:
        return out
    for c in args.named_children:
        if c.type == "simple_symbol":
            out.append(_txt(src, c).lstrip(":"))
        elif c.type == "string":            # define_method("foo")
            out.append(_txt(src, c).strip("\"'"))
    return out


def extract(src: bytes, path: str):
    """-> (functions, metrics). Each function is a dict with a version-stable sig."""
    tree = _parser.parse(src)
    funcs = []

    def visit(node, scope):
        t = node.type

        if t in SCOPE_NODES:
            nm = node.child_by_field_name("name")
            if t == "singleton_class":
                val = node.child_by_field_name("value")
                seg = "<<" + (_txt(src, val) if val else "self")
            else:
                seg = _txt(src, nm)
            inner = scope + [seg]
            for c in node.children:
                visit(c, inner)
            return

        if t in ("method", "singleton_method"):
            nm = _txt(src, node.child_by_field_name("name"))
            if t == "singleton_method":
                recv = _txt(src, node.child_by_field_name("object"))
                kind, sep = "singleton", "."
                nm = nm if recv == "self" else f"{recv}.{nm}"
            else:
                # a def inside `class << X` is effectively a singleton method
                kind = "singleton" if scope and scope[-1].startswith("<<") else "instance"
                sep = "." if kind == "singleton" else "#"
            funcs.append(dict(
                name=nm, kind=kind, scope="::".join(scope) or "(main)",
                sig=f"{'::'.join(scope) or '(main)'}{sep}{nm}",
                file=path, line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                loc=node.end_point[0] - node.start_point[0] + 1,
            ))
            for c in node.children:          # nested defs are legal Ruby
                visit(c, scope)
            return

        if t == "call":
            mname = _txt(src, node.child_by_field_name("method"))
            sc = "::".join(scope) or "(main)"
            base = dict(file=path, line=node.start_point[0] + 1,
                        end_line=node.start_point[0] + 1, loc=1,
                        scope=sc, kind="generated")
            if mname in ATTRS:
                for s in _sym_args(src, node):
                    for mode in ATTRS[mname]:
                        n2 = s + ("=" if mode == "w" else "")
                        funcs.append({**base, "name": n2, "sig": f"{sc}#{n2}",
                                      "kind": f"attr_{'writer' if mode=='w' else 'reader'}"})
            elif mname in ("define_method", "define_singleton_method"):
                for s in _sym_args(src, node)[:1]:
                    sep = "." if mname.endswith("singleton_method") else "#"
                    funcs.append({**base, "name": s, "sig": f"{sc}{sep}{s}",
                                  "kind": "define_method"})
            elif mname == "alias_method":
                a = _sym_args(src, node)
                if a:
                    funcs.append({**base, "name": a[0], "sig": f"{sc}#{a[0]}",
                                  "kind": "alias"})

        if t == "alias":                      # `alias new old`
            nm = _txt(src, node.child_by_field_name("name"))
            sc = "::".join(scope) or "(main)"
            funcs.append(dict(name=nm, kind="alias", scope=sc, sig=f"{sc}#{nm}",
                              file=path, line=node.start_point[0] + 1,
                              end_line=node.start_point[0] + 1, loc=1))

        for c in node.children:
            visit(c, scope)

    visit(tree.root_node, [])
    return funcs, _lines(src) | {"parse_error": tree.root_node.has_error}


def _lines(src: bytes):
    total = blank = comment = 0
    in_block = False
    for raw in src.split(b"\n"):
        total += 1
        s = raw.strip()
        if s.startswith(b"=begin"):
            in_block = True
        if in_block:
            comment += 1
            if s.startswith(b"=end"):
                in_block = False
            continue
        if not s:
            blank += 1
        elif s.startswith(b"#"):
            comment += 1
    return {"lines_total": total, "lines_blank": blank,
            "lines_comment": comment, "lines_code": total - blank - comment}


# ---- C extensions: Ruby-visible methods defined from C -------------------
C_DEF = re.compile(
    r'\brb_define_(method|singleton_method|module_function|global_function|'
    r'private_method|protected_method|alias|attr|method_id)\s*\('
    r'[^,()]*,\s*"([^"]+)"', re.S)
C_COMMENT = re.compile(rb'/\*.*?\*/|//[^\n]*', re.S)


def extract_c(src: bytes, path: str):
    clean = C_COMMENT.sub(b"", src).decode("utf8", "replace")
    funcs = []
    for m in C_DEF.finditer(clean):
        kind = m.group(1)
        sep = "." if "singleton" in kind or "module_function" in kind or "global" in kind else "#"
        funcs.append(dict(name=m.group(2), kind=f"c_{kind}", scope="(c-ext)",
                          sig=f"(c-ext){sep}{m.group(2)}", file=path,
                          line=clean[:m.start()].count("\n") + 1, end_line=0, loc=0))
    return funcs, _lines(src)
