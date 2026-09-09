# Whether each package is documented, and where the documentation is

A documentation link is not evidence of documentation. 93% of gems have a rubydoc.info page, but that page is generated from the gem's own source -- 532 gems have one and zero documented methods. `doc_coverage_pct` is the column that means something.

## Files

| file | size |
|---|---|
| `documentation-summary.csv` | 1 KB |
| `documentation.csv` | 1.2 MB |
| `xml-documentation-files.csv` | 454 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/collect-all-doc-links.py`

Collects every link a package has, separated by kind: hand-written site, tool-generated, README, docs folder, wiki, homepage. They are not equivalent and are kept apart.

### `scripts/find-doc-files.py`

Locates the compiler-generated XML documentation inside each NuGet package, reading only the zip index.

---

_The same folder exists in `ruby/` and answers the same question for that language._
