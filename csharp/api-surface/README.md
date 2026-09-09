# How large each package's public API is

The core measurement. Method counts per package, split by visibility.

Ruby is parsed from source; C# is read from compiled IL metadata. Different tools because a .gem contains code and a .nupkg contains a compiled assembly.

## Files

| file | size |
|---|---|
| `api-method-counts-other-assemblies.csv` | 71 KB |
| `api-method-counts.csv` | 627 KB |
| `api-summary.csv` | 1 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/count-methods.py`

The entry point. Ruby: downloads each .gem, unpacks it in memory, parses every .rb with tree-sitter. C#: reads the zip index with a ranged request, picks one assembly, and reads its metadata tables. Append-only and resumable.

## How this data was obtained

Read the last 64 KB of each `.nupkg` to get the zip index, chose one assembly by target-framework preference (Newtonsoft.Json ships eight builds of itself), then read only that assembly's bytes with a second ranged request and walked its IL metadata tables with dnfile. Transferred 202 MB against 8.7 GB of packages.

Scripts: `count-methods.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `methods_public` | Public and protected methods on public types, accessors excluded | IL metadata: MethodDef flags, read with dnfile |
| `properties` | Counted once each, not as get+set | IL Property table |
| `events` | Counted once each | IL Event table |
| `api_total` | methods_public + properties + events | Computed |
| `ctors` | Constructors -- not inside api_total | IL MethodDef named .ctor |
| `methoddef_rows` | Every method in the assembly, including private | IL MethodDef row count |
| `tfm` | Which target framework was counted | Chosen by preference order from the lib/ folders present |
| `asset_kind` | lib, ref, or a fallback folder such as analyzers | Path of the assembly inside the .nupkg |
| `status` | ok; or metapackage / native_only / tools_only -- real zeros | Determined from the package's file list |
| `bytes_fetched` | What the ranged read actually transferred | Measured during collection |
| `nupkg_bytes` | Full package size | HTTP Content-Range header |

Other columns: `all_types`, `assembly`, `assembly_bytes`, `fields_public`, `m_abstract`, `m_generic`, `m_sealed`, `m_static`, `m_virtual`, `methods_internal`, `methods_private`, `methods_protected`, `metric`, `note`, `operators`, `package`, `public_types`, `t_abstract` …

---

_The same folder exists in `ruby/` and answers the same question for that language._
