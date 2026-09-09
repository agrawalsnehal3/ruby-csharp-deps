# Whether each package is documented, and where the documentation is

A documentation link is not evidence of documentation. 93% of gems have a rubydoc.info page, but that page is generated from the gem's own source -- 532 gems have one and zero documented methods. `doc_coverage_pct` is the column that means something.

## Files

| file | size |
|---|---|
| `documentation-availability.xlsx` | 200 KB |
| `documentation-coverage--best-documented.csv` | 85 KB |
| `documentation-coverage--custom-doc-sites.csv` | 118 KB |
| `documentation-coverage--gems.csv` | 927 KB |
| `documentation-coverage--no-docs-at-all.csv` | 21 KB |
| `documentation-coverage--summary.csv` | 1 KB |
| `documentation-coverage.xlsx` | 746 KB |
| `documentation-sources.xlsx` | 692 KB |
| `primary-documentation-link--all-gems.csv` | 989 KB |
| `primary-documentation-link--custom-doc-sites.csv` | 109 KB |
| `primary-documentation-link--docs-on-rubygems.csv` | 957 KB |
| `primary-documentation-link--docs-only-on-github.csv` | 29 KB |
| `primary-documentation-link--no-docs-found.csv` | 4 KB |
| `primary-documentation-link--summary.csv` | 1 KB |
| `primary-documentation-link.xlsx` | 1.1 MB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/collect-all-doc-links.py`

Collects every link a package has, separated by kind: hand-written site, tool-generated, README, docs folder, wiki, homepage. They are not equivalent and are kept apart.

### `scripts/find-doc-links.py`

Decides where a gem's documentation actually lives: registry first, then GitHub. Records how strong that evidence is rather than just returning a URL.

### `scripts/measure-doc-coverage.py`

Parses the cached gems and measures what share of each one's methods carry a doc comment, plus which documentation files it ships.

---

_The same folder exists in `csharp/` and answers the same question for that language._
