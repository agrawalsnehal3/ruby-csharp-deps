# How we count APIs in a package

Plain-language explanation of what the two counting scripts do and why.

## The question

For each package (a Ruby gem or a NuGet package), we want one number:

> How many functions does this package offer to the people who use it?

Sounds simple. It isn't, because a package doesn't come with a list of its
functions. You have to open it up and look.

## Two ecosystems, two very different problems

The thing you download is different in each case, and that changes everything.

| | Ruby | NuGet (C#) |
|---|---|---|
| What's inside a package | **Source code** you can read | **Compiled code** — already turned into machine-ish instructions |
| So we must | Read the code and understand it | Read the built-in index that compilers leave behind |
| Tool used | tree-sitter | dnfile |

That's the single most important thing to understand. We are *not* using the
same method twice. We use whatever the package actually contains.

---

## Ruby: read the source code properly

A `.gem` file is just a compressed folder of Ruby source files.

**Step 1 — Get the package.** Download the `.gem` from rubygems.org. It's a
box inside a box, so we unpack it twice.

**Step 2 — Pick the real code.** Keep the `.rb` files. Throw away tests,
examples and documentation — those aren't part of what users call.

**Step 3 — Understand the code.** This is the important part. We do *not*
search for the word `def` with find-and-replace. That would be wrong in both
directions: it would miss functions and invent ones that don't exist.

Instead we use **tree-sitter**, which reads Ruby the way Ruby itself does. It
builds a proper tree of the program's structure. That lets us handle things a
simple text search can't:

- `attr_accessor :name` creates **two** functions (`name` and `name=`) while
  writing **zero** `def`s. A text search finds nothing. We find two.
- `def self.thing` is a different kind of function from `def thing`, and we
  label them correctly.
- The word `def` inside a comment or a string is not a function. tree-sitter
  knows the difference.

**Step 4 — Handle C code.** Some gems are partly written in C for speed
(nokogiri, for example). Those C files still create Ruby functions, using
calls named `rb_define_method`. We look for those too — otherwise those gems
would look almost empty.

**Step 5 — Remove duplicates.** The same function can be defined in two files.
We give every function a full name like `Rack::Builder#call` and count each
unique name once.

---

## NuGet: read the index the compiler already wrote

A `.nupkg` file contains a `.dll` — code that has already been compiled. You
can't read it like text. But you don't need to.

Every compiled .NET file carries a built-in **table of contents** listing every
type and every function, along with whether each one is public. The compiler
writes it automatically. We just read it.

This is *better* than reading source code, not a compromise:

- It's exact. No guessing, no interpretation.
- "Is this public?" is a yes/no flag, not something to work out.

**Step 1 — Don't download the package.** This is the trick that makes it fast.

A `.nupkg` is a ZIP file, and ZIP files keep their table of contents **at the
end**. So we ask the server for just the last 64 KB. That tells us every file
inside and exactly where it sits. Then we ask for only the bytes of the one
file we want.

Real example: `SkiaSharp.NativeAssets.Win32` is **81 MB**. We downloaded
**65 KB** of it — enough to see it contains no C# code at all, and stop.

Across all packages we fetched **716 MB instead of 4.7 GB**.

**Step 2 — Pick exactly one copy.** Packages often ship the *same* code several
times, built for different versions of .NET. Newtonsoft.Json contains **eight
copies of itself**. Counting all eight would multiply its number by eight.

So we choose one, by a fixed rule: prefer the most portable build, then the
newest. Every package is counted once.

**Step 3 — Count the public things.** We keep a function if it is public *and*
belongs to a public type. Private internal machinery doesn't count — users
can't call it.

---

## One tricky bit: properties

In C#, a property like `person.Name` looks like a simple value, but underneath
the compiler turns it into two hidden functions: `get_Name` and `set_Name`.

If we counted those, every property would count as two functions. So we don't.
We count each property **once**, from its own separate list.

Constructors and operators are counted too, but kept in **separate columns**,
so you can decide later whether to include them without re-running anything.

---

## What comes out

Each package gets one row:

| Column | Meaning |
|---|---|
| `functions` / `api_total` | The headline number |
| `status` | Whether it worked, and if not, why |
| `version` | Which version was measured |

`status` matters. Some packages genuinely have **no** functions:

- **metapackage** — an empty box that just lists other packages
- **native_only** — contains platform-specific binaries, no C# code
- **tools_only** — command-line tools, not a library

These are real zeros, not failures. We label them separately so a broken read
never gets mistaken for a small package.

---

## Results

| | Ruby | NuGet |
|---|---|---|
| Packages measured | 2,814 of 2,816 | 2,783 of 3,364 |
| Functions found | 1,202,590 | 2,821,798 |
| Time taken | ~15 min | ~7 min |
| Data downloaded | 1,135 MB | 716 MB |

The 581 NuGet packages without a number are mostly the "real zero" cases above.

---

## Two honest warnings

**1. Don't compare the two totals directly.**

NuGet's 2.8 million is 58% *properties*. Ruby has no such concept — in Ruby
those are just ordinary functions, already inside its 1.2 million.

Compare functions to functions and the picture changes completely:

- Ruby: 1,202,590
- NuGet: 1,180,993

Nearly identical. The "NuGet is twice as big" headline is an artifact of
counting two different things.

**2. Ruby's number is a floor; NuGet's is exact.**

Ruby lets programs create functions while running, with names decided on the
fly. No tool that reads source code can see those. So Ruby's real number is
somewhat higher than what we report.

NuGet has no such gap — the compiler's table lists everything.

This bias only runs one way, so any Ruby-vs-C# comparison understates Ruby by
an unknown amount.

---

## The scripts

| File | What it does |
|---|---|
| `gem_api_census.py` | Ruby: download `.gem`, read with tree-sitter |
| `nuget_api_census.py` | NuGet: read the `.dll` index without downloading |

Both can be stopped and restarted — they remember what they already did.

```
python gem_api_census.py
python nuget_api_census.py
```
