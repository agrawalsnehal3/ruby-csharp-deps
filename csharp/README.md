# NuGet packages

**3,352 packages** selected from the 100 most-starred and 100 most-forked C# repositories on GitHub, plus the packages covering 90% of all NuGet downloads.

---

## Which packages were selected

Three signals, combined. A package qualifies if any one of them picks it.

| Signal | Packages |
|---|---|
| stars | 2,185 |
| forks | 2,339 |
| downloads (90%) | 1,100 |
| **Union — the studied set** | **3,352** |

### Where each package came from

| Signals that picked it | Packages | Share |
|---|---|---|
| stars + forks | 1,006 | 30.0% |
| forks | 680 | 20.3% |
| stars | 566 | 16.9% |
| stars + forks + downloads | 564 | 16.8% |
| downloads | 398 | 11.9% |
| forks + downloads | 89 | 2.7% |
| stars + downloads | 49 | 1.5% |

### How much the signals agree

Jaccard = shared ÷ combined. 1.0 would mean identical sets.

| Pair | Shared | Combined | Jaccard |
|---|---|---|---|
| forks ↔ stars | 1,570 | 2,954 | **0.53** |
| downloads ↔ stars | 613 | 2,672 | **0.23** |
| downloads ↔ forks | 653 | 2,786 | **0.23** |

No pair is close to 1.0, so no signal is redundant — that is the reason for combining all three rather than picking one. Downloads measure what machines install; stars and forks measure what people write.

---

## How large the APIs are

| Measure | Count |
|---|---|
| Public methods | **1,316,375** |
| Properties | 1,268,587 (counted once, not get+set) |
| Events | 19,964 |
| **API members total** | **2,604,926** |
| Constructors | 375,984 (reported separately) |
| Operators | 40,087 (reported separately) |
| Every method incl. private | 6,060,400 |

| | |
|---|---|
| Packages counted | 2,849 of 3,352 |
| Median API members | 131 |
| Largest | 128,943 (Microsoft.Graph) |

### Packages with no countable API

These are real zeros, not failures — they ship no callable managed code.

| Reason | Packages |
|---|---|
| metapackage | 268 |
| native_only | 116 |
| tools_only | 91 |
| no_lib_dll | 21 |
| too_large | 5 |
| error:ValueError | 2 |

---

## Documentation

### What each package has

| Source | Packages | Share |
|---|---|---|
| A site someone wrote | 1,229 | 36.7% |
| README inside the package | 1,182 | 35.3% |
| XML doc file inside the package | 2,182 | 65.1% |
| Homepage | 2,606 | 77.7% |

### How much is actually written

A method counts as documented when a comment sits directly above it.

| | |
|---|---|
| Coverage percentage | not measurable |

> There is no coverage percentage for C#. The compiler records the comments that were written and nothing about the members that were not, so there is no denominator to divide by.

### Do the links still work?

Every distinct URL was fetched once.

| Link type | Links | Working | Dead | Dead % |
|---|---|---|---|---|
| homepage | 744 | 735 | 9 | 1.2% |
| handwritten_site | 281 | 251 | 19 | 6.8% |
| **ALL LINK TYPES** | **1,025** | **986** | **28** | **2.7%** |

Packages with at least one working link: **2,379** of 3,352.

---

## What it costs to download

| | | |
|---|---|---|
| TOTAL download size (GB) | **8.72** | every package at its current version |
| mean package size (KB) | **2541** |  |
| median package size (KB) | **193** |  |
| largest package (MB) | **260.3** | Mongo2Go |
| versions published in total | **269847** | sum of version_count across all packages |
| mean versions per package | **80.5** |  |
| ESTIMATED size of all versions (GB) | **1072.8** | version_count x latest size -- an over-estimate, since packages grow a |
| actually downloaded (MB) | **202.2** | ranged reads fetch only the zip index and one assembly |
| saving vs full download | **97.7%** |  |

---

## Folders

| Folder | What it answers |
|---|---|
| [`repositories`](repositories/) | The GitHub projects the study starts from |
| [`dependencies`](dependencies/) | What those projects declare they depend on |
| [`package-selection`](package-selection/) | The packages studied, and why each was included |
| [`api-surface`](api-surface/) | How many methods each package exposes |
| [`documentation`](documentation/) | Whether each package is documented, and where |
| [`releases`](releases/) | Every published version, with repository and registry links |
| [`storage-footprint`](storage-footprint/) | Bytes required to fetch the set |

Each folder holds its data, a `scripts/` subfolder with the code that produced it, and a README explaining both.

The same folders exist in [`ruby/`](../ruby/) and answer the same questions for that language. Every column is described in [`docs/data-dictionary.md`](../docs/data-dictionary.md).
