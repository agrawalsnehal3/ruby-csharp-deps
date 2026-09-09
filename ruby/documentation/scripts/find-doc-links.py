"""Where each gem's documentation actually lives, RubyGems first then GitHub.

Answers one question per gem: if someone wanted the docs, what URL would you
send them to, and is there anything there?

RubyGems is checked first because it is the registry of record. But its
documentation link is weak evidence: 1,503 of the 1,790 gems that declare one
point at rubydoc.info, which generates a page from the gem's own source
whether or not a single comment was written. A gem with 0% documented methods
still gets a rubydoc.info URL. So the registry tier is split into what is
merely declared and what is actually there -- a shipped README, a docs/
folder, doc comments in the source.

Only gems that come up empty on the registry are looked up on GitHub, where
four things can carry documentation:

    docs/ or guides/ directory
    a wiki with at least one page
    GitHub Pages (a published site)
    a homepage URL set on the repo

Each gem ends with a best_doc_url and a doc_source saying which tier it came
from, so a link is never presented as better evidence than it is.

Writes out/third_party_method_count_latest/ruby_doc_links.xlsx
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from census.core import GITHUB_API, OUT_DIR, fetch_json, gh_headers, log

DIR = os.path.join(OUT_DIR, "third_party_method_count_latest")
DOCDIRS = {"docs", "doc", "documentation", "guides", "guide", "website",
           "site", "manual", "book", "www"}
SITECFG = {"mkdocs.yml", "mkdocs.yaml", "_config.yml", "docusaurus.config.js",
           "book.toml", "readthedocs.yml", ".readthedocs.yaml"}


def probe_repo(repo):
    """What documentation this GitHub repo carries. One or two API calls."""
    out = dict(gh_docs_dir="", gh_site_config="", gh_has_wiki=False,
               gh_has_pages=False, gh_homepage="", gh_status="")
    try:
        meta = fetch_json(GITHUB_API + "/repos/" + repo, gh_headers(),
                          use_cache=True)
    except Exception as exc:
        out["gh_status"] = "repo_error:" + type(exc).__name__
        return out
    out["gh_has_wiki"] = bool(meta.get("has_wiki"))
    out["gh_has_pages"] = bool(meta.get("has_pages"))
    out["gh_homepage"] = (meta.get("homepage") or "").strip()
    try:
        tree = fetch_json(GITHUB_API + "/repos/" + repo + "/contents/",
                          gh_headers(), use_cache=True)
    except Exception as exc:
        out["gh_status"] = "contents_error:" + type(exc).__name__
        return out
    dirs = {i["name"].lower() for i in tree if i.get("type") == "dir"}
    files = {i["name"].lower() for i in tree if i.get("type") == "file"}
    hit = sorted(dirs & DOCDIRS)
    out["gh_docs_dir"] = hit[0] if hit else ""
    cfg = sorted(files & SITECFG)
    out["gh_site_config"] = cfg[0] if cfg else ""
    out["gh_status"] = "ok"
    return out


def main():
    docs = pd.read_excel(os.path.join(DIR, "ruby_documentation.xlsx"), "gems")
    log(str(len(docs)) + " gems from the documentation census")

    docs["has_readme"] = docs["has_readme"].fillna(False).astype(bool)
    docs["doc_dir_files"] = pd.to_numeric(docs["doc_dir_files"],
                                          errors="coerce").fillna(0)
    docs["doc_coverage_pct"] = pd.to_numeric(docs["doc_coverage_pct"],
                                             errors="coerce")

    # Tier 1 -- the registry. Declared is not the same as present, so keep both.
    docs["rg_declares_docs"] = docs["link_docs"].notna()
    docs["rg_custom_site"] = (docs["rg_declares_docs"]
                              & ~docs["doc_is_autogen"].fillna(False))
    docs["rg_has_real_docs"] = (docs["rg_custom_site"]
                                | (docs["doc_coverage_pct"].fillna(0) > 0)
                                | (docs["doc_dir_files"] > 0)
                                | docs["has_readme"])

    need = docs[~docs["rg_has_real_docs"] & (docs["github_url"] != "")].copy()
    log(str(int(docs["rg_has_real_docs"].sum())) + " covered by RubyGems; "
        + str(len(need)) + " to check on GitHub")

    repos = sorted({u.replace("https://github.com/", "").strip("/")
                    for u in need["github_url"] if isinstance(u, str) and u})
    log("probing " + str(len(repos)) + " distinct repos")
    with ThreadPoolExecutor(max_workers=8) as pool:
        probed = dict(zip(repos, pool.map(probe_repo, repos)))

    def gh(row, key):
        r = str(row.get("github_url", "")).replace("https://github.com/", "").strip("/")
        return probed.get(r, {}).get(key, "")

    for k in ("gh_docs_dir", "gh_site_config", "gh_has_wiki", "gh_has_pages",
              "gh_homepage", "gh_status"):
        docs[k] = docs.apply(lambda r, k=k: gh(r, k), axis=1)

    def _u(v):
        """A usable URL, or "". pandas NaN is a float and floats are truthy,
        so a bare `a or b` silently returns NaN instead of falling through --
        which blanked best_doc_url for every gem without a link_docs."""
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        v = str(v).strip()
        return "" if v.lower() in ("nan", "none") else v

    def _is_doc_site(u):
        """A homepage that is not just the repo or the registry page.

        bundler declares no link_docs at all; bundler.io is set as link_home
        and is unmistakably its documentation. Treating home as a doc
        candidate recovers those, as long as repo and registry URLs are
        excluded first.
        """
        if not u:
            return False
        low = u.lower()
        return not any(h in low for h in
                       ("github.com", "gitlab.com", "rubygems.org",
                        "bitbucket.org", "codeberg.org"))

    def best(r):
        """(url, source) -- strongest available evidence first."""
        docs, home = _u(r.get("link_docs")), _u(r.get("link_home"))
        if r["rg_custom_site"] and docs:
            return docs, "rubygems:custom_doc_site"
        if _is_doc_site(home):
            return home, "rubygems:project_site"
        if r["doc_dir_files"] > 0:
            return _u(r["github_url"]) or home, "gem:docs_folder"
        if pd.notna(r["doc_coverage_pct"]) and r["doc_coverage_pct"] > 0:
            return docs or ("https://rubydoc.info/gems/" + str(r["gem"])), \
                "rubygems:generated_from_comments"
        if _u(r.get("gh_docs_dir")):
            return _u(r["github_url"]) + "/tree/HEAD/" + r["gh_docs_dir"], "github:docs_folder"
        if r.get("gh_has_pages") and _u(r.get("gh_homepage")):
            return _u(r["gh_homepage"]), "github:pages"
        if r.get("gh_has_wiki"):
            return _u(r["github_url"]) + "/wiki", "github:wiki"
        if r["has_readme"]:
            return _u(r["github_url"]) or home, "gem:readme_only"
        if _u(r.get("gh_homepage")):
            return _u(r["gh_homepage"]), "github:homepage"
        return "", "none_found"

    res = docs.apply(best, axis=1, result_type="expand")
    docs["best_doc_url"], docs["doc_source"] = res[0], res[1]

    tier = docs["doc_source"].value_counts()
    summary = pd.DataFrame(
        [("gems examined", len(docs), "")]
        + [("", "", "")]
        + [("--- WHERE DOCS WERE FOUND ---", "", "")]
        + [(k, int(v), str(round(100 * v / len(docs), 1)) + "%")
           for k, v in tier.items()]
        + [("", "", ""),
           ("--- REGISTRY vs GITHUB ---", "", ""),
           ("found via RubyGems / the gem itself",
            int(docs.doc_source.str.startswith(("rubygems", "gem")).sum()), ""),
           ("found only on GitHub",
            int(docs.doc_source.str.startswith("github").sum()), ""),
           ("nothing found anywhere",
            int((docs.doc_source == "none_found").sum()), ""),
           ("rows with a blank best_doc_url",
            int((docs.best_doc_url.fillna("") == "").sum()),
            "should equal 'nothing found anywhere'"),
           ("", "", ""),
           ("declare a docs URL but 0% documented methods",
            int((docs.rg_declares_docs
                 & (docs.doc_coverage_pct.fillna(0) == 0)).sum()),
            "the link exists; the documentation does not")],
        columns=["metric", "value", "share"])

    cols = ["gem", "version", "downloads", "best_doc_url", "doc_source",
            "doc_coverage_pct", "methods_documented", "methods_total",
            "has_readme", "doc_dir_files", "link_docs", "docs_host",
            "doc_is_autogen", "gh_docs_dir", "gh_site_config", "gh_has_wiki",
            "gh_has_pages", "gh_homepage", "link_home", "link_changelog",
            "link_wiki", "github_url"]
    detail = docs[[c for c in cols if c in docs.columns]]

    sheets = {
        "summary": summary,
        "all_gems": detail,
        "docs_on_rubygems": detail[detail.doc_source.str.startswith(("rubygems", "gem"))],
        "docs_only_on_github": detail[detail.doc_source.str.startswith("github")],
        "no_docs_found": detail[detail.doc_source == "none_found"],
        "custom_doc_sites": detail[detail.doc_source == "rubygems:custom_doc_site"],
    }
    path = os.path.join(DIR, "ruby_doc_links.xlsx")
    try:
        w = pd.ExcelWriter(path, engine="xlsxwriter")
    except Exception:
        path = path.replace(".xlsx", "_live.xlsx")
        w = pd.ExcelWriter(path, engine="xlsxwriter")
    with w:
        hdr = w.book.add_format({"bold": True, "bg_color": "#121a24",
                                 "font_color": "white", "border": 1})
        num = w.book.add_format({"num_format": "#,##0"})
        for nm, t in sheets.items():
            t.to_excel(w, sheet_name=nm[:31], index=False)
            ws = w.sheets[nm[:31]]
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, max(len(t), 1), max(len(t.columns) - 1, 0))
            for i, c in enumerate(t.columns):
                wide = c in ("best_doc_url", "doc_source", "link_docs",
                             "link_home", "gh_homepage", "github_url",
                             "metric", "link_changelog", "link_wiki")
                ws.set_column(i, i, 46 if wide else 16,
                              num if c in ("downloads", "methods_total",
                                           "methods_documented", "value")
                              else None)
                ws.write(0, i, str(c), hdr)
    log("wrote " + os.path.basename(path))
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
