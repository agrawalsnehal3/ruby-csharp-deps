# How large each package's public API is

The core measurement. Method counts per package, split by visibility.

Ruby is parsed from source; C# is read from compiled IL metadata. Different tools because a .gem contains code and a .nupkg contains a compiled assembly.

## Files

| file | size |
|---|---|
| `api-method-counts.csv` | 349 KB |
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

## How this data was obtained

Downloaded each `.gem`, unpacked it in memory (a gem is a tar whose payload is a nested data.tar.gz), and parsed every `.rb` with tree-sitter. Counted `def`, `attr_*`, `define_method` and `alias`, then deduplicated by full signature. Visibility resolved by walking each class body in order carrying the current mode -- a bare `private` parses as an identifier, not a call, which is the trap. Native methods found by their registration call, not by file extension.

Scripts: `count-methods.py`, `lib-parser.py`, `lib-visibility.py`, `lib-native-extensions.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `functions` | Unique methods, deduplicated by signature | tree-sitter parse of the .gem |
| `functions_public` | Public methods | Sticky-mode visibility walk over each class body |
| `functions_private` | Private methods | Same walk |
| `functions_protected` | Protected methods | Same walk |
| `functions_ruby` | Methods found in .rb files, before dedup | tree-sitter |
| `functions_native` | Methods registered from C, C++ or Rust | rb_define_* and magnus patterns in the shipped source |
| `native_languages` | Which native languages the gem ships | File extensions present in the .gem |
| `lines_code` | Non-blank, non-comment lines | tree-sitter line pass |
| `parse_errors` | Files tree-sitter could not parse | tree-sitter has_error flag |
| `status` | ok; or metapackage / native_only / tools_only -- real zeros | Determined from the package's file list |

Other columns: `added`, `drift`, `functions_module_function`, `gem`, `gem_bytes`, `lines_total`, `metric`, `native_files`, `net`, `note`, `rb_files`, `released`, `removed`, `running_total`, `value`, `version`

---

_The same folder exists in `csharp/` and answers the same question for that language._
