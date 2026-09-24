> Historical record for the Volume 2-derived snapshot at `upstream/ouroboros`.
> Current source acquisition target: [canonical i25/SCoRE](I25_SOURCE_ACQUISITION.md).

# Source provenance and import scope

Assessment/import date: 2026-09-23.

## Selected baseline

| Field | Value |
| --- | --- |
| Requested project | Project Ouroboros / OuroDev |
| Canonical source location | https://git.ourodev.com/CoX/Source |
| Acquisition repository | https://github.com/Thunderspies/CityOfHeroes |
| Acquired branch | `master` |
| Acquired commit | `0b75ade0c801735e10c5798f641948a45cc50488` |
| Original Git tree | `f634e21e230009fa8edc91d15429cd4da69eee8c` |
| Destination | `upstream/ouroboros/` |
| Scope | Entire tracked tree: 5,995 regular files, 173,081,714 bytes (165.06 MiB) |
| Companion data candidate | `Thunderspies/i24` at `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |

The acquired repository's [README](../upstream/ouroboros/README.md) explicitly
states that it is a fork of OuroDev, originally intended to modernize the Visual
C compiler and also containing feature additions. This provenance is the fork's
own statement. It has not been independently compared against canonical OuroDev.
The import preserves that README and CONTRIBUTING file verbatim.

Direct HTTP requests to OuroDev GitLab and its API returned 502. `git ls-remote`
against the canonical source also returned 502. The wiki returned 403. These
results establish an access limitation in this environment, not that the project
has disappeared. No authenticated OuroDev session was available. A later canonical
export can be compared against this snapshot before changing the selected lineage.

The earlier 2026-09-13 planning document used the 2019 `zethfoxster/coh-score`
snapshot as a provisional Issue 25 reference. This import deliberately uses the
public OuroDev-derived source identified above instead. Do not combine its data,
protocols, executables, or schema templates with the older SCoRE baseline by default.

## What was preserved

| Area | Files | Purpose |
| --- | ---: | --- |
| `Game` | 851 | Client, UI, renderer, audio, input |
| `MapServer` | 600 | World/mission simulation and gameplay |
| `DBServer` | 92 | Persistence coordination, SQL provider and zone handoff |
| `Common` | 445 | Shared game types, protocol, SQL, physics wrappers |
| `libs` | 686 | Utility, networking, memory and supporting libraries |
| `3rdparty` | 1,839 | Bundled SDK headers, sources, import libraries and DLLs |
| `Utilities` | 1,102 | StructParser, TestClient, Pig and development/art tools |
| Other services and support files | 380 | Auth, accounts, chat, auctions, launcher, other services, configs and build support |

Full per-directory counts are in [source-inventory.json](source-inventory.json).
Every tracked file was copied without edits, including bundled binary SDK files,
resource files, notices, examples, and upstream workflow definitions. The largest
file is approximately 8.0 MiB; none requires Git LFS to avoid GitHub's per-file
limit. There are no submodule gitlinks or symlinks in this snapshot.

Upstream `.github` files live inside the snapshot, not at the destination repo's
root, and therefore do not automatically install upstream release automation.
This is a tree snapshot, not a transfer of the full upstream commit history.

A separate destination workflow, `Import pinned OuroDev-derived source`, performs
the initial authenticated import when command-line Git credentials are unavailable.
It fetches only the locked revision, verifies the source and staged tree identities,
and commits the unchanged snapshot. Rerunning it verifies an existing snapshot
instead of replacing it. This workflow does not build or publish game binaries.

## What is still external

- The complete game data set: text definitions, maps, textures, meshes, sounds,
  PIGG/HOGG archives and matching generated bins. The [companion data repository](https://github.com/Thunderspies/i24/tree/d51533ec8e6a9cf726b9214968077a05fdcf19f3)
  is pinned as a candidate, not claimed tested or imported. Its README distinguishes
  text data from separately downloaded binary assets.
- Dependencies fetched by CPM/CMake. Their existing source pins/URL hashes are
  preserved under `cmake/dependencies`; their downloaded bytes are not in this import.
- Windows build tools, SQL Server reference environment, PostgreSQL/ODBC packages,
  Wine/FEX, graphics drivers, Android SDK/NDK and Gradle tooling.
- A known-good client/content/database combination, Android implementation and APK.

Bundled Windows DLLs and `.lib` files are included because upstream build/runtime
definitions use them; they are not ARM64 libraries. Existing notices remain
unchanged. No new blanket license has been applied to inherited code or SDKs.

## Reproduce and verify

In an empty scratch directory with Git access:

```sh
git clone https://github.com/Thunderspies/CityOfHeroes.git source
git -C source checkout --detach 0b75ade0c801735e10c5798f641948a45cc50488
git -C source archive --format=tar --output=../source.tar HEAD
mkdir snapshot
tar -xf source.tar -C snapshot
```

In this repository, run `python3 tools/verify_source.py` to compare file bytes,
Git blob identities, file count, modes and extra files with the committed manifest.
The lock records the original tree SHA for an independent Git comparison.
Future import updates should be isolated commits that update the lock, manifests,
inventory and this provenance document together. Port patches should remain
separate from upstream refreshes; do not describe a modified tree as byte-identical.
