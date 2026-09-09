# How large each package's public API is

The core measurement. Method counts per package, split by visibility.

Ruby is parsed from source; C# is read from compiled IL metadata. Different tools because a .gem contains code and a .nupkg contains a compiled assembly.

## Files

| file | size |
|---|---|
| `api-method-counts-other-assemblies.csv` | 71 KB |
| `api-method-counts.csv` | 891 KB |
| `api-summary.csv` | 1 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/count-methods.py`

The entry point. Ruby: downloads each .gem, unpacks it in memory, parses every .rb with tree-sitter. C#: reads the zip index with a ranged request, picks one assembly, and reads its metadata tables. Append-only and resumable.

---

_The same folder exists in `ruby/` and answers the same question for that language._
