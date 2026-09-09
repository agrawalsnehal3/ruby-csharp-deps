# How the C# data was collected

Everything in `csharp/` is derived from data collected before any analysis
began. This explains where that data came from.

---

## The short version

**NuGet publishes no database dump.** Unlike RubyGems, there is no file to
download containing the registry. Every fact had to be pulled from the public
V3 API, and no single endpoint carries everything needed — so three were used,
each for what only it provides.

That is the whole reason this side took 4.4 GB of harvesting where Ruby took
one download.

---

## The sources

| Source | Size | What only it gives |
|---|---|---|
| V3 catalog | 4.4 GB | Full nuspec, including `<repository>` |
| V3 search service | 71 MB | Download counts, owners, verified flag |
| nuget.org page scrape | 28 MB | Computed frameworks, "Used By" counts |

### 1. The catalog — for metadata

Two endpoints could have supplied package metadata, and only one is complete:

| Endpoint | Problem |
|---|---|
| `registration5-gz-semver2` | One request per package, but its `catalogEntry` **omits `<repository>`** — the field the census reports as `with_repository`. Using it would have baked a permanent zero into that column. |
| **the catalog** | An append-only log of every publish event. Its leaves are permalinks carrying the full nuspec projection, `repository` included, plus `packageSize`, `packageHash` and `created`. |

So the catalog it is — 4.4 GB of publish events, read in two passes and
projected down to one row per package.

### 2. The search service — for download counts

The catalog records publish events and manifests. A download count is neither,
so it is not there. The only public source is the V3 search service, which is
also the only source for `owners` and the prefix-reservation `verified` flag.

Three things matter about these numbers:

**They are cumulative for all time.** No windowed figure exists anywhere in the
API — no week, month or year field. nuget.org renders a "Last 6 Weeks" chart,
but only for the top ~200 packages and only as JavaScript in a web page, not an
endpoint. A time series would have to be built by snapshotting and differencing
later runs.

**The V2 API would have given wrong answers.** Its `DownloadCount` saturates at
int32 max, so Newtonsoft.Json reports **2,147,483,647** there against a true
**9,039,911,147**. Every package past ~2.1 billion returns the same wrong
number.

**Coverage is partial by construction.** The search index holds ~481k packages
against the catalog's **844,471** — unlisted packages are absent entirely. Those
are recorded as `not_indexed` rather than dropped, because *absent from the
index* and *zero downloads* are different facts.

### 3. The page scrape — for what the API cannot express

The gallery page carries things no endpoint exposes:

- **Computed target frameworks.** The nuspec declares what a package *targets*
  (`net6.0`); the gallery runs NuGet's compatibility rules and shows what it is
  *usable from*. Newtonsoft.Json declares 3 frameworks and is compatible with
  100+. Only the page knows.
- **"Used By"** — NuGet's own dependent-package count and its count of GitHub
  repositories referencing the package.
- Prefix reservation, per-day download average, rendered package sizes.
- Deprecation, vulnerability and unlisted banners as a consumer sees them.

---

## How it fits together

    V3 catalog        ─┐
    search service    ─┼─→ all_package_nuget.csv ─→ frame_nuget.csv
    page scrape       ─┤        (32 columns)          (45 columns)
    GitHub API        ─┘                                    │
                                                            ▼
                                        everything in this repository

`frame_nuget.csv` is the file the census scripts read. One row per package,
844,471 of them.

---

## Two columns that are deliberately empty

`dependency_count_all_versions` and `reverse_dependency_count_all_versions` are
emitted blank rather than silently dropped. NuGet metadata is latest-version
only, so an all-versions dependency picture would need a separate harvest of
about **23 hours**. The `*_latest` columns are populated.

---

## What is not in this repository

The raw sources total roughly **5.8 GB** and are excluded by `.gitignore`. They
are inputs, not findings, and they are re-fetchable from the public API —
though the catalog pass alone takes several hours.

What is committed is everything computed *from* them.

---

## Compared with RubyGems

The Ruby side was collected from a published database dump in a single
download. See [`ruby/data-collection/`](../../ruby/data-collection/).
