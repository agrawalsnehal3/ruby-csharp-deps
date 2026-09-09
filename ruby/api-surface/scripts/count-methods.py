"""Public-method census per gem, counted from the published .gem.

The artifact is the right unit here rather than a git checkout: it is what the
version actually shipped, it excludes tests by construction, and it exists for
the gems that publish no repository at all -- 146 of the 2,816 in the union
list, which a clone-based census cannot reach.

A .gem is a tar whose payload is a nested data.tar.gz, so unwrapping is two
passes. Both Ruby sources and C extensions are counted: a gem like nokogiri
defines much of its surface from C via rb_define_method, and ignoring that
would report it as nearly empty.

Versions
--------
Default is the current version only -- one fetch per gem, about ten minutes
for the whole list. The machinery for multi-version diffing is here because
counting every published version is 209,418 fetches and roughly two hours for
this list (sorbet-static alone has 13,325, nearly all platform builds of the
same code), so it is opt-in rather than the default:

    latest  current version only            (default)
    minor   latest patch of each major.minor
    major   latest of each major
    all     every version
    N       the N most recent

When more than one version is selected, consecutive versions are diffed as set
differences over method signatures: added / removed / net, plus running_total
reconciled against a fresh full count. A nonzero `drift` means the diff chain
disagrees with the direct count and that row should not be trusted. With the
default single version those columns are simply the full count and zero.

Output is append-only and keyed by gem, so an interrupted run resumes by
reading back what it already wrote.

Writes out/third_party_method_count_latest/ruby_api_versions.csv  -- one row per (gem, version)
       out/third_party_method_count_latest/ruby_api_summary.csv   -- one row per gem
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import re
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

# census/ has no __init__.py, so it is only a namespace package -- and a
# regular module found later on sys.path outranks a namespace portion.
# ruby-fn-census/census.py is exactly such a module, so this import has to
# happen BEFORE that directory joins the path or it silently wins.
from census.core import OUT_DIR, SSL_CONTEXT, USER_AGENT, log  # noqa: E402

sys.path.append(r"c:\Users\agraw\OneDrive\Desktop\experiment\ruby-fn-census")
from rubycount import extract                                 # noqa: E402

import rubynative                                             # noqa: E402
from rubyvis import annotate                                  # noqa: E402

# Results live in their own folder rather than loose in out/, which already
# holds the registry harvests. Created on import so a fresh clone can run
# without a setup step.
API_DIR = os.path.join(OUT_DIR, "third_party_method_count_latest")
os.makedirs(API_DIR, exist_ok=True)

API = "https://rubygems.org/api/v1"
DL = "https://rubygems.org/downloads"
WORKERS = 12                    # rubygems.org is a shared service; be polite
SKIP_DIR = re.compile(r"(^|/)(test|tests|spec|specs|benchmark|benchmarks|"
                      r"sample|samples|example|examples|doc|docs|fixtures?|"
                      r"vendor)(/|$)")
# A bare "232" is a legal gem version -- github-pages numbers its releases
# that way -- so the minor and patch parts have to be optional or every
# version of such a gem is filtered out and the gem looks like it has none.
SEMVER = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?")
# Native languages are selected by whether they register Ruby methods, not by
# popularity: C/C++ via rb_define_*, Rust via magnus. Go is excluded on purpose
# -- a bundled Go binary is a subprocess, not an extension, so it defines no
# Ruby method to count. See rubynative.py.
SRC_EXT = tuple(rubynative.EXT)
VER_FIELDS = ["gem", "version", "released", "status", "gem_bytes", "rb_files",
              "native_files", "functions", "functions_ruby", "functions_native",
              "functions_public", "functions_private", "functions_protected",
              "functions_module_function", "native_languages",
              "lines_code", "lines_total", "parse_errors",
              "added", "removed", "net", "running_total", "drift"]
_lock = threading.Lock()


def fetch(url, tries=3):
    """GET with retry. 404 is final -- a missing version will not appear."""
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(rq, timeout=60, context=SSL_CONTEXT) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 or i == tries - 1:
                raise
        except Exception:
            if i == tries - 1:
                raise
        time.sleep(2 ** i)
    raise RuntimeError("unreachable")


def version_list(gem):
    """[(version, released, platform)], prereleases and bad numbers dropped.

    platform matters for the download URL. A java- or linux-only gem has no
    <gem>-<version>.gem at all; its artifact is <gem>-<version>-java.gem, and
    asking for the plain name gets a 403 rather than a 404. Where a version
    ships for several platforms, prefer the portable "ruby" build.
    """
    raw = fetch(API + "/versions/" + gem + ".json")
    best = {}
    for v in json.loads(raw.decode("utf8", "replace")):
        num = v.get("number", "")
        if v.get("prerelease") or not SEMVER.match(num):
            continue
        plat = v.get("platform") or "ruby"
        if num not in best or plat == "ruby":
            best[num] = (num, (v.get("created_at") or "")[:10], plat)
    return list(best.values())


def _key(v):
    m = SEMVER.match(v)
    return tuple(int(x or 0) for x in m.groups()) if m else (0, 0, 0)


def select(vers, policy):
    """Version numbers to count, oldest first."""
    ordered = sorted({v[0] for v in vers}, key=_key)
    if not ordered:
        return []
    if policy == "all":
        return ordered
    if policy == "latest":
        return ordered[-1:]
    if policy.isdigit():
        return ordered[-int(policy):]
    n = 2 if policy == "minor" else 1
    best = {}
    for v in ordered:
        best[_key(v)[:n]] = v        # ascending, so the last write wins
    return [best[k] for k in sorted(best)]


def api_of(gem, version, platform="ruby"):
    """(signature set, stats) for one published version.

    Visibility is resolved per definition site rather than assumed public, and
    native methods come from rubynative, which keeps the declaring class so two
    same-named methods on different classes stay distinct.
    """
    stem = gem + "-" + version + ("" if platform == "ruby" else "-" + platform)
    raw = fetch(DL + "/" + stem + ".gem")
    sigs = {}
    langs = set()
    st = dict(gem_bytes=len(raw), rb_files=0, native_files=0, functions_ruby=0,
              functions_native=0, functions_public=0, functions_private=0,
              functions_protected=0, functions_module_function=0,
              lines_code=0, lines_total=0, parse_errors=0)
    with tarfile.open(fileobj=io.BytesIO(raw)) as outer:
        member = outer.extractfile("data.tar.gz")
        if member is None:
            return sigs, st
        payload = gzip.decompress(member.read())
    with tarfile.open(fileobj=io.BytesIO(payload)) as inner:
        for mem in inner.getmembers():
            if not mem.isfile() or SKIP_DIR.search(mem.name):
                continue
            low = mem.name.lower()
            is_rb = low.endswith(".rb")
            if not (is_rb or rubynative.language_of(mem.name)):
                continue
            fh = inner.extractfile(mem)
            if fh is None:
                continue
            src = fh.read()
            if is_rb:
                fns, met = extract(src, mem.name)
                fns = annotate(fns, src)
                st["rb_files"] += 1
                st["functions_ruby"] += len(fns)
                st["lines_code"] += met["lines_code"]
                st["lines_total"] += met["lines_total"]
                st["parse_errors"] += int(bool(met.get("parse_error")))
            else:
                fns, lang = rubynative.extract_native(src, mem.name)
                if lang:
                    langs.add(lang)
                st["native_files"] += 1
                st["functions_native"] += len(fns)
            for f in fns:
                # first definition wins, matching Ruby: a later reopen does not
                # change the visibility a method was first declared with
                sigs.setdefault(f["sig"], (f.get("visibility", "public"),
                                           bool(f.get("module_function"))))
    for vis, mf in sigs.values():
        st["functions_" + vis] = st.get("functions_" + vis, 0) + 1
        if mf:
            st["functions_module_function"] += 1
    st["native_languages"] = "+".join(sorted(langs))
    return sigs, st


def do_gem(gem, policy):
    """Every selected version of one gem, in order, with diffs between them."""
    try:
        vers = version_list(gem)
    except Exception as exc:
        return [dict(gem=gem, version="",
                     status="versions_error:" + type(exc).__name__)]
    if not vers:
        return [dict(gem=gem, version="", status="no_versions")]

    released = {v[0]: v[1] for v in vers}
    platform = {v[0]: v[2] for v in vers}
    rows, prev, running = [], None, 0
    for v in select(vers, policy):
        try:
            sigs, st = api_of(gem, v, platform.get(v, "ruby"))
        except urllib.error.HTTPError as exc:
            rows.append(dict(gem=gem, version=v, released=released.get(v, ""),
                             status="http_" + str(exc.code)))
            continue
        except Exception as exc:
            rows.append(dict(gem=gem, version=v, released=released.get(v, ""),
                             status="error:" + type(exc).__name__))
            continue
        if prev is None:
            added, removed, running = len(sigs), 0, len(sigs)
        else:
            added, removed = len(set(sigs) - set(prev)), len(set(prev) - set(sigs))
            running += added - removed
        rows.append(dict(gem=gem, version=v, released=released.get(v, ""),
                         status="ok", functions=len(sigs), added=added,
                         removed=removed, net=added - removed,
                         running_total=running, drift=running - len(sigs),
                         **st))
        prev = sigs
    return rows


def already_done(path):
    if not os.path.exists(path):
        return set()
    d = pd.read_csv(path, usecols=["gem"], low_memory=False)
    return set(d["gem"].astype(str))


def union_names(n=None):
    """The selected package set, read from the union file.

    This used to return the top N by downloads, which silently made the census
    cover only the download leg of a three-leg selection -- everything reached
    via stars or forks but outside the download cut was never counted (1,589
    packages on the NuGet side). The union file is the authority.
    """
    path = os.path.join(OUT_DIR, "final", "3_union", "ruby_union.csv")
    if os.path.exists(path):
        u = pd.read_csv(path)
        # registry_name carries the registry's own casing but is null for
        # packages that reached the union via stars/forks without appearing in
        # the download frame -- fall back to the union key so those are kept
        names = u["package"].astype(str)
        if "registry_name" in u.columns:
            names = u["registry_name"].fillna(u["package"]).astype(str)
        names = names[names.str.lower().ne("nan") & names.ne("")]
        return names.drop_duplicates().tolist()
    raise SystemExit("union file missing: " + path)


def summarise(vpath):
    """(all rows, ok rows, one row per gem). Restored after a patch to
    union_names accidentally spanned this function."""
    d = pd.read_csv(vpath, low_memory=False)
    ok = d[d["status"] == "ok"]
    if not len(ok):
        return d, ok, pd.DataFrame()
    g = ok.groupby("gem")
    s = pd.DataFrame({
        "versions_counted": g.size(),
        "first_version": g["version"].first(),
        "last_version": g["version"].last(),
        "functions_first": g["functions"].first(),
        "functions_last": g["functions"].last(),
        "functions_ruby_last": g["functions_ruby"].last(),
        "functions_native_last": g["functions_native"].last(),
        "functions_public_last": g["functions_public"].last(),
        "functions_private_last": g["functions_private"].last(),
        "functions_protected_last": g["functions_protected"].last(),
        "functions_added_total": g["added"].sum(),
        "functions_removed_total": g["removed"].sum(),
        "max_abs_drift": g["drift"].apply(lambda x: x.abs().max()),
        "rb_files_last": g["rb_files"].last(),
        "native_files_last": g["native_files"].last(),
        "native_languages": g["native_languages"].last(),
        "lines_code_last": g["lines_code"].last(),
        "gem_bytes_last": g["gem_bytes"].last(),
        "parse_errors_last": g["parse_errors"].last(),
    }).reset_index()
    s["net_change"] = s["functions_last"] - s["functions_first"]
    return d, ok, s


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", default="",
                    help="CSV with a name column; default is the union list")
    ap.add_argument("--versions", default="latest",
                    help="latest | minor | major | all | <N>")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--out", default="ruby_api_versions",
                    help="basename for the two output csvs")
    a = ap.parse_args(argv)

    names = (pd.read_csv(a.packages)["name"].dropna().astype(str).tolist()
             if a.packages else union_names())
    if a.limit:
        names = names[:a.limit]

    vpath = os.path.join(API_DIR, a.out + ".csv")
    have = already_done(vpath)
    todo = [n for n in names if n not in have]
    log(str(len(names)) + " gems, " + str(len(names) - len(todo))
        + " already done, " + str(len(todo)) + " to do (versions="
        + a.versions + ")")

    fresh = not os.path.exists(vpath)
    with open(vpath, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=VER_FIELDS, extrasaction="ignore")
        if fresh:
            w.writeheader()
        n = 0
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futs = {pool.submit(do_gem, g, a.versions): g for g in todo}
            for f in as_completed(futs):
                try:
                    rows = f.result()
                except Exception as exc:
                    rows = [dict(gem=futs[f], version="",
                                 status="fatal:" + type(exc).__name__)]
                with _lock:
                    for r in rows:
                        w.writerow(r)
                    fh.flush()
                    n += 1
                    if n % 50 == 0:
                        log("  " + str(n) + "/" + str(len(todo)) + " gems")

    d, ok, s = summarise(vpath)
    spath = os.path.join(API_DIR, a.out.replace("versions", "summary")
                         if "versions" in a.out else a.out + "_summary")
    spath += ".csv"
    if len(s):
        s.to_csv(spath, index=False)
    log("-> " + os.path.basename(vpath) + "  " + str(len(d)) + " rows, "
        + str(len(ok)) + " ok")
    log("-> " + os.path.basename(spath) + "  " + str(len(s)) + " gems")
    bad = d[d["status"] != "ok"]["status"].value_counts()
    if len(bad):
        log("   non-ok: " + ", ".join(k + "=" + str(v) for k, v in bad.items()))
    if len(ok):
        log("   functions total " + str(int(ok["functions"].sum()))
            + ", median " + str(int(ok["functions"].median()))
            + ", drift nonzero on " + str(int((ok["drift"] != 0).sum())) + " rows")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
