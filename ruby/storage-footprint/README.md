# What it costs to download the whole set

Size of every selected package, the distribution, and an estimate for every published version.

The all-versions figure is version_count x latest size: an over-estimate, since packages grow and older versions are smaller. Treat it as a ceiling.

## Files

| file | size |
|---|---|
| `storage-requirements.csv` | 149 KB |
| `storage-summary.csv` | 1 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/report-storage-requirements.py`

Aggregates package sizes from the census runs. For C# it also reports bytes actually transferred, which ranged reads keep far below the package sizes.

## How this data was obtained

Sizes recorded during the method census -- the Content-Length of each `.gem` as it was fetched. The all-versions figure multiplies that by the version count.

Scripts: `report-storage-requirements.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `bytes` | Size of the current version | Content-Length of the .gem / .nupkg |
| `size_mb` | The same in MB | Computed |
| `version_count` | Every published version | Registry version list |
| `all_versions_bytes_est` | version_count x latest size | Computed. An over-estimate -- packages grow, so older versions are smaller than the one this extrapolates from |

Other columns: `all_versions_gb_est`, `metric`, `note`, `package`, `stable_versions`, `value`, `version`

---

_The same folder exists in `csharp/` and answers the same question for that language._
