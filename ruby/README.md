# RubyGems packages

**2,814 packages** selected from the 100 most-starred and 100 most-forked Ruby repositories on GitHub, plus the packages covering 90% of all RubyGems downloads.

---

## Which packages were selected

Three signals, combined. A package qualifies if any one of them picks it.

| Signal | Packages |
|---|---|
| stars | 2,117 |
| forks | 1,906 |
| downloads (90%) | 1,841 |
| **Union — the studied set** | **2,814** |

### Where each package came from

| Signals that picked it | Packages | Share |
|---|---|---|
| stars + forks + downloads | 1,119 | 39.8% |
| stars + forks | 711 | 25.3% |
| downloads | 621 | 22.1% |
| stars | 209 | 7.4% |
| stars + downloads | 78 | 2.8% |
| forks | 53 | 1.9% |
| forks + downloads | 23 | 0.8% |

### How much the signals agree

Jaccard = shared ÷ combined. 1.0 would mean identical sets.

| Pair | Shared | Combined | Jaccard |
|---|---|---|---|
| forks ↔ stars | 1,830 | 2,193 | **0.83** |
| downloads ↔ stars | 1,197 | 2,761 | **0.43** |
| downloads ↔ forks | 1,142 | 2,605 | **0.44** |

No pair is close to 1.0, so no signal is redundant — that is the reason for combining all three rather than picking one. Downloads measure what machines install; stars and forks measure what people write.

---

## How large the APIs are

| Measure | Count | Share |
|---|---|---|
| Methods, all visibilities | 1,140,669 | 100% |
| — public | **1,028,895** | 90.2% |
| — private | 101,806 | 8.9% |
| — protected | 9,968 | 0.9% |
| Defined in C, C++ or Rust | 9,123 | 0.8% |

| | |
|---|---|
| Gems counted | 2,808 of 2,814 |
| Median methods per gem | 67 |
| Mean methods per gem | 406.2 |
| Largest | 186,722 (google-api-client) |
| Gems with native extensions | 185 |

> Counts are a **lower bound**. `method_missing` and `define_method` with a computed name cannot be seen by a parser.

---

## Documentation

### What each package has

| Source | Packages | Share |
|---|---|---|
| A site someone wrote | 555 | 19.8% |
| Tool-generated page (rubydoc.info) | 2,622 | 93.4% |
| README inside the package | 2,143 | 76.3% |
| docs/ folder inside the package | 149 | 5.3% |
| GitHub wiki | 1,268 | 45.2% |
| Homepage | 2,750 | 97.9% |

### How much is actually written

A method counts as documented when a comment sits directly above it.

| | |
|---|---|
| Methods examined | 809,967 |
| Methods with a comment | **370,879** (45.8%) |
| Median coverage per package | 27.4% |
| Packages at 0% | 487 |
| Packages above 80% | 293 |

> A documentation **link** is not evidence of documentation. rubydoc.info builds a page for every gem automatically, so the page exists whether or not anyone wrote a word. `doc_coverage_pct` is the column that means something.

Packages with at least one working link: **2,769** of 2,808.

---

## What it costs to download

| | | |
|---|---|---|
| TOTAL download size (GB) | **1.39** | every package at its current version |
| mean package size (KB) | **485** |  |
| median package size (KB) | **28** |  |
| largest package (MB) | **257.2** | wkhtmltopdf-binary |
| versions published in total | **202083** | sum of version_count across all packages |
| mean versions per package | **72** |  |
| ESTIMATED size of all versions (GB) | **250.9** | version_count x latest size -- an over-estimate, since packages grow a |

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

The same folders exist in [`csharp/`](../csharp/) and answer the same questions for that language. Every column is described in [`docs/data-dictionary.md`](../docs/data-dictionary.md).
