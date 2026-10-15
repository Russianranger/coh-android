# Combined server/native client — October 15, 2026

## Startup repair 0.1.1

Runtime source: `d26253eaf38e254aadda7e1c18b4dfee39296dc8`.
Client payload source: `623b51299f32cbc7d09195c039a63caaa9e06179`.
Packaging/qualification source: `159a3a3ebb79c7e8173b2662331655d317037311`.
The current ARM64 delivery is 11,242,291 bytes, SHA256
`278363e57b04148a4e5653026105873b164cab557fece651feb0d20ffad9f4ec`.
It retains `org.coh.nativecombined`, uses versionCode 2 and the established signer.
The import contract, runtime pins, Atlas import settings and accepted scene assets
are unchanged. Update in place; no imports or runtime setup need repeating.

The actual Thor 0.1.0 report is preserved under
`evidence/20261015/startup-failure-0.1.0/`. Startup lasted 825.923 seconds and
failed in `local_dbserver_startup` before a DbServer, MapServer or TestClient
process was recorded. PostgreSQL/Wine/ODBC succeeded, and cleanup completed.
The generic original failure does not prove the exact helper exception or a
port conflict. Legacy child elapsed fields were ages at cleanup, not execution
durations. Source TestClient provisioning had not started and did not cause
this observed delay.

Changes remove duplicate ODBC installation/probing, retain the accepted Wine INF
timestamp correction, mark its real proof before later server preparation, and
check actual local port availability early. Reports retain safe exception
class/source-site/errno without messages, credentials or child output. Primary
and cleanup failures remain separate. Launcher progress is session-bound,
bounded and timed, freezes on exit, identifies its app version/storage, and
labels older guest reports as previous-session evidence. Only a matching,
strictly typed private cleanup report can release the owner marker.

All seven local host suites pass: 143 diagnostic boundaries, 24 lease checks,
17 framework-driver controls, import guards and current/exact-donor runtime
contracts. Runtime suites each run 26 methods: 25 pass and one AF_UNIX test is
skipped because this executor blocks Unix socket creation. Actual TCP/UDP bind
admission tests pass. Existing local/DB contracts pass release, ASan and UBSan,
including malformed inputs and explicit descriptor cleanup; Android boundary
binaries compile. Both independent Gradle ABI builds and lint pass (zero errors,
74 warnings). Exact local receipts are in
`evidence/20261015/startup-repair-0.1.1/local/`.

Delivery reuses the pinned CI package artifact `11999855486`, SHA256
`7d878cad7e73f8e7b0f36cde4b35057f773a03bc7d4d258a2687be10805f852d`.
Only `combined/server_runtime.py`, `test_runtime.py` and their build-input receipt
change inside each APK. Every other payload entry, including native ELFs, DEX,
manifest, resources and scene, matches CI byte for byte. Source ancestry,
package pins, signer, 16 KiB alignment and three-entry-only deltas are audited;
three local repacks reproduce identical hashes. Local compiler ELF build IDs
differed from CI, so those local binaries are not the delivery payload.
`tools/reuse_server_helper.py` makes this reuse reproducible and refuses any
other runtime/client source changes. Its qualified source pins are intentionally
strict; future client development requires a new qualified base package.

Workflow [38788212809](https://github.com/Russianranger/coh-android/actions/runs/38788212809)
passed package/host/ARM64 stages and eleven Android checks through JSON export,
then failed because Pillow was absent in the separate emulator job. The failure
is preserved. The dependency is now installed in that job, and final-package
framework continuation [38790024223](https://github.com/Russianranger/coh-android/actions/runs/38790024223)
passed all fourteen checks on the final x86 APK, including actual donor SAF
import/refusal, current GLES scene, Surface/Home recovery, real JSON export and
464 scripted UDP checks across six scenarios. The actual foreground scene has
336 frames in context 6, zero GL/transform errors, 557,056 GPU bytes, 556,562 bright
pixels and at least 14,241 colors. The screenshot was independently viewed.
Hosted source/exact-donor runtime tests pass all 52 executions with zero skips;
143 diagnostic controls pass. Its [artifact](https://github.com/Russianranger/coh-android/actions/runs/38790024223/artifacts/12000096595)
ZIP SHA256 is
`b172f88fad43b38b1fe83a7ba8afb84bbf3715ed8dd21ee5847d7d3827205160`.
Downloaded ZIP CRCs, both APK hashes and byte equality with the delivered files
were independently verified. Exact receipts are under
`evidence/20261015/startup-repair-0.1.1/hosted/`; the consolidated record is
`evidence/20261015/startup-repair-0.1.1/qualification.json`.

Implemented and host-qualified server corrections are not actual device boot
proof. ARM64 guest startup, physical 0.1.1 acceptance, real DB/Map exchange,
encrypted AuthServer authentication and authoritative world spawn/render remain
pending. No gate 25–27 acceptance is inferred from a scripted socket or x86
framework test. Follow the updated [THOR-TEST.md](THOR-TEST.md).

## Original 0.1.0 package and evidence

## Package and source identity

The ARM64 runtime source is `5637133133a3654bb1a4f4b0fdb74ae575d05520`.
The APK is `CoH-Native-Combined-0.1.0-arm64.apk`, 11,493,783 bytes,
SHA256 `4ae4ef25c6ea60bfdcac000f4ff9016ae202aa42e3414024a40c99dcf66b97ee`.
It installs as `org.coh.nativecombined`, separate from the conventional launcher
and accepted native Session Client. The original 0.3.0 preview inputs retain SHA
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
No accepted client APK, original asset, database, account or report was changed.

[Clean package and host artifact](https://github.com/Russianranger/coh-android/actions/runs/38763514350/artifacts/11987440686)
contains both audited packages and deterministic receipts. Its ZIP SHA256 is
`77856abfca3df1975f1b4d13908246286de2116ac1b1bfc12bb578d26aa74729`.
ZIP CRCs, exact APK digests, ABI, signer, source cleanliness and receipts were
independently checked after download. New ARM64 and x86_64 native libraries are
byte-identical to the first integrated package; the correction changed Java path
handling. Large runtime/game payloads are absent. OpenSSL's reviewed license is
included. Public crypto libraries were reused from artifact `11980774730` after
output and current-source hash verification.

Use [THOR-TEST.md](THOR-TEST.md), not a new build of the accepted standalone 0.3.0
client. The startup-repair instructions above supersede the old APK handoff.

## Implementation and evidence boundaries

| Area | Implemented | Verified evidence | Still pending |
|---|---|---|---|
| Imports | Pinned donor APK, all four existing asset parts, optional runtime archives and logical profile dump; atomic private generations | 48 host controls plus 6 regressions using the actual Atlas importer | Thor imports of the user's full asset set |
| Setup/server | ARM64 runtime extraction, retained headless PostgreSQL/DbServer/MapServer, source TestClient provisioning of one saved disposable character, readiness lease and bounded stop | 15 methods run against current source and exact donor closure: 30 executions | Actual ARM64 guest boot, provisioning, stop/restart and physical acceptance |
| Gate 25 local path | Native DB/Map sockets, source framing/reliability preserved, lifecycle owner, real server-issued UID binding | Original-function oracle, sanitized host and Android scripted socket tests | Real server exchange on Thor |
| Gate 26 local handoff | Existing-character list/selection and real DB-to-Map transition contracts; explicit loopback development policy | 464 checks and 6 full scripted socket scenarios per release/ASan/UBSan mode | Real encrypted AuthServer login and its compatible controlled database/account service |
| Gate 27 boundary | Bounded initial Map reception and explicit unsupported scene/entity states | 29,537 Map checks, 10,657 negatives, 18 socket scenarios per sanitizer mode | Complete initial scene/entity decoding and server-authoritative render/spawn |
| Native scene | Accepted 0.3.0 preview retained alongside manual local connect | Existing physical acceptance; new app framework qualification recorded below | New combined Thor report; preview is not a server world |

DB qualification also passes 95,949 wire/parser checks, 10,000 malformed inputs
and 958 checks across 14 socket scenarios in each release/ASan/UBSan mode. Leak
sanitizer is disabled for the documented executor process-inspection limitation;
address/undefined checks and explicit socket descriptor lifetime checks remain.
Both Android ABI native libraries link; ARM64 assembly, lint and package audit
pass. No offline or scripted peer test is labelled authentic server login.

The local policy follows the existing server's `UseFakeAuth` development mode.
It does not forge an AuthServer receipt or weaken the separately authenticated
Map path. Character provisioning uses the existing real TestClient helper and
saved-character validation, not synthetic SQL rows; this is not native character
creation. Native rendering currently remains the offline preview and ends the
network milestone at `SCENE_INCOMPLETE` when more decoding is required.

## Android framework qualification

Final [workflow 38768616549](https://github.com/Russianranger/coh-android/actions/runs/38768616549)
passed all fourteen framework checks using the exact corrected APKs. Its
[artifact](https://github.com/Russianranger/coh-android/actions/runs/38768616549/artifacts/11990384382)
ZIP SHA256 is `738d737fc09c8775ececd426047750e54ddc9bf47ee6b3f42d536fb8c973b949`.
The visible foreground scene reached 267 frames in context 6, with 557,056 GPU
bytes, zero GL errors and transform mismatches. Its actual Surface crop contains
556,406 bright pixels and at least 14,194 colors. The screenshot was independently
viewed and shows the textured character, floor and benches. Actual JSON document
export and all 464 native UDP checks across six scripted DB/Map scenarios passed.
No external ANR recovery or app crash was recorded in this final run. ZIP CRCs,
export digest, clean driver/source binding and unchanged binaries were verified
independently. Exact receipts are in `evidence/20261015/qualification.json`.
The thirteen framework checks first passed in
[38766853490](https://github.com/Russianranger/coh-android/actions/runs/38766853490),
using the exact earlier APKs with no external ANR recovery or app crash. Final
visual review found its screenshot was captured during a new Surface startup
after document export. Additional driver qualification waits for current GPU
ownership and further presented frames, then measures the actual scene crop.
The prior successful receipt and startup snapshot are preserved separately.
The x86_64 emulator can verify imports, native GLES preview, framework lifecycle
and scripted socket ownership; it cannot execute the ARM64 Wine/FEX server.

Earlier failures remain preserved:

* [First run](https://github.com/Russianranger/coh-android/actions/runs/38760894566):
  package/host stages passed, but initial inspection encountered the framework
  files-parent alias, and the driver tapped a background file row behind the SAF
  drawer. The app canonicalizes only the framework parent; unsafe child links
  remain refused. Actual importer regression tests cover both boundaries.
* [Corrected package run](https://github.com/Russianranger/coh-android/actions/runs/38763514350):
  clean startup/import readiness passed, then a system Pixel Launcher ANR
  interrupted the driver before its first picker test. App code and APKs were
  retained; the driver correction and subsequent result are recorded separately.

* [External provider interruption](https://github.com/Russianranger/coh-android/actions/runs/38765658808):
  the external Files app stopped responding after the first picker cancellation.
  Driver correction waits for actual cancellation return, stores UI dumps outside
  the document-provider index and permits bounded recovery only when framework
  traces positively identify that external component. Native app ANRs/crashes
  remain unconditional failures. Seventeen host driver controls include rejected
  black-scene/stale-state examples and strict ANR identity checks.

The full native core workflow
[38763514525](https://github.com/Russianranger/coh-android/actions/runs/38763514525)
and native session foundation regression workflow
[38760894317](https://github.com/Russianranger/coh-android/actions/runs/38760894317)
passed. Existing accepted gate and earlier host/emulator/Thor evidence remains
available.

## Actual concurrent work

Five isolated worktrees ran real independent work, then integrated into
`native-android` with nonoverlapping ownership:

| Worker | Ownership/result |
|---|---|
| Local protocol | Explicit development DB login, genuine UID binding, character selection and Map owner; host/sanitizer/two-ABI contracts |
| Native view | Manual native Activity, JNI and public crypto linkage; lifecycle generation checks and retained preview |
| Imports | Pinned donor/parts/archive imports, setup and path regression fix; no old app storage access |
| Server | Retained donor helper adapter, owned runtime and source-created disposable character; donor API contracts |
| Build | Input preparation, packages, host aggregation, Android driver and workflow evidence |

The coordinator owns launcher/service integration, endpoint lease checks, Map
policy guard, final integration/review, publication and the unified test handoff.
All local worker commits/worktrees and intermediate outputs were retained. A
pre-publication fetch also found twelve concurrent support/HUD/audio/animation/
appearance commits through `c14a831b55163dbcf2b3e63b4c52805785fceafa`,
changing 90 independent files. They were preserved. Their paths are outside the
combined APK source/header/build closure, whose identity was checked before
reusing the package. Two further independent support adapter/evidence commits
through `23060a2ba954441ec16c204fc904516e7d770928` were also preserved. Only
`native-android` was updated, with a checked expected remote SHA; no force push,
reset or merge into `main` occurred.

## Recovery and next work

The earlier agent's recovered stopping point was the completed 22–24
qualification/publication handoff. No actual stalled build/emulator/test process
or unpublished implementation was found in the surviving original tree: 1,151
tracked files matched, and 323 extra files were generated/dependency/reference
outputs. Lost historical Git metadata remains an explicit limit. The exact
[recovery record](../RECOVERY-20261015.md) is preserved. This batch began from the
newer `132a813df53d94c38b441932f85ec42741123abf` remote and did not repeat gates
22–24; the user's physical acceptance stands.

Next independent workstreams, gated on actual device evidence:

1. Capture bounded real local DB/Map states and fix any interoperability/lifecycle
   mismatch from the first Thor report; retain exact framing and transport kernels.
2. Complete source scene and initial entity decoding, then native spawn at the
   received server position. Keep offline preview identity separate until then.
3. Qualify the existing encrypted authentication provider/serialization against a
   real authorized AuthServer and its ODBC/SQL Server account schema. The current
   PostgreSQL/UseFakeAuth local server does not supply this evidence.
4. Integrate independently qualified audio/UI/animation support behind reversible
   boundaries while preserving the accepted renderer and controls.
