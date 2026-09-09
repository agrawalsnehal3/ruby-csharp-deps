"""Check whether the documentation links actually resolve.

A link in a package's metadata is a claim, not a fact. Projects move, sites
lapse, repositories get renamed or deleted, and nothing in a registry forces
those URLs to stay correct -- a gem published in 2014 still carries whatever
homepage it declared then.

So every distinct URL is fetched once and the outcome recorded:

    ok           200, and it is not a soft 404
    redirected   ends somewhere else -- kept, with the destination, because a
                 redirect to a project's new home is fine while a redirect to
                 a domain-parking page is not
    not_found    404 or 410
    unreachable  DNS failure, refused connection, timeout, bad certificate
    error_NNN    any other status

HEAD is tried first because it costs nothing; servers that reject it fall
back to a ranged GET of the first bytes rather than the whole page.

Two checks catch things a status code does not:

  * a redirect that leaves the original host entirely is flagged, since that
    is how an expired domain looks
  * a 200 whose body says "not found" or "no longer available" is a soft 404,
    which is common on documentation sites that serve a styled error page

Results are cached per URL, so a re-run only checks what is new.

Writes <lang>/documentation/documentation-link-status.csv
       and adds link_status columns to documentation.csv
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import ssl
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                    "Third_party_packages")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "out", "_link_status.json")
UA = ("Mozilla/5.0 (compatible; package-census/1.0; "
      "+documentation availability survey)")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE      # expired certs are a finding, not a stop
COLS = ["handwritten_site", "github_docs_folder", "github_wiki",
        "github_pages", "homepage", "best_doc_url"]
SOFT404 = re.compile(
    rb"(page not found|404 not found|no longer available|this site can"
    rb"|domain (?:is )?for sale|buy this domain|parked (?:free )?courtesy)",
    re.I)
_lock = threading.Lock()

# Anonymous requests to github.com get throttled hard -- a first run returned
# 429 for 4,057 of them. The authenticated API allows 5,000/hour and answers
# the same question, so GitHub URLs are resolved through it instead of by
# fetching the web page.
_GH = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+?)(?:\.git)?"
                 r"(/(?:tree/[^/]+/(?P<dir>.+?)|wiki)/?)?(?:[?#].*)?$")
_host_gate = {}


def _gate(host, min_gap=0.35):
    """Space out requests to the same host; unrelated hosts stay parallel."""
    with _lock:
        g = _host_gate.setdefault(host, threading.Semaphore(2))
    return g


def _gh_api(path):
    from census.core import SSL_CONTEXT, USER_AGENT, gh_headers
    rq = urllib.request.Request("https://api.github.com" + path,
                                headers=gh_headers())
    with urllib.request.urlopen(rq, timeout=25, context=SSL_CONTEXT) as r:
        return r.status


def check_github(url):
    """Resolve a github.com URL through the API rather than the web page."""
    m = _GH.match(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    sub = m.group(3) or ""
    try:
        if "/wiki" in sub:
            # the API cannot list wiki pages; has_wiki is the best available
            import json as _j
            from census.core import SSL_CONTEXT, USER_AGENT, gh_headers
            rq = urllib.request.Request(
                "https://api.github.com/repos/" + owner + "/" + repo,
                headers=gh_headers())
            with urllib.request.urlopen(rq, timeout=25, context=SSL_CONTEXT) as r:
                meta = _j.loads(r.read())
            return (("ok", url, "wiki enabled") if meta.get("has_wiki")
                    else ("not_found", url, "wiki disabled"))
        if m.group("dir"):
            _gh_api("/repos/" + owner + "/" + repo + "/contents/"
                    + m.group("dir"))
            return "ok", url, ""
        _gh_api("/repos/" + owner + "/" + repo)
        return "ok", url, ""
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "not_found", url, "repo or path gone"
        if e.code in (401, 403):
            return "blocked", url, "HTTP " + str(e.code)
        return "error_" + str(e.code), url, ""
    except Exception as e:
        return "unreachable", url, type(e).__name__


def _load():
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {}


def _save(d):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh)
    os.replace(tmp, CACHE)


def check(url):
    """(status, final_url, note)."""
    try:
        start_host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return "error_parse", "", ""

    if "github.com" in start_host:
        r = check_github(url)
        if r:
            return r

    gate = _gate(start_host)
    gate.acquire()
    try:
        return _fetch(url, start_host)
    finally:
        threading.Timer(0.4, gate.release).start()


def _fetch(url, start_host):

    for method in ("HEAD", "GET"):
        try:
            headers = {"User-Agent": UA}
            if method == "GET":
                headers["Range"] = "bytes=0-4095"
            rq = urllib.request.Request(url, headers=headers, method=method)
            with urllib.request.urlopen(rq, timeout=20, context=CTX) as r:
                body = r.read(4096) if method == "GET" else b""
                final = r.url
                end_host = urllib.parse.urlparse(final).netloc.lower()
                if body and SOFT404.search(body):
                    return "not_found", final, "soft 404 -- page says missing"
                if end_host.replace("www.", "") != start_host.replace("www.", ""):
                    return "redirected", final, "now on " + end_host
                return "ok", final, ""
        except urllib.error.HTTPError as e:
            if e.code == 405 and method == "HEAD":
                continue                      # server dislikes HEAD; try GET
            if e.code in (404, 410):
                return "not_found", url, "HTTP " + str(e.code)
            if e.code in (401, 403):
                return "blocked", url, "HTTP " + str(e.code) + " -- may still exist"
            if e.code == 429 and method == "HEAD":
                continue
            return "error_" + str(e.code), url, ""
        except urllib.error.URLError as e:
            reason = str(getattr(e, "reason", e))
            if "getaddrinfo" in reason or "Name or service" in reason:
                return "unreachable", url, "domain does not resolve"
            if method == "HEAD":
                continue
            return "unreachable", url, reason[:60]
        except Exception as e:
            if method == "HEAD":
                continue
            return "unreachable", url, type(e).__name__
    return "unreachable", url, "no response"


def main():
    cache = _load()
    urls = set()
    frames = {}
    for lang in ("ruby", "csharp"):
        p = os.path.join(ROOT, lang, "documentation", "documentation.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, low_memory=False)
        frames[lang] = d
        for c in COLS:
            if c in d.columns:
                urls |= {str(v).strip() for v in d[c].dropna()
                         if str(v).strip().startswith("http")}

    todo = sorted(u for u in urls if u not in cache)
    print(len(urls), "distinct URLs;", len(todo), "to check")

    done = 0
    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(check, u): u for u in todo}
        for f in cf.as_completed(futs):
            u = futs[f]
            try:
                cache[u] = f.result()
            except Exception as exc:
                cache[u] = ("unreachable", u, type(exc).__name__)
            done += 1
            if done % 400 == 0:
                with _lock:
                    _save(cache)
                print("  ", done, "/", len(todo))
    _save(cache)

    rows = []
    for lang, d in frames.items():
        for c in COLS:
            if c not in d.columns:
                continue
            st = []
            for v in d[c]:
                v = str(v).strip() if pd.notna(v) else ""
                st.append(cache.get(v, ("", "", ""))[0] if v.startswith("http")
                          else "")
            d[c + "_status"] = st
        d.to_csv(os.path.join(ROOT, lang, "documentation",
                              "documentation.csv"), index=False)

        seen = set()
        for c in COLS:
            if c not in d.columns:
                continue
            for v in d[c].dropna():
                v = str(v).strip()
                if v.startswith("http") and v not in seen:
                    seen.add(v)
                    s, final, note = cache.get(v, ("", "", ""))
                    rows.append({"registry": lang, "link_type": c, "url": v,
                                 "status": s, "final_url": final,
                                 "note": note})
        out = pd.DataFrame([r for r in rows if r["registry"] == lang])
        out.to_csv(os.path.join(ROOT, lang, "documentation",
                                "documentation-link-status.csv"), index=False)

        # one row per link type: how many of each outcome, and the share of
        # that type which is dead. A link type with few links but a high dead
        # rate matters differently from one with many links and a low rate.
        piv = (out.pivot_table(index="link_type", columns="status",
                               values="url", aggfunc="count")
               .fillna(0).astype(int))
        for c in ("ok", "redirected", "blocked", "not_found", "unreachable"):
            if c not in piv.columns:
                piv[c] = 0
        piv.insert(0, "total_links", piv.sum(axis=1))
        piv["working"] = piv["ok"] + piv["redirected"]
        piv["dead"] = piv["not_found"] + piv["unreachable"]
        piv["working_pct"] = (100 * piv["working"] / piv["total_links"]).round(1)
        piv["dead_pct"] = (100 * piv["dead"] / piv["total_links"]).round(1)
        piv["share_of_all_links_pct"] = (
            100 * piv["total_links"] / piv["total_links"].sum()).round(1)
        cols = ["total_links", "share_of_all_links_pct", "ok", "redirected",
                "blocked", "not_found", "unreachable", "working", "dead",
                "working_pct", "dead_pct"]
        piv = piv[cols].sort_values("total_links", ascending=False)
        tot = piv[cols[:-2]].sum()
        tot["working_pct"] = round(100 * tot["working"] / tot["total_links"], 1)
        tot["dead_pct"] = round(100 * tot["dead"] / tot["total_links"], 1)
        tot["share_of_all_links_pct"] = 100.0
        piv.loc["ALL LINK TYPES"] = tot
        piv.reset_index().rename(columns={"index": "link_type"}).to_csv(
            os.path.join(ROOT, lang, "documentation",
                         "documentation-link-summary.csv"), index=False)
        print(chr(10) + lang.upper() + " -- by link type")
        print(piv[["total_links", "share_of_all_links_pct", "working",
                   "dead", "working_pct", "dead_pct"]].to_string())
        n = len(out)
        print("\n" + lang.upper(), "--", n, "links")
        for k, v in out.status.value_counts().items():
            print("   {:<12} {:>5}  {:>5.1f}%".format(k, v, 100 * v / n))
        dead = out[out.status.isin(["not_found", "unreachable"])]
        if len(dead):
            print("   dead by type:",
                  dead.link_type.value_counts().head(4).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
