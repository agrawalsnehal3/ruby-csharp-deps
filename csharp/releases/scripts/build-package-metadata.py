"""Per-package inventory: every published version, the repository, and the
documentation that actually exists.

Two files per registry, because they answer different questions and one of
them is long:

    <reg>_versions.csv    one row per (package, version) -- the full mapping.
                          Some packages have thousands of versions, so this
                          cannot be a cell inside the other file.
    <reg>_inventory.csv   one row per package -- counts, links, and what
                          documentation is present.

Documentation is reported as three separate things, because they are not
interchangeable:

    doc_site_url    an external site, when one is published
    readme_file     the README shipped inside the package
    docs_folder     files under docs/ or guides/ inside the package, listed

The distinction matters: a published documentation URL is frequently just
rubydoc.info, which generates a page from the package's own source whether or
not anyone wrote a word. A shipped README or docs/ folder is content that
exists by definition.

Version lists are the only network cost -- one request per package, cached, so
a re-run is free. Everything else comes from the gem cache and from scans
already on disk.

Writes out/final/7_inventory/<reg>_versions.csv
       out/final/7_inventory/<reg>_inventory.csv
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import re
import sys
import tarfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from census.core import CACHE_DIR, OUT_DIR, SSL_CONTEXT, USER_AGENT, log

FINAL = os.path.join(OUT_DIR, "final")
OUTDIR = os.path.join(FINAL, "7_inventory")
SRC = os.path.join(OUT_DIR, "third_party_method_count_latest")
GEM_CACHE = os.path.join(SRC, "_gem_cache")
VER_CACHE = os.path.join(CACHE_DIR, "versions")
DOCDIR = re.compile(r"(^|/)(docs?|documentation|guides?|manual)/", re.I)
README = re.compile(r"^(?:[^/]+/)?readme", re.I)


def _cached(key, fetch):
    """Version lists never shrink, but they do grow -- cache anyway and let a
    stale entry be refreshed by deleting the file rather than by expiry."""
    os.makedirs(VER_CACHE, exist_ok=True)
    p = os.path.join(VER_CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", key) + ".json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    val = fetch()
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(val, fh)
    os.replace(tmp, p)
    return val


def _get(url):
    rq = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(rq, timeout=60, context=SSL_CONTEXT) as r:
        return r.read()


def ruby_versions(gem):
    def go():
        try:
            raw = _get("https://rubygems.org/api/v1/versions/" + gem + ".json")
        except Exception as exc:
            return {"error": type(exc).__name__}
        return [{"version": v.get("number"), "released": (v.get("created_at") or "")[:10],
                 "platform": v.get("platform") or "ruby",
                 "prerelease": bool(v.get("prerelease"))}
                for v in json.loads(raw.decode("utf8", "replace"))]
    return _cached("gem_" + gem, go)


def nuget_versions(pkg):
    low = pkg.lower()

    def go():
        try:
            raw = _get("https://api.nuget.org/v3-flatcontainer/" + low
                       + "/index.json")
        except Exception as exc:
            return {"error": type(exc).__name__}
        return [{"version": v, "released": "", "platform": "",
                 "prerelease": "-" in v}
                for v in json.loads(raw.decode()).get("versions", [])]
    return _cached("nuget_" + low, go)


def gem_doc_files(stem):
    """(readme path, [docs/ files]) from the cached .gem."""
    p = os.path.join(GEM_CACHE, stem + ".gem")
    if not os.path.exists(p):
        return "", []
    try:
        with open(p, "rb") as fh:
            raw = fh.read()
        with tarfile.open(fileobj=io.BytesIO(raw)) as outer:
            payload = gzip.decompress(outer.extractfile("data.tar.gz").read())
        readme, docs = "", []
        with tarfile.open(fileobj=io.BytesIO(payload)) as inner:
            for m in inner.getmembers():
                if not m.isfile():
                    continue
                if README.match(m.name) and not readme:
                    readme = m.name
                if DOCDIR.search(m.name):
                    docs.append(m.name)
        return readme, docs
    except Exception:
        return "", []


def build_ruby(limit=0):
    u = pd.read_csv(os.path.join(FINAL, "3_union", "ruby_union.csv"))
    names = u["registry_name"].fillna(u["package"]).astype(str).tolist()
    if limit:
        names = names[:limit]
    log("ruby: " + str(len(names)) + " packages")

    with ThreadPoolExecutor(max_workers=12) as pool:
        vers = list(pool.map(ruby_versions, names))

    fr = pd.read_csv(os.path.join(OUT_DIR, "frame_ruby.csv"), low_memory=False,
                     usecols=["name", "downloads", "repo_owner", "repo_name"])
    fr["key"] = fr["name"].astype(str).str.lower()
    fr = fr.drop_duplicates("key").set_index("key")

    links = {}
    for p in (os.path.join(SRC, "ruby_doc_links.xlsx"),):
        if os.path.exists(p):
            try:
                t = pd.read_excel(p, "all_gems")
                links = dict(zip(t.gem.astype(str).str.lower(),
                                 t.best_doc_url.fillna("")))
            except Exception:
                pass

    api = pd.read_csv(os.path.join(SRC, "ruby_api_v2_versions.csv"),
                      low_memory=False)
    api = api[api.status == "ok"]
    cur = dict(zip(api.gem.astype(str).str.lower(), api.version.astype(str)))

    vrows, irows = [], []
    for name, vs in zip(names, vers):
        k = name.lower()
        if isinstance(vs, dict):
            stable = []
            err = vs.get("error", "")
        else:
            err = ""
            stable = [v for v in vs if not v["prerelease"]]
            for v in vs:
                vrows.append(dict(package=name, version=v["version"],
                                  released=v["released"],
                                  platform=v["platform"],
                                  prerelease=v["prerelease"]))
        latest = cur.get(k, stable[0]["version"] if stable else "")
        readme, docs = gem_doc_files(name + "-" + latest) if latest else ("", [])
        row = fr.loc[k] if k in fr.index else None
        owner = row["repo_owner"] if row is not None else None
        rname = row["repo_name"] if row is not None else None
        gh = ("https://github.com/" + str(owner) + "/" + str(rname)
              if pd.notna(owner) and pd.notna(rname) else "")
        irows.append(dict(
            registry="rubygems", package=name,
            downloads=row["downloads"] if row is not None else None,
            latest_version=latest,
            version_count=len(vs) if not isinstance(vs, dict) else 0,
            stable_version_count=len(stable),
            first_release=stable[-1]["released"] if stable else "",
            latest_release=stable[0]["released"] if stable else "",
            github_url=gh,
            registry_url="https://rubygems.org/gems/" + name,
            doc_site_url=links.get(k, ""),
            readme_file=readme,
            has_readme="Yes" if readme else "No",
            docs_folder_count=len(docs),
            docs_folder_files="; ".join(docs[:40]),
            error=err))
    return pd.DataFrame(vrows), pd.DataFrame(irows)


def build_csharp(limit=0):
    u = pd.read_csv(os.path.join(FINAL, "3_union", "csharp_union.csv"))
    names = u["registry_name"].fillna(u["package"]).astype(str).tolist()
    if limit:
        names = names[:limit]
    log("csharp: " + str(len(names)) + " packages")

    with ThreadPoolExecutor(max_workers=16) as pool:
        vers = list(pool.map(nuget_versions, names))

    fr = pd.read_csv(os.path.join(OUT_DIR, "frame_nuget.csv"), low_memory=False,
                     usecols=["name", "downloads", "repo_owner", "repo_name"])
    fr["key"] = fr["name"].astype(str).str.lower()
    fr = fr.drop_duplicates("key").set_index("key")

    pg = pd.read_csv(os.path.join(OUT_DIR, "nuget_pages.csv"), low_memory=False,
                     usecols=["package", "project_url"]).drop_duplicates("package")
    site = dict(zip(pg.package.astype(str).str.lower(),
                    pg.project_url.fillna("")))

    docs = {}
    p = os.path.join(SRC, "_nuget_docs_scan.csv")
    if os.path.exists(p):
        t = pd.read_csv(p, low_memory=False)
        docs = {r.package.lower(): (r.readme if isinstance(r.readme, str) else "",
                                    r.xml_doc if isinstance(r.xml_doc, str) else "")
                for r in t.itertuples()}

    vrows, irows = [], []
    for name, vs in zip(names, vers):
        k = name.lower()
        if isinstance(vs, dict):
            stable, err = [], vs.get("error", "")
        else:
            err = ""
            stable = [v for v in vs if not v["prerelease"]]
            for v in vs:
                vrows.append(dict(package=name, version=v["version"],
                                  released="", platform="",
                                  prerelease=v["prerelease"]))
        latest = (stable or vs or [{}])[-1].get("version", "") if not isinstance(vs, dict) else ""
        readme, xml = docs.get(k, ("", ""))
        row = fr.loc[k] if k in fr.index else None
        owner = row["repo_owner"] if row is not None else None
        rname = row["repo_name"] if row is not None else None
        gh = ("https://github.com/" + str(owner) + "/" + str(rname)
              if pd.notna(owner) and pd.notna(rname) else "")
        irows.append(dict(
            registry="nuget", package=name,
            downloads=row["downloads"] if row is not None else None,
            latest_version=latest,
            version_count=len(vs) if not isinstance(vs, dict) else 0,
            stable_version_count=len(stable),
            first_release="", latest_release="",
            github_url=gh,
            registry_url="https://www.nuget.org/packages/" + name,
            doc_site_url=site.get(k, ""),
            readme_file=readme,
            has_readme="Yes" if readme else "No",
            xml_doc_file=xml,
            has_xml_docs="Yes" if xml else "No",
            error=err))
    return pd.DataFrame(vrows), pd.DataFrame(irows)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(OUTDIR, exist_ok=True)

    for reg, fn in (("ruby", build_ruby), ("csharp", build_csharp)):
        v, i = fn(a.limit)
        v.to_csv(os.path.join(OUTDIR, reg + "_versions.csv"), index=False)
        i.to_csv(os.path.join(OUTDIR, reg + "_inventory.csv"), index=False)
        log(reg + ": " + str(len(i)) + " packages, " + str(len(v))
            + " version rows")
        log("   github link " + str(int((i.github_url != "").sum()))
            + " | doc site " + str(int((i.doc_site_url != "").sum()))
            + " | readme " + str(int((i.has_readme == "Yes").sum())))
        if "docs_folder_count" in i.columns:
            log("   docs/ folder " + str(int((i.docs_folder_count > 0).sum())))
        if "has_xml_docs" in i.columns:
            log("   xml docs " + str(int((i.has_xml_docs == "Yes").sum())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
