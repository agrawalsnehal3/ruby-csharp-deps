"""Does each NuGet package ship its documentation, and can it be downloaded?

A .nupkg normally carries an XML file beside every assembly -- the compiler's
output from /// doc comments -- holding a <member> entry per public type and
method with <summary>, <param> and <returns>. That is real API documentation,
structured, inside the package.

Only the zip index is read here, not the files themselves: one ranged request
tells us whether the XML exists and how large it is. Answering "is there
documentation" for the whole set therefore costs a few MB rather than gigabytes.

Writes out/third_party_method_count_latest/_nuget_docs_scan.csv
"""
from __future__ import annotations

import csv
import os
import sys
import threading
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from census.core import OUT_DIR, log
from nuget_api_census import FLAT, central_directory, latest_version

DIR = os.path.join(OUT_DIR, "third_party_method_count_latest")
FIELDS = ["package", "version", "status", "xml_doc", "xml_bytes",
          "readme", "n_dll", "n_xml", "nupkg_bytes", "bytes_read"]
_lock = threading.Lock()


def scan(pkg):
    low = pkg.lower()
    try:
        v = latest_version(low)
        if not v:
            return dict(package=pkg, status="no_version")
        url = FLAT + "/" + low + "/" + v + "/" + low + "." + v + ".nupkg"
        entries, fetched, total = central_directory(url)
    except urllib.error.HTTPError as exc:
        return dict(package=pkg, status="http_" + str(exc.code))
    except Exception as exc:
        return dict(package=pkg, status="error:" + type(exc).__name__)

    names = [e[0] for e in entries]
    # the doc xml sits beside the assembly it documents, so pair them up
    dlls = [n for n in names if n.lower().endswith(".dll")
            and n.split("/")[0].lower() in ("lib", "ref")]
    xmls = [n for n in names if n.lower().endswith(".xml")
            and n.split("/")[0].lower() in ("lib", "ref")]
    paired, size = "", 0
    for d in dlls:
        cand = d[:-4] + ".xml"
        for e in entries:
            if e[0].lower() == cand.lower():
                paired, size = e[0], e[4]
                break
        if paired:
            break
    readme = next((n for n in names
                   if n.lower().split("/")[-1].startswith("readme")), "")
    return dict(package=pkg, version=v, status="ok", xml_doc=paired,
                xml_bytes=size, readme=readme, n_dll=len(dlls),
                n_xml=len(xmls), nupkg_bytes=total, bytes_read=fetched)


def main(argv):
    src = pd.read_csv(os.path.join(DIR, "nuget_api.csv"), low_memory=False)
    names = src["package"].astype(str).tolist()
    path = os.path.join(DIR, "_nuget_docs_scan.csv")
    done = set()
    if os.path.exists(path):
        done = set(pd.read_csv(path, usecols=["package"])["package"].astype(str))
    todo = [n for n in names if n not in done]
    log(str(len(names)) + " packages, " + str(len(todo)) + " to scan")

    fresh = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if fresh:
            w.writeheader()
        n = 0
        with ThreadPoolExecutor(max_workers=20) as pool:
            futs = {pool.submit(scan, p): p for p in todo}
            for f in as_completed(futs):
                try:
                    row = f.result()
                except Exception as exc:
                    row = dict(package=futs[f], status="fatal:" + type(exc).__name__)
                with _lock:
                    w.writerow(row)
                    fh.flush()
                    n += 1
                    if n % 250 == 0:
                        log("  " + str(n) + "/" + str(len(todo)))

    d = pd.read_csv(path, low_memory=False)
    ok = d[d.status == "ok"]
    log("-> " + str(len(d)) + " rows, " + str(len(ok)) + " ok")
    if len(ok):
        log("   with XML docs: " + str(int((ok.xml_doc.fillna("") != "").sum()))
            + " / " + str(len(ok)))
        log("   with README:   " + str(int((ok.readme.fillna("") != "").sum())))
        log("   read " + str(round(ok.bytes_read.sum() / 1e6, 1)) + " MB of "
            + str(round(ok.nupkg_bytes.sum() / 1e9, 2)) + " GB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
