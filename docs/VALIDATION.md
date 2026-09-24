# Validation record

Date: 2026-09-23. This record covers source preservation and assessment accuracy.

| Check | Result |
| --- | --- |
| Source snapshot byte count | 173,081,714 bytes across 5,995 tracked regular files |
| Per-file integrity | SHA-256, Git blob SHA-1, size and executable-bit checks passed for all files |
| Extra/missing imported files | None |
| Staged Git subtree | `f634e21e230009fa8edc91d15429cd4da69eee8c`, identical to the acquired upstream commit's root tree |
| Submodules/symlinks | None in the acquired snapshot |
| Source exclusions | None from the acquired tracked tree |
| Largest file | `3rdparty/cg/bin.x64/cg.dll`, 8,421,480 bytes |
| Documentation | Local links and referenced source paths checked; main constraints confirmed in imported code |
| Executable/game changes | None; imported source is byte-identical |

The verifier uses only Python's standard library:

```sh
python3 tools/verify_source.py
```

An independent Git check, after files are staged, is:

```sh
git write-tree
# Use the returned tree as TREE in the following command:
git rev-parse TREE:upstream/ouroboros
```

The result must equal the original tree in `upstream-lock.json`.

## Not performed

- No Windows/MSVC build performed by us. The exact-commit upstream build was later verified; see the 2026-09-24 addendum below.
- No PostgreSQL integration test or SQL Server migration.
- No game-data download, template/bin generation or source/data compatibility test.
- No Wine/FEX, PhysX, graphics or gameplay execution.
- No Android APK build, emulator/device run, performance or thermal benchmark.

The source's CMake restrictions were read directly; they were not reported as a
failed build experiment. Likewise, the PostgreSQL defect was established through
source inspection against PostgreSQL syntax, not a running database test.

The imported upstream workflows remain nested in the snapshot and are not enabled
as workflows in this destination. Successful source checks must not be represented
as a passing Android build.

## 2026-09-24 completeness addendum

Reran the source verifier successfully: all 5,995 files and 173,081,714 bytes
still match. Inspected successful upstream Windows run
[35934567567](https://github.com/Thunderspies/CityOfHeroes/actions/runs/35934567567)
for the exact source commit. Its server/client builds and nine utility, archive,
development-mode and codec tests passed. This was an upstream run, not a build
performed in this repository. Downloaded the v2i3 runtime ZIP, verified its
published SHA-256, and inspected its file list/build metadata without execution;
it uses a different source commit. See the
[completeness audit](LOCAL_SERVER_CLIENT_COMPLETENESS.md) for missing runtime
content/database setup and concrete companion-script gaps. No gameplay or Android
execution was performed.
