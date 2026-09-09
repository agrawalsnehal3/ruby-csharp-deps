# Third-party packages: selection, API size and documentation

A census of widely-used **RubyGems** and **NuGet** packages — which ones
matter, how large their public API is, and whether they are documented.

| | Ruby | C# |
|---|---|---|
| packages studied | **2,814** | **3,352** |
| public methods | **1,028,895** | **1,381,956** |
| versions catalogued | 202,083 | 269,847 |
| documentation available | 99.3% | 93.7% |
| obtainable without scraping | 96.4% | 74.6% |
| download size, latest versions | 1.4 GB | 8.7 GB |

---

## How packages were chosen

Three selections, combined:

    direct dependencies of the top 100 repositories by stars   ─┐
    direct dependencies of the top 100 repositories by forks   ─┼─→ union
    the packages covering 90% of all registry downloads        ─┘

Downloads measure what machines install. Dependencies measure what people
write. They agree far less than you would expect:

| overlap (Jaccard) | Ruby | C# |
|---|---|---|
| stars ↔ forks | 0.83 | 0.53 |
| downloads ↔ stars | 0.43 | 0.23 |
| downloads ↔ forks | 0.44 | 0.23 |

No pair is close to 1.0, so no selection is redundant — that is the case for
using all three rather than picking one.

**Direct dependencies only.** GitHub's dependency-graph SBOM returns direct
and transitive flattened together: 1,084 packages for `rails/rails`, of which
only 338 are declared. The direct ones are recovered from the SBOM's own
`relationships` graph — an edge starting at the repository's root node is
direct; anything else was pulled in by a dependency.

---

## Layout

    Third_party_packages/
    │
    ├── ruby/                          ← everything about RubyGems
    │   ├── step-1-github-repositories/    which repos we studied
    │   ├── step-2-their-dependencies/     what they declare
    │   ├── step-3-selected-packages/      the studied set + overlap
    │   ├── step-4-method-counts/          how big each API is
    │   ├── step-5-documentation/          is it documented, and where
    │   ├── step-6-versions-and-links/     every version, repo, README
    │   └── step-7-package-sizes/          bytes to download
    │
    ├── csharp/                        ← identical structure, NuGet
    │
    └── docs/                          ← methodology

`ruby/` and `csharp/` mirror each other, so the same question lives at the same
path in both and the two can be diffed folder by folder. Every folder has a
README explaining what is in it.

---

## How it was measured

|  | Ruby | C# |
|---|---|---|
| the package contains | **source code** | **compiled IL** |
| so we | parse it (tree-sitter) | read metadata tables (dnfile) |
| visibility | inferred from a sticky mode | a flag — exact |
| documentation | doc comments + README | compiler-emitted XML |

Different tools because the published artifact is a different kind of thing —
not a preference.

---

## Reading the numbers

**The two languages are reported separately and are not directly comparable.**
C# counts properties, which Ruby has no concept of -- an `attr_accessor` is
simply two ordinary methods, already inside Ruby's figure. Each tree carries
its own summary with the caveats that apply to it.

**Ruby counts are a lower bound.** `method_missing`, and `define_method` with
a name computed at runtime, are invisible to any parser. C# is read from
compiled metadata and has no equivalent blind spot.

**A documentation link is not evidence of documentation.** 93% of gems have a
rubydoc.info page, but that page is generated from the gem's own source — 532
gems have one and zero documented methods. `doc_coverage_pct` is the column
that means something.

Every file and column is described in `docs/data-dictionary.md`.
To download the packages themselves, see `docs/fetching-packages.md`.
The method and its limits are in `docs/methodology.md`.

---

## Running it

    pip install -r requirements.txt

Each stage folder carries the scripts that produced it, and its README says
what each one does. Run them in stage order: repositories, dependencies,
package-selection, api-surface, documentation, releases, storage-footprint.
Every stage is append-only and resumable: an interrupted run continues where
it stopped rather than starting over.

Requires a GitHub token in `GITHUB_TOKEN` for the repository and SBOM fetches.
