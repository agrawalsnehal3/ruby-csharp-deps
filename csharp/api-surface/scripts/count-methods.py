"""Public API census per NuGet package, read from IL without downloading it.

A .nupkg is a zip, and zip keeps its index at the end, so the whole package
never has to be fetched. Three ranged requests do it:

  1. the last 64 KB, which contains the end-of-central-directory record
  2. the central directory itself, if it did not fit in that tail
  3. the bytes of the one assembly we actually want

That matters at this scale. The union list's mean .nupkg is 2.9 MB and the
largest is 262 MB -- 10 GB in total -- because native-asset packages bundle a
binary per platform. Reading one 200 KB assembly out of each avoids nearly all
of it.

Counting from IL rather than source is also more accurate, not just cheaper.
The metadata tables ARE the public surface: no parse, no heuristics, and
visibility is a flag rather than something to infer.

One assembly per package
------------------------
Newtonsoft.Json ships eight builds of itself -- net20 through netstandard2.0 --
and they are the same API eight times. Counting every lib/ dll would inflate
exactly the big framework packages that dominate the download ranking, so a
single target framework is chosen per package by TFM_RANK. ref/ wins over lib/
when present: a reference assembly is public surface with the bodies stripped,
which is precisely what is being counted.

What is counted
---------------
A method is counted when it is public, protected or protected-internal, its
declaring type is publicly visible, and it is not SpecialName. That last flag
is what removes property get_/set_ and event add_/remove_ accessors, which are
real MethodDef rows but not separate APIs -- properties and events are counted
once each from their own tables instead. Constructors and operators carry
SpecialName too and are therefore excluded from methods; they are reported
separately so the choice can be revisited without a re-run.

Writes out/third_party_method_count_latest/nuget_api.csv
-- one row per package, append-only and resumable
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import struct
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

import dnfile
import pandas as pd

from census.core import OUT_DIR, SSL_CONTEXT, USER_AGENT, log

# Results live in their own folder rather than loose in out/, which already
# holds the registry harvests. Created on import so a fresh clone can run
# without a setup step.
API_DIR = os.path.join(OUT_DIR, "third_party_method_count_latest")
os.makedirs(API_DIR, exist_ok=True)

FLAT = "https://api.nuget.org/v3-flatcontainer"
WORKERS = 16
TAIL = 65536 + 22                 # max zip comment plus the EOCD record itself
# dnfile is pure Python, and its parse time grows sharply with assembly size:
# Microsoft.Graph.Beta's 76 MB assembly took 4,719 seconds against 6 seconds to
# fetch it. A handful of code-generated SDKs are far larger than everything
# else, so they are recorded as too_large rather than allowed to stall a run.
MAX_ASSEMBLY = 24 * 1024 * 1024
FALLBACK = [False]           # set by --fallback
EOCD, EOCD64, LOC64, CEN, LOC = (b"PK\x05\x06", b"PK\x06\x06", b"PK\x06\x07",
                                 b"PK\x01\x02", b"PK\x03\x04")
FIELDS = ["package", "version", "status", "asset_kind", "tfm", "assembly",
          "assembly_bytes",
          "bytes_fetched", "nupkg_bytes", "public_types", "methods_public",
          "properties", "events", "ctors", "operators", "api_total",
          "methods_private", "methods_protected", "methods_internal",
          "m_static", "m_virtual", "m_abstract", "m_sealed", "m_generic",
          "t_interface", "t_abstract", "t_sealed", "fields_public",
          "all_types", "methoddef_rows", "typedef_rows"]
_lock = threading.Lock()


def rank_tfm(tfm):
    """Lower is better. Portable first, then newest, then legacy desktop."""
    t = tfm.lower()
    if t.startswith("netstandard"):
        try:
            return (0, -float(t[11:] or 0))
        except ValueError:
            return (0, 0)
    if t.startswith("netcoreapp"):
        try:
            return (2, -float(t[10:] or 0))
        except ValueError:
            return (2, 0)
    if t.startswith("net") and "." in t:            # net6.0, net8.0
        try:
            return (1, -float(t[3:].split("-")[0]))
        except ValueError:
            return (1, 0)
    if t.startswith("net") and t[3:].isdigit():     # net48, net472, net20
        return (3, -int(t[3:]))
    return (4, 0)


def get(url, rng=None, tries=3):
    h = {"User-Agent": USER_AGENT}
    if rng:
        h["Range"] = "bytes=" + rng
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(rq, timeout=60, context=SSL_CONTEXT) as r:
                return r.read(), int(r.headers.get("Content-Range", "0/0")
                                     .split("/")[-1] or 0)
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 403) or i == tries - 1:
                raise
        except Exception:
            if i == tries - 1:
                raise
        time.sleep(2 ** i)
    raise RuntimeError("unreachable")


def central_directory(url):
    """[(name, comp_size, method, local_offset)], plus bytes fetched and size."""
    tail, total = get(url, "-" + str(TAIL))
    fetched = len(tail)
    i = tail.rfind(EOCD)
    if i < 0:
        raise ValueError("no EOCD")
    cd_size, cd_off = struct.unpack_from("<II", tail, i + 12)

    z64 = tail.rfind(LOC64)
    if (cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF) and z64 >= 0:
        rec_off = struct.unpack_from("<Q", tail, z64 + 8)[0]
        blk, _ = get(url, str(rec_off) + "-" + str(rec_off + 55))
        fetched += len(blk)
        if blk.startswith(EOCD64):
            cd_size, cd_off = struct.unpack_from("<QQ", blk, 40)

    start = total - len(tail) if total else -1
    if start >= 0 and cd_off >= start:
        cd = tail[cd_off - start:cd_off - start + cd_size]
    else:
        cd, _ = get(url, str(cd_off) + "-" + str(cd_off + cd_size - 1))
        fetched += len(cd)

    out, p = [], 0
    while p + 46 <= len(cd) and cd[p:p + 4] == CEN:
        method, = struct.unpack_from("<H", cd, p + 10)
        comp, = struct.unpack_from("<I", cd, p + 20)
        nlen, elen, clen = struct.unpack_from("<HHH", cd, p + 28)
        loff, = struct.unpack_from("<I", cd, p + 42)
        unc, = struct.unpack_from("<I", cd, p + 24)
        name = cd[p + 46:p + 46 + nlen].decode("utf8", "replace")
        out.append((name, comp, method, loff, unc))
        p += 46 + nlen + elen + clen
    return out, fetched, total


def read_entry(url, name, comp, method, loff):
    """Inflate one zip member using a single ranged request."""
    # For a package smaller than the slice we would ask for, one plain GET is
    # cheaper than a ranged read that overlaps the tail already fetched.
    span = 30 + len(name.encode()) + 512 + comp
    blob, _ = get(url, str(loff) + "-" + str(loff + span))
    if not blob.startswith(LOC):
        raise ValueError("bad local header")
    nlen, elen = struct.unpack_from("<HH", blob, 26)
    start = 30 + nlen + elen
    data = blob[start:start + comp]
    if method == 0:
        return data, len(blob)
    return zlib.decompress(data, -15), len(blob)


def pick_assembly(names, fallback=False):
    """(name, tfm, asset_kind) of the assembly to count, or (None, reason, "").

    lib/ and ref/ are the consumer API and are always preferred. With
    fallback=True a package that has neither is retried against the assemblies
    it does ship -- analyzers/, build/, tools/, runtimes/ -- because "ships no
    consumer API" and "has nothing countable" are different claims, and only
    the first is true for most of them. asset_kind records which it was, so
    those rows can be included or excluded downstream on purpose.

    A metapackage with no .dll anywhere is a genuine zero and stays excluded.
    """
    cands = []
    for n in names:
        low = n.lower()
        if not low.endswith(".dll"):
            continue
        parts = n.split("/")
        if len(parts) >= 3 and parts[0].lower() in ("lib", "ref"):
            cands.append((0 if parts[0].lower() == "ref" else 1,
                          rank_tfm(parts[1]), n, parts[1], parts[0].lower()))
        elif len(parts) == 2 and parts[0].lower() in ("lib", "ref"):
            cands.append((1, (5, 0), n, "", parts[0].lower()))
    if cands:
        cands.sort(key=lambda c: (c[0], c[1], len(c[2])))
        return cands[0][2], cands[0][3], cands[0][4]

    anydll = [n for n in names if n.lower().endswith(".dll")]
    if not anydll:
        return None, "metapackage", ""

    if fallback:
        # Managed assemblies do exist outside lib/. Analyzers are ordinary
        # .NET libraries; build/ often holds reference assemblies. runtimes/
        # is usually native and will simply fail to parse, which is recorded.
        order = {"analyzers": 0, "build": 1, "buildtransitive": 1,
                 "tools": 2, "runtimes": 3, "native": 4}
        ranked = sorted(anydll, key=lambda n: (order.get(n.split("/")[0].lower(), 5),
                                               len(n)))
        top = ranked[0].split("/")[0].lower()
        return ranked[0], "", top

    top = {n.split("/")[0].lower() for n in anydll}
    if top & {"runtimes", "native", "build", "buildtransitive"}:
        return None, "native_only", ""
    if top & {"tools", "analyzers"}:
        return None, "tools_only", ""
    return None, "no_lib_dll", ""


def count_api(data):
    """Public surface of one assembly from its metadata tables.

    Visibility is tallied across every method, not just the public ones, so
    the public figure can be read against a denominator -- the same
    public/private split the Ruby side reports. ECMA-335 II.23.1.10 defines
    the MemberAccess mask these flags come from, so this is exact rather than
    inferred: unlike Ruby, .NET records visibility in the metadata itself.
    """
    pe = dnfile.dnPE(data=data)
    if pe.net is None or pe.net.mdtables is None:
        raise ValueError("not a managed assembly")
    md = pe.net.mdtables
    types = getattr(md, "TypeDef", None)
    if types is None:
        raise ValueError("no TypeDef table")

    pub_types = methods = ctors = ops = 0
    priv = prot = internal = 0
    # method-shape flags: single bits in the same walk, so effectively free.
    # Control flow is deliberately absent: C# compiles if/while/for/foreach to
    # the same IL branch opcodes, so the distinction no longer exists here and
    # cannot be recovered at any cost.
    st = vi = ab = se = gen = 0
    t_iface = t_abs = t_sealed = 0
    for t in types.rows:
        f = t.Flags
        type_public = f.tdPublic or f.tdNestedPublic
        if type_public:
            pub_types += 1
            t_iface += bool(f.tdInterface)
            t_abs += bool(f.tdAbstract)
            t_sealed += bool(f.tdSealed)
        for ref in t.MethodList:
            m = ref.row
            if m is None:
                continue
            mf = m.Flags
            name = str(m.Name or "")
            # every method gets a visibility bucket, public or not
            if mf.mdPublic:
                pass
            elif mf.mdFamily or mf.mdFamORAssem:
                prot += 1
            elif mf.mdAssem or mf.mdFamANDAssem:
                internal += 1
            else:
                priv += 1
            if not type_public:
                continue
            if not (mf.mdPublic or mf.mdFamily or mf.mdFamORAssem):
                continue
            if name.startswith("<") or "<>" in name:      # compiler-generated
                continue
            st += bool(mf.mdStatic)
            vi += bool(mf.mdVirtual)
            ab += bool(mf.mdAbstract)
            se += bool(mf.mdFinal)
            gen += "`" in name
            if mf.mdSpecialName or mf.mdRTSpecialName:
                if name in (".ctor", ".cctor"):
                    ctors += 1
                elif name.startswith("op_"):
                    ops += 1
                continue                                   # accessors: skip
            methods += 1

    props = len(getattr(md, "Property", None).rows) if getattr(md, "Property", None) else 0
    evts = len(getattr(md, "Event", None).rows) if getattr(md, "Event", None) else 0
    meths = len(getattr(md, "MethodDef", None).rows) if getattr(md, "MethodDef", None) else 0
    return dict(public_types=pub_types, methods_public=methods,
                properties=props, events=evts, ctors=ctors, operators=ops,
                api_total=methods + props + evts,
                methods_private=priv, methods_protected=prot,
                methods_internal=internal,
                m_static=st, m_virtual=vi, m_abstract=ab, m_sealed=se,
                m_generic=gen, t_interface=t_iface, t_abstract=t_abs,
                t_sealed=t_sealed,
                fields_public=len(getattr(md, "Field", None).rows)
                if getattr(md, "Field", None) else 0,
                all_types=len(types.rows),
                methoddef_rows=meths, typedef_rows=len(types.rows))


def latest_version(pkg):
    """Newest stable, or newest prerelease when a package has only those.

    Some widely-used packages never leave beta -- the OpenTelemetry
    instrumentation family is entirely prerelease and still heavily
    downloaded. Skipping them would drop real API surface, so prerelease is a
    fallback rather than an exclusion.
    """
    raw, _ = get(FLAT + "/" + pkg + "/index.json")
    allv = json.loads(raw.decode()).get("versions", [])
    stable = [v for v in allv if "-" not in v]
    return (stable or allv)[-1] if (stable or allv) else ""


def do_pkg(pkg, version=""):
    low = pkg.lower()
    try:
        v = version or latest_version(low)
        if not v:
            return dict(package=pkg, status="no_version")
        url = FLAT + "/" + low + "/" + v + "/" + low + "." + v + ".nupkg"
        entries, fetched, total = central_directory(url)
        name, tfm, kind = pick_assembly([e[0] for e in entries], FALLBACK[0])
        if name is None:
            return dict(package=pkg, version=v, status=tfm,
                        bytes_fetched=fetched, nupkg_bytes=total)
        ent = next(e for e in entries if e[0] == name)
        if ent[4] and ent[4] > MAX_ASSEMBLY:
            return dict(package=pkg, version=v, status="too_large", tfm=tfm,
                        asset_kind=kind,
                        assembly=name, assembly_bytes=ent[4],
                        bytes_fetched=fetched, nupkg_bytes=total)
        data, got = read_entry(url, *ent[:4])
        row = count_api(data)
        return dict(package=pkg, version=v, status="ok", tfm=tfm,
                    asset_kind=kind,
                    assembly=name, assembly_bytes=len(data),
                    bytes_fetched=fetched + got, nupkg_bytes=total, **row)
    except urllib.error.HTTPError as exc:
        return dict(package=pkg, version=version, status="http_" + str(exc.code))
    except Exception as exc:
        return dict(package=pkg, version=version,
                    status="error:" + type(exc).__name__)


def union_names(n=None):
    """The selected package set, read from the union file.

    This used to return the top N by downloads, which silently made the census
    cover only the download leg of a three-leg selection -- everything reached
    via stars or forks but outside the download cut was never counted (1,589
    packages on the NuGet side). The union file is the authority.
    """
    path = os.path.join(OUT_DIR, "final", "3_union", "csharp_union.csv")
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


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--out", default="nuget_api")
    ap.add_argument("--fallback", action="store_true",
                    help="count assemblies outside lib/ (analyzers, build, tools)")
    a = ap.parse_args(argv)

    FALLBACK[0] = a.fallback
    names = (pd.read_csv(a.packages)["name"].dropna().astype(str).tolist()
             if a.packages else union_names())
    if a.limit:
        names = names[:a.limit]

    path = os.path.join(API_DIR, a.out + ".csv")
    have = set()
    if os.path.exists(path):
        have = set(pd.read_csv(path, usecols=["package"],
                               low_memory=False)["package"].astype(str))
    todo = [n for n in names if n not in have]
    log(str(len(names)) + " packages, " + str(len(names) - len(todo))
        + " already done, " + str(len(todo)) + " to do")

    fresh = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if fresh:
            w.writeheader()
        n = 0
        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            futs = {pool.submit(do_pkg, p): p for p in todo}
            for f in as_completed(futs):
                try:
                    row = f.result()
                except Exception as exc:
                    row = dict(package=futs[f],
                               status="fatal:" + type(exc).__name__)
                with _lock:
                    w.writerow(row)
                    fh.flush()
                    n += 1
                    if n % 100 == 0:
                        log("  " + str(n) + "/" + str(len(todo)))

    d = pd.read_csv(path, low_memory=False)
    ok = d[d["status"] == "ok"]
    log("-> " + os.path.basename(path) + "  " + str(len(d)) + " rows, " + str(len(ok)) + " ok")
    bad = d[d["status"] != "ok"]["status"].value_counts()
    if len(bad):
        log("   non-ok: " + ", ".join(k + "=" + str(v) for k, v in bad.items()))
    if len(ok):
        log("   api_total " + str(int(ok["api_total"].sum()))
            + ", median " + str(int(ok["api_total"].median())))
        log("   fetched " + str(round(ok["bytes_fetched"].sum() / 1e6, 1))
            + " MB of " + str(round(ok["nupkg_bytes"].sum() / 1e9, 2))
            + " GB of packages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
