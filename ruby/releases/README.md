# Every published version, and where to find each package

One row per (package, version), plus the repository, registry page, README and docs folder for each package. Versions are a separate file because some packages have thousands.

## Files

| file | size |
|---|---|
| `package-metadata.csv` | 622 KB |
| `release-history.csv` | 8.9 MB |

## Scripts

The code that produced these files. They import each other by module name, so gather them into one directory to run them.

### `scripts/build-package-metadata.py`

Fetches the full version list for every package -- one request each, cached -- and pairs it with the repository and documentation locations already established.

---

_The same folder exists in `csharp/` and answers the same question for that language._
