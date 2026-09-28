# Real DbServer on the ARM64 Wine runtime

This is the first M3 qualification after the [accepted Thor diagnostic](THOR_DEVICE_ACCEPTANCE.md).
It builds the actual CoH DbServer with a separately identified Wine compatibility
overlay, then exercises it against native ARM64 PostgreSQL through the accepted
PRoot/Wine/FEX runtime. The stock Windows reference and immutable source are preserved.

Status: implementation and focused checks are ready; hosted qualification is pending.
The [workflow](../.github/workflows/android-dbserver.yml) builds separate normal
and persistence-fixture products, checks their exact ODBC imports and dependency
closure, runs the real fixture on Windows, then performs the ARM64 test.

## Compatibility and build identity

`tools/prepare_wine_dbserver_source.py` first verifies and stages the existing
PostgreSQL source changes. The separate Wine overlay is confined to DbServer's
ODBC calls. It selects implemented ANSI names for connection, execution and
statement preparation; metadata uses wide entry points with checked UTF-8/UTF-16
conversion, preserving optional NULL filters and numeric buffers. Source receipt
hashes bind the PostgreSQL patch, Wine patch, adapter, original source and modified
files. This is a pinned application adapter, not a replacement ODBC manager; local
validation errors do not synthesize driver diagnostic records.

The normal binary is built with `COH_PG_PERSISTENCE_TESTS=OFF` and preserved before
reconfiguring the build with the fixture enabled. Packaging verifies both cache
modes, requires distinct executable hashes and rejects the known Wine-stubbed
imports. Only the actual dependency closure and dynamic CrashRpt dependency are
included, with app-local x86 MSVC runtime libraries.

## Runtime qualification

The host runner uses the exact 0.1.5 M2 runtime manifest and all twelve verified
inputs from run `36364550345`. The new guest script is bound separately; it reuses
the accepted process ownership and cleanup implementation. A separate Linux network
namespace permits loopback only, with the guest running as the original non-root
runner user. Normal DbServer startup opens wildcard listeners, so this isolation
is required for the hosted gate. Android listener binding remains unfinished.

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
