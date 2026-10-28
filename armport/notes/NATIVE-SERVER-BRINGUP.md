# Native ARM64 server bring-up: source-backed plan

2026-10-28. Investigation only: no compiler, CI, binary install, runtime-pin change,
or upstream edit was performed. Native source observations refer to the prepared
ArmPort tree through patch 0118 (the server metric patch 0119 does not change
these build dependencies). Repo wrapper observations refer to `7d3f234c7` and the
0.13.45 preparation. Source line numbers are orientation aids; function names
and patch/source receipts remain the authoritative identity.

The smallest useful native-server milestone is **DbServer plus the existing x86
MapServer**, followed by native MapServer after its simulation contract is
explicit. This separates database/queue correctness from the physics decision.
The 9.5-minute Thor MapServer startup is still the main structural target; no
speedup has been measured and removing FEX does not remove Wine, PRoot or SQL.

## Confirmed build and packaging blockers

| Surface | Current source evidence | Next change and proof |
|---|---|---|
| Compiler/toolchain | `armport/cmake/aarch64-w64-mingw32.cmake:11–22` already selects Windows/aarch64 and the real llvm-mingw tools. Its alternate headers-only mode at24–42 cannot link a server. | Reuse the pinned real llvm-mingw release from `armport-build.yml`, with the existing Wine emulator. Do not report headers-only compilation as a native executable. |
| DbServer target admission | Prepared `cmake/CoXTargets.cmake:8–30,53–59` already admits `COX_ARMPORT_WINDOWS`; `Common/CMakeLists.txt:1–3` is an interface target. | Do not invent a second architecture flag or port Common again. Explicitly enable only Common/DbServer; leave Game and all unrelated server targets off. |
| DbServer link/configure | `DBServer/CMakeLists.txt:171–182` links `odbc32`, unconditionally passes MSVC `/Gy;/Oi;/Zi` and `/LARGEADDRESSAWARE`, and stages `LogServer`. `cmake/CoXTargets.cmake:66–87` refuses executable aliases without MSVC and evaluates PDB-only generator expressions. | First native patch: guard MSVC flags, add the mingw link/runtime policy already used by Game, and support an executable-only LogServer alias without PDB expressions under mingw. Preserve current Win32 output byte semantics where possible. Add extracted CMake/source checks with an upstream negative control. |
| Host source generator | `cmake/StructParser.cmake:55–72` invokes `StructParser::Host`; `Utilities/StructParser/CMakeLists.txt:47–67` builds the host parser through ExternalProject when cross compiling. | Keep this path and its generated-source receipts. Set `CMAKE_BUILD_PARALLEL_LEVEL=2` in the entire environment, including nested builds; avoid simultaneous client/server jobs. |
| MapServer admission | Root `CMakeLists.txt:9–12` explicitly rejects any MapServer target other than MSVC Win32, despite the wider generic target helper. | Add a narrowly named experimental native-server option only after the physics policy below is defined; do not loosen all target restrictions. |
| MapServer dependencies | Root CMake's MapServer branch includes `dependencies/PhysX`; `MapServer/CMakeLists.txt:1006–1026` links PhysX Loader/Cooking, sets MSVC flags and stages PhysX. `libs/AILib/CMakeLists.txt:34–35` also applies MSVC-only flags including unbounded `/MP`. | Separate CPU/AI source compilation from the binary SDK selection. Guard compiler-specific flags. Any MSVC reference builds use `/MP1` with `cmake --build ... --parallel 2`; `--parallel 2` alone does not bound nested `/MP`. |
| DbServer source ancestry | `tools/prepare_wine_dbserver_source.py:17–34,181–208` adds the PostgreSQL patch plus Wine ODBC/fixed-input/loopback/progress overlays. `tools/android/interactive/package_startup_dbserver.py:132–157` reproduces the donor profile before later overlays. | An ArmPort-only DbServer build is not the app's qualified server. Import/preserve the accepted PostgreSQL and Wine/startup changes through patchwork commits and publish new exact source receipts. Never rewrite old receipts to describe new ARM64 code. |
| PE validation | `tools/android/dbserver/package_dbserver.py:32–78` explicitly parses PE32 (32-bit import thunks, PE32 data-directory offset). `package_startup_dbserver.py:160–165` requires Win32 CMake cache. `android/guest/local_character_server.py:1248` verifies every map-package file as PE32. | Introduce an explicit ARM64 package lane with PE machine 0xaa64 and PE32+ magic 0x20b, 64-bit import thunks, correct directory offsets, import bounds checks and matching-architecture DLL dependencies. Keep all x86 validators strict. Test wrong-machine, mixed-DLL, truncated-table and legacy-lane controls. |
| ODBC installer/probe | `android/runtime-lock.json:24–28` pins 18.00.0004 `psqlodbc_x86.msi`. `android/guest/local_login_server.py:214–224` explicitly invokes PE32 syswow64 msiexec and the x86 driver preflight; `diagnostic.py:129–146,211–227` requires pointer_bits 32 and PE32 DLL loading. | Qualify a distinct ARM64 driver/probe/installer path. Do not merely change the filename or accept both machine types in the old validator. Keep the native Linux ARM64 PostgreSQL backend and existing loopback-only database policy. |
| Data/cache ownership | ARM64 binaries will have different source/build identities from retained server packages, which are bound into the current source/cache contracts. | Build server bins with the correct producer and separate their cache namespace by exact producer/schema/architecture. Reuse text/assets where validated; do not bless x86 binary caches as ARM64 caches by updating a digest alone. Preserve owned shutdown before returning caches. |

## ARM64 ODBC is available to investigate

The official PostgreSQL announcement dated 2026-10-14 says psqlODBC 18.00.0005
provides Windows ARM64 installers and merge modules. Its current official CI has
an ARM64 libpq source build and ARM64 driver build/test path. This provides a
concrete candidate, **not evidence it loads in the pinned Wine10 runtime**.
No ARM64 artifact was downloaded, hashed or executed in this investigation.

- [Official release announcement](https://www.postgresql.org/about/news/psqlodbc-18000005-released-with-security-fix-for-cve-2026-109448-3404/)
- [Official driver build workflow](https://github.com/postgresql-interfaces/psqlodbc/blob/main/.github/workflows/main.yml)

Proposed dependency work: first identify exact official ARM64 release bytes and
source tag, inspect its DLL dependency closure, pin all bytes, and run a native
ARM64 probe against existing PostgreSQL. Changing the driver's version from the
current 18.00.0004 is a separately disclosed runtime-input change; do not bundle
it silently into a client/server pointer fix. The release also fixes a parameter
binding overflow affecting 18.00.0004, but this investigation did not establish
that COH constructs vulnerable statements. No exposure claim is made.

The probe must check SQLWCHAR remains2 bytes while pointers/SQLLEN/SQLULEN are 8,
load the registered ARM64 driver through ARM64 odbc32, exercise the exact accepted
ANSI/wide API aliases, and preserve the stock 65-connection test and shutdown/restart
persistence proof. `Common/sql/sqlconn.c:20–21` already checks size_t/ssize_t against
SQLULEN/SQLLEN. `container_sql.c:505,524,656` uses size_t storage viewed as SQLLEN;
its signed sentinels and output lengths need explicit 64-bit tests, not blind casts.

The current Wine adapter deliberately redirects APIs because specific ANSI
aliases in the pinned Wine are stubs (`database/wine-dbserver/overlay/Common/sql/
wine_odbc.h:33–42`). A new CPU architecture does not justify removing that adapter.
Its required/forbidden import list is in `prepare_wine_dbserver_source.py:29–34`.

## Physics is a simulation decision, not a linker workaround

Prepared `Common/NovodeX/NwWrapper.h:8–14` disables NOVODEX on aarch64 without a
CLIENT restriction. Reusing it for a native MapServer would implicitly disable
server physics. `Common/entity/ragdoll.h:6–8` still defines RAGDOLL for SERVER,
and `MapServer/src/entity/entserver.c:853–929` uses physics-produced hips matrices
to update entity transforms. `MapServer/src/svr/svr_tick.c:2043–2049` steps scenes
before entity execution and network updates. These are server behavior paths.

`armport/standins/CMakeLists.txt:1–21` is explicitly a client SDK stand-in bundle;
it supplies NULL ragdolls and unrelated client intrinsics through PhysX targets.
Importing that bundle into MapServer would hide missing functions while changing
simulation. It is not the server port.

Before runtime qualification choose and document one of:

1. Preserve equivalent server physics with a qualified ARM64 implementation of
   the required API and behavior. No suitable implementation has been established
   by this investigation, and bundled PhysX binaries are Win32-only
   (`cmake/dependencies/PhysX.cmake:4–5,29–39`). This is substantial separate work.
2. Deliberately qualify a reduced server without that simulation, with an explicit
   product decision and x86 reference runs using the identical reduced semantics.
   Tests must cover death/ragdoll/recovery/knockback, collision/movement and packet
   state; a client already hiding ragdoll poses does not establish equivalence.

A nonshipping compile-only MapServer milestone may expose compiler/type defects
before that decision. It must stay labeled compile-only and never replace the
Thor server package. Keep the existing x86 server until a real behavioral lane
is approved and qualified.

## Width and ordering fixes before native server execution

These are concrete siblings from the full prepared source, not claims of an
observed ARM64 server crash (there is no running ARM64 server yet).

| Defect family | Source evidence | Required test before changing the server lane |
|---|---|---|
| Evaluator stores pointers as int | `MapServer/src/entity/character_combat_eval.c:33` and many FetchInt calls, stores 1356–1368/1398–1410; `MapServer/src/player/badges_server.c:880,893`; `badges_load.c:78,395`. Common's client-visible evaluator was fixed separately in 0036. | Convert pointer-valued variables to existing eval_StorePointer/eval_FetchPointer API. Extract actual server store/retrieve blocks and preserve high pointer bits; original source must fail. Preserve real integer expression semantics. |
| Pointer arrays cleared as ints | `MapServer/src/gameSys/Turnstile.c:256,313` Entity* array; `MapServer/src/group/groupnetdb.c:67,1152` DefTracker* array. | Use element-sized clear operations, include a nonzero upper-half canary across every element, and show the original leaves stale pointer bytes. |
| Pointer-derived narrow keys | `Common/gameData/store_data.h:9–10`, `store_data.c:225,230`, `store.c:66` use U32 composite/pointer keys. | Test two distinct pointers sharing low32 bits. Choose genuine pointer/composite key storage; widening only one cast is insufficient. |
| SQL result queues | `libs/UtilitiesLib/include/utilitieslib/UtilsCXX/semaphoreworkerpool.hpp:48–70,115–122` publishes ringOut without a completion semaphore. `ring.hpp:44–75` accesses plain pointer slots with compiler barriers; `ringchain.hpp:44–76` also publishes/frees page links. | Fix the whole SPSC slot and page-lifetime publication protocol with acquire/release atomics, not just index variables or an extra compiler barrier. Run extracted real ring+chain code with concurrent payload checks/TSan, small pages forcing rollover/reuse, and an original negative control where deterministic instrumentation permits. |
| Other asynchronous queues | `DBServer/src/mapcrashreport.c:30–51` volatile queue and int SOCKET fields; shared `libs/UtilitiesLib/src/utils/log.c` background queue. | Confirm each producer/consumer ownership model before conversion. Extract queue publication/reset/overflow/teardown tests; fix SOCKET as SOCKET separately from serialized int protocol fields. |
| SQL output size ABI | `Common/sql/sqlconn.c:20–21,903–910`, `DBServer/src/container_sql.c:505,524,656` length storage and signed sentinels. | Assert widths under the real ARM64 toolchain and run native ODBC values/null/long-data/row-count binding. Keep actual 32-bit SQL integer payloads 32-bit; sizeof(int) near SQL data is not automatically a pointer bug. |

The 64 SQL workers currently block in `WaitForSingleObject(INFINITE)`
(`semaphoreworkerpool.hpp:18–23`); `sql_fifo.c:26,170–175` selects SQLCONN_MAX−1
workers. Do not add the client render-worker 2 ms spin to this pool. DbServer's
main loop calls `msgScan` then `NMMonitor(1)` (`dbinit.c:370–377,1984–1991`), which
is a separate measurement target. Neither thread count nor cumulative system
CPU identifies which wait path caused the reported cost.

## Bounded implementation order

1. Finish/qualify server telemetry on the retained x86 lane. It supplies an actual
   baseline and leaves the existing Thor build recoverable.
2. In a fresh patchwork checkout, create the DbServer CMake/alias portability
   patch and receipt adapter preserving PostgreSQL/Wine/startup overlays. Export
   only through `armport/scripts/patchwork.py`; never edit upstream. Configure
   Common+DbServer only with the real ARM64 toolchain. Build host StructParser,
   existing libraries, then DbServer sequentially, at most 2 compiler processes.
3. Fix compiler-detected width issues and the SQL queue publication contract with
   source-extracted controls. Produce a nonshipping ARM64 DbServer package with
   exact source/tree/compiler/binary and dependency receipts. Preserve LogServer
   alias semantics if the runtime invokes it.
4. Qualify ARM64 ODBC independently, then the DbServer persistence fixtures and
   fresh private schema. Use a disposable copied profile for the first smoke;
   no automatic migration of the user's saved profile. Exercise 65 connections,
   save/restart, login, map registration and owned clean shutdown.
5. Pair native DbServer with the retained x86 MapServer for the existing client
   creation/reopen/zoning/save tests. Prove socket/wire protocol remains compatible
   and collect per-process CPU. Only then propose a Thor APK through the normal
   build→app-runtime→thor-apk sequence with reviewer approval before handoff.
6. Resolve MapServer physics policy; port target/AILib build settings and all
   server evaluator/array/key defects. Build/qualify native MapServer first with
   the already-qualified DbServer and exact server data ancestry. Compare x86 and
   ARM64 gameplay state, movement/combat/defeats, zoning, save, tick and file-load
   windows. Do not use matching screenshots as complete server equivalence.
7. Optimize only from measured native results: removal of FEX translation is the
   expected structural mechanism, but a numerical FPS/startup/battery improvement
   remains an inference until controlled Thor tests.

For every native fix the CI check must run code extracted from the prepared
source; negative upstream controls should fail for the actual defect. Do not
start a second workflow while one stage of the agreed pipeline is active. New
native/runtime lanes need new provenance and acceptance checks; a green retained
0.10 app-runtime job cannot certify the complete Thor stack.
