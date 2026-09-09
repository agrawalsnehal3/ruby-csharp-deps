# What those repositories declare they depend on

Direct dependencies only. GitHub's SBOM returns direct and transitive flattened together -- 1,084 packages for rails/rails, of which only 338 are declared. A package pulled in by something else was never a choice anyone made, so it is excluded.

## Files

| file | size |
|---|---|
| `dependency-summary-by-repository.csv` | 8 KB |
| `direct-dependencies.csv` | 767 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/select-packages.py`

Reads each cached SBOM and keeps only edges starting at the repository's own root node, which is what makes a dependency direct. Filters to this language using the SPDX purl, so an npm package sharing a gem's name cannot slip through.

## How this data was obtained

Identical, filtering on `pkg:nuget/`. For rails/rails the SBOM lists 1,084 packages of which only 338 are declared; for dotnet/runtime, 740 and 300.

Scripts: `select-packages.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `repository` | Which repository declares this dependency | GitHub search API |
| `ranking` | stars or forks -- which list the repository came from | Derived |
| `package` | The dependency's name | SBOM package entry |
| `version` | The constraint as declared, not resolved | SBOM versionInfo |
| `ecosystem` | gem, nuget, npm, githubactions ... | SBOM purl -- pkg:gem/ etc. Exact, not name-matched |
| `direct_deps` | Direct dependencies in every ecosystem | Counted from SBOM edges starting at the repository root node |
| `direct_in_ecosystem` | Only those in the registry being studied | The above, filtered by purl |
| `status` | ok, or why the SBOM could not be read | GitHub API response |

---

_The same folder exists in `ruby/` and answers the same question for that language._
