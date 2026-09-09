# The packages this study measures, and why each is included

Three selections combined: direct dependencies of the top 100 by stars, the same by forks, and the packages covering 90% of registry downloads. The `sources` column records which of the three put each package here.

The download cut is 90%. A 95% file is included for reference but nothing reads it.

## Files

| file | size |
|---|---|
| `download-coverage-curve.csv` | 0 KB |
| `download-coverage.csv` | 239 KB |
| `selected-packages.csv` | 303 KB |
| `selection-overlap.csv` | 0 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/report-coverage-and-overlap.py`

Writes the download-coverage files and the overlap analysis. The overlap is the evidence for using three selections rather than one: no pair of them agrees closely enough to be redundant.

### `scripts/select-packages.py`

Builds the union and writes selected-packages.csv.

---

_The same folder exists in `ruby/` and answers the same question for that language._
