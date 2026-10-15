# Combined application import and setup contract

The combined APK has its own application storage. Importing never reads or writes
another installed launcher's private files, database, reports or accepted APKs.
The graphical fallback can remain installed and usable.

The user selects already owned inputs through Android's document picker:

- The exact published `COH-Atlas-Gameplay-0.13.36.apk` (42,076,692 bytes, SHA-256
  `14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f`).
  This is an authenticated payload donor; it is never installed or launched.
  All required donor `assets/runtime/` members have separate pinned sizes/hashes.
- All four existing `COH-Assets-1.0.0-*.zip` volumes. The unchanged asset importer
  checks the APK-pinned volume manifest, ZIP metadata, every payload size/hash,
  complete inventory, storage and cancellation before publishing. The unchanged
  Atlas importer then expands the verified source assets and game definitions.
- Optionally, the two existing `runtime-arm64.tar.gz` and
  `runtime-fex-arm64.tar.gz` archives. Their exact identities come from the shipped
  runtime lock. Missing archives are downloaded over HTTPS and verified against
  those same pins during explicit setup.
- Optionally, a PostgreSQL custom-format logical profile dump (`PGDMP`). This is
  candidate user data: importing checks the bounded container header, while the
  server controller must run `pg_restore` and validate the actual account,
  character and saved map in a newly isolated profile. Raw `pgdata` is rejected.

The donor file name alone does not authorize anything. Both full APK identity
and each selected runtime member must match the trust roots embedded in this
APK. No arbitrary APK, external executable or ZIP can supply replacement pins.

`combined/import-contract.json` is generated from that exact donor by the build
worker. It contains `format:1`, `donor_apk:{name,bytes,sha256}`, a `donor_files`
map keyed by exact `assets/runtime/<leaf>` paths, and a `bundled_files` map keyed
by `runtime/<leaf>`. Bundled metadata must have the exact final runtime manifest
pins. New server-only helpers remain outside the donor's `/opt/coh` closure so
its existing `client-manifest.json` remains valid.

Setup has a separate file lock and memory admission controller. It installs a
fresh private generation with `rootfs`, `wine`, `pg`, `assets`, `dbserver`,
`schema`, `passwd` and `group`. The accepted GNU/USTAR/PAX extractor defers links
until regular files finish, never writes through archive links, verifies the
complete gzip/tar trailer and observes cancellation. Immutable imported runtime
payloads are verified then hard-linked into the generation. A success receipt
and atomic directory publication occur only after all required inputs and
runtime entry points are verified. Setup itself starts no server or game.

Cancellation and failed imports preserve previously accepted content. Partial
input never gets a success receipt. Import operations own and close document
provider streams before publication. Root UI/service ownership must serialize
imports/setup against a running server; these helpers do not manage the server.

Host qualification:

```
python3 native-android/combined-client/imports/tests/check_imports.py
python3 -m unittest discover -s tools/android/interactive -p test_asset_pack_import.py
python3 -m unittest discover -s tools/android -p test_setup_memory_guard.py
```

The new suite executes the shipped methods with real ZIP/filesystem operations
and small real tar archives. Android, asset-store readiness and JSON metadata
are explicit host adapters. Its 48 controls cover donor identity and reimport,
malformed/missing members, provider closure, cancellation before/during reads,
symlink rejection, rollback, logical dump bounds/header, pinned runtime input,
fresh tar installation, immutable inode reuse, repeat setup and damaged-content
rejection. It also verifies the copied tar extractor and memory guard are exact
source adaptations limited to package/class names. The reused asset importer
passes 17 tests; its memory guard passes 22 tests. These are host checks, not a
claim of Android execution, SQL restore, server readiness or native login.
