# Real DbServer on the ARM64 Wine runtime

This is the first M3 qualification after the [accepted Thor diagnostic](THOR_DEVICE_ACCEPTANCE.md).
It builds the actual CoH DbServer with a separately identified Wine compatibility
overlay, then exercises it against native ARM64 PostgreSQL through the accepted
PRoot/Wine/FEX runtime. The stock Windows reference and immutable source are preserved.

**The full hosted Atlas workflow passed in run `36460005201`**, using unchanged
DbServer donor `36451873322`. All three jobs passed, including all 18 ARM64
stages and the final host validator. The
[acceptance receipt](android-evidence/accepted-game-hosted-36460005201.json)
records both saves, same-cluster restart and exact-name resume; the
[runtime details](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow) preserve
the independently verified evidence. The accepted APK remains 0.1.5.

**The opt-in loopback listener package passed hosted Windows and ARM64 qualification.**
[Run 36460867428](https://github.com/Russianranger/coh-android/actions/runs/36460867428)
at `eed2ce1f5388195f65a07853919761a93657aca6` passed all three jobs on
2026-09-28. The [acceptance receipt](android-evidence/accepted-dbserver-hosted-36460867428.json)
binds the package, native Windows contracts and ARM64 reports. Windows passed
four dispatch, four fixed-input and eleven loopback contracts, plus all 21
persistence groups across 14 phases. ARM64 passed all 28 stages in 191.502348
seconds, including default normal-schema startup followed by fixed-input and
loopback mode together. The latter emitted its exact activation acknowledgment
and all 13 mandatory bind records: 12 TCP endpoints plus UDP 7000. The optional
asynchronous TCP 6992 bind was also observed, for 14 verified loopback endpoints.
These records establish successful binds; the existing network namespace gate
remains required.

Both fresh exports preserved 99 tables, 5,935 ordered columns, 58,272 exact
attribute IDs/names and the full catalog. All 111 process captures closed;
cleanup left zero owned processes or inspection errors. This qualifies the
hosted [listener-binding prerequisite](../database/wine-dbserver/LOOPBACK_BINDING.md).
Physical Android listener execution and app integration remain unvalidated;
Atlas continues to use donor `36451873322`, and the accepted APK remains 0.1.5.

The first [attempt 36460005041](https://github.com/Russianranger/coh-android/actions/runs/36460005041)
at `cfc8ac477e449037213d5242f43480acf4f1cb85` failed Windows loopback test-fixture
setup before either DbServer build or ARM64 execution. Its
[failure receipt](android-evidence/dbserver-qualification-failure-36460005041.json)
preserves the result. The fixture consumed a CRLF patch against LF source files;
the correction normalizes only its temporary patch input to LF and adds a CRLF
regression. The later pass does not reclassify the failed attempt.

**The fixed-input DbServer package is qualified and remains the Atlas donor.**
[Run 36451873322](https://github.com/Russianranger/coh-android/actions/runs/36451873322)
at `53c6270dff8a0efcc6be09da756408504d8313bd` passed all three jobs on
2026-09-28. The [acceptance receipt](android-evidence/accepted-dbserver-hosted-36451873322.json)
binds the package, Windows contracts and ARM64 persistence/schema results.
Its manifest SHA-256 is
`e4f8a66802f29643b13aec2228ada1549a80c22efa11de1549a9b145bb43e06b`;
the normal fixture-OFF executable SHA-256 is
`659e9072234f75ad02c8cac2636df93f5249ff1de385c1ed7d6c6fc0c04a453a`.
The normal ARM64 schema gate passed default startup followed by an explicitly
acknowledged [fixed-input reload](../database/wine-dbserver/FIXED_INPUTS.md).
The [full hosted Atlas workflow](ANDROID_GAME_RUNTIME.md#accepted-full-hosted-workflow)
passed in run `36460005201` with this donor. The earlier
[post-correction acceptance](android-evidence/accepted-game-hosted-36454174481.json)
and [original workflow failure](android-evidence/game-runtime-failure-36454174481.json)
remain preserved separately. Physical Android execution and rendering remain
unvalidated.

The [ARM64 report](android-evidence/dbserver-arm64-36451873322.json) passed all
28 stages in 192.280590 seconds: 21 persistence check groups across 14 fixture
phases, followed by two fresh empty schema exports with 99 tables, 5,935 ordered
columns, 58,272 exact attribute IDs/names and an unchanged full catalog. All 111
process captures closed; cleanup left zero owned processes or inspection errors.
Windows passed the same fixture coverage, four dispatch contracts and four
fixed-input contracts. Tooling ran 77 checks: 69 passed and eight Windows-only
checks skipped.

The separate sibling [run 36454174374](https://github.com/Russianranger/coh-android/actions/runs/36454174374)
at `8944bd598990b33b63a750a64ae448403e4542cd` preserves an unresolved runtime
failure. Attempt 1 passed 18 stages, then the `dbserver-rebuild` process exited
with SIGSEGV (`-11`) after `PG_TEST_COMPLETE rebuild` and teardown messages.
It did not reach normal-schema execution. The
[failure receipt](android-evidence/dbserver-runtime-failure-36454174374.json)
records closed captures for all 57 processes and complete cleanup. Attempt 2
used the byte-identical package and passed all 28 stages in 190.362494 seconds,
including rebuild exit 0, both schema phases and the fixed-input acknowledgment;
all 111 captures closed, with zero owned processes or inspection failures left.
The [repeat receipt](android-evidence/dbserver-runtime-repeat-36454174374-attempt2.json)
retains the failed attempt. The failure is intermittent and unexplained; the
successful repeat does not establish a repair. Atlas continues to use accepted
donor `36451873322`, not the sibling package.

The earlier diagnostic package's
[Run 36425508780](https://github.com/Russianranger/coh-android/actions/runs/36425508780)
at `41f3aff596826e22e2774375e11590de895ca33d` passed all three jobs on
2026-09-28. Its Windows contract verified enabled publication of the
[opt-in dispatch record](../database/wine-dbserver/DISPATCH_PROGRESS.md).
The ARM64 fixture and normal schema gates passed with that observer disabled;
Atlas run `36428915900` subsequently verified enabled publication on ARM64 and
localized its startup stall to `FOLDER_CALLBACKS` or nested work.
This qualifies the package, not a startup blocker correction or completed Atlas
restart/resume. Its [acceptance receipt](android-evidence/accepted-dbserver-hosted-36425508780.json)
preserves the package and runtime evidence. Its manifest SHA-256 is
`656c7e764798dc7ecee01cef836cd758177fd9cdcf1477799517e9d5a959c632`;
the normal fixture-OFF executable SHA-256 is
`3d6098da1655a380f09d7c0ba5b984c98b68b1294f75128c28b08be851cf1830`.

The [earlier Windows report](android-evidence/dbserver-windows-36425508780.json)
passed all 21 persistence check groups across 14 fixture phases, and all four
Windows dispatch-record contracts passed. The
[earlier ARM64 report](android-evidence/dbserver-arm64-36425508780.json) passed 28 stages
in 187.299219 seconds, including the same persistence coverage and two normal
fixture-OFF exports/reloads: 99 tables, 5,935 ordered columns, 58,272 exact
attribute IDs/names and an unchanged catalog. All 111 process captures closed;
cleanup left zero owned processes or inspection failures.

The separately receipted fixed-input mode prevents
directory-watch creation before the first file cache and disables notification
updates, while preserving initial reads and the chosen lookup mode. Default
startup remains unchanged. This avoids leaving undrained notifications in Wine;
it does not establish a generic notification fix. The two normal schema launches
cover default startup followed by acknowledged fixed-input reload, with the same
exact schema/catalog checks and no additional launches.

Run `36434692816` at `73323b72262d7e61064c16023258e0bfe9016583` passed
source/tooling checks, both native Windows option contracts, both builds and the
Windows persistence fixture. Both ARM64 attempts stopped before DbServer execution:
the talloc download exhausted three transport attempts and ended with HTTP 503.
Those failed attempts remain unqualified. Successful run `36451873322` recovered
the identical hash-pinned talloc archive from accepted runtime `36364550345`'s
corresponding-source bundle, validating the manifest, build receipt, bundle and
exact archive member before rebuilding PRoot. The compiler recipe and source
hashes remain unchanged; the extraction receipt is retained with ARM64 evidence.

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
runner user. Default normal DbServer startup opens wildcard listeners, so this
isolation is required for the hosted gate. The separate opt-in loopback package
passed hosted qualification in run `36460867428`; it has not replaced the Atlas
donor, and the network namespace requirement remains in force.

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

The successful full Atlas workflow `36460005201` used donor `36451873322` and
completed all 18 guest stages, both protocol saves and exact-name resume.
LoginCount progressed 1 → 1 → 2, both fixed-input acknowledgments and all four
input checks passed, and all 123 captures closed with complete cleanup. Keep
the accepted donor unchanged. Physical Android listener validation and app lifecycle
integration precede the next device candidate; retain the accepted 0.1.5
diagnostic and runtime in the meantime.
