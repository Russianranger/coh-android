# Second parallel coordinator — 15 October 2026

The six support streams were developed concurrently in six real delegated
workers, then integrated through opt-in libraries and one separate offline test
application. Each full gate remains open. Host qualification and ARM64 builds
are bounded implementation evidence, not physical acceptance or a playable
live world.

## Recovery and concurrency protection

The fresh coordinator clone checked out and fetched
`2c32f5686246fa28cf3341e8e89dd1014eacd5f4`; the old 61860394 checkpoint was
superseded. The primary worktree was inspected read-only at
`/workspace/scratch/cd30b2fc1c9e/coh-native`. Its initially unpublished protocol,
authentication, replication, audio lifecycle and qualification changes were
preserved. The primary agent subsequently published them through
`239dc9e0613d3cebcc093d33f430d2855bed80b9`.

Before integration, that remote head was fetched, all intervening commits were
inspected, and its 83 changed paths were compared with our 112 integrated paths:
zero overlaps. An ordinary local merge preserved both histories. No primary
worktree file, active network/auth/session/replication implementation, existing
workflow, root build driver or common ABI was edited by this batch. A second
read-only inventory found the primary worktree clean at 239dc9e0. The older
partial `coh-native-coordinator` directory remains preserved; it has no Git
metadata and was not substituted for the actual repository.

The accepted 0.3.0 APK remains byte-identical, SHA256
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
User-supplied physical evidence `COH-NativeSession-20261015-015232.json` and the
acceptance note confirm 29,105 frames, five contexts, zero GL/transform errors,
controller movement/animation, Near/Far selection, cache reuse and lifecycle
recovery. This applies to the bounded offline scene only. Existing receipts
were preserved, including primary-agent receipts.

## Workers and independent ownership

All paths below are beneath `/workspace/scratch/bd17f7dd7d03`. Worktrees were
detached at shared contract commit 218b576a1. Six workers ran concurrently,
reported independently and produced scope-only local commits. Finished workers
subsequently assisted with isolated adapters, clean-snapshot reproduction,
packaging and independent integration review.

| Worker | Worktree | Ownership | Local review commits |
|---|---|---|---|
| A, character | support-appearance | engine/appearance | 5faf57514316; preparation helper 73614b4c0041 |
| B, physics | support-physics | engine/physics | 3963019c8f46; adapter d59f3e50af74 |
| C, animation | support-animation2 | new sequencer playback and continuation | 3081f1e8d173; landing/adapter 094ba4fab7a3 |
| D, HUD | support-hud | new HUD and gameplay UI adapters | 4adcc1ef8602; adapter 2f210efa805a |
| E, audio | support-audio2 | music/resample and android-integration | 276386c1385d; adapter 146575613b56 |
| F, performance | support-perf | engine/perf | e21b553b5d4e; packaging 12923a61278e, 59124cb21fa6 |

Coordinator-owned new support-client files and a new standalone workflow were
explicitly delegated for narrow follow-up tasks. No worker edited old shared
JNI/build/CI. The coordinator owns the final harness, integration and reports.
No new remote branch was created. Local worker commits remain reviewable in
the worktrees; published integration identifiers are recorded separately.

## Per-gate results

| Gate | Implemented bounded scope | Host/source/sanitizer evidence | Android status | Remaining requirements |
|---|---|---|---|---|
| 31 | General body descriptors, costume identity/color rules, parts, attachments, palette adapters | Four authentic costumes; 1,292 identity and 2,040 color comparisons; seven extra GEO files/402 models/908,735 source scalar comparisons; 20 negative cases, ASan/UBSan | ARM64 linked; new-body execution pending | Complete geometry/texture/rig closure, morphology and GPU rendering for additional bodies; device proof |
| 32 | Immutable multi-segment collision BVH, bounded source CTri queries, source WALK neighborhoods | 15,331 checks; 2,050 original contacts; 378 exact WALK steps; adapter 250 exact ticks on actual 2,304-triangle fixture; zero hot allocations, ASan/UBSan | ARM64 linked; x86_64 offline adapter exercised | Regular jump/fall physics unsupported; dynamic objects, complete map streaming and device movement proof |
| 33 | Generic pose bindings, recursive original blend rules, transitions, local cue timing, mock event adapter | 20,523,420 original pose scalars plus 5,478,444 additional scalars (zero max error), 13 authentic clips/three bodies, 36,000 graph comparisons; 26,000 family sanitizer samples; adapter 10,002 samples | ARM64 built; x86_64 neutral previews exercised | Full graph closure, morph/root-motion/FX composition and regular jump/fall locomotion; device proof |
| 34–36 | Native health/endurance, ten-slot power tray, target/chat/character mock UI, touch/controller/IME APIs, original font GLES backend | 30,759 source-color comparisons; 18 malformed states; 32 lifecycle cycles; 95 source glyphs; 9,915 real Mesa glyph pixels; 104 adapter GL frames with concurrent input/snapshots; ASan/UBSan | ARM64 linked; x86_64 HUD/input/lifecycle exercised | Actual UI icon/skin closure, broader Unicode, real bindings, Android/Thor interaction and lifecycle proof |
| 43 | Incremental compressed music, rational PCM16 resampling, ambient/positional mixing through accepted 32-voice engine; Android control worker | 2,147,431 checks, 2,053,295 reference samples, 23 negatives; 120 simulated seconds/291 loops/45 pauses; zero callback allocations and tracked teardown residue; ASan/UBSan | ARM64 AAudio linked; x86_64 streams/pause/resume exercised | Audible Android/Thor evidence, route changes, extended playback; linear resampler is not a band-limited/source DirectSound parity claim |
| 44–45 prep | Fixed frame/stage/counter diagnostics and bounded exact CPU skin cache | 3,555,890 checks/63,024 oracle comparisons/11 authentic meshes, zero warm allocations, ASan/UBSan | ARM64 linked; x86_64 cache/timing exercised | Real Adreno GPU timers, complete maps and representative gameplay measurements; no 30 FPS claim |

LeakSanitizer is disabled where the executor cannot inspect `/proc`; ASan and
UBSan run with failure-on-error. Tracked allocation/teardown and no-allocation
symbol checks supplement that limitation. Detailed provenance, APIs, memory
bounds, negative tests and rollback notes live in each module's README/audit
and qualification receipts.

## Combined integration and validation

`CONTRACTS.md` preserves existing ABI1 statuses, immutable path/generation asset
IDs and borrowed spans. Appearance emits bounded assembly data; physics accepts
immutable segments and emits contacts/WALK state; animation emits caller poses
and typed actor/tick events; HUD accepts copied state and emits local intents;
audio accepts bounded events/emitters and streams off the callback; performance
records explicit observations. GL resources belong to one Surface generation.
Cancellation is outside realtime callbacks. No new packet formats are defined.

The fresh `qualify.py` run passed all six modules with at most two checker
processes at once. Each checker required relevant corpus/source/sanitizer and
ARM64 evidence. An empty-corpus run failed all six, as expected. All 61 protected
baseline files matched primary 239dc9e0 before and after, including accepted
Session renderer SHA256
`15467486339dfb5d7c28b6be1e1345fb07f3fb4b5e32c30084e4c5909cfc8552`.
The modules' checksums did not change during qualification.

Independent exact-commit source snapshots separately reproduced appearance,
physics, audio and performance. Real Mesa GLES testing qualified the HUD command
path on software-host graphics only. Combined ownership review fixed partial
configuration leaks, reset placement, stale frame scopes and failed audio-close
retention. A 102-case ASan/UBSan fault-injection test verified retry ownership;
this uses controlled dependencies, not a fabricated platform close failure.

The separate `org.coh.nativesupport` APK uses original Wretch assets, static BVH
WALK, neutral authentic animation previews, source-font mock HUD, original Atlas
music/steam ambience and exact skin caching. Character selections are mock data;
additional body GPU rendering is false in its report. Source asset closure and
network-link exclusion checks pass. Its binaries are native ARM64 or emulator
x86_64, with no Wine/Box64/FEX runtime.

Local full APK packaging/signing/manifest/asset checks passed for both ABIs.
The final committed source and Actions build receipts provide exact source and
APK identities. Local QEMU crashed with SIGSEGV before app install, including a
bounded one-core/no-Vulkan retry; logs are retained. This is an infrastructure
blocker, not an emulator pass. New physical Thor evidence remains pending.

Only the new support-client workflow is added. Its push filter is restricted to
this separate application and its own workflow; primary changes do not trigger
it. It builds both ABIs, executes a framework-driven emulator scenario and
uploads APK/checksum/report/screenshot evidence even if qualification fails.
Existing workflow definitions are unchanged. Failed execution must be reported
as failed, and the test APK must not be described as physically accepted.

## Rollback and next work

The original client/launcher remains functional and untouched. Uninstall only
`org.coh.nativesupport` to remove the test application. Keep the accepted 0.3.0
APK and receipt. Revert opt-in support commits additively if needed; never reset,
rebase or force the integration branch. No library is inserted into the active
Session Client or primary live-session execution path.

Work that can proceed independently: additional body resource/rig closure and
source morph composition; source jump/fall collision behavior; remaining graph
edges/FX timing; original UI icons/Unicode; improved audio filtering and route
observability; real asynchronous GPU timing adapters and larger-map profiling.
The asset loader plus collision segment API help full Atlas loading, but do not
supply every map dependency or qualify full-map streaming. Nothing in this
batch establishes actual server login: gates 25–27 remain primary-owned and
must supply authenticated session events later. The future adapter can use the
stable value/event interfaces without modifying their packet formats.

Recommended next concurrent batch: character closure, vertical movement,
sequencer graph/FX closure, HUD skin/Unicode, Android route/stream testing and
Adreno/full-map instrumentation. Consolidate device checks using the support
client README procedure after successful Android qualification. Do not request
separate Thor sessions for every small library change.


## Published integration identifiers

The branch update used an expected-head guard and `force=false`. GitHub's final
integration tree `d6b82d4b8101bcd6748302f9f1d19c883acc1b18` exactly matched the
reviewed local tree. Parent 239dc9e0 remains an ancestor.

| Scope | Published commit |
|---|---|
| Character/costume | 24ef6d4ad142075c97fe552e56e5ce1a82f4e937 |
| Physics | 8ce3b208e91381f33af4f38f3e9c988cf6d1f441 |
| Animation | b28c65cb297ff6d254c6a2eeabb1caa437bedff0 |
| HUD/UI | 4331b2218e3a93acf3fe9798f3bdf66ececf401c |
| Audio | 3692fe10296d94e4ed2963d1186b228cc4bea399 |
| Performance preparation | 5051a4fdee3f001c066f3d2ae86f725422b2ba50 |
| Consolidated app/contracts/receipts | 37128acb3c41e5bb81e247c87f313a20a758f326 |
| Lifecycle lock separation | 9f6d053e5605c5707e2dfad1b12392a1ae49fc20 |
| Hosted selector/focus/Surface diagnostics | c988abbb55affe890542c505150e0f418f0b18e8 |

The full repository portable-core and primary protocol-contract workflows passed
at integration 37128acb3 (runs 38700728679 and 38700728540). This is regression
evidence for the unchanged primary code, not new server interoperability.

The first support run 38700728779 built both APKs and booted Android API33.
It installed the new app and exported 82 rendered frames, zero GL errors,
zero source-transform mismatches, 126 physics ticks over three segments/2,304
triangles, source-font HUD rendering, cache hits and initialized AAudio streams.
The scenario failed at the first Android button selector because display text
was uppercase. No interaction/lifecycle pass is inferred from that partial run.
Artifact 11955638663 was independently downloaded, ZIP-CRC checked and SHA256
verified (`9b8a50be14934ac9011c683f65cdcf5f3100dc518e0de2f5ac930c09f849b474`).
Original failed-run reports remain alongside later evidence. The follow-up fixes
case-insensitive selectors, explicit keyboard focus, animation admission after
startup comparisons and per-Surface rather than per-frame recreation counters.


## Hosted Android execution

[Run 38701533777](https://github.com/Russianranger/coh-android/actions/runs/38701533777)
passed all 12 consolidated scenarios at source c988abbb55affe890542c505150e0f418f0b18e8.
Its clean source-bound build receipt, both APK checksums and the artifact archive
were independently verified after download. The source field in that emulator
summary was null; the source binding is instead proven by its build receipt and
identical installed APK digest. The final driver reads this binding directly.

The observed run exported 993 scene frames, four started/three completed contexts
(the final context remained live), zero scene/HUD GL errors, zero transform
mismatches, 1,803 physics ticks over three segments/2,304 triangles, 238 neutral
animation samples, power/chat/character intents, controller navigation and
retained HUD state after Home and Surface recreation. A paused audio checkpoint
recorded 6,008 callbacks, 3,194,692 rendered audio frames and zero stream-underrun
frames. Maximum callback elapsed time was 56,850,901 ns on the emulator. This is
not a Thor latency result or proof of a real-time deadline guarantee; extended
playback, route changes, audible quality and device latency remain pending.

The final touch-capture follow-up is b69bbf232e1746f1fb35ef1aa624a636f2cce490.
Fourteen additional persisted host EGL/ASan/UBSan pointer tests and ARM64 builds
passed. It routes captured HUD gestures independently of operation status so a
HUD drag cannot also steer the scene camera. The Android scenario adds an
explicit camera-yaw isolation assertion. No older receipt is overwritten.

Current diagnostic coverage is explicit: CPU timing and module-specific byte,
cache, collision, HUD and quiescent audio observations are available. Generic
performance counters without a caller adapter are uninstrumented; their zero
values are not observations of zero allocations, copies or draw calls. No GPU
timer is installed. The audio emitter in this offline harness uses a diagnostic
listener; binding it to the moving scene camera remains integration work.

Nothing establishes new character-body GPU rendering. Gate31 remains host
qualified/ARM64 built only. Emulator evidence for the other modules applies to
the exact bounded offline adapters; full gates and physical Thor acceptance
remain open. Primary gates25–27 still require an audited Android crypto provider,
authentication TCP/DB integration, version/profile-compatible controlled server
exchange, full bounded entity/scene decoding and an authoritative render handoff.
Those implementations remain exclusively with the primary coordinator.


## Final qualified consolidated artifact

[Successful workflow](https://github.com/Russianranger/coh-android/actions/runs/38702695275)
and [APK/report/screenshot artifact](https://github.com/Russianranger/coh-android/actions/runs/38702695275/artifacts/11957750066)
qualify exact source **b69bbf232e1746f1fb35ef1aa624a636f2cce490**.
Both the build receipt and emulator summary identify this exact clean source.
All **13 Android framework scenarios passed**, including the captured HUD drag
that activates a power while leaving camera yaw exactly unchanged.

ARM64 file: `CoH-Native-Support-Client-0.1.0-support-batch-arm64.apk`.
Size: 2,393,455 bytes. SHA256:
`4cf976478654ab5005257923a177a9c56126bc323871429ca73e70f0439ffde0`.

Emulator x86_64 file: 2,442,604 bytes. SHA256:
`bd6f0caf69d6a636594486a70b19817a3955a99fa07cdbe2e1ede1776503f0a8`.
The artifact archive SHA256 is
`71bd89e52b113222e0e9a8ba22f09c39bf3880edeb6807e6c77eb24e0d2b1594`.
The coordinator independently downloaded the archive, verified its digest and
ZIP CRCs, both APK hashes, exact source/build binding and installed emulator APK
identity. Both native libraries are byte-identical between local and hosted
builds; APK signatures use disposable test certificates.

The final export records 956 presented scene frames, four started contexts,
zero GL/EGL cleanup errors, zero transform/depth-order mismatches, zero support
failures and zero invalid performance samples. It records 1,778 collision ticks,
228 neutral animation samples, three power intents, one chat submit and one mock
character selection. The joined audio checkpoint records 5,910 callbacks,
3,180,480 audio frames and zero stream-underrun frames. Maximum callback elapsed
time is 27,688,367 ns on this emulator; no physical latency/30FPS claim follows.
The final context is live at export, so completed contexts are three rather than
four. This is not a claim that Activity-destroy/device-route teardown was tested.

Install the ARM64 APK from the artifact and follow the single combined procedure
in [the support-client README](../../support-client/README.md). It coexists with
the accepted client. For an upgrade from another support test certificate, export
that app's report and uninstall only `org.coh.nativesupport` first. Do not remove
or replace the accepted Session Client/conventional launcher.

Machine-readable status is in `STATUS.json`; final receipts and paused-audio/
HUD-drag witnesses are in `evidence/hosted-final/`. Additional bodies remain host
qualified/ARM64 built; physics, animation, HUD, audio and performance adapters have
bounded x86_64 emulator qualification. Every new full gate and physical Thor
acceptance remains pending. Existing0.3.0 APK identity and source/asset inputs were
preserved; a full accepted APK rebuild was intentionally not repeated.

No source conflicts remain. The remaining blockers are scope dependencies and
physical measurements, not Git conflicts. Work on full body closures, vertical
movement, graph/FX closure, UI assets/Unicode, audio routes/listener binding and
Adreno/full-map profiling can continue independently. Real login and authoritative
live-world binding wait for the primary agent's gates25-27.
