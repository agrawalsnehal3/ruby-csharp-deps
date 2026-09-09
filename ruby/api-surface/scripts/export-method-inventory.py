"""One data file per gem, holding every method it defines.

The census CSVs give a count per gem. This gives the methods themselves --
signature, visibility, parameters, arity, body calls, raises and control flow
-- as JSON Lines, one file per package under ruby_methods/.

Per gem rather than one combined file: the whole set is roughly 1.2 million
records, which is awkward to open and pointless to re-read in full when the
usual question is about one package. One file per gem also means a re-run can
skip gems already written, so an interrupted run resumes for free.

A disk cache sits under the gem files because this is the third full fetch of
the same 2,816 packages -- v1, then v2 for visibility, now this. A published
gem version is immutable, so the cache can never go stale and needs no
invalidation. It costs about 1.1 GB and makes any further pass parse-only.

Writes out/third_party_method_count_latest/ruby_methods/<gem>.jsonl
       out/third_party_method_count_latest/ruby_methods_index.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from census.core import OUT_DIR, SSL_CONTEXT, USER_AGENT, log

API_DIR = os.path.join(OUT_DIR, "third_party_method_count_latest")
OUT_METHODS = os.path.join(API_DIR, "ruby_methods")
CACHE = os.path.join(API_DIR, "_gem_cache")
os.makedirs(OUT_METHODS, exist_ok=True)

sys.path.append(r"c:\Users\agraw\OneDrive\Desktop\experiment\ruby-fn-census")
from rubydeep import extract_methods                          # noqa: E402
import rubynative                                             # noqa: E402

DL = "https://rubygems.org/downloads"
WORKERS = 12
SKIP = __import__("re").compile(
    r"(^|/)(test|tests|spec|specs|benchmark|benchmarks|sample|samples|"
    r"example|examples|doc|docs|fixtures?|vendor)(/|$)")
_lock = threading.Lock()


def fetch_gem(gem, version, platform="ruby", use_cache=True):
    stem = gem + "-" + version + ("" if platform == "ruby" else "-" + platform)
    path = os.path.join(CACHE, stem + ".gem")
    if use_cache and os.path.exists(path):
        with open(path, "rb") as fh:
            return fh.read()
    for i in range(3):
        try:
            rq = urllib.request.Request(DL + "/" + stem + ".gem",
                                        headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(rq, timeout=60, context=SSL_CONTEXT) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404) or i == 2:
                raise
        except Exception:
            if i == 2:
                raise
        time.sleep(2 ** i)
    if use_cache:
        os.makedirs(CACHE, exist_ok=True)
        tmp = path + ".part"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)          # atomic, so a kill cannot leave a stub
    return raw


def dump_gem(row, use_cache=True):
    gem, version = row.gem, row.version
    out = os.path.join(OUT_METHODS, gem.replace("/", "_") + ".jsonl")
    if os.path.exists(out):
        return gem, "skipped", 0
    try:
        raw = fetch_gem(gem, str(version), use_cache=use_cache)
    except Exception as exc:
        return gem, "fetch_error:" + type(exc).__name__, 0
    recs = []
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as outer:
            member = outer.extractfile("data.tar.gz")
            if member is None:
                return gem, "no_payload", 0
            payload = gzip.decompress(member.read())
        with tarfile.open(fileobj=io.BytesIO(payload)) as inner:
            for mem in inner.getmembers():
                if not mem.isfile() or SKIP.search(mem.name):
                    continue
                fh = inner.extractfile(mem)
                if fh is None:
                    continue
                if mem.name.lower().endswith(".rb"):
                    recs += extract_methods(fh.read(), mem.name, gem, str(version))
                elif rubynative.language_of(mem.name):
                    fns, lang = rubynative.extract_native(fh.read(), mem.name)
                    for f in fns:
                        recs.append({"gem": gem, "version": str(version),
                                     "name": f["name"], "sig": f["sig"],
                                     "kind": f["kind"], "class": f["scope"],
                                     "visibility": "public", "file": f["file"],
                                     "start_line": f["line"], "end_line": None,
                                     "loc": None, "parameters": [],
                                     "language": lang, "calls": [],
                                     "raises": [], "control_flow": {}})
    except Exception as exc:
        return gem, "parse_error:" + type(exc).__name__, 0
    tmp = out + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, out)
    return gem, "ok", len(recs)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)

    src = pd.read_csv(os.path.join(API_DIR, "ruby_api_v2_versions.csv"),
                      low_memory=False)
    src = src[src.status == "ok"][["gem", "version"]]
    if a.limit:
        src = src.head(a.limit)
    log(str(len(src)) + " gems to dump (cache "
        + ("off" if a.no_cache else "on") + ")")

    rows, n = [], 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = [pool.submit(dump_gem, r, not a.no_cache)
                for r in src.itertuples()]
        for f in as_completed(futs):
            gem, status, cnt = f.result()
            rows.append({"gem": gem, "status": status, "methods": cnt})
            n += 1
            if n % 100 == 0:
                log("  " + str(n) + "/" + str(len(src)))

    idx = pd.DataFrame(rows).sort_values("methods", ascending=False)
    idx.to_csv(os.path.join(API_DIR, "ruby_methods_index.csv"), index=False)
    ok = idx[idx.status == "ok"]
    log("-> ruby_methods/  " + str(len(ok)) + " files, "
        + str(int(ok.methods.sum())) + " method records")
    bad = idx[~idx.status.isin(["ok", "skipped"])]["status"].value_counts()
    if len(bad):
        log("   problems: " + ", ".join(k + "=" + str(v) for k, v in bad.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
