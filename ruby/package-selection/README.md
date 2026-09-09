# The packages this study measures, and why each is included

Three selections combined: direct dependencies of the top 100 by stars, the same by forks, and the packages covering 90% of registry downloads. The `sources` column records which of the three put each package here.

The download cut is 90%. A 95% file is included for reference but nothing reads it.

## Files

| file | size |
|---|---|
| `download-coverage-curve.csv` | 0 KB |
| `download-coverage.csv` | 263 KB |
| `selected-packages.csv` | 198 KB |
| `selection-overlap.csv` | 0 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/report-coverage-and-overlap.py`

Writes the download-coverage files and the overlap analysis. The overlap is the evidence for using three selections rather than one: no pair of them agrees closely enough to be redundant.

### `scripts/select-packages.py`

Builds the union and writes selected-packages.csv.

## How this data was obtained

Combined three sets: direct dependencies of the top 100 by stars, the same by forks, and the gems covering 90% of RubyGems downloads. Download ranking came from the database dump's lifetime totals, sorted descending with a running cumulative sum.

Scripts: `select-packages.py`, `report-coverage-and-overlap.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `package` | Lowercase key used for joining | Derived |
| `registry_name` | The registry's own casing -- use this for URLs | RubyGems dump / NuGet catalog |
| `downloads` | Lifetime downloads, all versions | RubyGems database dump / NuGet V3 search service |
| `in_stars` | Declared by a top-100-by-stars repository | SBOM direct dependencies |
| `in_forks` | Declared by a top-100-by-forks repository | SBOM direct dependencies |
| `in_downloads_90pct` | Inside the 90% download cut | Cumulative sum over the download ranking |
| `sources` | The three flags as text | Derived |
| `target_pct` | Which coverage cut this row belongs to (90 or 95) | Derived |
| `cumulative_share_pct` | Running share of registry downloads | Computed from the download ranking |
| `jaccard` | Shared / combined between two selections | Computed |

Other columns: `cumulative_downloads`, `in_both`, `in_either`, `name`, `packages_needed`, `pct_of_a_also_in_b`, `pct_of_b_also_in_a`, `rank`, `set_a`, `set_b`, `share_of_all_packages_pct`, `size_a`, `size_b`

---

_The same folder exists in `csharp/` and answers the same question for that language._
