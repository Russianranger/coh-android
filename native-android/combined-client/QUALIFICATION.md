# Combined server/native client — October 15, 2026

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
client. This is the next combined physical test.

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
