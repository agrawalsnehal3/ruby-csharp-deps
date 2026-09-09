# Whether each package is documented, and where the documentation is

A documentation link is not evidence of documentation. 93% of gems have a rubydoc.info page, but that page is generated from the gem's own source -- 532 gems have one and zero documented methods. `doc_coverage_pct` is the column that means something.

## Files

| file | size |
|---|---|
| `documentation-link-status.csv` | 601 KB |
| `documentation-link-summary.csv` | 1 KB |
| `documentation-summary.csv` | 3 KB |
| `documentation.csv` | 1.4 MB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/check-doc-links.py`

Fetches every documentation URL once and records whether it resolves. A link in package metadata is a claim, not a fact -- 20% of hand-written Ruby doc sites no longer exist. GitHub URLs go through the authenticated API, because anonymous requests get rate-limited.

### `scripts/collect-all-doc-links.py`

Collects every link a package has, separated by kind: hand-written site, tool-generated, README, docs folder, wiki, homepage. They are not equivalent and are kept apart.

### `scripts/find-doc-links.py`

Decides where a gem's documentation actually lives: registry first, then GitHub. Records how strong that evidence is rather than just returning a URL.

### `scripts/measure-doc-coverage.py`

Parses the cached gems and measures what share of each one's methods carry a doc comment, plus which documentation files it ships.

## How this data was obtained

Three passes. First, doc-comment coverage: re-parsed the cached gems and counted methods with a comment run ending on the line above them. Second, link collection from the rubygems.org page scrape, with GitHub probed only for gems the registry had nothing for. Third, every distinct URL fetched once to see whether it still resolves.

Scripts: `measure-doc-coverage.py`, `find-doc-links.py`, `collect-all-doc-links.py`, `check-doc-links.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `doc_coverage_pct` | Share of methods with a comment above them | tree-sitter: a comment run ending on the line before a def |
| `methods_documented` | Methods carrying a doc comment | tree-sitter |
| `methods_total` | Methods examined | tree-sitter |
| `handwritten_site` | A documentation site someone wrote | rubygems.org / nuget.org page, excluding auto-generated hosts |
| `tool_generated_docs` | rubydoc.info page | The page's Documentation link, which rubygems.org fills in automatically when the gemspec declares none |
| `readme_in_package` | Path to the README inside the archive | Walking the .gem / .nupkg |
| `docs_folder_in_package` | Whether the archive ships docs/ or guides/ | Walking the .gem |
| `xml_docs_in_package` | Path to the compiler-generated XML file | Reading only the .nupkg zip index |
| `github_repo` | Repository URL | Declared repository field, or inferred from a homepage |
| `github_docs_folder` | docs/ folder in the repository | GitHub contents API, fallback only |
| `github_wiki` | Wiki URL, only where a wiki genuinely exists | GitHub API has_wiki, then verified by fetching |
| `homepage` | Homepage as declared | Registry page |
| `doc_types_available` | Which kinds of documentation exist | Derived |
| `link_count` | How many distinct links | Derived |
| `*_status` | Whether that link resolved | check-doc-links.py -- one fetch per distinct URL |
| `has_working_link` | At least one link resolves | Derived |

Other columns: `best_doc_url`, `best_doc_url_status`, `blocked`, `changelog`, `dead`, `dead_pct`, `doc_files`, `doc_source`, `docs_folder_files`, `documentation_location`, `download_url`, `downloads`, `final_url`, `github_docs_folder_status`, `github_pages`, `github_pages_status`, `github_wiki_status`, `handwritten_site_status` …

---

_The same folder exists in `csharp/` and answers the same question for that language._
