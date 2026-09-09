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

---

_The same folder exists in `ruby/` and answers the same question for that language._
