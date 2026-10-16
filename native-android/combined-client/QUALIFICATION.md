# Combined server/native client — October 16, 2026

## Complete normal-world scene structure 0.1.7

APK runtime source: `fe037348c9a184d98aff96f0803b2afc0e631b71`, tree `93390b9fb6f765e4b864669eac66995e56c1f955`, on `native-android`.
Local integration `127ce7292297aebb55b3b1dbeb59000a1cab91dc` has the same tree.
Publication uses a fresh remote check and guarded non-force update. The user's
[physical 0.1.6 acceptance](evidence/20261016/thor-0.1.6-acceptance/THOR-016-ACCEPTANCE.md)
is preserved: real 42,889-byte GROUPS reception, prefix inspection, owned-buffer
release and explicit Return with the server still reported ready. The accepted
0.1.6 APK was not rebuilt. This section describes a separate new implementation
and does not extend physical acceptance to 0.1.7.

The new zero-allocation inspector traverses the complete bounded normal-world
GROUPS grammar: prefix, group files, definitions and all supported optional
blocks, child/root matrices, properties, texture swaps, removals, sparse ordered
identities and the four-field footer. Exact logical end is required. Packed and
byte-aligned representations use the existing reader kernels. Floats must be
finite. File/definition/root/string/work budgets reject oversized input before
unbounded work; base/raid and unknown texture-mask branches remain unsupported.
Source producers traverse definition/root identities in ascending order; the
inspector rejects duplicate/decreasing records without allocating an identity set.

Reader/output changes are transactional. Map keeps the last successful numeric
inspection and a separate current failure checkpoint, then releases the owned
body on every path. Begin clears the receipts; cleanup preserves them. Full
supported structure increments `scene_structures`; malformed supported tails
fail and close the client, while unsupported variants remain incomplete. The
JNI report adds 23 numeric inspection fields and a three-field failure receipt.
The UI distinguishes the latest unsupported variant from an earlier successful
inspection instead of showing a stale success hint. Failure bit offsets are the
last completed read boundary; prefix failures retain the accepted prefix parser's
rollback boundary rather than locating an exact malformed field.

This is structural decoding, not a resolved scene graph. Footer checksums are
observed, not verified against imported definitions. Matrices are traversed, not
reconstructed or compared to renderer transforms. Saved library definitions may
be omitted by the authentic producer, so the wire packet alone need not contain
the whole world. No entity request, READY/full-update acknowledgement, selected
character identity, authoritative position or world render is introduced. The
endpoint stays `SCENE_INCOMPLETE`; DB server/generation binding is distinct from
verified character identity. Encrypted AuthServer login remains pending.

Six workers actually ran concurrently in isolated worktrees with nonoverlapping
ownership: physical evidence, parser, original-source oracle, Map/local
integration, Android qualification and independent review. The coordinator owns
JNI/UI/release, common build linkage and handoff. Independent review corrected a
test-oracle compression-mode adapter and a driver interpretation of DB binding
before integration. Every corrected fixture payload remained bit-identical.

The faithful oracle executes 41 unchanged original functions, with 16 original
source files pinned, with controlled graph objects and explicit packet-factory/profile
adapters. It emits 44 deterministic fixtures: 40 complete normal-world bodies
and four deliberately partial unsupported-base headers. Coverage includes raw
and original-packed matrices with PYR/scale, optional property/trick blocks,
saved-library omission, force reload, deletion and incremental updates. Original
compression/alignment helpers execute; packed fixtures use the source incremental
path and full updates use byte alignment. A one-byte source mutation is refused.
The source producer/checksum traversal and independent expected metadata agree;
this is not execution of the complete MapServer or Game client.

Release, ASan and UBSan each pass 2,473,492 parser checks, 172,422 negative cases,
138,722 every-bit truncations, 1,028 large-boundary truncations and 40,000 fuzz
cases, with zero wrapped allocation/free calls. Independent probes separately
pass 22,188 assertions/2,775 cases/2,728 truncations per mode. The independent
host object's largest emitted parser frame is 912 bytes, not a measurement of
the whole Android call stack. The exact JNI report function passes host serialization and strict format
checks through a JNI shim, including all 23+3 positional mappings; its worst numeric report is 3,656 bytes
within the unchanged 6,144-byte buffer. Map passes 31,480 checks/10,665 negatives/
33 UDP scenarios per mode. Local passes 1,078 checks/nine UDP scenarios and a
separate complete headless DB-to-Map peer flow per mode. Earlier replication and
transport kernels remain covered by their preserved suites.

All fourteen consolidated host suites pass, including the original 170 strict driver controls.
Local release, ASan and UBSan receipts are retained. Both ABI packages assemble,
lint with zero errors and the unchanged 75 warnings, and pass clean-source audits.
Local runtime tests pass 36/38 methods with two sandbox AF_UNIX skips; hosted
current and donor runtime tests each pass 38/38 with zero skips. The first local
source pass lacked three pinned original files; exact tracked blobs were hydrated
and the complete batch then passed. The initial isolated Gradle cache setup stop
preceded compilation; the existing cached toolchain completed both builds.
Local APKs are not the delivery binaries.

The package job in [workflow 38836479975](https://github.com/Russianranger/coh-android/actions/runs/38836479975)
passes all fourteen hosted suites and both ABI builds/lint/audits. Its exact
[package artifact](https://github.com/Russianranger/coh-android/actions/runs/38836479975/artifacts/12018934207)
has 43 CRC-verified members, 11,084,577 bytes, SHA256
`18057b8aa24df3457cc4fc6c547abc8c66a3d8973fd3bc44c6fbe87ac1d44970`.
The ARM64 APK is **11,536,171 bytes**, SHA256
`58c45d44501373309788d70e2483786e412d9b0593e86ba1bae94140a8147475`;
the x86_64 companion is 11,132,732 bytes, SHA256
`9ff5c3393477f71175729b6f9e4e3bae1c8860b4e63a9f4436cefe570ec6165f`.
Both have versionCode 8 and the unchanged package/signing identity. Against the
accepted exact 0.1.6 CI packages, all 74 assets, PRoot/runtime helpers and both
renderer ELFs are byte-identical; only `libcoh_combined_network.so` changes among
native/asset payloads. Large game or server archives are not embedded.

The original Android job stopped when Android UIAutomation crashed with a bad
file descriptor and returned 137. The driver rejected its capture; no CoH app
fault was evidenced. Retrying only that failed job reused the successful package.
Its next attempt passed 19 checks, then exposed a new driver assumption: a fresh
Activity deliberately reports exactly `IDLE` until explicit Connect creates its
native controller. The correction requires that exact minimal report before
Connect and the complete zeroed scene schema at `CHARACTERS_READY` after Connect.
Active-session guards are unchanged. It passes 185 host driver controls and
replays correctly against both archived real framework reports. Both incomplete
attempts remain recorded as failures rather than qualified runs.

The [exact-package continuation 38838677592](https://github.com/Russianranger/coh-android/actions/runs/38838677592)
uses qualification driver `8e237b984c188dd19c171387914e795916712556`, tree
`06d7627e2b70608201db9bb3afa0200d06d5c72d`. Its 38 reuse controls cover source,
archive, APK, ELF, receipt and generated-header mutations. Admission pins all
165,488 production/build paths, both APK identities, six standalone Android
protocol/peer/Map ELFs and 57 source-pin entries. Only exact driver/helper,
documentation/evidence and continuation-workflow changes are allowed. The main
package build and old continuation are skipped. No APK or native peer is rebuilt.

All **34/34 actual Android13 app checks pass** in the continuation, including
complete GROUPS traversal in the JNI-backed app, actual SAF donor imports/refusal,
protected donor bytes, held framework input across Return, retained launcher/task/
process, disconnected fresh preview, Near/Far, Surface recreation, Home recovery,
JSON and ZIP exports, and the Android local controller's 1,078 checks/nine socket
scenarios. The final foreground has 1,249 frames, four contexts, 557,056 GPU bytes,
478,874 bright pixels and at least 12,515 colors. No CoH crash/ANR or GL/transform
failure is recorded. The [successful framework artifact](https://github.com/Russianranger/coh-android/actions/runs/38838677592/artifacts/12020004551)
is 2,078,136 bytes, SHA256
`99d52db03995364705d12c7d40f476a41eccbe003cab6442452eba8b023a17f9`.
All 458 archive members pass CRC verification. Three saved picker/preview frames
were independently viewed and hash-bound in `visual-review.json`; they show the
accepted offline preview rather than a server world. The complete scene-message
receipt is separately bound by the actual after-selection numeric report.

Supplemental [portable-core](https://github.com/Russianranger/coh-android/actions/runs/38836479966),
[session-protocol](https://github.com/Russianranger/coh-android/actions/runs/38836479985)
and [live-protocol](https://github.com/Russianranger/coh-android/actions/runs/38836479986)
workflows all pass on the runtime source. Five live Android native suites total
130,830 checks; the separate UDP owner passes 1,194 checks/22 socket scenarios.
These controlled peers do not execute the ARM64 game server or establish real
encrypted authentication or a server-authoritative world. The actual 0.1.6 Thor
server evidence remains separately accepted.

The actual app's peer message is a complete original-producer fixture, not the
previous prefix plus unparsed zero tail: 139,794 decoded bytes, 1,118,352 bits and
3,575 compressed wire bytes over three sibling datagrams. It contains 192
definition records, 384 children/properties/swaps, four root updates, 194 raw
and 194 packed matrices. The fixture's expected counts and footer values are
independently bound. These synthetic graph records do not represent a complete
imported Atlas world or an authentic captured session. Live-world/authentication
flags remain false, retained owned bytes return to zero, and disconnect closes
both client sockets.

Install the exact qualified CI ARM64 package over Combined, keeping imports,
runtime, saved test character, reports and earlier APKs/fallback apps. Do not
repeat setup or clear storage. New physical full-structure reception awaits the
Thor report. Complete imported-library resolution/checksums and authoritative
entity identity/position remain the next dependencies. Startup/cache ownership
and memory protections are unchanged; no startup-speed or prior kill-cause
claim is made. Final evidence/documentation does not rebuild or repack the APK.

Final publication preserves the concurrent offline-support commit
`bae8cca2b4ae0e43070d5e86ca1c6f1df668bc00`. Its 116 paths do not overlap this
handoff, the Combined/Session source prefixes, or 80 checked tracked ARM64
compiler/build inputs. Those inputs still match the qualified APK source. The
[concurrent integration audit](evidence/20261016/full-scene-0.1.7/concurrent-integration.json)
keeps that separate support batch's qualification distinct; no new support code
is silently included in this exact APK or newly accepted by these results.

## Physical Thor acceptance of 0.1.6

The user declared the exact code-7 APK successful. The new
[physical acceptance record](evidence/20261016/thor-0.1.6-acceptance/THOR-016-ACCEPTANCE.md)
binds both native snapshots and the current launcher report to the qualified
11,532,139-byte APK, SHA256
`c41000d95573e5ed7baa73dabce0baa3d5c85d75bff6b88a3253385384f6345d`.
Actual MapServer `GROUPS` reception succeeds: **42,889 decoded bytes** from
**10,354 compressed bytes**, one supported scene prefix, zero decode failure,
zero retained owned bytes and no local connection failure. This physically
accepts the bounded large-body receive milestone, beyond the old 16 KiB cap.

The later report captures explicit Return requested/ready **15 ms** apart,
both client sockets closed, both rendering contexts completed, released GPU
resources and zero cleanup/GL/transform errors. The subsequent launcher report
still records its server ready and owned process alive. This accepts Return and
reported server continuity for this attempt; launcher PID/task identity, fresh
client reopen, held-input Return and a current server Stop are not new physical
observations. Existing hosted regressions and earlier controller acceptance
remain separate.

Current server readiness is **392,192 ms (6m32.192s)**. The detailed guest cache
timings in this ZIP belong to the previous 0.1.4 session, so current warm/cold
classification and the cause of its faster start remain unknown. No current
low-memory exit is evidenced. All eight recorded Android exits predate this
native session; the separate earlier low-memory causes remain unresolved.

The accepted endpoint remains `SCENE_INCOMPLETE`: its full `GROUPS` tail is
unsupported, zero entity prefixes were inspected, and AuthServer authentication
and server-world rendering remain false. This does not accept complete Gates
25–27. Gates 1–24 retain their earlier documented physical scope. The next
milestone was complete bounded normal-world scene-message structural decoding,
implemented separately in 0.1.7 above. Imported-library resolution and authoritative
entities remain subsequent dependencies; 0.1.7 has its own pending physical test.

## Bounded compressed scene receive 0.1.6

Historical qualification at delivery; the physical record above supersedes the
then-pending Thor receive/Return status within its stated scope.

Qualified runtime and driver source: `7c9cfdb9d5f87c2297f8772fc3aeff528577728f`, tree `15cce2275e7d6c55b4b4f0acddd62c6803174e76`, on
`native-android`. Local integration pin `648ebf2d0c2cca9dfa5ef9acf9b1fe705ffe9c01`
has the same tree. Fresh remote checks and guarded non-force publication preserve
concurrent development. Earlier worktrees, unpublished changes and qualified APKs
remain preserved. Recovery reached the qualified 0.1.5 handoff; no actual stalled
build was established. Process enumeration was unavailable in this environment.

The exact 0.1.4 Thor report establishes server startup, DB character selection,
initial Map CONNECT/SHORTCUTS acceptance and REQSCENE, followed by a queued decode
`COH_LIMIT` before scene-prefix inspection. Its failed declared size was unknown.
This batch removes the default decoded-body bound from the Map GROUPS path using
an explicit per-session 4 MiB budget. The ordinary 16 KiB message/queue and
compressed-wire bounds, 16-sibling bound, transport framing, Blowfish, ACK,
reliability and ordering contracts remain. DB/Auth continue using ordinary
delivery. This is not evidence that every possible real scene fits those bounds.

One owned decoded body may be outstanding. Declared size is checked before
allocation, decoding retains the persistent zlib stream, and inspection is
synchronous. Every inspected body is released; close, cancel, suspend and destroy
invalidate retained views. A monotonic UDP lease generation rejects an old view
across link recreation, including address reuse. Non-GROUPS messages remain
limited to 16 KiB at Map dispatch. Replication's bounded entry point allows only
GROUPS bodies above that limit; ordinary APIs retain their existing contract.

Reports add numeric decode reason, compressed/declared bytes, output budget,
allowlisted normalized command, and owned allocation/retention high-water data.
Map records actual last decoded and successfully inspected scene-prefix bytes.
If inflation fails, those Map last-message fields still describe the preceding
success; the decoder receipt describes the failed body. No packet payload,
credential, cookie, account name or server-provided text is added to diagnostics.
The UI provides a bounded failure hint and retains Return to launcher.

Workers actually ran concurrently in isolated worktrees with separate network,
replication, Map/local, Android tools and independent review ownership. The
coordinator integrated release/JNI/UI and guarded publication. No runtime/cache
implementation, imported data, accepted renderer or preview assets were changed.

Host evidence includes release and ASan/UBSan runs: network 127,218 checks with
53,808 negative cases, UDP 1,194 checks/22 actual socket scenarios, Map 31,007
checks/10,661 negative cases/29 scenarios, local 659 checks/seven socket chains,
and replication 86,632 assertions/6,947 truncations/34,000 fuzz cases. Original
compression fixtures cover decoded bodies up to 4 MiB. An independent 49-check
source oracle verifies streaming compatibility and rejection of a hostile
4,294,967,299-byte declaration before allocation. Eight actual-JNI serialization
cases pass strict format checking and sanitizers, with a maximum 2,804/6,144 bytes.

All thirteen consolidated host suites pass, including 126 driver controls.
Both ARM64 and x86_64 assemble, lint and pass clean-source/package audits; lint
has zero errors and the same 75 warnings. All 74 assets retain qualified 0.1.4
and 0.1.5 bytes. Local renderer binaries differ only in their generated 20-byte
GNU build-ID descriptors; all other bytes are identical. These local APKs are
not the delivery binaries. The initial isolated checkout lacked a pinned oracle
source file; it was hydrated exactly and the full batch then passed.

The package and Android13 jobs in [workflow 38830583681](https://github.com/Russianranger/coh-android/actions/runs/38830583681)
both pass. The [package artifact](https://github.com/Russianranger/coh-android/actions/runs/38830583681/artifacts/12016524031)
has 40 CRC-verified members, 11,018,789 bytes, SHA256
`5977465de145377c756f40a305caf16e1ef4aa407577c526bc1ddd5daefae4ce`.
Hosted current/exact-donor runtime tests pass 76/76 methods, zero skips, including
the AF_UNIX interruption and numeric-resource capture controls. This does not
execute the ARM64 game server.

The exact CI ARM64 APK is **11,532,139 bytes**, SHA256 `c41000d95573e5ed7baa73dabce0baa3d5c85d75bff6b88a3253385384f6345d`.
The x86_64 companion is 11,128,916 bytes, SHA256
`f757499766d507dc3df26d00e720c243a665fab962ccb624f543b3c5869d0c1e`.
Both hosted packages retain all 74 assets, PRoot and renderer binaries exactly
from qualified 0.1.4/0.1.5; only the native network library changes among those
payloads. The local build-ID difference is absent in the CI-to-CI comparison.
Package/signing identity and external import contract remain; versionCode is 7.
No large game/runtime archive is added.

The [framework artifact](https://github.com/Russianranger/coh-android/actions/runs/38830583681/artifacts/12016899930)
has 455 CRC-verified members, 2,064,737 bytes, SHA256
`ecd08f0cdd69e9080caba13f17e2ce33872dcd25b5ef36da2b8d7c6839802cc6`.
All **33/33 Android13 checks** pass. The actual app receives the expanded scene
fixture, records `SCENE_INCOMPLETE`, one scene prefix, 131,072 decoded bytes,
8,745 compressed bytes, a 4,194,304-byte budget, zero current owned bytes and
131,072 high-water bytes. Explicit Disconnect closes both client sockets.
Held framework input clears on Return from the character picker; the same
retained launcher/task/process resumes, and reopening remains IDLE until explicit
Connect. Actual SAF imports/refusal, protected donor files, Near/Far, Surface
recreation, Home/return, native JSON and launcher ZIP exports also pass. The
final foreground has 1,121 frames, four contexts, 557,056 GPU bytes, 478,903 bright
pixels and at least 12,535 colors, with no app crash/ANR or GL/transform failure.
Three saved picker/preview frames were independently viewed and hash-bound.

Independent [portable-core 38830583564](https://github.com/Russianranger/coh-android/actions/runs/38830583564)
and [live-protocol 38830583527](https://github.com/Russianranger/coh-android/actions/runs/38830583527)
workflows pass, including all five actual Android native crypto/TCP/UDP contract
suites. Those peers remain explicitly synthetic. The separate session socket
binary also reported 1,194 checks/61 negatives/22 scenarios on Android, but its
old strict validator expected 886/49/16. A reviewed qualification-only correction
at `a724487ecf774151ad73cd004023341e7d18381d` adds 55 strict controls and a
[narrow continuation](https://github.com/Russianranger/coh-android/actions/runs/38831867730)
using the exact archived binary, archive/ELF/source/header pins and unchanged
production closure. The successful original host/build jobs are skipped; the
consolidated APK is not rebuilt. The continuation passes all steps, including
the same binary's 1,194 checks/61 negatives/22 socket scenarios on Android13.
Its [artifact 12018335330](https://github.com/Russianranger/coh-android/actions/runs/38831867730/artifacts/12018335330)
is 76,352 bytes, SHA256
`63f99bb8dd352c36107b90e3da0113e2f425b3c5147cbfbd7c4b442c8746c506`.

Deliver the exact qualified CI **CoH-Native-Combined-0.1.6-arm64.apk** without
repacking or rebuilding it. Install over Combined and reuse imports/runtime/test
profile. Keep the conventional launcher and accepted native APKs/data. This
documentation/evidence handoff does not trigger a second build.

The Android peer intentionally supplies a source-layout GROUPS prefix with an
unparsed synthetic tail: 131,072 decoded bytes from 8,745 compressed wire bytes,
eight UI-peer fragments, and 1,048,576 payload bits. It is not an authentic server
capture or a complete GROUPS fixture. Expected state is `SCENE_INCOMPLETE`, one
scene prefix, zero owned bytes retained, and no authenticated/world success flag.
Complete tail validation, imported-library graph resolution, checksums, initial
entity identity/position and authoritative rendering remain pending. The source
[GROUPS audit](../engine/replication/GROUPS-AUDIT.md) records omitted library
definitions, sparse root updates and unsupported base/raid branches for the next
decoder. No REQALLENTS/READY shortcut or fabricated spawn is introduced.

Physical 0.1.6 large-scene reception and Return/server continuity were accepted
by the October 16 report above within its documented scope. Encrypted AuthServer
authentication and a live native world are not accepted. Gates 1–24 retain their
documented physical scope. The prior low-memory exit cause and warm-start performance are unresolved; this batch does not change
server startup/cache ownership or claim a speed improvement.

## Return to launcher 0.1.5

Historical qualification at delivery. The 0.1.6 section above supersedes its
then-pending scene-receive implementation; physical acceptance stays separate.

Runtime/UI and qualification source:
`5bf8d954190d3e924d3c23b51735eebe7a07c0e3`, Git tree
`5bdb21d3e733bbf4cd6a3fcc1e082b01e46ddb97`, exclusively on `native-android`.
Publication freshly checked `bfbbdbc487c4e4a53ce5d7396e3ff4bf9eebbed0` and used
a guarded non-force update. The five local integration commits remain on
`preserved/combined-015-local-validation`; prior worktrees and qualification
history remain preserved.

The new [physical 0.1.4 evidence](evidence/20261015/thor-0.1.4-connection/THOR-014-CONNECTION.md)
matches the exact qualified APK in both the standalone report and launcher ZIP.
It confirms readiness at **13m20.298s**, a clean manual stop in **4.304s**, real
native DB list/selection and initial Map application CONNECT/shortcut acceptance.
The source state machine successfully queues REQSCENE. Queued compressed receive
then fails with `COH_LIMIT`, before any scene prefix reaches its parser. The
reported command/length belong to the preceding accepted shortcut message; the
failed declared size and exact decode subcondition were not recorded. This is
bounded real local interoperability, not encrypted AuthServer login, full Gate
25–27 acceptance or a native live world.

The physical preview remains healthy through 6,039 frames and ten contexts with
zero GL/EGL, transform or depth-order errors. The picker retains an accepted
camera aspect. There is no new Android low-memory exit in this run; 897 valid
memory samples show no measured pressure stop. Earlier memory-kill causes remain
unresolved. The recorded cold data mirror takes 438.672s; beacon work takes
67.561s. No warm-start timing or speed improvement is inferred from one clean
run. A UI APK update does not itself prove a server-data cache invalidation.

The native client now has a full-width **Return to launcher** button at the top
of its existing bounded scrolling controls. It blocks repeated navigation and
new Connect requests, invalidates pending character selection, and queues
suspension on the existing single network owner. Capture completion returns on
the main Handler; a two-second deadline records `cleanup_pending` rather than
blocking the UI or claiming completion. Normal pause/destroy still clear input,
release rendering resources and close the client handle. The action does not
reference the server service or issue a server stop/cancel operation. Normal
same-task navigation finishes the native Activity and resumes the retained
launcher. A direct-task fallback creates Main with CLEAR_TOP/SINGLE_TOP before
finishing. That fallback is source-reviewed, not emulator-executed: the native
Activity remains non-exported and no qualification hook is added.

Workers actually ran concurrently in isolated worktrees: minimal Activity
implementation/lifecycle review, Android build/framework qualification, sanitized
physical evidence and independent protocol/lifecycle analysis. File ownership
did not overlap. The coordinator integrated release metadata, source/remote
guards and this handoff. No runtime, engine, native renderer, assets, imported
data, account, character or profile was changed.

All twelve local host suites pass, including release/ASan/UBSan protocol
regressions, 94 driver controls, 83 installed-APK identity checks and 152 guest
diagnostic checks. Sixteen new Activity-inventory controls distinguish historical
references, duplicate/recreated launchers, wrong task/native Activity records,
pending finish/stop and malformed dumps. Both ABI packages assemble, lint and
pass clean-source/package audits. Lint has zero errors and 75 warnings; the one
additional warning is the new English button label, consistent with the existing
direct-label UI. All 74 asset entries, build-input metadata, runtime helpers,
import contract, PRoot payloads and native/engine/Session Client source closure
are unchanged from qualified 0.1.4. VersionCode advances from 5 to 6 with the
same package and signer. Local packages are not the delivery binaries.

The package job in [workflow 38818477241](https://github.com/Russianranger/coh-android/actions/runs/38818477241)
passes. The [package artifact](https://github.com/Russianranger/coh-android/actions/runs/38818477241/artifacts/12011278016)
is 10,981,949 bytes, SHA256
`423198cd177deb242f5d17321d85dca3d26e11ae56e45360d5f3ef825d67fdaa`;
all 38 member CRCs and both clean-source/package receipts were independently
checked. Hosted current/exact-donor runtime tests each pass 38/38 with zero skips.

The exact CI ARM64 package is **11,528,591 bytes**, SHA256
`71e2f272bfadfc1076b3fcf832b41eba8d83c5541db7198ab69f4f38b2cb5671`.
The companion x86_64 package is 11,125,424 bytes, SHA256
`49163fcaa39708a462bb375ea13df9b4f8e266a1c9a2bd3143386a0c67d05144`.
Independent entry comparison verifies all 74 assets and all six native ELF
payloads across both ABIs are byte-for-byte identical to qualified 0.1.4. Only
AndroidManifest.xml and classes2.dex differ. The signing certificate remains
`9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522`.
Deliver the exact CI ARM64 binary without rebuilding or repacking it.

The independently triggered [portable-core workflow 38818477277](https://github.com/Russianranger/coh-android/actions/runs/38818477277)
also passes its pinned derivative, host core/oracle and ARM64 Bionic crossbuild.
That job does not execute the ARM64 server or establish a native live world.

The Android13 job also passes, **32/32 checks**. Its [framework artifact](https://github.com/Russianranger/coh-android/actions/runs/38818477241/artifacts/12012113270)
is 2,063,319 bytes, SHA256
`1a46047963786bd25046df9d92892a67c985f661d937ab8dbb31303445c40328`.
During a real framework-held W input at the scripted character picker, the source
held mask is 1 before Return and zero afterward; focus-clear count increases
0 → 2, client phase becomes SUSPENDED, and its one opened socket is closed.
Android resumes the exact retained Main Activity token/task/process, with one
Main instance, no Native Activity and no pending finish/stop record. The observed
service state and independent scripted peer/policy remain intact. A new native
Activity renders at least 72 frames in IDLE with clear input before the explicit
Connect command. The second unchanged peer then exercises the complete existing
scripted DB-to-Map scene-prefix contract. Both peers close their two sockets and
their fixture policies are removed.

Return before launcher ZIP export again resumes the same Main/process and
records both client sockets closed. The actual SAF ZIP is 11,432 bytes, SHA256
`3516e9a159608eee28c76ee4d238b80607634316638877de193392f36f978865`;
it keeps the current code-6 APK identity and explicitly labels the preserved
scripted code-3 native report as historical. All prior import/lifecycle/scene
checks remain: 71 protected donor files, two actual SAF imports with descriptor
counts 115 → 115 → 115, malformed-donor refusal, Near/Far, Surface recreation,
Home/return and native JSON export. Picker and reopened Surfaces remain 1920×382.
The final foreground scene has 1,209 frames, four contexts, 557,056 GPU bytes,
479,008 bright pixels and at least 12,554 colors, with no GL/transform errors or
app ANR/crash. The button/picker and final preview screenshots were independently
viewed. Android native UDP contracts also pass 659 checks/seven scenarios.

This is actual x86_64 app/framework navigation and explicitly scripted peer
execution. It does not run the ARM64 Wine/FEX server, establish its liveness
after Return, or prove post-destruction renderer teardown from the saved pause
report. Actual 0.1.5 Thor Return/server continuity remain the next physical
checks. Compact receipts are under `evidence/20261015/return-launcher-0.1.5/`.
This final evidence/documentation handoff does not rebuild the exact CI APK.

The scene receive limit remains independent work. First export bounded numeric
decoder reason, compressed/declared size and output budget; the current report
cannot identify the rejected allocation/size. Then design owned per-session
large-message storage and incremental decode rather than increasing every queue
and worker-stack buffer through a global macro. Complete GROUPS/ALLENTS and
authoritative spawn still follow that admission contract. Separately, expose
allowlisted cache/graph reuse/refusal outcomes and measure unchanged-input clean
Stop → restart. Existing strict cache ownership/closed-generation checks must
remain intact; preserved character/profile data does not prove cache reuse.

## Interrupted-start recovery 0.1.4

Historical qualification at delivery. The later physical report and current
0.1.5 section above supersede its then-pending server/Map acceptance status.

Runtime and qualification source: `294041ddff3b5f80ae4dbf25073b01e037ecc7ee`,
Git tree `53a6d2a95f0ddcb9d85ffe6db14f1b33c9b5d5a1`, exclusively on
`native-android`. Publication freshly checked remote
`8168d20ea4753c3a0891840cc8ef8dc3e78261c2` and used a guarded non-force update.
The eight local integration commits remain on
`preserved/combined-014-local-validation`. Earlier worktrees, imports, profiles,
reports and all prior qualified APKs remain preserved.

The new [Thor evidence](evidence/20261015/startup-repair-0.1.4/thor-failure-sanitized.md)
separates two failures. The current 0.1.3 attempt stops normally after 15,652 ms
with `OWNED_DISPLAY_SOCKET_ALREADY_EXISTS`, before Wine/client startup. The
existing object's type/listener liveness was not reported. The preceding attempt
has an Android `LOW_MEMORY` exit around 5.4 seconds into startup, with its last
snapshot still in input admission. Seven valid samples show no measured pressure
and over 8 GB system headroom. No guest allocation site, cgroup limit or fatal
transient is retained; the kill's cause remains unresolved. The embedded native
report is byte-identical old 0.1.2 evidence, not a new 0.1.3 client attempt.

Each server session now uses a private 25-byte endpoint component derived from
96 bits of its full session identity. Both the runtime and Java admission check
the actual Android backing pathname against the Unix-socket limit, including
secondary Android user paths. The existing display bootstrap/readiness, private
directory permissions, free-display selection, collision rejection and exact
device/inode owned cleanup remain. Old, live, foreign and symlink endpoints are
not deleted or reclaimed. Session identity remains full-length in ownership and
diagnostic records. This repairs the restart collision without assuming a stale
object is safe to unlink.

Stage transitions now immediately flush bounded numeric guest RSS/peak samples;
Android retains at most 32 current-session rows with allowlisted fields. Unknown
cgroup metrics remain null. No packet bodies, private paths, credentials, cookies
or authentication keys are added. Report persistence serializes snapshot through
write so an older ticker cannot erase a newly captured boundary. An independent
host scheduling model reproduces 100 old overwrites and retains fresh reports in
100 serialized cases; it does not establish Android filesystem durability.
The launcher streams its installed APK digest once on a background owner and
records it in exports. Older-version native reports keep their content under
`previous-app-native-client-report.json` rather than masquerading as current.

The input-admission audit finds bounded reads and streamed verification, not a
whole-asset heap load: the 11,975-byte client manifest is capped at 1 MiB, the
3,872,410,072-byte payload is hashed in 1 MiB chunks, and PE/ELF identity reads are
bounded. The larger visual validator already runs later in its own reaped
process. Those facts neither identify nor eliminate the Android kill. Original
asset checks, memory admission, process cleanup and Android protections remain
enabled; no verified input is skipped to make this retry pass.

Workers actually ran concurrently in isolated worktrees with separate ownership:
runtime interruption regression, sanitized Thor evidence, APK/build/framework
qualification and independent Java/concurrency review. The coordinator integrated
the owner, export, pathname admission and unified release handoff. No native
client, engine, accepted renderer or imported profile was changed.

All twelve local host suites pass, including release/ASan/UBSan protocol
regressions, 83 APK identity checks, 152 diagnostic checks and 78 framework-driver
controls. Current/exact-donor runtime suites each execute 38 methods locally:
36 pass and two AF_UNIX controls are explicitly sandbox-skipped. Hosted Linux
must execute those controls rather than treating the local skips as success.
The interruption fixture uses a real host AF_UNIX listener and SIGKILL; owned
inode cleanup is a separate production-method fixture with mocked dead display
process status. Numeric flush is a real Python pipe observation, not Android
durability or a full Xvnc/Wine/PRoot/server restart qualification.
Both ABI packages assemble and lint with zero errors and 74 existing warnings.
Published-source clean audits pass without rebuilding unchanged production code.
Only four of 74 asset entries change: build-input metadata and the three changed
Python runtime/test/collector files. All 11 accepted scene assets, import
contract, both PRoot payloads, package and signer remain identical to 0.1.3;
versionCode advances from 4 to 5. These local APKs are not the delivery binaries.

Both jobs in [workflow 38811852104](https://github.com/Russianranger/coh-android/actions/runs/38811852104)
pass. The [package artifact](https://github.com/Russianranger/coh-android/actions/runs/38811852104/artifacts/12007874953)
is 10,979,954 bytes, SHA256
`a94bdc50e6e89cc2f2d06b30e4d73954021fa29688b73b94496d5a4a0ee25190`;
all 38 member CRCs and clean source/package receipts were independently checked.
Hosted current and exact-donor runtime suites each pass **38/38**, zero skips;
both explicitly record actual execution of the AF_UNIX interruption and abrupt
numeric-resource capture controls. These retain the host-only scope above.

Deliver **CoH-Native-Combined-0.1.4-arm64.apk**, **11,527,815 bytes**, SHA256
`18b06672a11af3a50bd2ece77ce41bc2fecec7f8ebe6037408245119ca21ad2c`.
The exact companion x86_64 APK is 11,124,648 bytes, SHA256
`c090590092c638508fbd5a17235a63604ae8757d809b0fc70fc1e2b16805e0ee`.
Both ABIs retain every native ELF payload byte-for-byte from qualified 0.1.3.
Only six APK entry payloads differ: the version manifest, launcher classes2.dex
and the four helper/metadata asset entries listed above. Every other payload,
the import contract, accepted scene and signer are identical. No large game or
runtime archives are added. The delivery is the exact CI APK, not a local rebuild
or repack; this evidence/documentation handoff does not require another build.

The [Android13 framework artifact](https://github.com/Russianranger/coh-android/actions/runs/38811852104/artifacts/12009526078)
is 1,680,745 bytes, SHA256
`afc8b4db146fa0ec2afc41dc4b4743103f89147b456e211a94a4f9139f80b0a4`.
All **26/26 framework checks** pass. Current launcher identity becomes ready and
matches the exact installed x86_64 APK. A real SAF ZIP export keeps its current
code-5 report and preserves the explicitly scripted old code-3 native report
under the historical filename; the original native report is restored afterward.
The exported ZIP is 12,206 bytes, SHA256
`61bc334b6d2bb2cdd042da59a56e2cacb4d267e6cc1d2e33cb136a2ff764d290`.
Its empty guest-resource list is correctly scoped to x86, not claimed ARM64 guest
execution. Numeric-resource validation remains source/host qualified.

Actual picker and post-selection Surfaces remain 1920×382 with 572-pixel controls.
The full scripted 915-name catalog reaches `SCENE_INCOMPLETE`, accepts two Map
messages and one scene prefix, then closes both peer sockets and removes its
fixture policy. Near/Far, Surface recreation, Home/return, actual native JSON
export and no-app-crash/ANR checks pass. The final foreground scene has 1,342
frames, seven contexts, 557,056 GPU bytes, 556,553 bright pixels and at least
14,281 colors, with no GL/transform mismatch. The picker and final preview
screenshots were independently viewed. Two real SAF donor imports retain all 71
read-only protected files and exact FX bytes; observed descriptors are
114 → 114 → 115, within the explicit bounded framework/provider-cache limits,
not a claim of zero descriptor growth. The separate Android native UDP controller
passes 659 checks/seven scripted scenarios. The framework executes the x86_64 app
and source-layout UDP peers, not ARM64 Wine/FEX, a real AuthServer session or a
live server world. Compact local/hosted receipts are preserved beside the Thor
failure record.

Follow the current [THOR-TEST.md](THOR-TEST.md): install over Combined, retain all
inputs/runtime/profile, recover only after owned children are gone, start the
server, then manually launch/connect the native client. Export before another
retry. Normal stop/restart and optional force-stop/recover/restart need physical
Thor evidence. The independent low-memory exit, real Map application acceptance,
encrypted authentication and authoritative live world remain pending. Accepted
Gates 22–24 and the earlier physical 0.1.2 server/DB handoff evidence are unchanged.

## Connection repair 0.1.3

Runtime and qualification source: `1ca6afc1b375d1e3a59ed13be562d9f9d1d0b81e`,
Git tree `52afd541c445c6c5c949e5bf88f9f167b73acfde`, exclusively on
`native-android`. Publication checked the current remote HEAD and used a guarded
non-force update from `339003eaddb67947c28bc88e2aef8b33b75bd4e5`.
The complete local integration history is retained on
`preserved/combined-013-local-validation`; earlier worktrees and unpublished
history remain preserved. Recovery found the clean 0.1.2 qualification/handoff
checkpoint, not an unfinished source edit or an actual stalled build/emulator
process. No completed 0.1.2 qualification was restarted.

The new [physical Thor evidence](evidence/THOR-012-SERVER-CONNECTION.md) confirms
that the exact qualified 0.1.2 APK booted the local server after 556.310 seconds,
received a real DbServer character list, selected a character and began the
DB-provided Map handoff. Its ready snapshot has 701 valid memory samples and no
pressure stop. The older low-memory exit is independently recorded by Android;
the latest user-requested exits are different records. The ZIP's old 0.1.1 FX
failure is historical evidence, and the fresh stopped report does not invalidate
the archived running snapshot. Graceful real-server stop/restart still needs its
own device evidence. This is partial real local interoperability, not encrypted
AuthServer login, completed Map application acceptance or a native live world.

Showing the character list shrank the Surface from 1920×469 to 1920×137. The
unchanged source camera rejects the resulting aspect of 14.0146. The new Android
controls scroll within at most 60% of available height, and the actual measured
Surface is fitted within the existing [0.25, 8] aspect and 16384-pixel limits.
The accepted renderer, camera, asset inputs and Gates 22–24 are unchanged. A
compiled unchanged-camera oracle reproduces the exact rejection and accepts the
fitted 1096×137 rectangle.

The source server's static accessible-name table has 915 entries (14,264 string
bytes), distinct from the shortcut schema. The old common 256-entry limit could
reject a valid development-server catalog. The new parser streams and discards
accessible names under a separate 1024-entry bound, retains the 256-entry schema
bound and never authorizes native command execution from those strings. The
existing transport/framing/encryption/reliability kernels and 16 KiB message bound
are unchanged. The old `COH_LIMIT` report lacks the failed packet, so this proven
compatibility defect is a plausible cause, not an identified captured packet.
Terminal DB/Map phases, parser stage/status and numeric UDP/NetLink counters now
survive cleanup and suspend. Reports contain no account identifiers, packet
bodies, passwords, cookies or authentication keys.

Workers actually ran concurrently in isolated worktrees with separate ownership:
viewport policy/oracle, protocol/parser/socket qualification, Android build and
framework driver, sanitized Thor evidence, and independent read-only review.
The coordinator integrated the Activity and release handoff. No server runtime
or imported/private profile was changed for this repair.

All eleven local host suites pass. New checks include 5,021 Java viewport cases,
1,441 controls-height cases, 4,904 unchanged C-camera comparisons and 625 exhaustive
area checks. Fifty framework-driver controls include invalid/stale EGL viewport
and numeric privacy rejection. Per release/ASan/UBSan mode, replication passes
75,165 checks (5,318 truncations and 30,000 fuzz cases), Map passes 29,927 checks
across 21 scripted OS-UDP scenarios, and the local owner passes 659 checks across
seven scenarios. Full 915-name fragmented catalogs pass bitpacked and compressed
profiles. A separate bounded UI peer roundtrip also passes all three modes and
builds for ARM64/x86_64. These peers are explicitly synthetic source-layout
fixtures; they do not prove an authenticated or real guest-server session.

Both local ABI APKs assemble, lint and pass clean package audits; lint has zero
errors and 74 existing warnings. The first Map collector attempt lacked source
references in its sparse worktree; adding the required upstream source folders
allowed the complete eleven-suite run to pass. All 74 asset entries, both PRoot
binaries, the signing certificate, import contract and accepted scene match the
exact 0.1.2 delivery. The application stays `org.coh.nativecombined`, versionCode
increases from 3 to 4, and SDK requirements stay unchanged. Compact receipts are
under `evidence/20261015/connection-repair-0.1.3/local/`; those local APKs are not
the delivery binary.

The exact [hosted workflow 38804511398](https://github.com/Russianranger/coh-android/actions/runs/38804511398)
passes both jobs. The [package artifact](https://github.com/Russianranger/coh-android/actions/runs/38804511398/artifacts/12005078271)
ZIP SHA256 is `42edf73c989ba385514e0c8e5a367bf84fa665d379bcfed29cd5c078c5d1c761`;
all 37 CRCs and both APK receipts were independently checked. The ARM64 delivery
is **11,521,251 bytes**, SHA256
`8b60102521c23d42e2706331d266602d5c7429b3b42799e053361f47331b90c5`.
Hosted current/exact-donor runtime tests pass all 60 executions without skips.
The CI package differs from the local candidate only in the two newly compiled
native libraries; all assets, DEX, manifest and resources match. Deliver the CI
binary; do not substitute the local candidate or rebuild it for documentation.

All **24 Android13 x86_64 framework checks** pass on the exact companion package.
The [framework artifact](https://github.com/Russianranger/coh-android/actions/runs/38804511398/artifacts/12005214269)
ZIP SHA256 is `1d53ff01bfd388e92c47af7e8241577dc3d5f04ddf271dde83127f6e065c9787`.
The actual Surface/EGL remains **1920×382** before the picker, at frame 593 while
characters are selectable, and after selection at frame 823. Controls occupy
572 pixels. The scripted peer's complete 915-name catalog produces two accepted
Map messages and one partial scene, reaching `SCENE_INCOMPLETE`, not a live world.
Its two sockets close and its test policy is removed. Actual scene screenshots
were independently viewed; the final foreground frame 1330/context 6 has 557,056
GPU bytes, 556,442 bright pixels, at least 14,269 colors, and no GL/transform
errors. Near/Far, Surface/Home, real JSON export, numeric diagnostics, original
71-member donor protection and two actual SAF imports pass. Import descriptor
counts stay **115 → 115 → 115**. No app crash or ANR is recorded.

The [portable core](https://github.com/Russianranger/coh-android/actions/runs/38804511475),
[session contracts](https://github.com/Russianranger/coh-android/actions/runs/38804511582)
and [live foundations](https://github.com/Russianranger/coh-android/actions/runs/38804511301)
workflows also fully pass at this source. They include actual Android13 x86_64
socket/crypto/DB/login/Map contract execution and ARM64 crossbuilds. Their peers
remain scripted; none establishes an authentic encrypted login or live world.
Hashes, exact scope, numeric checkpoints, screenshots and compact/full receipts
are preserved in `evidence/20261015/connection-repair-0.1.3/`.


Follow [THOR-TEST.md](THOR-TEST.md): update Combined in place, reuse the existing
imports/runtime/profile, start the server, open the native client manually,
connect, select the saved character, and export both native JSON and launcher
ZIP. Actual real Map acceptance, encrypted AuthServer login, complete scene/entity
decoding and server-authoritative render/spawn remain pending. A larger real
`SERVER_GROUPS` message may expose another supported-message bound; preserve the
new numeric report instead of inferring a completed world from the offline
preview. The next independent milestones are authentic Thor Map exchange with
these diagnostics, bounded initial scene/entity decoding and authoritative spawn,
and separate encrypted authentication against an authorized compatible server.
Source-defined follow-up work can run independently: transactional GROUPS
file/definition/reference transforms and CRC validation; a complete ALLENTS
record/tail walker with real player identity and DBID; and the REQALLENTS/READY
plus application-ack sequence with secure cookie lifetime. Only then may a
validated immutable server snapshot drive the existing renderer. A larger message
must use an explicit owned/session byte budget or incremental decode contract;
globally increasing message macros also enlarges queued bodies and worker-stack
buffers. Measure the owned server's numeric world-update size first. Existing
native audio/UI modules can be integrated separately without reimplementing
accepted transport or rendering kernels.

The accepted standalone [Session Client 0.3.0 APK](https://github.com/Russianranger/coh-android/actions/runs/38673357918/artifacts/11945445541)
and its [original Thor instructions](../session-client/THOR-TEST.md) remain
available. Gates 22–24 remain physically accepted; no rebuild or new acceptance
claim is required for that unchanged package.

## Startup repair 0.1.2

Source: `377584651471e748fbbd4a24cdf08bd2c48ca4a3`, tree
`0329c6a8e9ee7454c7152f29ba85a4683ee4c964`, exclusively on `native-android`.
The four local validation commits are preserved on
`preserved/combined-012-local-validation`; publication used an expected-head
check against `0b6abf77370d152462c3e9ba267f27f634d908c0` with no force update.

The 0.1.1 Thor report identifies the exact unchanged FX regular-file guard.
A writable imported payload acquired two hardlinks during setup; its pinned
contents are correct. The actual donor regression reproduces the rejection,
then passes the same guard after production Java seals the same inode and
bytes. Existing ready generations are repaired in place after full streamed
pin checks, with owner/type/no-follow validation and an atomic success receipt.
Warm starts check protected metadata and retain the guest's own verification.
The runtime identity and profile stay unchanged; imports/setup are not repeated.
Explicit `Os.close` avoids Android's non-owning FileInputStream descriptor
behavior. Atomic close-on-exec uses the Linux UAPI value verified by both pinned
Android26 ABI compilers; final lint has zero errors and 74 existing warnings.

The user reported a preceding Android low-memory kill, but that attempt was
not retained in the ZIP. The exact donor's 48,591,999-byte visual manifest
validates 10,401 files and 406 GEO identities in a reaped host subprocess with
225,116 KiB peak RSS. This is host parser evidence, not Android peak usage or
proof of the kill's cause. The cold original validator now finishes and is
reaped before PostgreSQL/Wine start; the parent checks the original warm proof,
and valid warm starts skip the child. No original manifest/archive/geometry
checks are weakened. Cooperative Android memory admission and sustained-pressure
cleanup retain bounded telemetry; they cannot guarantee prevention of OS kills.
Exports include numeric OS exit evidence when available and four preceding
attempts, without descriptions, traces, account identifiers or credentials.

Eight local host suites pass, including ASan/UBSan transport contracts, 2,710
memory-policy controls, 143 diagnostics, 67 imports and six canonical-path
controls. Both current and exact-donor runtime suites execute 30 methods: 29
pass and one AF_UNIX test is skipped per suite because the local sandbox blocks
Unix sockets. Tests include real child cancellation/reaping, retained-source
cold/warm behavior, tampering and startup order. ARM64 and x86_64 builds, lint
and clean package audits pass. The source snapshot, upgrade comparison, ABI
flag probes and failed/successful build-attempt hashes are preserved under
`evidence/20261015/startup-repair-0.1.2/local/`.

Independent workers ran concurrently in isolated worktrees: immutable imports,
original-geometry lifecycle, pure Java memory policy, build/framework checks,
and a read-only integration review. File ownership did not overlap. The
coordinator integrated service/launcher reporting and publication. The update
retains the same signer, raises versionCode 2 to 3 and preserves all 72 checked
import/scene/donor/PRoot entries byte for byte.

The delivery APK is **11,519,003 bytes**, SHA256
`1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449`.
The successful package/host job of [38795244645](https://github.com/Russianranger/coh-android/actions/runs/38795244645)
produced the [exact package artifact](https://github.com/Russianranger/coh-android/actions/runs/38795244645/artifacts/12002281757).
All 60 hosted current/donor runtime executions pass with zero skips. That run's
Android step stopped at a nonzero hierarchy-capture command whose stdout the
old driver discarded; its app screenshot and captured fault records show no
recorded native ANR/crash. The first five checks and failure evidence remain
preserved. The original capture cause remains unclassified.

A driver-only continuation [38797308843](https://github.com/Russianranger/coh-android/actions/runs/38797308843),
source `0f4240352a0d2878d1e1e86878267ef68997e027`, passes **all 18 Android13
framework checks** using the unchanged APKs. Its [artifact](https://github.com/Russianranger/coh-android/actions/runs/38797308843/artifacts/12003880020)
binds the archive/APK hashes, source ancestry and unchanged runtime/build inputs.
Thirty host driver controls reject stale XML, unknown failures and native
crashes/ANRs; only exact AOSP idle/null-root diagnostics permit bounded retries.
No new APK was built for this continuation.

Actual Android checks verify all 71 donor members have no write bits, retain
the original 3,380,680-byte FX hash, and complete two SAF imports with app FD
counts 111 → 114 → 115 within the declared cache-growth bounds. A failed attempt
survives framework force-stop/relaunch without clearing data, with a numeric OS
exit record. This is force-stop evidence, not a simulated low-memory kill. The
x86 emulator refuses the ARM64 server before its memory admission; pressure
policy execution is host-qualified and actual server memory behavior is pending.
The visible native preview reaches 403 frames in context 6, zero GL/transform
errors and 557,056 GPU bytes; the scene screenshot was independently viewed.
Near/Far, Surface/Home recovery, JSON export and 464 scripted UDP controls across
six scenarios pass. Those scripted peers do not prove real server exchange.
The portable-core workflows also pass.

Independent CI APK audits confirm the same signer, import identity, donor
metadata, accepted scene and PRoot bytes. CI DEX/manifest/resources/all 74 assets
match the clean local builds; native compiler outputs differ, so the exact CI
APK is the delivery. The accepted prior APKs and every build attempt are kept.

Actual 0.1.2 Thor server boot, DB/Map interoperability, encrypted AuthServer login
and server-authoritative native world rendering remain pending. Gates 22–24
remain physically accepted within their existing scope. Next work depends on the
Thor boot report: qualify actual local DB/Map exchange, then source entity/scene
decoding and authoritative spawn, while encrypted AuthServer negotiation is
qualified independently against an authorized server with the required schema.

## Startup repair 0.1.1

Runtime source: `d26253eaf38e254aadda7e1c18b4dfee39296dc8`.
Client payload source: `623b51299f32cbc7d09195c039a63caaa9e06179`.
Packaging/qualification source: `159a3a3ebb79c7e8173b2662331655d317037311`.
The previous 0.1.1 ARM64 delivery is 11,242,291 bytes, SHA256
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
