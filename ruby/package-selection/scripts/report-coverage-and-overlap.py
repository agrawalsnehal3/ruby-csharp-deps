"""Four reports that sit alongside the main pipeline.

  download-coverage-90pct.xlsx   the packages accounting for 90% of downloads
  download-coverage-95pct.xlsx   the same at 95%, as a separate file because
                                 the two are used for different purposes and
                                 mixing them in one workbook invites reading
                                 the wrong column
  selection-overlap-jaccard.xlsx how much the three selections actually agree
  package-sizes.xlsx             per-package bytes and the total to download

The Jaccard workbook is the one worth reading first. It is the justification
for using three selections rather than one: stars and forks agree strongly
with each other (they are both "what people write"), but neither agrees much
with downloads ("what machines install"). If any pair were near 1.0, that
selection would be redundant.

Writes into the Third_party_packages tree directly.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from census.core import OUT_DIR

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                    "Third_party_packages")
SRC = os.path.join(OUT_DIR, "third_party_method_count_latest")
FINAL = os.path.join(OUT_DIR, "final")
FRAME = {"ruby": "frame_ruby.csv", "csharp": "frame_nuget.csv"}
S3 = "package-selection"
S7 = "storage-footprint"
HDR = {"bold": True, "bg_color": "#1f3a5f", "font_color": "white", "border": 1}


def _xl(path, sheets, widths=()):
    try:
        w = pd.ExcelWriter(path, engine="xlsxwriter")
    except Exception:
        path = path.replace(".xlsx", "_live.xlsx")
        w = pd.ExcelWriter(path, engine="xlsxwriter")
    with w:
        hdr = w.book.add_format(HDR)
        num = w.book.add_format({"num_format": "#,##0"})
        for name, t in sheets.items():
            t.to_excel(w, sheet_name=name[:31], index=False)
            ws = w.sheets[name[:31]]
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, max(len(t), 1), max(len(t.columns) - 1, 0))
            for i, c in enumerate(t.columns):
                wide = str(c) in widths
                ws.set_column(i, i, 46 if wide else 18,
                              num if any(k in str(c) for k in
                                         ("download", "bytes", "size", "count",
                                          "packages", "value"))
                              else None)
                ws.write(0, i, str(c), hdr)
    return path


def ranked(reg):
    d = pd.read_csv(os.path.join(OUT_DIR, FRAME[reg]), low_memory=False,
                    usecols=["name", "downloads"])
    d = d[d["name"].notna()].drop_duplicates("name")
    d["downloads"] = pd.to_numeric(d["downloads"], errors="coerce")
    live = d[d["downloads"] > 0].sort_values(["downloads", "name"],
                                             ascending=[False, True]).copy()
    live["rank"] = range(1, len(live) + 1)
    c = np.cumsum(live["downloads"].values)
    live["cumulative_downloads"] = c
    live["cumulative_share_pct"] = (100 * c / c[-1]).round(4)
    return live


def coverage_report(reg, target):
    """The packages reaching target% of downloads, plus how the curve behaves."""
    live = ranked(reg)
    total = live["downloads"].sum()
    n = int(np.searchsorted(live["cumulative_downloads"].values,
                            target / 100 * total, side="left") + 1)
    cut = live.head(n).copy()

    curve = []
    for t in (10, 25, 50, 75, 80, 85, 90, 95, 99, 99.9):
        k = int(np.searchsorted(live["cumulative_downloads"].values,
                                t / 100 * total, side="left") + 1)
        curve.append({"target_pct": t, "packages_needed": k,
                      "share_of_all_packages_pct": round(100 * k / len(live), 4)})

    summary = pd.DataFrame([
        ("registry", reg, ""),
        ("target", str(target) + "% of all downloads", ""),
        ("packages needed", n,
         str(round(100 * n / len(live), 3)) + "% of the registry"),
        ("downloads covered", int(cut["downloads"].sum()),
         str(round(100 * cut["downloads"].sum() / total, 3)) + "%"),
        ("packages in registry (downloads > 0)", len(live), ""),
        ("total registry downloads", int(total), ""),
        ("", "", ""),
        ("most downloaded", cut.iloc[0]["name"], int(cut.iloc[0]["downloads"])),
        ("least downloaded in this set", cut.iloc[-1]["name"],
         int(cut.iloc[-1]["downloads"])),
    ], columns=["metric", "value", "note"])

    return {"summary": summary,
            "packages": cut[["rank", "name", "downloads",
                             "cumulative_downloads", "cumulative_share_pct"]],
            "how_the_curve_behaves": pd.DataFrame(curve)}, n


def jaccard(reg):
    """Agreement between the three selections."""
    u = pd.read_csv(os.path.join(FINAL, "3_union", reg + "_union.csv"))
    dl_col = [c for c in u.columns if c.startswith("in_downloads")][0]
    sets = {"stars": set(u.loc[u.in_stars, "package"]),
            "forks": set(u.loc[u.in_forks, "package"]),
            "downloads": set(u.loc[u[dl_col], "package"])}

    rows = []
    for a in ("stars", "forks", "downloads"):
        for b in ("stars", "forks", "downloads"):
            if a >= b:
                continue
            A, B = sets[a], sets[b]
            inter, union = len(A & B), len(A | B)
            rows.append({
                "set_a": a, "set_b": b, "size_a": len(A), "size_b": len(B),
                "in_both": inter, "in_either": union,
                "jaccard": round(inter / union, 4) if union else 0,
                "pct_of_a_also_in_b": round(100 * inter / len(A), 1) if A else 0,
                "pct_of_b_also_in_a": round(100 * inter / len(B), 1) if B else 0,
            })
    three = sets["stars"] & sets["forks"] & sets["downloads"]
    allu = sets["stars"] | sets["forks"] | sets["downloads"]
    rows.append({"set_a": "all three", "set_b": "", "size_a": len(allu),
                 "size_b": "", "in_both": len(three), "in_either": len(allu),
                 "jaccard": round(len(three) / len(allu), 4) if allu else 0,
                 "pct_of_a_also_in_b": "", "pct_of_b_also_in_a": ""})

    breakdown = (u["sources"].value_counts().rename_axis("came_from")
                 .reset_index(name="packages"))
    breakdown["share_pct"] = (100 * breakdown.packages
                              / breakdown.packages.sum()).round(1)
    return pd.DataFrame(rows), breakdown, sets


def sizes(reg):
    """Bytes per package and what a full download would cost."""
    if reg == "ruby":
        d = pd.read_csv(os.path.join(SRC, "ruby_api_v2_versions.csv"),
                        low_memory=False)
        d = d[d.status == "ok"][["gem", "version", "gem_bytes"]]
        d = d.rename(columns={"gem": "package", "gem_bytes": "bytes"})
        note = "size of the published .gem"
    else:
        d = pd.read_csv(os.path.join(SRC, "_nuget_docs_scan.csv"),
                        low_memory=False)
        d = d[d.status == "ok"][["package", "version", "nupkg_bytes",
                                 "xml_bytes", "bytes_read"]]
        d = d.rename(columns={"nupkg_bytes": "bytes"})
        note = "size of the published .nupkg"

    u = pd.read_csv(os.path.join(FINAL, "3_union", reg + "_union.csv"))
    keep = set(u["registry_name"].fillna(u["package"]).astype(str).str.lower())
    d = d[d["package"].astype(str).str.lower().isin(keep)].copy()
    d["bytes"] = pd.to_numeric(d["bytes"], errors="coerce")
    d["size_mb"] = (d["bytes"] / 1e6).round(3)

    # every published version, estimated as version_count x latest size.
    # An estimate, and a high one: packages grow over time, so early versions
    # are smaller than the latest. Treat it as a ceiling, not a measurement.
    inv = os.path.join(FINAL, "7_inventory", reg + "_inventory.csv")
    if os.path.exists(inv):
        iv = pd.read_csv(inv, low_memory=False,
                         usecols=["package", "version_count",
                                  "stable_version_count"])
        iv["key"] = iv["package"].astype(str).str.lower()
        iv = iv.drop_duplicates("key").set_index("key")
        k = d["package"].astype(str).str.lower()
        d["version_count"] = k.map(iv["version_count"]).fillna(1).astype(int)
        d["stable_versions"] = k.map(iv["stable_version_count"]).fillna(1).astype(int)
        d["all_versions_bytes_est"] = d["bytes"] * d["version_count"]
        d["all_versions_gb_est"] = (d["all_versions_bytes_est"] / 1e9).round(4)
    d = d.sort_values("bytes", ascending=False)

    b = d["bytes"].dropna()
    rows = [
        ("registry", reg, note),
        ("packages", len(d), ""),
        ("", "", ""),
        ("TOTAL download size (GB)", round(b.sum() / 1e9, 2),
         "every package at its current version"),
        ("TOTAL download size (MB)", round(b.sum() / 1e6, 1), ""),
        ("", "", ""),
        ("mean package size (KB)", round(b.mean() / 1024), ""),
        ("median package size (KB)", round(b.median() / 1024), ""),
        ("90th percentile (KB)", round(b.quantile(0.9) / 1024), ""),
        ("largest package (MB)", round(b.max() / 1e6, 1),
         str(d.iloc[0]["package"])),
        ("smallest package (KB)", round(b.min() / 1024, 1), ""),
    ]
    if "all_versions_bytes_est" in d.columns:
        av = d["all_versions_bytes_est"].dropna()
        vc = d["version_count"]
        rows += [
            ("", "", ""),
            ("--- EVERY PUBLISHED VERSION ---", "", ""),
            ("versions published in total", int(vc.sum()),
             "sum of version_count across all packages"),
            ("mean versions per package", round(float(vc.mean()), 1), ""),
            ("median versions per package", int(vc.median()), ""),
            ("most versions", int(vc.max()),
             str(d.loc[vc.idxmax(), "package"]) if len(vc) else ""),
            ("ESTIMATED size of all versions (GB)", round(av.sum() / 1e9, 1),
             "version_count x latest size -- an over-estimate, since packages "
             "grow and older versions are smaller"),
            ("  vs latest-version-only (GB)", round(b.sum() / 1e9, 2),
             str(round(av.sum() / max(b.sum(), 1), 1)) + "x larger"),
            ("largest by all-versions estimate (GB)",
             round(av.max() / 1e9, 1),
             str(d.loc[av.idxmax(), "package"]) if len(av) else ""),
        ]
    if reg == "csharp":
        read = pd.to_numeric(d["bytes_read"], errors="coerce").sum()
        rows += [
            ("", "", ""),
            ("actually downloaded (MB)", round(read / 1e6, 1),
             "ranged reads fetch only the zip index and one assembly"),
            ("saving vs full download", str(round(100 * (1 - read / b.sum()), 1))
             + "%", ""),
        ]
    band = pd.cut(b / 1e6, [0, 0.05, 0.1, 0.5, 1, 5, 10, 1e6],
                  labels=["<50 KB", "50-100 KB", "100-500 KB", "0.5-1 MB",
                          "1-5 MB", "5-10 MB", ">10 MB"])
    dist = (band.value_counts().rename_axis("size_band")
            .reset_index(name="packages").sort_values("size_band"))
    return pd.DataFrame(rows, columns=["metric", "value", "note"]), d, dist


def main():
    for lang in ("ruby", "csharp"):
        os.makedirs(os.path.join(ROOT, lang, S3), exist_ok=True)
        os.makedirs(os.path.join(ROOT, lang, S7), exist_ok=True)

        for target in (90, 95):
            sh, n = coverage_report(lang, target)
            p = _xl(os.path.join(ROOT, lang, S3,
                                 "download-coverage-" + str(target) + ".xlsx"),
                    sh, widths=("name", "metric", "note", "value"))
            print(lang, target, "% ->", n, "packages ->", os.path.basename(p))

        # the overlap belongs beside the selection it describes, not only in
        # the cross-language folder -- it is the evidence for using three
        # selections rather than one
        j, b, sets = jaccard(lang)
        note = pd.DataFrame([
            ("What this measures",
             "How much the three selections agree. Jaccard = overlap / union: "
             "1.0 means identical sets, 0 means nothing in common."),
            ("Why it is here",
             "It is the justification for combining three selections instead "
             "of picking one. If two agreed closely, one would be redundant."),
            ("Download selection used",
             "90% of registry downloads. The 95% cut is in "
             "download-coverage-95pct.xlsx for reference and is not part of "
             "the selection."),
            ("What it shows",
             "stars and forks agree strongly -- both measure what people "
             "write. Neither agrees much with downloads, which measures what "
             "machines install, largely as transitive dependencies nobody "
             "names."),
        ], columns=["", "explanation"])
        counts = pd.DataFrame(
            [("stars (direct deps of top-100 by stars)", len(sets["stars"])),
             ("forks (direct deps of top-100 by forks)", len(sets["forks"])),
             ("downloads (90% of registry downloads)", len(sets["downloads"])),
             ("union -- the selected set",
              len(sets["stars"] | sets["forks"] | sets["downloads"])),
             ("in all three", len(sets["stars"] & sets["forks"]
                                  & sets["downloads"]))],
            columns=["selection", "packages"])
        _xl(os.path.join(ROOT, lang, S3, "selection-overlap-analysis.xlsx"),
            {"how_to_read_this": note, "selection_sizes": counts,
             "overlap": j, "where_each_package_came_from": b},
            widths=("explanation", "", "selection", "came_from", "set_a",
                    "set_b"))
        print(lang, "overlap ->", {r.set_a + "/" + r.set_b: r.jaccard
                                   for r in j.itertuples() if r.set_b})

        summ, det, dist = sizes(lang)
        _xl(os.path.join(ROOT, lang, S7, "storage-requirements.xlsx"),
            {"summary": summ, "size_distribution": dist, "per_package": det},
            widths=("metric", "note", "value", "package"))
        print(lang, "sizes ->", summ.iloc[3]["value"], "GB total")

    return 0


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    sys.exit(main())
