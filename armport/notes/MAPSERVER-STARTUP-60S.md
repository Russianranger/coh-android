# MapServer startup experiment — continuation record

Updated 2026-11-01 (America/Chicago). Branch `armport/mapserver-startup-60s`.
**The 60-second Thor target is unproven. No candidate APK or controlled cold
MapServer timing exists from this work.** This checkpoint implements measurement
and one dependency-startup experiment; it is not a performance acceptance.

## Source and comparison identities

Implementation base: `8dc2a66d72477b3c62227e572538b13f0e4f912b`
(`armport/sampler-review-fix`). The task commits follow that base; obtain the
current identity with `git rev-parse HEAD`. Only this isolated branch is changed.
`COH-ArmPort` was `16bf1b3fa7cbde9e01f98398dcf376a655a14f4d` and PR #8's
`armport/m5-thor` was `2da76f65b489669b6dfc637cc940d4339956a53a` at inspection.

The playable comparison is 0.13.44, source
`a5bd2bbe393fd6be22a11b3a9e8b0491b45515f3`, APK run 40743596575,
artifact 12840043807, APK SHA-256
`2cf80a03a0161fc42581147f0c75d8f22ea2ad93fc8884c9abab5c72388e5c1b`.
Its reported warm second launch (~12 minutes tap-to-connected; ~9.5 minutes
outer Atlas interval; internal ready 287 seconds) is historical evidence,
not a controlled baseline. No raw Thor report was recovered here.

The newest built predecessor is 0.13.46/code 61 at the implementation base:
build 40929292200, runtime 40945708189, APK 40952408285, artifact 12931682996.
APK SHA-256 `ca9e4e132a5514eefcfcc6ebad0e772b1c678cbc36667124eaddda5ef71de510`.
Modern MapServer SHA-256
`f359eecc07a92990701c3cdbeb1409d2a8a1f3ab5fbce941f52fd161d25526c1`.
Actual job 123723671400 and PR #8 comment 6508052528 establish this chain.
It executed the **retained** server, not the modern Thor server. Last formal
handoff approval remains .45 review 5692088051. Older pending-CI notes are stale.
Inherited .46 changes include unqualified modern-server instrumentation,
bounded enhancement additions and sampler fixes; none gains Thor acceptance here.

## Measurement and implementation

Guest `map_startup_timing` rows are additive in the character report and existing
`map-startup-observation.json`. Initial request starts at guest service
construction before initialization/dependencies; Android transport and earlier
app work are excluded. Zoning starts at supervisor request receipt, including
validation, baseline query and destination preparation. Spawn-to-ready is a
separate number. Readiness still requires existing owned completed-loop and
DbServer endpoint-status proof; telemetry cannot authorize readiness.
Resident returns are labelled separately. Dependency state at initial receipt
is not automatically a fully stopped-session proof. Client-world observation
is not proof the character is movable; UI tap timing is explicitly unavailable.

Native 0119 now emits separate opt-in `ARMPORT_SERVER_STARTUP_V1` checkpoints.
QPC begins at main entry; output begins only after `parseArgs1` to preserve
query protocols. Directory-cache, definitions, sequencers/animations, DB connect,
group load, map setup, ready-publication and main-loop points are observed.
Group load includes geometry, collision and PhysX; those are not individually
isolated. Loader/Wine/FEX time is outside main-entry timing. Native publication
alone is not the primary readiness proof. Logging cost belongs to the following
phase. Full Atlas/zoning console exports preserve these lines; the existing
`server_metrics.jsonl` parser still concerns post-ready activity only.

The first optimization experiment keeps the modern **Win32** MapServer,
x86 DbServer/ODBC and native ARM64 Linux PostgreSQL. `ensure_local_odbc` avoids
repeating MSI installation when installer/probe hashes and the actual driver DLL
match a successful prior installation. Every launch still executes the native
32-bit registration, DLL-load and required-export probe. Any generation/byte
change, absent/corrupt cache or ordinary failed probe reinstalls and rechecks.
Timeout/cancellation remains failure. The disposable prefix-local cache is under
4 KiB; it contains no credentials. Installation cost and actual time saved remain
unmeasured. This changes dependency startup, not native map initialization.
No schema, durability, character semantics, resolution or simulation is changed.

## Experiments ranked by present evidence

| Approach | Evidence | Next experiment / risk |
| --- | --- | --- |
| Full startup phase observation | Implemented and host compiled | Shipping PE and collection overhead still untested |
| Avoid repeated ODBC MSI transaction | Exact reuse/refusal mechanism host-tested | Measure dependency interval with same driver/prefix; may be a small gain |
| Persistent portable FolderCache index | Native `FolderCacheAddFolder` traverses the full data tree; client scans were slow | Key to immutable data generation; preserve timestamps/private BIN updates and fallback; not implemented |
| Reusable cooked physics meshes | `nwCookAndLoadMeshShape` calls Nx cooking each process | Measure group-load first; SDK/input/architecture-keyed cache needs bounded stream and corruption fallback |
| Startup priority | Development-data `sysInit` selects IDLE priority | Controlled isolated experiment, not a default change; contention-dependent |
| ARM64 MapServer | Real ABI and physics blockers found | Dependency work required before full-function build; no stubbed physics candidate |

Physics closure: bundled SDK 2.8.4 has Win32 **and x64** import libraries but
no ARM64 library/core source found. CMake currently requires MSVC Win32.
Normal startup initializes NovodeX after custom collision; physics stepping and
ragdoll-driven entity recovery remain server behavior. The client ARM patch
globally disables NOVODEX and must not be copied into a server port. Modern
[PhysX migration](https://nvidia-omniverse.github.io/PhysX/physx/5.8.0/docs/MigrationFrom28.html)
is an API/behavior migration, not a compatible binary replacement.
An ARM MapServer can retain the x86 DbServer: callback U32 fields are echoed by
DbServer and can use a MapServer-local full-pointer token registry. Evaluator
pointer/int pairs, pointer-array clears, queues and derived-cache layouts still
need controls. Keep `-nosharedmemory`. No reason to port PostgreSQL was found.

## Validation and limits

See `armport/evidence/mapserver-startup-*-host-checks.json` for actual extracted
source GCC/ASan/UBSan execution on plain patchwork, retained, exact retained donor
and modern certified source. Each prepared lineage passed 11 positive cases and
two original-source negative assertions. This uses Windows-clock/file-I/O shims,
not a shipping PE. Original source inventory remains 5,995 files/173,081,714 bytes.
Modern animation inputs came from authenticated artifact 12926674360 of build
40929292200; ZIP SHA-256
`8389fda6eb2911c9de9165239ea0a82cae7503d3e246f8338bb001ee221e44fe`.

Full ArmPort suite: 419 tests passed with the exact c86 historical baseline and
the installed Java compiler module exposed as `javac`. ODBC cache suite: 9 passed.
Guest lifecycle results and final integration counts are recorded in STATUS.md.
An initial run without those prerequisites failed four checks; it was not a
source failure. Existing server fixtures also reproduce two errors at the base
(missing `map_package` and manifest `files`); a scheduler ownership test is
namespace-sensitive. No acceptance/ownership guard was weakened to hide them.

No new Windows server execution, PostgreSQL persistence/network regression run,
full modern runtime, physical device, memory/thermal result, or acceptance start
has occurred. All ten required Atlas/King's Row process-cold acceptance slots
remain unrun, as do post-reboot and gameplay/save/reopen/zoning checks.

## Build access and exact continuation

The connector supports authenticated source writes and workflow reads but has
no workflow-dispatch operation. Shell GitHub `/user` returned HTTP 401; no
GitHub CLI credential binding or connected Thor was exposed. No duplicate or
push-trigger workaround was used. Native full compilation needs the established
Windows CI and runtime stages. No job is continuing after this checkpoint.

Once authenticated dispatch is available, freeze the branch SHA and run:

```sh
gh workflow run armport-build.yml --repo Russianranger/coh-android \
  --ref armport/mapserver-startup-60s -f build_server_metrics=true
# After every job succeeds, use that exact run ID for all three inputs:
gh workflow run armport-app-runtime.yml --repo Russianranger/coh-android \
  --ref armport/mapserver-startup-60s \
  -f client_run_id=BUILD_RUN -f data_run_id=BUILD_RUN -f server_run_id=BUILD_RUN
```

Existing runtime success still qualifies only retained-server creation/reopen.
Execute the exact modern full-data server, persistence/network acknowledgement
tests on disposable DBs and Atlas/King's Row gameplay before treating it as
qualified. Only then dispatch `armport-thor-apk.yml` with that exact
`m4_run_id` and `server_metrics=true`. Reserved candidate metadata is
**0.13.47/code 62**, same app ID/retained signer; no such APK exists yet.

Before handing off an APK, also produce an authenticated installable rollback
that actually restores the predecessor modern MapServer package (a client
selector change is insufficient). The original pinned .36 donor package is
retained in the producer ancestry; its MapServer is `fea96d0a...8071363`.
Use a greater versionCode for a normal install-over rollback, or a separately
verified supported downgrade mechanism. Do not uninstall/clear the profile.

Then install over the app, keep assets/settings/save constant, and use Save/Logout,
Finish, report export and complete owned shutdown between launches. Collect five
Atlas and five King's Row launches with destination stopped; label first cache
generation separately, plus a separate reboot start. Export every attempt,
including failures. Record OS/cache/dependency state, temperature and battery;
compare phase and full supervisor intervals, then play combat/rewards/collision,
zone/save/reopen and verify destination persistence. Preserve app data on every
failure. No physical 60-second verdict follows from host timing or resident return.

Review task commits against the frozen implementation base first. Incorporation
into `COH-ArmPort` depends on the relevant M5/.46 lineage; cherry-pick task commits
in parent order after that dependency is integrated, not unrelated branch history.
