"""Top-200 repos by stars and by forks, with their dependency lists.

Extends the hand-built top-100 files to 200 per ranking, using the same source
they came from: GitHub's dependency-graph SBOM endpoint. That was confirmed
rather than assumed -- /repos/rails/rails/dependency-graph/sbom returns 1,084
packages against the 1,084 in Ruby_top100_stars.csv, with the same '^0.20.2'
constraint format. Anything else (the REST dependency listing, manifest
parsing) yields a different set, and mixing sources across ranks 1-100 and
101-200 would make the union incoherent.

One thing this adds that the originals dropped: the SPDX externalRefs carry a
purl, so every package arrives labelled with its real ecosystem (pkg:gem/,
pkg:nuget/, pkg:npm/). The originals kept only 'name@version', which is why
filtering them needs a name-match against the registry and lets npm packages
that happen to share a gem name through. Both are written -- ecosystem for the
clean answer, and the raw name so the old and new rows stay comparable.

Repos are re-fetched for ranks 1-100 too. One extra request each, and it means
the whole 200 comes from one snapshot rather than two.

Writes out/top200_<lang>_<ranking>.csv   -- one row per repo
       out/top200_deps_<lang>.csv        -- one row per (repo, package)
"""
from __future__ import annotations

import csv
import os
import sys
import time
import urllib.parse

from census.core import GITHUB_API, OUT_DIR, fetch_json, gh_headers, log

LANGS = {"ruby": "Ruby", "nuget": "C#"}
N = 200


def search(lang, sort):
    """Top N repos for a language by stars or forks, 100 per page."""
    out, q = [], urllib.parse.quote(f"language:{lang}", safe="")
    for page in (1, 2):
        url = (f"{GITHUB_API}/search/repositories?q={q}&sort={sort}"
               f"&order=desc&per_page=100&page={page}")
        for it in fetch_json(url, gh_headers(), use_cache=False).get("items", []):
            out.append({"repository": it["full_name"], "stars": it["stargazers_count"],
                        "forks": it["forks_count"], "url": it["html_url"]})
        time.sleep(2.2)          # search is 30/min; two pages a list is fine
    return out[:N]


def sbom(repo):
    """(packages, status). packages are (name, version, ecosystem)."""
    try:
        s = fetch_json(f"{GITHUB_API}/repos/{repo}/dependency-graph/sbom",
                       gh_headers(), use_cache=True)
    except Exception as exc:                       # 404 = graph off/empty
        return [], f"unavailable:{type(exc).__name__}"
    pk = (s.get("sbom") or {}).get("packages") or []
    rows = []
    for p in pk:
        nm = (p.get("name") or "").strip()
        if not nm or nm.lower().startswith("com.github."):
            continue                               # the repo's own root node
        eco = ""
        for ref in p.get("externalRefs") or []:
            loc = ref.get("referenceLocator") or ""
            if loc.startswith("pkg:"):
                eco = loc[4:].split("/", 1)[0].lower()
                break
        rows.append((nm, p.get("versionInfo") or "", eco))
    return rows, "available"


def main():
    for reg, lang in LANGS.items():
        seen, lists = {}, {}
        for sort in ("stars", "forks"):
            lists[sort] = search(lang, sort)
            log(f"{reg}/{sort}: {len(lists[sort])} repos")
        for sort, rows in lists.items():
            for r in rows:
                seen.setdefault(r["repository"], r)

        deps, status = {}, {}
        for i, repo in enumerate(seen, 1):
            pk, st = sbom(repo)
            deps[repo], status[repo] = pk, st
            if i % 25 == 0 or i == len(seen):
                log(f"  {reg}: sbom {i}/{len(seen)}")

        dp = os.path.join(OUT_DIR, f"top200_deps_{reg}.csv")
        with open(dp, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["repository", "package", "version", "ecosystem"])
            for repo, pk in deps.items():
                for nm, ver, eco in pk:
                    w.writerow([repo, nm, ver, eco])

        for sort, rows in lists.items():
            p = os.path.join(OUT_DIR, f"top200_{reg}_{sort}.csv")
            with open(p, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["rank", "repository", "stars", "forks",
                            "dependency_status", "dependency_count"])
                for i, r in enumerate(rows, 1):
                    w.writerow([i, r["repository"], r["stars"], r["forks"],
                                status[r["repository"]],
                                len(deps[r["repository"]])])
            ok = sum(1 for r in rows if status[r["repository"]] == "available")
            log(f"  -> {os.path.basename(p)}  ({ok}/{len(rows)} resolved)")
        log(f"  -> {os.path.basename(dp)}  ({sum(len(v) for v in deps.values()):,} rows)")


if __name__ == "__main__":
    sys.exit(main())
