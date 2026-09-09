# RubyGems packages

2,814 gems: the direct dependencies of the top 100 Ruby repositories by stars and by forks, plus the gems covering 90% of all RubyGems downloads.

The two language trees are structured identically, so the same question
lives at the same path in both.

| folder | the question it answers |
|---|---|
| `repositories` | The GitHub projects the study starts from |
| `dependencies` | What those projects declare they depend on |
| `package-selection` | The packages studied, and why each was included |
| `api-surface` | How many methods each package exposes |
| `documentation` | Whether each package is documented, and where |
| `releases` | Every published version, with repository and registry links |
| `storage-footprint` | Bytes required to fetch the set |

Each folder has a README describing its files, and a `scripts/` subfolder
holding the code that produced them. To re-run a stage, gather that
folder's scripts into one directory first -- they import each other by
module name.

## Columns worth knowing

**`step-3-selected-packages/selected-packages.csv`**
`sources` -- which of stars / forks / downloads put this package in the set.

**`step-4-method-counts/method-counts-per-package.csv`**
`functions` (deduplicated total), `functions_public`, `functions_private`,
`functions_protected`, `functions_native` (methods defined from C, C++ or
Rust), `native_languages`.

**`step-5-documentation/where-the-docs-are.xlsx`**
`best_doc_url` and `doc_source` -- where the documentation is, and how strong
that evidence is. `doc_coverage_pct` says whether anything is actually there.

**`step-6-versions-and-links/all-versions.csv`**
One row per (package, version).

