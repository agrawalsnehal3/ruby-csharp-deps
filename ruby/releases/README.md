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

## How this data was obtained

One request per gem to `/api/v1/versions/<gem>.json`, cached, giving every published version with its date and platform. Paired with the repository and documentation locations already established.

Scripts: `build-package-metadata.py`

## What each field means, and where it came from

| Column | Meaning | Source |
|---|---|---|
| `version` | As published | RubyGems versions API / NuGet index.json |
| `released` | Publication date (Ruby only) | RubyGems versions API |
| `platform` | ruby, java, x86_64-linux ... | RubyGems versions API |
| `prerelease` | True for betas and release candidates | RubyGems flag / a hyphen in the NuGet version |
| `version_count` | Every published version | Counted |
| `stable_version_count` | Excluding prereleases | Counted |
| `github_url` | Repository | Registry metadata |
| `registry_url` | Package page | Built from the name |
| `doc_site_url` | Best documentation link found | The documentation tier resolution |
| `readme_file` | README path inside the package | Archive walk |
| `docs_folder_files` | Files under docs/ inside the package | Archive walk |

Other columns: `docs_folder_count`, `downloads`, `error`, `first_release`, `has_readme`, `latest_release`, `latest_version`, `package`, `registry`

---

_The same folder exists in `csharp/` and answers the same question for that language._
