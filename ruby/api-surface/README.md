# How large each package's public API is

The core measurement. Method counts per package, split by visibility.

Ruby is parsed from source; C# is read from compiled IL metadata. Different tools because a .gem contains code and a .nupkg contains a compiled assembly.

## Files

| file | size |
|---|---|
| `api-method-counts.csv` | 310 KB |
| `api-summary.csv` | 1 KB |
| `method-inventory.csv.gz` | 17.0 MB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/count-methods.py`

The entry point. Ruby: downloads each .gem, unpacks it in memory, parses every .rb with tree-sitter. C#: reads the zip index with a ranged request, picks one assembly, and reads its metadata tables. Append-only and resumable.

### `scripts/export-method-inventory.py`

Writes those records out. method-inventory.csv.gz holds 1.17 million of them.

### `scripts/lib-method-details.py`

Builds the per-method records -- parameters, calls, raises, control flow.

### `scripts/lib-native-extensions.py`

Methods registered from C, C++ and Rust. Selected by whether the code registers a Ruby method, not by file extension: a bundled Go binary is a subprocess and defines nothing.

### `scripts/lib-parser.py`

Extracts methods from a Ruby syntax tree. Counts attr_accessor and define_method, which create real methods without writing a def. Cross-validated against lizard.

### `scripts/lib-visibility.py`

Resolves public / private / protected. Visibility in Ruby is a sticky mode set by a bare word, and that bare `private` parses as an identifier rather than a call -- a scan that checks only call nodes reports about 1.5% private against a true 9%.

---

_The same folder exists in `csharp/` and answers the same question for that language._
