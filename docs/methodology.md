# Methodology

How the package set was chosen, how methods were counted, and how
documentation was located — for RubyGems and NuGet.

---

## 1. Choosing which packages to study

Three independent selections, then a union. Each answers a different question,
and none is sufficient alone.

```
top 100 repos by stars   → their direct dependencies
top 100 repos by forks   → their direct dependencies
90% of registry downloads
─────────────────────────────────────────────────────
union = the package set
```

**Why three.** Downloads measure what machines install; dependencies measure
what humans write. They overlap far less than you would expect — Jaccard 0.42
for Ruby, 0.21 for C#. Downloads over-weight packages that arrive
transitively through an SDK and that nobody ever names, while dependency lists
over-weight test and build tooling.

**Direct dependencies only.** GitHub's dependency-graph SBOM returns direct and
transitive flattened into one `packages` array — 1,084 entries for
`rails/rails` where only 338 are declared. The distinction is recoverable from
the same response, because the SBOM also carries a `relationships` graph:

| edge | meaning |
|---|---|
| `DESCRIBES` | the document → the repository's own root node |
| `DEPENDS_ON` | package → package |

A dependency is **direct** when the edge starts at the root node. Anything else
was pulled in by a dependency. This costs no extra requests.

**Ecosystem filter.** Repositories declare dependencies across many
ecosystems — a Ruby repo's SBOM is roughly 70% npm. Each package carries a
purl (`pkg:gem/…`, `pkg:nuget/…`), so filtering is exact. Filtering by name
instead would let npm packages through wherever a name collides, which
measured at 19% of the Ruby set.

**Result**

| | Ruby | C# |
|---|---|---|
| direct deps, top-100 stars | 2,117 | 2,185 |
| direct deps, top-100 forks | 1,906 | 2,339 |
| 90% download coverage | 1,841 | 1,100 |
| **union** | **2,814** | **3,352** |

---

## 2. Counting methods

The two ecosystems need different tools, because the published artifact is a
different kind of thing.

| | Ruby | C# |
|---|---|---|
| `.gem` / `.nupkg` contains | **source code** | **compiled IL** |
| so we | parse it | read the metadata tables |
| tool | tree-sitter | `dnfile` |

### Ruby

1. Download the `.gem` (a tar whose payload is a nested `data.tar.gz`).
2. Keep `lib/**.rb`; drop tests, specs, examples, vendor.
3. Parse with tree-sitter and walk the AST.
4. Deduplicate by full signature (`Rake::Application#load_rakefile`).

Counting nodes, not text, is what makes `attr_accessor :a, :b` resolve to four
methods with zero `def`s, and keeps `def` inside a comment or string from
counting.

**Visibility** is a sticky mode, not a property of a definition: `private` on
its own line flips state for everything after it until the class body ends. The
trap is that a bare `private` parses as an **`identifier`**, not a `call` — a
scan that inspects only call nodes silently reports ~1.5% private against a
true 9.2%.

**Native extensions** are counted by whether the code *registers a Ruby
method*, not by file extension:

| mechanism | registers? | counted |
|---|---|---|
| C/C++ `rb_define_method` | yes | ✅ |
| Rust `magnus` | yes | ✅ |
| Java `@JRubyMethod` | only under JRuby | opt-in |
| bundled Go binary | no — a subprocess | ✅ correctly skipped |

The declaring class is captured from the `rb_define_method` call, so
`Node#children` and `Document#children` stay distinct. Without it they collapse
into one bucket — which was costing openssl 66% of its native methods.

### C#

1. Range-read the last 64 KB of the `.nupkg` — a zip keeps its index at the
   end, so this yields the full file list without downloading the package.
2. Choose **one** assembly. Newtonsoft.Json ships eight builds of itself; each
   `lib/<tfm>/` is the same API again. `ref/` is preferred over `lib/` because
   a reference assembly is public surface with the bodies stripped.
3. Range-read only that assembly's bytes.
4. Read `TypeDef` / `MethodDef` / `Property` / `Event` with `dnfile`.

This is more accurate than parsing source, not a compromise: the metadata
tables *are* the public surface, and visibility is a flag rather than something
to infer.

**Counted** when a method is public, protected or protected-internal, its
declaring type is publicly visible, and it is not `SpecialName`. That last flag
removes property `get_`/`set_` and event `add_`/`remove_` accessors, which are
real `MethodDef` rows but not separate APIs — properties and events are counted
once each from their own tables. Constructors and operators also carry
`SpecialName`; they are reported in their own columns and excluded from
`api_total`.

Assemblies over 24 MB are recorded as `too_large`: `dnfile` is pure Python and
took 4,719 seconds on one 76 MB assembly against 6 seconds to fetch it.

---

## 3. Finding documentation

Documentation ships **inside the package** in both ecosystems, which makes
scraping largely unnecessary.

| | Ruby | C# |
|---|---|---|
| where | doc comments in the source, plus README | an XML file beside each assembly |
| format | free prose | structured `<summary>` / `<param>` / `<returns>` |
| present for | 96.2% | 74.4% |

A Ruby doc comment is the run of `comment` nodes ending on the line immediately
above a `def`.

**A documentation link is not evidence of documentation.** 1,503 gems point at
rubydoc.info, which generates a page by running YARD over the gem's own
source — the page exists whether or not anyone wrote a word. 459 gems declare a
docs URL and have **0%** documented methods. So `doc_coverage_pct` is reported
beside every URL.

**Package file beats scraping by ~50×.** Recovering a gem's documentation from
rubydoc.info means one request per class page: 134,963 requests across the set
against 2,201 gem downloads, for content that is generated from the source you
would be downloading anyway.

---

## Known limits

**Ruby counts are a floor.** `method_missing`, `define_method` with a computed
name, and `class_eval` on strings are invisible to any parser. C# has no
equivalent gap — IL metadata is complete by construction. Cross-ecosystem
comparisons are therefore biased against Ruby by an unknown amount.

**Headline totals are not comparable.** Ruby's total is all methods; C#'s
`api_total` is public surface and is 58% properties, a construct Ruby lacks —
an `attr_accessor` is simply two ordinary methods, already inside Ruby's total.
Compare `functions_public` against `methods_public`.

**C# has no control-flow data, and cannot.** `if`, `while`, `for` and `foreach`
compile to identical IL branch opcodes. The distinction is destroyed at compile
time and no amount of effort recovers it. Ruby has it because the source
survives in the package.

**381 C# packages have no countable API.** 329 are metapackages that ship zero
`.dll` files — verified against their repositories, where the source folder is
a `.csproj` and a `.nuspec` with no code. 45 are native binaries with no IL.
7 are too large to parse. These are genuine zeros, not measurement failures.
