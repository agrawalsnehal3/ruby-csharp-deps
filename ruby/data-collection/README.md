# How the Ruby data was collected

Everything in `ruby/` is derived from data collected before any analysis
began. This explains where that data came from.

---

## The short version

**RubyGems publishes its own database.** A dump of the live rubygems.org
PostgreSQL database is available publicly, so package metadata and download
totals were read from it rather than crawled from the website or pulled one
package at a time from the API.

That single fact shapes everything else. There was no rate limit to work
around, no pagination, and no risk of a partial harvest — the whole registry
arrives in one file.

---

## The sources

| Source | Size | What it gave us |
|---|---|---|
| RubyGems database dump | 1.8 GB | Every package, every version, dates, authors, dependencies |
| Download totals (from the same dump) | 4.4 MB | Lifetime downloads per gem — 232,737 rows |
| rubygems.org page scrape | 105 MB | Links the API does not surface in one place |
| GitHub API | 21 MB | Stars, forks, issues, topics for linked repositories |

### 1. The database dump

The dump is the backbone. It produced a table of **659,390 rows** carrying
package identity and release history:

    package_id, package_name, package_created_at, package_updated_at,
    package_age_years, package_indexed, organization_id,
    latest_version_id, latest_version, latest_authors, latest_description

Two things this gives that an API crawl does not:

- **Completeness.** Every gem, including unlisted and yanked ones, with no
  chance of missing a page or being throttled part-way.
- **A consistent snapshot.** All rows are from the same moment. A crawl taking
  hours would mix states.

### 2. Download totals

Lifetime download counts came from the same dump, as a simple `name, count`
table of 232,737 gems.

**Lifetime, not latest-version.** The dump also carries a
`latest_version_downloads` field and it was deliberately not used: it counts
only the newest release, so nokogiri reads **1,919** against a lifetime
**1.25 billion**. Ranking on it would have produced a nonsense ordering.

### 3. The page scrape

The RubyGems JSON API would have been easier to consume, but the gem page
carries several things the API does not put in one place:

- the documentation, homepage, changelog, wiki, source and bug-tracker links
  as the maintainer entered them
- the rendered description
- the recent-versions list with per-version `.gem` sizes
- the SHA-256 checksum of the current release

The scraper anchors on element ids (`home`, `changelog`, `code`, `bugs`,
`gem_sha_256_checksum`) and `data-testid` markers rather than CSS classes,
because the 2026 layout is Tailwind and its class attributes change whenever
the design does.

### 4. GitHub enrichment

Where a gem declared a repository, the GitHub API supplied stars, forks, open
issues and topics.

Three columns exist specifically to stop those numbers being read as more than
they are:

| Column | Why it exists |
|---|---|
| `link_source` | Whether the publisher **declared** the repository or it was **inferred** from a homepage. The weak case once put a Go tool's 82,684 stars against a Ruby wrapper. |
| `repo_status` | Marks the **19%** of links whose repository no longer exists. |
| `repo_gem_count` | How many gems share that repository. A monorepo's stars are not evidence about any one gem — `aws/aws-sdk-ruby` backs **476**. |

---

## How it fits together

    RubyGems database dump ─┐
    download totals        ─┼─→ all_package_ruby.csv ─→ frame_ruby.csv
    page scrape            ─┤        (17 columns)         (35 columns)
    GitHub API             ─┘                                   │
                                                                ▼
                                            everything in this repository

`frame_ruby.csv` is the file the census scripts read. One row per gem, 232,737
of them, joining registry facts, downloads, links and repository signals.

---

## What is not in this repository

The raw sources total roughly **2 GB** and are excluded by `.gitignore`. They
are inputs, not findings, and they are reproducible:

- the database dump is published by rubygems.org
- the page scrape and GitHub enrichment are re-runnable from the scripts

What is committed is everything computed *from* them.

---

## Compared with NuGet

The C# side had to be collected completely differently, because **NuGet
publishes no database dump**. See [`csharp/data-collection/`](../../csharp/data-collection/).
