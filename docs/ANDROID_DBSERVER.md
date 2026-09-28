# Real DbServer on the ARM64 Wine runtime

This is the first M3 qualification after the [accepted Thor diagnostic](THOR_DEVICE_ACCEPTANCE.md).
It builds the actual CoH DbServer with a separately identified Wine compatibility
overlay, then exercises it against native ARM64 PostgreSQL through the accepted
PRoot/Wine/FEX runtime. The stock Windows reference and immutable source are preserved.

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
the same runtime. Android listener binding and app lifecycle integration must be
completed before the next device candidate; retain the accepted 0.1.5 diagnostic
and runtime in the meantime.
