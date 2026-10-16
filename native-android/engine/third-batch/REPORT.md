# Third parallel gameplay development batch — 2026-10-16

This batch develops the separate, entirely offline `org.coh.nativesupport` app
and reusable modules. It does not qualify live gameplay or replace the accepted
Session Client. Release identity and emulator results are recorded in `release.json`.
Implementation, build and emulator status must not be read as physical acceptance.
The published source is `bae8cca2b4ae0e43070d5e86ca1c6f1df668bc00`; its Git tree
exactly matches local reviewed integration `4ea4b7352e37f16178cd13005a75a0d834cfe7c1`.
Shell push lacked credentials, so publication used the connected GitHub app with
`expected_sha=8e237b984c188dd19c171387914e795916712556` and `force=false`.
Worker/local commits remain preserved; GitHub received one additive integration
commit, not a rewrite of existing history.

## Repository, recovery and ownership

The actual fetched starting remote HEAD was
`58caf1d4ab3b39757190f194100ccbc697d57857`, not the historical `bf653dd4…`
checkpoint. Six workers ran genuinely concurrently in separate detached
worktrees at that common commit. `recovery-audit.json` and
`recovered-worktrees.json` preserve the original working-tree/unpublished-work
inventory; none of that work was reset, overwritten or integrated implicitly.

While this batch ran, the primary agent advanced the branch through
`fe037348c9a184d98aff96f0803b2afc0e631b71`. Its intervening paths did not overlap
ours. Integration used a fresh detached worktree at that remote commit and
cherry-picked only this batch's reviewed commits. Original worker/coordinator
commits remain available locally. The subsequent primary commit `8e237b984c188dd19c171387914e795916712556`
was also nonoverlapping. Final promotion uses a fresh worktree at that HEAD;
`commit-ledger.json` maps preserved integration commits to promoted commits.
`final-scope-workflow-audit.json` records zero primary workflow triggers.

| Owner | Exclusive edits | Shared dependencies |
| --- | --- | --- |
| A | `support-client/` | Existing assets, renderer, physics, sequencer, UI, audio and perf |
| B | `engine/appearance/` | Original costume/geometry/texture/rig sources and accepted GLES renderer |
| C | New `engine/offline-world/` | Existing world math and indexed asset loader, read-only |
| D | `engine/ui/` | Existing HUD/font/GLES renderer |
| E | `engine/physics/`, `engine/sequencer/` | Original WALK laws and source rigs |
| F | `engine/audio/`, `engine/perf/` | Existing mixer/listener/perf observer; no audio runtime changes needed |
| Coordinator | `engine/third-batch/`, support-only workflow | Integration and publication audit |

The primary agent retains exclusive gates 25–27, network/auth/dbclient/login/
mapclient/live/session/replication, combined client, server source/configuration,
shared session interfaces and its workflows. These paths, accepted Session
Client files, shared root build/JNI and main renderer were not modified by this
batch. No server, account, character, database, existing Android application or
runtime import was reset. No primary workflow was canceled or restarted.

`CONTRACT.md` specifies resource ownership, actor/rig bindings, immutable physics
generations, renderer generations, copied UI snapshots/typed intents, audio
lifecycle messages, diagnostic provenance and Android thread/cancellation rules.
Cross-worker reviews found and resolved bounded-string, partial-submit recovery,
mask-selection evidence and report-publication issues before integration.

## Recovered qualification, preserved unchanged

The previous Support Client **0.2.0 code 200** was already signed and qualified on
an Android 13 x86_64 emulator: 13 scenarios, 1,006 rendered frames, three contexts,
zero reported GL/transform/support errors. This was recovered rather than rebuilt
merely to repeat established evidence.

- Source: `c14a831b55163dbcf2b3e63b4c52805785fceafa`.
- [Actions artifact 11990195263](https://github.com/Russianranger/coh-android/actions/runs/38765087744/artifacts/11990195263).
- ARM64 SHA256: `26bad28b029fef86931108b531f883c9a948a16aff1dc2cdba9d8447c6c4d935`.
- Independent recovery checked signatures, 113 tracked source/header/shader inputs,
  15 report identities and seven byte-identical accepted assets; six negative
  identity controls rejected malformed evidence.

Accepted Session Client 0.3.0 remains unchanged, SHA256
`75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Gates 1–24 retain their original physically accepted scopes. The newer starting
checkpoint records physical acceptance of Combined 0.1.6's **bounded scene
reception and return-to-launcher scope**. That does not establish complete scene
decoding, authoritative spawning or full gates 25–27 acceptance.

The primary agent subsequently published `27efb628d4d01bc5b63a8fb4d9d1996c7b1fbc8e`,
preserving this batch without overlap. Its Combined 0.1.7 handoff records 34/34
Android checks for bounded full normal-world structure parsing. Imported scene
graphs/checksums, authoritative identities/positions/entities and encrypted
AuthServer login remain open; the new 0.1.7 physical test is pending. This
coordinator did not modify or independently requalify those capabilities.

## Development and independent qualification

### A — consolidated Support Client 0.2.0, code 201

Recovery commit `80896484a0`; core integration commit
`b0626762fcd6c92399d288f4b483eba21e417a40`; later appearance integration is listed
in the final commit ledger: runtime `f3fe45117109c65afc4acb742e7b77e253553295`,
evidence `3770bca0abadb06942a434d8d8943d14379f5e3c` and documentation
`14c9bbec36b4e45d7e36b9591400b1e27853f9a4`. Only A edited the application.

The existing offline Wretch/Atlas WALK scene, authentic source font, Near/Far,
health/endurance, targeting, powers, keyboard/chat, controller, music/ambient and
lifecycle behavior are reused. Added five gameplay panels and typed mock-hit
cues driving the authentic Huge punch preview, compact/collapsible landscape
controls, immutable background process-memory samples, robust report scheduling,
and an explicit optional neutral Male costume preview. Preview audio remains
background Wretch-scene audio and is labeled accordingly.

New package filenames contain `code201`; the package remains
`org.coh.nativesupport`, with manifest/report/signature/installed-APK verification.
The protected-source checker rejects all eleven primary source scopes. Targeted
host GLES, thread/lifecycle, maximum JSON and ASan/UBSan checks are source-bound
under `support-client/qualification-next/`. Fresh Android execution is required
for these changed runtime inputs; retained code-200 evidence cannot qualify them.

### B — reusable complete Male appearance rendering

Commits `49420fc8645546fbb1ac7137d7ab95781e77b341` and
`c083907355a1fed442e798136a76d8d035b477c3` add the actor/preview adapter.
It resolves eight authentic Male costume parts,
original textures and matching neutral Male rig: chest, hips, two gloves, two
boots, head and hair. It preserves source selection, explicit first `None` mask
choice, material/color behavior and attachment transforms. Package preparation
is hash-pinned and reproducible; missing Female/Huge resources are explicit.

The qualified fixture contains 943 vertices and 3,792 indices. Source comparison
covers 789 geometry models / 1,160,514 scalars, 137 costume identities and 192
color bytes. Negative/lifecycle checks, ASan/UBSan, ARM64/x86_64 linkage and actual
host GLES rendering across context recreation are independently recorded under
`engine/appearance/`. E reviewed source-mask evidence and failure cleanup; F
reviewed application resource/thread ownership.

Independent Android screenshot review rejected the first counter-passing
candidate: full jump root motion escaped a camera fitted to its first pose.
Appearance fix `7208f42e5684c192f74952bcc1a5e9329a5a9d9c` holds the first
source pose and fits all bounds to 70% of both viewport dimensions. Thirty-six
raster checks across four aspects and clocks through 24 hours reproduce the
old failure and pass after correction. Support fix `a7aac83a3114477290cb575a5936db81767e0e0d`
hides chat/tray and closes any presentation panel to
prevent occlusion; required screenshot bounds now form part of acceptance.
The original failed candidate artifact is retained in the release record.

This is one authentic **source-menu custom Male costume**, not an authored NPC,
full morphology parity, Female/Huge completion or animated multi-actor gameplay.
Wretch remains the default regression scene. Preview CPU byte accounting is
partial; texture bytes are source payload, not measured driver residency.

### C — offline Atlas/Kings Row dependency preparation

Commit `7cc2b40dad74bdbd4e217b5ffe0e7b2bf97daeeb` adds bounded source closure,
original transforms/tints/overrides, dependency reports and generation-aware
spatial selection with transactional cache pins and cancellation.

| Source evidence | Atlas Park | Kings Row |
| --- | ---: | ---: |
| Actual geometry roots | 1 | 1 |
| Visited nodes | 477,073 | 1,000,000, capped |
| Expanded source placements | 322,328 | 672,529 |
| Unique endpoints | 1,940 | 2,128 |
| Original/native matrix components | 5,724,876 | 12,000,000 |
| Byte differences | 0 | 0 |
| Missing definition keys | 714 | 497 |
| Unavailable source blobs | 0 | 10 |

Counts are source placements, not rendered objects. Atlas includes 262,144
recursively authored wall panels. Eleven accepted station instances compare
byte-for-byte. Host/ASan/UBSan passed 4,047 assertions and 1,000 selection cycles;
a 1,024-instance/256-cell case examines four candidates. Fourteen preparation
negative cases and ARM64 object compilation passed. E independently reran checks.

The external metadata-only pack is `COH-Offline-Zone-Preparation-58caf1d4.zip`,
7,151,551 bytes, SHA256
`abe01439226438561f288ec62e5ed3619d6f22a892e42da89060677799a6697f`.
It is **not a runnable complete-zone asset pack**. GEO v8 admission, complete
model/material/texture closure, conservative geometry bounds, runtime pages and
collision/render alignment remain unfinished. Kings Row is capped/incomplete.
This module is retained for later support integration, not presented as broader
rendered geometry in code 201.

### D — local gameplay UI and combat presentation

Commits `38f6e842df` and `4d2a476101` add details, inventory, enhancements,
missions and contacts using copied revision/actor-tagged snapshots, four typed
inspection intents, touch/controller navigation and existing analog hysteresis.
Bounded target markers, damage/healing text and animation/audio cues remain mock;
they do not mutate authoritative state or send packets.

Qualification includes 72 original damage-color comparisons, four mission/contact
color comparisons, 16 malformed snapshots, 12 malformed events, 64 Surface
recreations, ASan/UBSan and ARM64/x86_64 linking without allocator imports.
Five actual source-font GLES frames have zero GL errors and checked color pixels.
The fixed arena is 337,120 bytes, with eight effects and sixteen intents/cues.
Code 201 integrates this adapter. Missing authentic power icons and impact audio
remain labeled; no fabricated art/audio or projectile/particle acceptance.

### E — asynchronous collision neighborhoods and rig recovery

Commit `3148ec9a00481bf9c80e7f4e50c3b2c268781121` adds copied-state capture,
loader-thread WALK-cache preparation, generation-guarded publication preserving
current motion, allocation-free swaps and loader-thread retirement. It rejects
stale scenes/actors and explicitly handles missing neighborhoods.

Qualification passed 4,737 checks, 532 exact source/control states, 80 actual
pthread preparations during movement and 81 swaps, with zero hot allocations or
tracked leaks. Original C-triangle oracle, ASan/UBSan and ARM64 linkage passed.
Unchanged snapshot regression passed 10,566 checks, 160 WALK states and 8,000
queries. Five source-qualified Male rigs were recovered and supplied to B.

The new neighborhood adapter remains separately qualified, not integrated into
the code-201 runtime. Synthetic terrain does not qualify authentic larger maps,
dynamic actors, jump physics or server prediction. Additional Female animation
recovery was blocked by unavailable source assets.

### F — audio reuse and process-memory diagnostics

Commits `af68933ffc4c21befb285f11115f926616743fe9`,
`c781558f096c4bb9772f9df602302afb43f9217b` and `4ef1680602` add fixed-storage
process-memory observation and independent application publication/lifetime review.
The existing authenticated music/ambient mixer, listener and fixed perf observer
were reused without unnecessary runtime edits.

The sampler reads bounded `smaps_rollup`, falling back to `status` RSS with
explicit known/source/error fields; it never invents PSS. Limits are 16 KiB/file,
32 reads including EINTR and an 80-byte snapshot. Tests passed 114,112 checks,
2,048 independent oracle cases, 10,000 fault cycles, ASan/UBSan and both ABI
linkages. LeakSanitizer was unavailable in the host environment; bounded explicit
counts and ASan/UBSan are the stated evidence.

A samples on its report worker at 1 Hz through a zero-session-handle JNI call,
publishes JSON/time/duration atomically and yields between queued report writes.
No proc-file I/O occurs in GL/audio/UI hot paths. Physical audio route quality,
thermal endurance, GPU timing and sustainable full-game FPS remain unqualified.

## Acceptance boundaries and next batch

| Area | Current boundary |
| --- | --- |
| Gates 1–24 | Existing physical acceptance preserved within original scopes |
| Gates 25–27 | Primary agent only; no completion inferred from this work |
| Gate 31 | Complete authentic Male neutral preview; Female/Huge/morphology still open |
| Gates 32–33 | Source/host/ARM64 neighborhood module and rig recovery; larger-world/multi-actor acceptance open |
| Gates 34–38 | Local mock UI/combat preparation; no authoritative combat or complete FX |
| Gates 43–45 | Reused bounded audio/perf plus new memory diagnostics; physical endurance/performance open |
| Support code 201 | Fresh build/emulator status in release record; Thor pending user evidence |

Recommended next parallel work: complete Female/Huge asset and morphology closure;
qualify GEO v8/material decoding and conservative streamed bounds/pages; recover
authentic power icons and impact/FX resources; integrate immutable neighborhoods
with real collision-aligned zone chunks; extend authenticated multi-actor clips;
measure Thor audio, frame pacing, memory and thermal behavior. Live session
integration stays with the primary agent until its gate-27 evidence is stable.

Rollback is additive: use scoped revert commits in reverse dependency order, or
retain the exact code-200 APK for its historical offline scope. Never reset the
shared branch or touch Session/Combined app data. Each module README describes
its optional adapter removal. Original local commits and recovered APKs remain
available; no remote development branches were created.
