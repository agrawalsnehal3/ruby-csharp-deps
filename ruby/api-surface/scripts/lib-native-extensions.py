"""Ruby methods defined from native code, whatever language that code is in.

rubycount.extract_c only recognises C, which was never a principled choice --
it is what the original counter happened to support. The criterion that
actually matters is not the file's language but whether the code *registers a
Ruby method*. That splits the languages three ways:

  C / C++   rb_define_method(...)         -- registers.  counted.
  Rust      class.define_method("x", ..)  -- registers.  counted (was missed).
  Go        ships a compiled binary       -- does NOT register. correctly ignored:
                                             lefthook shells out to an exe, so
                                             there is no Ruby method in the Go.
  Java      @JRubyMethod                  -- registers, but only under JRuby, so
                                             the method does not exist on CRuby.
                                             Off by default; --jruby to include.

Scope is captured, which extract_c does not do
----------------------------------------------
extract_c matches the class argument but throws it away, so every C method
lands in one bucket called "(c-ext)". Two genuinely different methods --

    rb_define_method(cNokogiriXmlNode,     "children", ...)
    rb_define_method(cNokogiriXmlDocument, "children", ...)

-- collapse to a single "(c-ext)#children" and one of them is lost. That is 42
of nokogiri's 205 native methods, and 249 of openssl's 791. Capturing the first
argument keeps them apart, and has the second benefit of letting a native
method collide with its Ruby definition when they really are the same method,
which is the deduplication that never happened before.

The C variable name is not the Ruby class name -- cNokogiriXmlNode is not
Nokogiri::XML::Node -- so scopes here are identifiers, not resolved constants.
They separate methods reliably, which is what counting needs; they are not
suitable for display as Ruby class names.
"""
from __future__ import annotations

import re

# --- C / C++ ---------------------------------------------------------------
# Group 1 = which rb_define_* was called, 2 = the class/module argument,
# 3 = the Ruby method name. The class argument is the part extract_c drops.
C_DEF = re.compile(
    r"\brb_define_(method|singleton_method|module_function|global_function|"
    r"private_method|protected_method|alias|attr|method_id)\s*\(\s*"
    r"([^,()]*?)\s*,\s*\"([^\"]+)\"", re.S)
C_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)

# --- Rust (magnus / rb-sys) ------------------------------------------------
# receiver.define_method("name", ...) and its singleton/module variants.
RUST_DEF = re.compile(
    r"(?:([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?define_"
    r"(method|singleton_method|module_function|private_method)\s*\(\s*"
    r"\"([^\"]+)\"")
RUST_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)

# --- Java (JRuby) ----------------------------------------------------------
JAVA_DEF = re.compile(
    r"@JRubyMethod\s*(?:\([^)]*\bname\s*=\s*\{?\s*\"([^\"]+)\"[^)]*\))?"
    r"[^{;]*?\b(?:public|protected|private)?[^{;]*?\b(\w+)\s*\(", re.S)

SINGLETON_KINDS = {"singleton_method", "module_function", "global_function"}
EXT = {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp",
       ".hpp": "cpp", ".rs": "rust", ".java": "java"}


def language_of(path):
    low = path.lower()
    for ext, lang in EXT.items():
        if low.endswith(ext):
            return lang
    return ""


def extract_native(src: bytes, path: str, jruby: bool = False):
    """(functions, language). Same record shape as rubycount.extract()."""
    lang = language_of(path)
    if not lang or (lang == "java" and not jruby):
        return [], lang
    text = src.decode("utf8", "replace")
    out = []

    def add(name, scope, kind, pos):
        sep = "." if kind in SINGLETON_KINDS or kind.endswith("singleton_method") else "#"
        sc = scope or "(native)"
        out.append(dict(name=name, kind="native_" + kind, scope=sc,
                        sig=sc + sep + name, file=path,
                        line=text[:pos].count("\n") + 1, end_line=0, loc=0,
                        language=lang))

    if lang in ("c", "cpp"):
        clean = C_COMMENT.sub("", text)
        for m in C_DEF.finditer(clean):
            add(m.group(3), m.group(2).strip() or None, m.group(1), m.start())
    elif lang == "rust":
        clean = RUST_COMMENT.sub("", text)
        for m in RUST_DEF.finditer(clean):
            add(m.group(3), m.group(1), m.group(2), m.start())
    elif lang == "java":
        for m in JAVA_DEF.finditer(text):
            add(m.group(1) or m.group(2), None, "method", m.start())
    return out, lang


if __name__ == "__main__":                     # quick self-check
    import gzip, io, ssl, sys, tarfile, urllib.request, collections
    ctx = ssl.create_default_context()

    def gem(n, v):
        u = "https://rubygems.org/downloads/" + n + "-" + v + ".gem"
        raw = urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "census/1.0"}),
            timeout=90, context=ctx).read()
        with tarfile.open(fileobj=io.BytesIO(raw)) as o:
            return gzip.decompress(o.extractfile("data.tar.gz").read())

    sys.path.append(r"c:\Users\agraw\OneDrive\Desktop\experiment\ruby-fn-census")
    from rubycount import extract_c
    for name, ver in [("nokogiri", "1.19.4"), ("openssl", "3.3.2"),
                      ("commonmarker", "2.10.0")]:
        data = gem(name, ver)
        new, old, langs = [], [], collections.Counter()
        with tarfile.open(fileobj=io.BytesIO(data)) as inner:
            for mem in inner.getmembers():
                if not mem.isfile():
                    continue
                lang = language_of(mem.name)
                if not lang:
                    continue
                src = inner.extractfile(mem).read()
                fns, _ = extract_native(src, mem.name)
                new += fns
                langs[lang] += 1
                if lang in ("c", "cpp"):
                    old += extract_c(src, mem.name)[0]
        print(name.ljust(14), dict(langs))
        print("   old extract_c : raw", len(old), " unique", len({f["sig"] for f in old}))
        print("   new           : raw", len(new), " unique", len({f["sig"] for f in new}))
