# What those repositories declare they depend on

Direct dependencies only. GitHub's SBOM returns direct and transitive flattened together -- 1,084 packages for rails/rails, of which only 338 are declared. A package pulled in by something else was never a choice anyone made, so it is excluded.

## Files

| file | size |
|---|---|
| `dependency-summary-by-repository.csv` | 8 KB |
| `direct-dependencies.csv` | 767 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/select-packages.py`

Reads each cached SBOM and keeps only edges starting at the repository's own root node, which is what makes a dependency direct. Filters to this language using the SPDX purl, so an npm package sharing a gem's name cannot slip through.

---

_The same folder exists in `ruby/` and answers the same question for that language._
