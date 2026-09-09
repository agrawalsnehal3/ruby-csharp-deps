# The GitHub projects this study starts from

The 100 most-starred and 100 most-forked repositories for this language, as returned by the GitHub search API. Everything downstream begins here: these are projects people actually chose to build on.

## Files

| file | size |
|---|---|
| `most-forked-repositories.csv` | 5 KB |
| `most-starred-repositories.csv` | 5 KB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/fetch-repositories.py`

Queries the GitHub search API for the two rankings, then fetches each repository's dependency SBOM. One request per repository; results are cached so a re-run costs nothing.

### `scripts/select-packages.py`

Also writes these lists, trimmed to the top 100 of each ranking.

## How this data was obtained

The same, with `language:C#`. Note GitHub returns the two rankings independently, so a repository can appear in both -- 59 Ruby and 41 C# repositories do.

Scripts: `fetch-repositories.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `rank` | Position in that ranking, 1 = most stars or forks | GitHub search API result order |
| `repository` | owner/name on GitHub | GitHub search API |
| `stars` | Stargazers at fetch time | GitHub search API |
| `forks` | Forks at fetch time | GitHub search API |
| `dependency_status` | Whether GitHub returned a dependency SBOM | GitHub dependency-graph API |
| `dependency_count` | Packages in the SBOM, all ecosystems, unfiltered | GitHub dependency-graph SBOM |

---

_The same folder exists in `ruby/` and answers the same question for that language._
