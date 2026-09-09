"""Write the ruby/ and csharp/ READMEs with the findings in them.

A folder listing tells you where things are; it does not tell you what they
say. These READMEs carry the actual tables -- selection, overlap, API size,
documentation, storage -- so the top level of each language answers the
questions without opening a single CSV.

Everything is computed from the files themselves, so the numbers cannot drift
away from the data they describe.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                    "Third_party_packages")
NAME = {"ruby": "RubyGems", "csharp": "NuGet"}


def _n(x, dp=0):
    try:
        return f"{float(x):,.{dp}f}"
    except (TypeError, ValueError):
        return str(x)


def _read(lang, *parts):
    p = os.path.join(ROOT, lang, *parts)
    return pd.read_csv(p, low_memory=False) if os.path.exists(p) else None


def selection_block(lang):
    sel = _read(lang, "package-selection", "selected-packages.csv")
    ov = _read(lang, "package-selection", "selection-overlap.csv")
    if sel is None:
        return []
    src = sel.sources.value_counts()
    rows = ["## Which packages were selected", "",
            "Three signals, combined. A package qualifies if any one of them "
            "picks it.", "",
            "| Signal | Packages |", "|---|---|"]
    if ov is not None:
        sizes = ov[ov.set_b.isna() | (ov.set_b == "")]
        for r in sizes.itertuples():
            if str(r.set_a).startswith("all three"):
                continue
            rows.append("| " + str(r.set_a) + " | " + _n(r.size_a) + " |")
    rows += ["| **Union — the studied set** | **" + _n(len(sel)) + "** |", ""]

    rows += ["### Where each package came from", "",
             "| Signals that picked it | Packages | Share |", "|---|---|---|"]
    for k, v in src.items():
        rows.append("| " + str(k).replace("+", " + ") + " | " + _n(v) + " | "
                    + f"{100 * v / len(sel):.1f}%" + " |")
    rows.append("")

    if ov is not None:
        pairs = ov[ov.set_b.notna() & (ov.set_b != "")]
        rows += ["### How much the signals agree", "",
                 "Jaccard = shared ÷ combined. 1.0 would mean identical sets.",
                 "",
                 "| Pair | Shared | Combined | Jaccard |", "|---|---|---|---|"]
        for r in pairs.itertuples():
            label = (str(r.set_a) + " ↔ " + str(r.set_b)
                     if str(r.set_a) != "all three" else "all three")
            rows.append("| " + label + " | " + _n(r.in_both) + " | "
                        + _n(r.in_either) + " | **" + f"{r.jaccard:.2f}" + "** |")
        rows += ["",
                 "No pair is close to 1.0, so no signal is redundant — that is "
                 "the reason for combining all three rather than picking one. "
                 "Downloads measure what machines install; stars and forks "
                 "measure what people write.", ""]
    return rows


def api_block(lang):
    d = _read(lang, "api-surface", "api-method-counts.csv")
    if d is None:
        return []
    ok = d[d.status == "ok"]
    rows = ["## How large the APIs are", ""]
    if lang == "ruby":
        tot = ok.functions.sum()
        rows += ["| Measure | Count | Share |", "|---|---|---|",
                 "| Methods, all visibilities | " + _n(tot) + " | 100% |",
                 "| — public | **" + _n(ok.functions_public.sum()) + "** | "
                 + f"{100 * ok.functions_public.sum() / tot:.1f}%" + " |",
                 "| — private | " + _n(ok.functions_private.sum()) + " | "
                 + f"{100 * ok.functions_private.sum() / tot:.1f}%" + " |",
                 "| — protected | " + _n(ok.functions_protected.sum()) + " | "
                 + f"{100 * ok.functions_protected.sum() / tot:.1f}%" + " |",
                 "| Defined in C, C++ or Rust | "
                 + _n(ok.functions_native.sum()) + " | "
                 + f"{100 * ok.functions_native.sum() / tot:.1f}%" + " |", "",
                 "| | |", "|---|---|",
                 "| Gems counted | " + _n(len(ok)) + " of " + _n(len(d)) + " |",
                 "| Median methods per gem | " + _n(ok.functions.median()) + " |",
                 "| Mean methods per gem | " + _n(ok.functions.mean(), 1) + " |",
                 "| Largest | " + _n(ok.functions.max()) + " ("
                 + str(ok.loc[ok.functions.idxmax(), "gem"]) + ") |",
                 "| Gems with native extensions | "
                 + _n((ok.native_files > 0).sum()) + " |", "",
                 "> Counts are a **lower bound**. `method_missing` and "
                 "`define_method` with a computed name cannot be seen by a "
                 "parser.", ""]
    else:
        rows += ["| Measure | Count |", "|---|---|",
                 "| Public methods | **" + _n(ok.methods_public.sum()) + "** |",
                 "| Properties | " + _n(ok.properties.sum())
                 + " (counted once, not get+set) |",
                 "| Events | " + _n(ok.events.sum()) + " |",
                 "| **API members total** | **" + _n(ok.api_total.sum())
                 + "** |",
                 "| Constructors | " + _n(ok.ctors.sum())
                 + " (reported separately) |",
                 "| Operators | " + _n(ok.operators.sum())
                 + " (reported separately) |",
                 "| Every method incl. private | "
                 + _n(ok.methoddef_rows.sum()) + " |", "",
                 "| | |", "|---|---|",
                 "| Packages counted | " + _n(len(ok)) + " of " + _n(len(d))
                 + " |",
                 "| Median API members | " + _n(ok.api_total.median()) + " |",
                 "| Largest | " + _n(ok.api_total.max()) + " ("
                 + str(ok.loc[ok.api_total.idxmax(), "package"]) + ") |", ""]
        st = d[d.status != "ok"].status.value_counts()
        if len(st):
            rows += ["### Packages with no countable API", "",
                     "These are real zeros, not failures — they ship no "
                     "callable managed code.", "",
                     "| Reason | Packages |", "|---|---|"]
            for k, v in st.items():
                rows.append("| " + str(k) + " | " + _n(v) + " |")
            rows.append("")
    return rows


def docs_block(lang):
    d = _read(lang, "documentation", "documentation.csv")
    if d is None:
        return []
    n = len(d)

    def has(c):
        return int((d[c].fillna("").astype(str).str.strip() != "").sum()) \
            if c in d.columns else 0

    rows = ["## Documentation", "",
            "### What each package has", "",
            "| Source | Packages | Share |", "|---|---|---|"]
    for col, label in (("handwritten_site", "A site someone wrote"),
                       ("tool_generated_docs", "Tool-generated page (rubydoc.info)"),
                       ("readme_in_package", "README inside the package"),
                       ("xml_docs_in_package", "XML doc file inside the package"),
                       ("docs_folder_in_package", "docs/ folder inside the package"),
                       ("github_wiki", "GitHub wiki"),
                       ("homepage", "Homepage")):
        c = has(col)
        if c:
            rows.append("| " + label + " | " + _n(c) + " | "
                        + f"{100 * c / n:.1f}%" + " |")
    rows.append("")

    if "doc_coverage_pct" in d.columns:
        cov = pd.to_numeric(d.doc_coverage_pct, errors="coerce")
        # C# has no per-method denominator: the compiler records what was
        # written and nothing about what was not, so these columns are absent
        mt = (pd.to_numeric(d["methods_total"], errors="coerce")
              if "methods_total" in d.columns else None)
        md = (pd.to_numeric(d["methods_documented"], errors="coerce")
              if "methods_documented" in d.columns else None)
        rows += ["### How much is actually written", "",
                 "A method counts as documented when a comment sits directly "
                 "above it.", "", "| | |", "|---|---|"]
        if mt is not None and md is not None and mt.notna().any():
            rows += ["| Methods examined | " + _n(mt.sum()) + " |",
                     "| Methods with a comment | **" + _n(md.sum()) + "** ("
                     + f"{100 * md.sum() / mt.sum():.1f}%" + ") |"]
        if cov.notna().any():
            rows += ["| Median coverage per package | "
                     + f"{cov.median():.1f}%" + " |",
                     "| Packages at 0% | " + _n((cov == 0).sum()) + " |",
                     "| Packages above 80% | " + _n((cov > 80).sum()) + " |"]
        else:
            rows += ["| Coverage percentage | not measurable |"]
        rows += ["",
                 "> A documentation **link** is not evidence of "
                 "documentation. rubydoc.info builds a page for every gem "
                 "automatically, so the page exists whether or not anyone "
                 "wrote a word. `doc_coverage_pct` is the column that means "
                 "something." if lang == "ruby" else
                 "> There is no coverage percentage for C#. The compiler "
                 "records the comments that were written and nothing about "
                 "the members that were not, so there is no denominator to "
                 "divide by.", ""]

    ls = _read(lang, "documentation", "documentation-link-summary.csv")
    if ls is not None and len(ls):
        rows += ["### Do the links still work?", "",
                 "Every distinct URL was fetched once.", "",
                 "| Link type | Links | Working | Dead | Dead % |",
                 "|---|---|---|---|---|"]
        for r in ls.itertuples():
            lt = str(getattr(r, "link_type", ""))
            bold = lt == "ALL LINK TYPES"
            f = (lambda x: "**" + x + "**") if bold else (lambda x: x)
            rows.append("| " + f(lt) + " | " + f(_n(r.total_links)) + " | "
                        + f(_n(r.working)) + " | " + f(_n(r.dead)) + " | "
                        + f(f"{r.dead_pct:.1f}%") + " |")
        rows.append("")
    if "has_working_link" in d.columns:
        w = int((d.has_working_link == "Yes").sum())
        rows += ["Packages with at least one working link: **" + _n(w)
                 + "** of " + _n(n) + ".", ""]
    return rows


def storage_block(lang):
    st = _read(lang, "storage-footprint", "storage-summary.csv")
    if st is None:
        return []
    keep = ["TOTAL download size (GB)", "mean package size (KB)",
            "median package size (KB)", "largest package (MB)",
            "versions published in total", "mean versions per package",
            "ESTIMATED size of all versions (GB)",
            "actually downloaded (MB)", "saving vs full download"]
    rows = ["## What it costs to download", "", "| | | |", "|---|---|---|"]
    for r in st.itertuples():
        m = str(r.metric).strip()
        if m in keep:
            note = "" if pd.isna(r.note) else str(r.note)
            rows.append("| " + m + " | **" + str(r.value) + "** | "
                        + note[:70] + " |")
    rows.append("")
    return rows


FOLDERS = [
    ("repositories", "The GitHub projects the study starts from"),
    ("dependencies", "What those projects declare they depend on"),
    ("package-selection", "The packages studied, and why each was included"),
    ("api-surface", "How many methods each package exposes"),
    ("documentation", "Whether each package is documented, and where"),
    ("releases", "Every published version, with repository and registry links"),
    ("storage-footprint", "Bytes required to fetch the set"),
]


def build(lang):
    sel = _read(lang, "package-selection", "selected-packages.csv")
    head = [
        "# " + NAME[lang] + " packages", "",
        "**" + _n(len(sel)) + " packages** selected from the 100 most-starred "
        "and 100 most-forked " + ("Ruby" if lang == "ruby" else "C#")
        + " repositories on GitHub, plus the packages covering 90% of all "
        + NAME[lang] + " downloads.", "",
        "---", ""]
    body = (selection_block(lang) + ["---", ""] + api_block(lang)
            + ["---", ""] + docs_block(lang) + ["---", ""]
            + storage_block(lang) + ["---", ""])
    tail = ["## Folders", "",
            "| Folder | What it answers |", "|---|---|"]
    for f, q in FOLDERS:
        if os.path.isdir(os.path.join(ROOT, lang, f)):
            tail.append("| [`" + f + "`](" + f + "/) | " + q + " |")
    other = "csharp" if lang == "ruby" else "ruby"
    tail += ["",
             "Each folder holds its data, a `scripts/` subfolder with the code "
             "that produced it, and a README explaining both.", "",
             "The same folders exist in [`" + other + "/`](../" + other
             + "/) and answer the same questions for that language. Every "
             "column is described in [`docs/data-dictionary.md`]"
             "(../docs/data-dictionary.md).", ""]
    return "\n".join(head + body + tail)


def main():
    for lang in ("ruby", "csharp"):
        p = os.path.join(ROOT, lang, "README.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(build(lang))
        print("wrote", p, "(" + str(round(os.path.getsize(p) / 1024, 1)) + " KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
