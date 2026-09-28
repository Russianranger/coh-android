# Real DbServer on the ARM64 Wine runtime

This is the first M3 qualification after the [accepted Thor diagnostic](THOR_DEVICE_ACCEPTANCE.md).
It builds the actual CoH DbServer with a separately identified Wine compatibility
overlay, then exercises it against native ARM64 PostgreSQL through the accepted
PRoot/Wine/FEX runtime. The stock Windows reference and immutable source are preserved.

**The diagnostic DbServer package is qualified for the next hosted Atlas run.**
[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` passed all three jobs on
2026-09-28. Its Windows contract verified enabled publication of the
[opt-in dispatch record](../database/wine-dbserver/DISPATCH_PROGRESS.md).
The ARM64 fixture and normal schema gates passed with that observer disabled;
Atlas run `36428915900` subsequently verified enabled publication on ARM64 and
localized its startup stall to `FOLDER_CALLBACKS` or nested work.
This qualifies the package, not a startup blocker correction or completed Atlas
restart/resume. The [new acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
preserves the package and runtime evidence. Its manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632`;
the normal fixture-OFF executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

The [new Windows report](android-evidence/dbserver-windows-36425508780.json)
passed all 21 persistence check groups across 14 fixture phases, and all four
Windows dispatch-record contracts passed. The
[new ARM64 report](android-evidence/dbserver-arm64-36425508780.json) passed 28 stages
in 187.299219 seconds, including the same persistence coverage and two normal
fixture-OFF exports/reloads: 99 tables, 5,935 ordered columns, 58,272 exact
attribute IDs/names and an unchanged catalog. All 111 process captures closed;
cleanup left zero owned processes or inspection failures.

A separately receipted [fixed-input mode](../database/wine-dbserver/FIXED_INPUTS.md)
is prepared for the controlled Atlas gate and awaits qualification. It prevents
directory-watch creation before the first file cache and disables notification
updates, while preserving initial reads and the chosen lookup mode. Default
startup remains unchanged. This avoids leaving undrained notifications in Wine;
it does not establish a generic notification fix. The existing two normal
schema launches will cover default startup followed by acknowledged fixed-input
reload, with the same exact schema/catalog checks and no additional launches.

Run `36434692816` at `73323b72262d7e61064c16023258e0bfe9016583` passed
source/tooling checks, both native Windows option contracts, both builds and the
Windows persistence fixture. Both ARM64 attempts stopped before DbServer execution:
the talloc download exhausted three transport attempts and ended with HTTP 503.
This package is not yet qualified for ARM64. The next build uses the identical
hash-pinned talloc archive from the accepted runtime's corresponding-source
bundle; the compiler recipe and source hashes remain unchanged.

**The first hosted M3 DbServer gate passed** in
[run 36369485666](https://github.com/Russianranger/coh-android/actions/runs/36369485666)
at `1a5eea159172a4698441eb8cfed5ea5ca99fcf12`, completed 2026-09-28 at
02:33:22 UTC. Physical Android DbServer execution remains unvalidated.
The [workflow](../.github/workflows/android-dbserver.yml) builds separate normal
and persistence-fixture products, checks their exact ODBC imports and dependency
closure, runs the real fixture on Windows, then performs the ARM64 test.

All 50 tooling checks passed. The [Windows report](android-evidence/dbserver-windows-36369485666.json)
records all 21 persistence check groups across 14 fixture invocations. The
[ARM64 report](android-evidence/dbserver-arm64-36369485666.json) passed all 28 stages
in 187.8792 seconds, including the same persistence coverage and two normal
fixture-OFF exports: 99 tables, 5,935 ordered columns, 58,272 exact attribute
IDs/names and a stable catalog on reload. All 111 process records have closed
input/output captures; cleanup left zero owned processes and no inspection errors.
The [acceptance receipt](android-evidence/accepted-dbserver-hosted-36369485666.json)
binds the verified artifacts, package and source receipts, runtime inputs and
network isolation evidence.

The [first attempt](android-evidence/dbserver-packaging-failure-36367594924.json)
compiled both binaries but stopped during packaging before any runtime test:
the import check did not yet resolve MSVC's ordinal ODBC imports.
[Run 36368424997](android-evidence/dbserver-runtime-failure-36368424997.json)
then passed all 21 persistence check groups on Windows, but its first ARM64
fixture invocation hit a FolderCache duplicate-slot assertion. Normal schema
startup was not reached. The accepted retry includes the initialization and local
hostname handling described below; the earlier attempt remains a failed run.

## Compatibility and build identity

`tools/prepare_wine_dbserver_source.py` first verifies and stages the existing
PostgreSQL source changes. The separate Wine overlay adapts DbServer's
ODBC calls. It selects implemented ANSI names for connection, execution and
statement preparation; metadata uses wide entry points with checked UTF-8/UTF-16
conversion, preserving optional NULL filters and numeric buffers. Source receipt
hashes bind the PostgreSQL patch, Wine patch, adapter, original source and modified
files. This is a pinned application adapter, not a replacement ODBC manager; local
validation errors do not synthesize driver diagnostic records.

The qualified diagnostic package also contains the opt-in main-thread dispatch
observer. Its receipt binds the marker source, patched call sites, record format
and stage names. With `COH_WINE_DB_PROGRESS` absent, it creates no record.
An explicitly supplied fresh private path enables bounded mapped publication;
loop markers perform no I/O, logging or platform calls. The Windows live contract
checked disabled and enabled behavior, external record visibility and refusal of
invalid or existing paths. Advancing sequence values demonstrate progress between
samples; a stopped stage identifies an operation and its nested calls, not a
particular instruction, deadlock, or SQL/gameplay success.

The receipted overlay also initializes the file cache and log path on the main
thread before the Wine persistence fixture starts its 64 SQL workers. That entry
point bypasses normal DbServer initialization; SQL notice logging otherwise
initializes the non-thread-safe file cache lazily on worker threads. This
fixture-only setup uses stderr-and-exit assertion handling. It does not change
the normal fixture-OFF startup path.

The normal binary is built with `COH_PG_PERSISTENCE_TESTS=OFF` and preserved before
reconfiguring the build with the fixture enabled. Packaging verifies both cache
modes and requires distinct executable hashes. It resolves ordinal ODBC imports
against the hash-checked export specification from the pinned Wine revision,
rejecting unknown ordinals and stubbed or unsupported exports as well as known
Wine-stubbed named imports. Only the actual dependency closure and dynamic
CrashRpt dependency are included, with app-local x86 MSVC runtime libraries.

## Runtime qualification

The host runner uses the exact 0.1.5 M2 runtime manifest and all twelve verified
inputs from run `36364550345`. The new guest script is bound separately; it reuses
the accepted process ownership and cleanup implementation. A separate Linux network
namespace permits loopback only, with the guest running as the original non-root
runner user. Normal DbServer startup opens wildcard listeners, so this isolation
is required for the hosted gate. Android listener binding remains unfinished.

Each binary variant runs from a private directory with both `data/` and `tools/`
markers, which the engine requires to recognize its local data root. The fixture
needs no game-data payload; the normal variant receives only the accepted schema
inputs below. A controlled guest `/etc/hosts` maps `localhost`, the kernel hostname
and its short form to `127.0.0.1`. Its contents and hash are retained with host
evidence, so local hostname resolution does not depend on external DNS.

The persistence fixture runs fourteen real DbServer invocations covering the
existing twenty-one check groups: worker queues, serialization, multi-batch saves,
rollback, retries, delete failures, connection loss, process reload, graceful and
immediate PostgreSQL restarts, schema rebuild and backup/restore. Expected failure
phases require their specific failure markers and independently verified SQL state.

The normal binary receives the accepted 56 generated payloads plus six pinned text
inputs. Two ordinary `-exportdump` runs must create fresh empty exports, establish
all 99 tables and 5,935 ordered columns, preserve 58,272 exact attribute IDs/names,
and leave the catalog unchanged on reload. Runtime errors, timeouts, missing
evidence, surviving owned workers or missing output EOF fail the gate.

This qualification does not establish physical Android execution of DbServer,
MapServer operation, character gameplay, Android graphics, physical input or audio.
No replacement diagnostic APK is required for the accepted M2 tests.

Continue M3 with managed Atlas MapServer and diagnostic TestClient execution in
the same runtime, using donor `36425508780` and a fresh enabled dispatch record
for each first/restart launch. Live ARM64 publication, exact-name resume and the
second protocol save remain pending. Android listener binding and app lifecycle
integration must be completed before the next device candidate; retain the accepted 0.1.5 diagnostic
and runtime in the meantime.
