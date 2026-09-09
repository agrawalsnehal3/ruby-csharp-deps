# Whether each package is documented, and where the documentation is

A documentation link is not evidence of documentation. 93% of gems have a rubydoc.info page, but that page is generated from the gem's own source -- 532 gems have one and zero documented methods. `doc_coverage_pct` is the column that means something.

## Files

| file | size |
|---|---|
| `documentation-summary.csv` | 3 KB |
| `documentation.csv` | 1.4 MB |

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
