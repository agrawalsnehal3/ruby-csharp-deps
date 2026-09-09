"""Direct dependencies per repository, and the union used for selection.

The dependency-graph SBOM lists every package a repository resolves to, which
is direct and transitive flattened together. Taking the package list at face
value therefore answers the wrong question: for rails/rails it returns 1,084
packages where only 338 are actually declared, and for dotnet/runtime 740
where only 300 are.

The distinction is recoverable from the SBOM itself. Alongside `packages` it
carries a `relationships` graph, and one edge type matters:

    DESCRIBES   the document -> the repository's own root node
    DEPENDS_ON  edges between packages

A dependency is DIRECT when the edge starts at the root node. Everything else
is something a dependency pulled in. That needs no extra requests -- the SBOMs
are already cached from the earlier fetch.

The union then combines three selections, all restricted to packages that
exist in the registry being studied:

    stars   direct dependencies of the top-N repos by stars
    forks   direct dependencies of the top-N repos by forks
    downloads   the smallest set of packages covering 90% of registry downloads

Writes out/final/2_dependencies/<registry>_direct_dependencies.csv
       out/final/3_union/<registry>_union.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import numpy as np
import pandas as pd

from census.core import GITHUB_API, OUT_DIR, fetch_json, gh_headers, log

FINAL = os.path.join(OUT_DIR, "final")
ECO = {"ruby": "gem", "csharp": "nuget"}
FRAME = {"ruby": "frame_ruby.csv", "csharp": "frame_nuget.csv"}
LISTS = {"ruby": ("top200_ruby_stars.csv", "top200_ruby_forks.csv"),
         "csharp": ("top200_nuget_stars.csv", "top200_nuget_forks.csv")}


def direct_deps(repo):
    """[(name, version, ecosystem)] declared by this repo, transitive excluded."""
    try:
        sbom = fetch_json(GITHUB_API + "/repos/" + repo
                          + "/dependency-graph/sbom", gh_headers(),
                          use_cache=True)["sbom"]
    except Exception as exc:
        return None, "unavailable:" + type(exc).__name__

    by_id = {p["SPDXID"]: p for p in sbom.get("packages") or []}
    rels = sbom.get("relationships") or []
    root = next((r["relatedSpdxElement"] for r in rels
                 if r.get("relationshipType") == "DESCRIBES"), None)
    if root is None:
        return None, "no_root"

    out = []
    for r in rels:
        if r.get("relationshipType") != "DEPENDS_ON":
            continue
        if r.get("spdxElementId") != root:      # transitive: skip
            continue
        p = by_id.get(r.get("relatedSpdxElement"))
        if not p:
            continue
        name = (p.get("name") or "").strip()
        if not name or name.lower().startswith("com.github."):
            continue
        eco = ""
        for ref in p.get("externalRefs") or []:
            loc = ref.get("referenceLocator") or ""
            if loc.startswith("pkg:"):
                eco = loc[4:].split("/", 1)[0].lower()
                break
        out.append((name, p.get("versionInfo") or "", eco))
    return out, "ok"


def coverage_set(frame_path, target=90.0):
    """Smallest set of packages reaching target% of registry downloads."""
    d = pd.read_csv(frame_path, low_memory=False, usecols=["name", "downloads"])
    d = d[d["name"].notna()].drop_duplicates("name")
    d["downloads"] = pd.to_numeric(d["downloads"], errors="coerce")
    live = d[d["downloads"] > 0].sort_values(["downloads", "name"],
                                             ascending=[False, True])
    c = np.cumsum(live["downloads"].values)
    n = int(np.searchsorted(c, target / 100 * c[-1], side="left") + 1)
    return set(live.head(n)["name"].str.lower()), live, n


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100,
                    help="how many repos from each ranking (default 100)")
    ap.add_argument("--target", type=float, default=90.0)
    a = ap.parse_args(argv)

    for d in ("1_repos", "2_dependencies", "3_union"):
        os.makedirs(os.path.join(FINAL, d), exist_ok=True)

    for reg in ("ruby", "csharp"):
        eco = ECO[reg]
        frame = os.path.join(OUT_DIR, FRAME[reg])
        universe_df = pd.read_csv(frame, low_memory=False, usecols=["name"])
        universe = set(universe_df["name"].dropna().astype(str).str.lower())

        rows, per_repo, sets = [], [], {}
        for sort, fn in zip(("stars", "forks"), LISTS[reg]):
            listing = pd.read_csv(os.path.join(OUT_DIR, fn)).head(a.top)
            listing.to_csv(os.path.join(
                FINAL, "1_repos", reg + "_top" + str(a.top) + "_" + sort
                + ".csv"), index=False)
            found = set()
            for r in listing.itertuples():
                deps, status = direct_deps(r.repository)
                n_direct = 0 if deps is None else len(deps)
                in_eco = 0
                for name, ver, e in (deps or []):
                    if e == eco:
                        in_eco += 1
                        rows.append(dict(repository=r.repository, ranking=sort,
                                         package=name, version=ver,
                                         ecosystem=e))
                        if name.lower() in universe:
                            found.add(name.lower())
                per_repo.append(dict(repository=r.repository, ranking=sort,
                                     status=status, direct_deps=n_direct,
                                     direct_in_ecosystem=in_eco))
            sets[sort] = found
            log(reg + "/" + sort + ": " + str(len(found))
                + " distinct direct " + eco + " packages")

        dep_path = os.path.join(FINAL, "2_dependencies",
                                reg + "_direct_dependencies.csv")
        pd.DataFrame(rows).drop_duplicates().to_csv(dep_path, index=False)
        pd.DataFrame(per_repo).to_csv(
            os.path.join(FINAL, "2_dependencies",
                         reg + "_repo_summary.csv"), index=False)

        cov, live, ncut = coverage_set(frame, a.target)
        union = sets["stars"] | sets["forks"] | cov
        log(reg + ": coverage cut " + str(ncut) + ", union " + str(len(union)))

        live["key"] = live["name"].str.lower()
        info = live.drop_duplicates("key").set_index("key")
        u = pd.DataFrame({"package": sorted(union)})
        u["downloads"] = u.package.map(info["downloads"])
        u["registry_name"] = u.package.map(info["name"])
        u["in_stars"] = u.package.isin(sets["stars"])
        u["in_forks"] = u.package.isin(sets["forks"])
        dl_col = "in_downloads_" + str(int(a.target)) + "pct"
        u[dl_col] = u.package.isin(cov)
        # name the column rather than indexing by position: adding a column
        # earlier silently shifted iloc and inverted a string
        u["sources"] = ["+".join(s for s, f in
                                 (("stars", a1), ("forks", b1), ("downloads", c1))
                                 if f)
                        for a1, b1, c1 in zip(u.in_stars, u.in_forks, u[dl_col])]
        u = u.sort_values("downloads", ascending=False, na_position="last")
        u.to_csv(os.path.join(FINAL, "3_union", reg + "_union.csv"),
                 index=False)

        log(reg + " union written: " + str(len(u)) + " packages")
        log("   " + str(u.sources.value_counts().to_dict()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
