# Fetching the packages

Every package studied here can be retrieved with a plain HTTP GET. No registry
client, no authentication, no scraping.

---

## Where to start

    ruby/package-selection/selected-packages.csv       2,814 gems
    csharp/package-selection/selected-packages.csv     3,352 packages

Use the `registry_name` column rather than `package`: `package` is lowercased
for matching, while NuGet URLs need the registry's own casing preserved.

`releases/release-history.csv` lists every published version if you need one
other than the current release.

---

## RubyGems

    curl -O https://rubygems.org/downloads/<gem>-<version>.gem
    curl -O https://rubygems.org/downloads/rack-3.2.7.gem

A `.gem` is a tar whose payload is a nested `data.tar.gz`:

    tar -xf rack-3.2.7.gem
    mkdir src && tar -xzf data.tar.gz -C src

The archive contains the full source, so this is also how you obtain the
documentation: doc comments live in the code you are already downloading.

All 2,814 gems at their current versions total **1.4 GB**.

    python - <<'PY'
    import csv, urllib.request
    sel = csv.DictReader(open("ruby/package-selection/selected-packages.csv",
                              encoding="utf-8"))
    meta = {r["package"]: r["latest_version"] for r in
            csv.DictReader(open("ruby/releases/package-metadata.csv",
                                encoding="utf-8"))}
    for r in sel:
        name = r["registry_name"] or r["package"]
        v = meta.get(name)
        if v:
            urllib.request.urlretrieve(
                f"https://rubygems.org/downloads/{name}-{v}.gem",
                f"{name}-{v}.gem")
    PY

**Platform builds.** A java- or linux-only gem has no plain
`<gem>-<version>.gem`; its artifact is `<gem>-<version>-java.gem`, and asking
for the plain name returns 403 rather than 404. The `platform` column in
`release-history.csv` says which suffix applies.

---

## NuGet

    curl -O https://api.nuget.org/v3-flatcontainer/<id-lower>/<version>/<id-lower>.<version>.nupkg
    curl -O https://api.nuget.org/v3-flatcontainer/newtonsoft.json/13.0.3/newtonsoft.json.13.0.3.nupkg

The identifier must be lowercased in the URL even though the display name is
not. A `.nupkg` is a zip:

    unzip newtonsoft.json.13.0.3.nupkg -d newtonsoft

All 3,352 packages total **8.7 GB**, dominated by a handful of native-asset
packages bundling one binary per platform. See
`storage-footprint/storage-requirements.xlsx` for the distribution.

**You rarely need the whole package.** A zip keeps its index at the end, so one
ranged request reads the file list and a second reads only the entry you want.
That is how this study read 3,352 packages while transferring 202 MB rather
than 8.7 GB.

    curl -H "Range: bytes=-65536" -o tail.bin <nupkg-url>

`scripts/04-count-csharp-methods.py` has a working implementation in
`central_directory()` and `read_entry()`.

Version list for a package:

    curl https://api.nuget.org/v3-flatcontainer/<id-lower>/index.json

---

## Source from GitHub

`releases/package-metadata.csv` carries a `github_url` for 2,663 gems and
2,838 NuGet packages.

    git clone --depth 1 https://github.com/<owner>/<repo>.git

Two caveats before preferring this to the registry.

**Not every package has one.** 151 gems and 514 NuGet packages publish no
repository, so the registry artifact is the only source for those.

**A repository is not a package.** It carries tests, samples and often several
packages built from one tree — `dotnet/runtime` produces hundreds. For what a
version actually shipped, take the artifact.

---

## Choosing a source

| requirement | source |
|---|---|
| what a version shipped | registry artifact |
| documentation | registry artifact — it is inside |
| git history, issues, tests | GitHub repository |
| C# public API only | `.nupkg`, ranged read of one assembly |
| package with no repository | registry artifact, the only option |
