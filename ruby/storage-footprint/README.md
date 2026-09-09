# What it costs to download the whole set

Size of every selected package, the distribution, and an estimate for every published version.

The all-versions figure is version_count x latest size: an over-estimate, since packages grow and older versions are smaller. Treat it as a ceiling.

## Files

| file | size |
|---|---|
| `storage-requirements.xlsx` | 147 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/report-storage-requirements.py`

Aggregates package sizes from the census runs. For C# it also reports bytes actually transferred, which ranged reads keep far below the package sizes.

---

_The same folder exists in `csharp/` and answers the same question for that language._
