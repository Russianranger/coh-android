# MapServer startup experiment — continuation record

Updated 2026-11-01 (America/Chicago). Branch `armport/mapserver-startup-60s`.
**The 60-second Thor target is unproven. No candidate APK or controlled cold
MapServer timing exists from this work.** This checkpoint implements the full Android request boundary, guest/native phase
observations and one dependency-startup experiment. It is not acceptance.

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

Android `android_startup_timing.service_receipt_to_map_ready_seconds` is the
primary initial-launch interval: `elapsedRealtime()` is captured at the first
`ClientService.onStartCommand` statement, before validation, profile checks,
worker queuing, Android runtime/import preparation and all guest startup. The
endpoint is Android receipt of a strictly session-bound event emitted only after
the existing owned completed-tick plus fresh DbServer status gate. It is a
conservative upper bound including event delivery; no Python/Android clock
arithmetic is used. Suspend is included. Optional Activity action-to-ready and
client-world observations are separate; a callback is not a physical finger-tap
timestamp, and client-world observation is not movable-character proof.

Guest `map_startup_timing` is retained as a narrower diagnostic. Its initial
clock starts at guest construction and excludes earlier Android work. Zoning
uses its own supervisor request, baseline check and complete destination prep;
resident returns are labelled separately. `runtime_database_route_seconds`
observes private-profile/PostgreSQL initialization through Wine/intervening
setup, ODBC/private DbServer preparation and DbServer-ready/schema snapshot.
This is a contiguous route, not exclusive CPU time. The older
`dependency_start_seconds` remains the narrower ODBC/DbServer subinterval.
Neither observer changes readiness, timeouts, saves, input or gameplay gates.
Initial dependency state alone does not certify a fully stopped session.

A single post-ready `/proc` observation records kernel VmHWM/VmRSS of the exact
owned Linux launch process, with PID-view, start-time and Popen-liveness checks.
It excludes other Wine/FEX workers, DbServer and client; it is not aggregate
MapServer peak or PSS. Missing/denied/mismatched proc views remain unavailable.
Android captures two optional thermal-severity and latest sticky battery-deci-C
observations. Read time is not battery sensor sample time; neither is CPU
thermal measurement. No additional permission, polling or setting is required.

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
| Portable FolderCache metadata replay | Traversal depends on mode: development-dynamic mode defers enumeration to demanded directories; client whole-tree timing is not a server baseline | Measure actual mode/directories first; a fresh host census must include metadata/private BIN updates and its cost inside startup. Persistent reuse needs stronger generation authority than current directory fingerprints |
| Reusable cooked physics meshes | `nwCookAndLoadMeshShape` calls Nx cooking each process | Measure group-load first; SDK/input/architecture-keyed cache needs bounded stream and corruption fallback |
| Startup priority | Development-data `sysInit` selects Win32 IDLE priority; Wine may only record that metadata | First measure actual Linux task scheduling/nice effects; direct zoning nice adjustments are separate |
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

Follow-up source correction during CI: `FolderCacheChooseMode` selects
development-dynamic mode when `./piggs/texts.pigg` is absent; that mode does not
perform the ordinary AddFolder full scan. Modern staging is expected to omit
texts.pigg, but the actual launched mode still needs observing. Per-directory
interception can retain demand behavior. A host-only fresh two-pass census of
162,937 server-like rows took 7.445 seconds including comparison and an 8.15 MB
compact packet on this x86 host. That is a corpus experiment, not an engine,
Wine, PRoot or Thor result. Earlier actual POSIX capture cost ~56 seconds, so
moving Python outside Wine alone has no established benefit. Current directory
fingerprints and a few anchor files do not prove every leaf remains unchanged.

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
The existing database protocol/receipt regressions also pass: network ACK17 and
character persistence18. These execute host process/capture controls and source/
receipt checks; they do not rerun the Windows/PostgreSQL commit-lock/failure
experiments or create a native gameplay character. New exact-PE runtime evidence
remains separate from these host regressions.
An initial run without those prerequisites failed four checks; it was not a
source failure. Existing server fixtures also reproduce two errors at the base
(missing `map_package` and manifest `files`); a scheduler ownership test is
namespace-sensitive. No acceptance/ownership guard was weakened to hide them.

The e563 modern PE executed the real Windows PostgreSQL network-ACK tests
successfully, but its app runtime failed package staging before any guest/map
launch. No new asset-backed modern map, physical device, startup timing or
acceptance run exists. All ten Thor Atlas/King's Row slots remain unrun, as do
reboot and complete gameplay/save/reopen/zoning checks.

## CI evidence and corrected continuation

Implementation branch: `armport/mapserver-startup-60s`; base remains
`8dc2a66d72477b3c62227e572538b13f0e4f912b`. Initial task commits are
a14d1a838 (instrumentation), 95a09d11d (ODBC reuse), 51fa0bbb8 (record),
155c33bcf (branch CI) and e563fe5664cd13570899800695c7e9680ac68877 (kickoff).
The corrected source is frozen by a separate workflow-only kickoff; obtain its
exact identity with `git rev-parse HEAD` and the live run IDs in draft PR #9.
No main/protected branch, repository setting, merge or release was changed.

| e563 attempt | Result / scope |
| --- | --- |
| Build41363927704 | All10 jobs passed, including both genuine Win32 builds |
| Native artifact13109558483 | 6,163,033B; SHA256 d54b90f27f6bab463d6304f68dc91286a31305bd6db819055b5027bacc293d7c |
| Modern PE | 7,494,656B; SHA256 f893cee6cd6c4dc8b7c45c8b5f7c07572aaabbe50ee5b8730b9ddd3da12dac94 |
| ACK41372568968 | Actual PE/unchanged reference DbServer, committed/blocked/failed-write ACK checks passed; not gameplay |
| ACK artifact13110032093 | 18,126B; SHA256 269445c6be39e7c94aacc54f5e337e1a7a5b60cec7f7c4dcf73a622871323551 |
| Runtime41372922907 | Staging failed after5.419s; guest_failures={}, no guest launched; not a startup measurement |
| Coordinator41363909847 | Failed, no APK dispatched |
| Modern41370488143 / rollback41368945719 | Failed their upstream waits, no native test/APK launched |

The independent native audit found the cause: guest validation still pinned
old0119 SHA49c0f73d...c387 while both actual packages use
5656eb55d3dcc7cb45ee7760a9befbf2d08bdae90e72dbd678eda6662bca085f.
The pin is corrected without widening admission. A real-file hash regression
fails before the repair; both real native bindings and actual modern archive
staging pass afterward. The initial fixtures derived their synthetic patch pin
from the validator and missed drift; the new check is independent of them.
The native/ACK success remains valid in its stated scope, not app qualification.

Retained source/SDK/native/ACK/rejection/repair evidence is under
`armport/evidence/mapserver-startup-*`. Corrected host checks: full ArmPort443;
Android timing6 plus69 existing lifecycle/stage/sidebar/budget/profile checks;
guest timing16, memory observation16, saved-map14. Two unrelated character
fixture errors reproduce with the original method and remain documented above.
Actual official SDK35 resource/all24 Java-source/D8 compilation passed; every
nonmanifest resource stayed byte-identical to .36 and manifest differs only in
version. This produced no signed installable APK or runtime claim.

The authorized coordinator uses the normal ephemeral Actions token on this
isolated branch, dispatching existing build → runtime → APK serially and refusing
failed/duplicate/moved-source stages. Setup uses [skip ci]; only its own YAML
kickoff is unskipped, avoiding a duplicate push build. Freeze its source until
both primary and rollback coordinators finish. Mock tests now suppress fixture
run IDs from real workflow summaries. Browser Run workflow was absent because
these ArmPort workflow files are missing from main; main stayed unchanged.

Supporting test code is on `armport/mapserver-modern-runtime-qualification`.
Modern full-data qualification authenticates original23 payloads, all173,011
import leaves, exact candidate PE/client/data and c86 validators, then runs
candidate Atlas creation/save, candidate reopen/save and original-modern-server
reopen of that same stopped disposable save. It preserves all native tick/status,
SQL/save, identity, cleanup and task gates. Windows ACK uses the original accepted
reference/schema receipts, separately authenticates only the MapServer overlay,
keeps all original ACK/lock/fatal/commit guards, and rehashes executed bytes.
Both supporting source/run constants must be refreshed for the corrected cohort.
No new native compiler or schema build is needed by those supporting jobs.

Earlier read-only modern41367191699 and ACK41370948195 were cancelled before
heavy execution to add baseline continuity and Windows byte-preserving checkout,
respectively. Unrelated PR diagnostic41363913327 was cancelled to avoid compiler
overlap. These are CI orchestration records, not failed MapServer timing runs.

After corrected build/runtime success, sign .47/code62 through the established
workflow and independently audit APK identity/signer/retained bytes/actual PE.
Produce one same-source/runtime `server_metrics=false` rollback APK only after
the primary coordinator succeeds. It restores actual original modern MapServer
fea96d0a...8071363, not a client selector. Equal code62 installs over the candidate
with the same retained signer. Save/Logout → verified Finish/cleanup → install →
Set up / update runtime activates the archive; APK installation alone does not.
Never uninstall/clear profile data. Physical install and recovery remain untested.

Use `armport/THOR-STARTUP-CAPTURE.md` and the offline report extractor for five
fully stopped Atlas plus five King's Row attempts, reboot and normal gameplay/
save/reopen/zoning. Preserve every failed/slow attempt, caches/settings and declared
snapshot conditions. The normal UI cannot restore identical database snapshots;
that comparison limitation is explicit. No Thor connection is currently exposed.
The <=60-second Thor target remains unproven until physical evidence is collected.
