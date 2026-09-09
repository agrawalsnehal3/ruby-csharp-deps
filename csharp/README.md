# NuGet packages

3,352 packages: the direct dependencies of the top 100 C# repositories by stars and by forks, plus the packages covering 90% of all NuGet downloads.

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
`methods_public`, `methods_private`, `properties`, `events`, `api_total`,
`tfm` (which target framework was counted).
`status` separates real zeros -- `metapackage`, `native_only`, `tools_only` --
from failures. A metapackage ships no code at all, so zero is correct.

**`step-5-documentation/xml-doc-files.csv`**
`xml_doc` is the path to the compiler-generated documentation inside the
package; `xml_bytes` is its size.

**`step-6-versions-and-links/all-versions.csv`**
One row per (package, version).

