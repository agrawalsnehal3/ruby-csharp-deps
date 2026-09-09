# Data dictionary

Every file in this project, what it holds, and what its columns mean.

Paths below are relative to `ruby/` or `csharp/` — the two trees mirror each
other, so a path that exists in one usually exists in the other.

---

## step-1-github-repositories

**`top-100-by-stars.csv`, `top-100-by-forks.csv`** — the repositories the study
starts from.

| column | meaning |
|---|---|
| `rank` | position in that ranking, 1 = most stars / forks |
| `repository` | `owner/name` on GitHub |
| `stars`, `forks` | counts at fetch time |
| `dependency_status` | `available` if GitHub returned a dependency SBOM |
| `dependency_count` | packages in the SBOM, all ecosystems, before filtering |

---

## step-2-their-dependencies

**`direct-dependencies.csv`** — one row per (repository, package) the
repository *declares*. Transitive dependencies are excluded.

| column | meaning |
|---|---|
| `repository` | which repo declares it |
| `ranking` | `stars` or `forks` — which list it came from |
| `package` | the dependency |
| `version` | the declared constraint, as written |
| `ecosystem` | from the SBOM purl: `gem`, `nuget`, `npm`, … |

**`summary-per-repository.csv`** — one row per repository.

| column | meaning |
|---|---|
| `direct_deps` | direct dependencies in every ecosystem |
| `direct_in_ecosystem` | only those in the registry being studied |
| `status` | `ok`, or why the SBOM could not be read |

---

## step-3-selected-packages

**`selected-packages.csv`** — the studied set.

| column | meaning |
|---|---|
| `package` | lowercase key used for matching |
| `registry_name` | the registry's own casing — use this for URLs |
| `downloads` | all-time downloads |
| `in_stars`, `in_forks`, `in_downloads_90pct` | which selections include it |
| `sources` | the same, as text: `stars+forks+downloads` |

**`selection-overlap.xlsx`** — how much the three selections agree.
`overlap` sheet: `jaccard` = shared ÷ combined. 1.0 identical, 0 disjoint.

**`download-coverage-90pct.xlsx`** — the download selection.
`packages` sheet is ranked by downloads with a running `cumulative_share_pct`.
`how_the_curve_behaves` gives the packages needed at 10% … 99.9%.

**`download-coverage-95pct.xlsx`** — the same at 95%. Reference only; nothing
downstream reads it.

---

## step-4-method-counts

**`method-counts-per-package.csv`** — the core measurement.

Ruby:

| column | meaning |
|---|---|
| `functions` | unique methods, deduplicated by signature |
| `functions_public` / `_private` / `_protected` | by visibility; these sum to `functions` |
| `functions_ruby`, `functions_native` | before dedup, by where they are defined |
| `native_languages` | `c`, `cpp`, `rust`, or a combination |
| `rb_files`, `native_files` | files parsed |
| `lines_code`, `lines_total` | non-blank, non-comment lines, and all lines |
| `parse_errors` | files tree-sitter could not parse |
| `status` | `ok`, or why not |

C#:

| column | meaning |
|---|---|
| `methods_public` | public + protected methods on public types, accessors excluded |
| `methods_private`, `methods_protected`, `methods_internal` | by visibility |
| `properties`, `events` | counted once each, not as get/set pairs |
| `ctors`, `operators` | reported separately, **not** inside `api_total` |
| `api_total` | `methods_public + properties + events` |
| `methoddef_rows` | every method in the assembly, including private |
| `tfm` | which target framework was counted |
| `asset_kind` | `lib`, `ref`, or a fallback folder such as `analyzers` |
| `status` | `ok`; or `metapackage` / `native_only` / `tools_only` — real zeros, not failures |

**`parsed-methods.csv.gz`** (Ruby) — the individual methods behind the counts.
1.17 million rows.

| column | meaning |
|---|---|
| `sig` | `Rake::Application#load_rakefile` — `#` instance, `.` singleton |
| `kind` | `instance`, `singleton`, `attr_reader`, `attr_writer`, `alias`, `define_method`, `native_*` |
| `visibility` | `public`, `private`, `protected` |
| `class` | enclosing module/class path |
| `file`, `start_line`, `end_line`, `loc` | where it is defined |
| `n_params`, `n_calls`, `n_raises`, `yields` | shape of the method |

**`method-counts-non-lib-assemblies.csv`** (C#) — packages with no `lib/`,
counted instead from `analyzers/`, `build/` or `tools/`.

---

## step-5-documentation

**`all-documentation-links.xlsx`** — every link, separated by kind.

| column | meaning |
|---|---|
| `handwritten_site` | documentation somebody wrote and maintains |
| `tool_generated_docs` | rubydoc.info — generated from the source; exists even with zero comments |
| `readme_in_package`, `docs_folder_in_package` | shipped inside the package |
| `xml_docs_in_package` | C#: compiler-emitted XML beside the assembly |
| `github_docs_folder`, `github_wiki`, `github_pages` | on the repository |
| `homepage`, `changelog`, `registry_page` | other links |
| `doc_types_available` | which kinds this package has |
| `link_count` | how many distinct links |
| `doc_coverage_pct` | Ruby: share of methods carrying a doc comment |

**`how-much-is-documented.xlsx`** (Ruby) — doc-comment coverage per gem.
**`where-the-docs-are.xlsx`** (Ruby) — one `best_doc_url` per gem, plus
`doc_source` saying how strong that evidence is.
**`xml-doc-files.csv`** (C#) — `xml_doc` path and `xml_bytes` per package.

---

## step-6-versions-and-links

**`all-versions.csv`** — one row per (package, version). 202,083 Ruby rows;
269,847 C#.

| column | meaning |
|---|---|
| `version` | as published |
| `released` | Ruby only |
| `platform` | `ruby`, `java`, `x86_64-linux`, … |
| `prerelease` | true for betas and release candidates |

**`package-inventory.csv`** — one row per package: `version_count`,
`stable_version_count`, `github_url`, `registry_url`, `doc_site_url`,
`readme_file`, `docs_folder_files`, `has_xml_docs`.

---

## step-7-package-sizes

**`package-sizes.xlsx`**

| column | meaning |
|---|---|
| `bytes`, `size_mb` | the current version |
| `version_count` | every published version |
| `all_versions_bytes_est` | `version_count x latest size` — an over-estimate, since packages grow over time |
| `bytes_read` | C#: what a ranged read actually transferred |

---

## comparison

**`method-count-comparison.xlsx`** — Ruby and C# side by side. Every row is
labelled comparable or not: compare `functions_public` with `methods_public`,
never the headline totals, because the C# figure counts properties and Ruby
has no such concept.

**`documentation-availability.xlsx`** — per package: `has_docs`,
`downloadable`, `needs_scraping`, `download_url`.

---

## Values that recur

| value | meaning |
|---|---|
| `status = ok` | measured successfully |
| `status = metapackage` | ships no code at all — a real zero |
| `status = native_only` | platform binaries, no managed code |
| `status = tools_only` | analyzers or build tooling, not a callable API |
| `status = too_large` | assembly above the parser's size limit |
| empty `github_url` | the package publishes no repository |
