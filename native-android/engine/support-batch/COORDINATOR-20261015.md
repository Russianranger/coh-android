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
| 32 | Immutable multi-segment collision BVH, bounded source CTri queries, source WALK neighborhoods | 15,331 checks; 2,050 original contacts; 378 exact WALK steps; adapter 250 exact ticks on actual 2,304-triangle fixture; zero hot allocations, ASan/UBSan | ARM64 linked; consolidated hook built | Regular jump/fall physics unsupported; dynamic objects, complete map streaming and device movement proof |
| 33 | Generic pose bindings, recursive original blend rules, transitions, local cue timing, mock event adapter | 20,523,420 original pose scalars plus 5,478,444 additional scalars (zero max error), 13 authentic clips/three bodies, 36,000 graph comparisons; 26,000 family sanitizer samples; adapter 10,002 samples | ARM64 built; neutral previews hooked | Full graph closure, morph/root-motion/FX composition and regular jump/fall locomotion; device proof |
| 34–36 | Native health/endurance, ten-slot power tray, target/chat/character mock UI, touch/controller/IME APIs, original font GLES backend | 30,759 source-color comparisons; 18 malformed states; 32 lifecycle cycles; 95 source glyphs; 9,915 real Mesa glyph pixels; 104 adapter GL frames with concurrent input/snapshots; ASan/UBSan | ARM64 linked; consolidated hook built | Actual UI icon/skin closure, broader Unicode, real bindings, Android/Thor interaction and lifecycle proof |
| 43 | Incremental compressed music, rational PCM16 resampling, ambient/positional mixing through accepted 32-voice engine; Android control worker | 2,147,431 checks, 2,053,295 reference samples, 23 negatives; 120 simulated seconds/291 loops/45 pauses; zero callback allocations and tracked teardown residue; ASan/UBSan | ARM64 AAudio linked; actual output qualification pending | Audible Android/Thor evidence, route changes, extended playback; linear resampler is not a band-limited/source DirectSound parity claim |
| 44–45 prep | Fixed frame/stage/counter diagnostics and bounded exact CPU skin cache | 3,555,890 checks/63,024 oracle comparisons/11 authentic meshes, zero warm allocations, ASan/UBSan | ARM64 linked; instrumentation hooked | Real Adreno GPU timers, complete maps and representative gameplay measurements; no 30 FPS claim |

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
