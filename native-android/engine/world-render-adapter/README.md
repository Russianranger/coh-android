# Immutable world/actor renderer adapter — isolated, not activated

This is an additive CPU publication and resource-lifetime boundary. It does not
parse server packets, reconstruct saved definitions, resolve appearance, upload
textures, send acknowledgments, or expose a READY/LIVE state. No accepted APK or
support/gameplay/renderer implementation is modified. Parent CMake/JNI/Combined
integration is deliberately absent.

## Current source and authority limits

Worker B's immutable graph, file/slot/name indexes and checksum checks are useful
read-only inputs. They do not yet qualify all inherited trick, tint, lighting,
LOD and material semantics. Worker C's staged DBID/entity/pose/character fields
remain incomplete until original character, appearance, NetFX and global tails
are validated as one transaction. Neither existing module may currently produce
the complete `CohWrReceipt` admitted by `coh_wr_prepare`.

The nine explicit prerequisites must originate from independent qualified
producers: authentic saved catalog, resolved topology, verified original
checksums, exact asset identities, complete render semantics, selected unique
player, full character transaction, full global tails and actor appearance.
The SHA256 fields preserve catalog, asset-manifest and packet-transaction
identity. This adapter checks presence/consistency; it does **not** independently
authenticate digests or verify attestations. C structs are not security tokens.
Only the coordinator's producer adapter can supply them after upstream closure.

`coh_wr_prepare_fixture` permanently marks its immutable result as fixture-only
and clears prerequisite bits. The production entry point refuses fixture scope,
missing flags or zero identities. Unit tests exercise an explicitly fabricated
complete receipt to check admission mechanics; that is not source/runtime
authority evidence. Local development-auth and encrypted-auth scopes are
different and cannot change inside one mailbox session. No actual source server,
saved Atlas catalog, selected real player, or encrypted login was exercised.

## Contract and ownership

1. On the simulation/asset worker, completely resolve world and selected actor,
   prepare the existing `CohRenderGeometry`/`CohRenderMaterial` inputs, and compose
   source-layout world matrices. Every CPU span remains immutable through
   `coh_wr_prepare`. Existing appearance mesh/pose/rig APIs can produce these
   spans read-only after their source identities and generation are qualified.
   A geometry cache identity must include pose generation for CPU-skinned data;
   asset generation alone does not identify animated vertex bytes.
2. Preparation validates bounded numbers, material enums, finite values, indices,
   selected-player identity and all prerequisites. It deep-copies geometry and
   descriptors into a single immutable allocation. Geometry with the same exact
   identity/generation is stored once; byte/count conflicts reject the snapshot.
   Different IDs remain separate even with identical bytes. Temporary bounded
   indexing is charged to the shared budget while the candidate is allocated.
   Both world and selected-player
   draw ownership must be represented. Failed validation/allocation/cancellation
   preserves output and memory accounting; existing published generations remain.
3. `coh_wr_publish` retains one complete scene+actor snapshot under a short mutex.
   Render acquisition retains that exact immutable generation before unlocking.
   Source/session/selected DBID are stable until explicit mailbox clear. Snapshot
   and transaction counters strictly increase. Scene/asset/entity generations do
   not decrease. Same scene retains catalog and asset generation; same asset
   generation retains manifest; same entity generation retains entity/slot and
   nondecreasing appearance/pose. Caller extends wrapping packet IDs to monotonic
   transaction counters before using this interface.
4. The control thread creates `CohWrBindings` before render consumption. This
   allocates two bounded numeric texture-name tables and retains the CPU snapshot.
   The GL owner binds *already decoded/uploaded* exact texture identities for an
   exact Surface generation. A complete scratch table replaces the active table
   only on success. Cancellation or a missing identity preserves prior binding.
   Zero logical texture ID means explicitly unbound, never unresolved/fallback
   geometry. The asset/material producer must qualify that semantic first.
5. `coh_wr_draw` performs bounded matrix arithmetic and numeric binding reads,
   without allocation, filesystem IO, decoding or name scans. It returns the
   accepted renderer's borrowed draw type. Keep bindings alive through every
   renderer flush or explicit abandonment. Texture/GPU owners similarly keep
   names alive until flush. The adapter never owns or deletes GL resources.
6. On Surface loss, abandon pending draws with existing renderer lifecycle APIs,
   invalidate adapter bindings, then invalidate GPU owner names. Preserve the CPU
   snapshot. Recreate GLES backend/renderer and exact texture handles, bind the
   new Surface generation, then resume. A stale Surface generation always rejects.
   Bind/draw/loss are serialized on the GL thread; binding destruction happens
   off-thread only after flush/abandon and no concurrent use.
7. Final snapshot release enqueues retirement; it does not free CPU memory on
   the render thread. `coh_wr_collect` frees on the control thread after all leases
   are gone. Mailbox clear ends session without invalidating old render leases.
   Stop/join users before destroying mailbox/budget. The budget must outlive all
   snapshots/bindings and refuses destruction while allocations remain.

No renderer/camera/input behavior is changed. The caller supplies its current
view/projection matrices. The matrix bridge is checked against **executed,
unchanged** original `mulMat44Inline` for 512 deterministic cases; this claim does
not extend to original world-loader or full material interpretation.

## Memory and performance bounds

Maximum adapter aggregate reservation is **96 MiB**. It includes adapter budget,
mailboxes, immutable old/current/candidate/retired CPU snapshots and both Surface
binding tables, plus `external_bytes` reserved for catalog, graphs, decoded
assets, renderer arenas and preparation scratch. Reserve the actual peak before
allocating upstream storage; update it only when storage lifetime truly ends.
Worker B's graph budget has its own accounting: the coordinator must count each
shared allocation once and feed the same ownership inventory into both checks.
Two independent 96 MiB caps are not a 96 MiB application cap. Allocator overhead,
stacks, GPU/driver storage and the separate local server are not measured here.

Limits are **4,096 draws**, **65,536 vertices per draw**, and **196,608 indices per
draw**, with aggregate reservation normally rejecting much earlier. Geometry is
shared only inside each immutable snapshot; there is no cross-generation mesh
cache or whole-Atlas capacity claim. Per-draw transforms, material and texture
identities are preserved. Identical pointer spans skip repeat byte scans under
the immutable-input contract; distinct spans with the same identity must compare
exactly. The hash lookup allocates at most 49,152 bytes, reserved alongside both
old snapshots and the candidate, and releases that scratch before return.
The 12,192-definition graph stress fixture is not a renderer throughput fixture.
The accepted renderer's default queue is 512 draws. Integration must use a
qualified larger configuration or bounded batches, preserving translucent order
and keeping leases through all batches. Its current submit path scans vertices
and indices; allocation-free adapter lookup does not prove a cheap frame or
acceptable live-world performance. No FPS/startup improvement is claimed.

One large candidate copy is bounded by the aggregate cap, with cancellation
polled during validation and between per-draw copies (maximum roughly 4.4 MiB
geometry copy per draw). Control-thread preparation may stall and must never
run on Android UI/render callbacks. Mutex acquisition is short but not lock-free.
`coh_wr_metrics` exposes unique versus instance vertex/index work, geometry and
snapshot ownership, and temporary preparation bytes without scans/allocations.
The retained shared-geometry fixture admits 4,096 draws of one 65,536-vertex,
196,608-index mesh: 4,456,448 geometry bytes and 5,964,128 snapshot bytes. Its
45,580,768-byte aggregate peak includes 39,518,208 externally reserved bytes
(32 MiB other ownership plus exact source draws/geometry) and bindings. This
replaces a calculated 18,253,611,008 bytes of per-instance geometry copies, but
**does not reduce 268,435,456 instanced vertices or 805,306,368 instanced indices**.
The stress fixture only reads adapter draw spans; it does not submit that workload
to the renderer or GPU. No real-world capacity or frame-time claim follows.

Renderer queue admission/flush can independently fail; a caller must preflight
its configuration and explicitly abandon pending submissions on failure. This
adapter guarantees atomic CPU publication, not atomic framebuffer rendering.

## Qualification and coordinator integration

Run `python3 native-android/engine/world-render-adapter/check.py --source-root .
--output /tmp/world-adapter/qualification.json --sanitize` from repository root.
`--ndk PATH --android-output /tmp/world-adapter/android` adds exact standalone
ARM64 and x86_64 binaries. Build receipts are relocatable and set execution false.
The coordinator owns Android emulator execution and preserved source matching.

Tests cover malformed identity/generations/materials/geometry, cancellation at
validation/copy stages, allocation failure, aggregate-budget refusal/rollback,
4,096 draws at maximum per-draw geometry, exact identity conflicts and distinct
identity hash collisions, byte-equal separate source spans, exact scratch-plus-
candidate budget boundaries, both preparation allocation failures, old-generation
leases, 2,000 publications with three reader threads,
transactional texture binding, Surface recreation, renderer submission/flush,
zero allocation/free during the measured render path, and 512 unchanged-original
matrix comparisons. 5,000 bounded mutations use valid allocated buffers; this
is a deterministic structural fuzz corpus, not arbitrary invalid-pointer fuzzing.
Release, ASan and UBSan must return identical native results. LSan task inspection
is unavailable in this traced executor; no leak-sanitizer success is claimed.
Exact budget retirement/cleanup assertions remain enabled.

Integration sequence, after upstream prerequisites are available:

1. Coordinator confirms stable graph/entity/appearance ABIs and ownership.
2. Add coordinator-owned adapters that mint receipts only after complete source
   transaction and semantic validation. Require authentic catalog and selected
   player. Do not convert offline preview geometry or staged entities to authority.
3. Prepare and publish complete immutable snapshot off-thread; connect existing
   camera/controller view and accepted renderer through the binding/lease path.
4. Independently test exact binaries on Android, lifecycle/recreation/cancellation,
   active scene replacement, aggregate memory and borrowed GPU-name retirement.
5. Build a meaningful consolidated Combined successor only when actual server
   world and player can reach this boundary; qualify on Thor with real data.
   Gate 27 remains open until then. Encrypted-auth acceptance remains separate
   from any future provisional development-auth world session.

Rollback is additive: omit this standalone target and producer integration.
Accepted APKs, profile/database, renderer code and support APIs are unchanged.

## Recovered visibility frame tranche, 2026-10-17

The preserved `/workspace/scratch/142ad4bc669b/worker-e` had unpublished frame
APIs in `coh_world_render.c` and `.h`, absent from remote `3e8b5c9f5`.
Those two files are recovered byte-for-byte; the original worktree remains intact.
The former worktree's Git directory pointer was unavailable. This recovery uses
content comparison, rather than claiming its unpublished commit identity.

`coh_wr_frame_create` now pins an immutable ordered visibility selection and
camera, charges its allocation to the aggregate budget, and preflights geometry
and finite model-view output. It partitions that selection into at most 512 draws
per batch, without sorting translucent draws. This does not derive visibility,
qualify LOD, or increase the 4,096-draw snapshot bound. An explicit empty selection
is allowed; NULL indices mean the entire snapshot only.

`coh_wr_frame_bind` resolves exactly the selected working set. It atomically
replaces both numeric texture bindings and selection mask after complete success;
missing resources or cancellation preserve the previous complete state. A draw
outside the committed selection refuses, including after committing an empty
frame. The frame, binding and draw must refer to the identical retained snapshot.
Frames require off-thread destruction after all borrowed spans flush/abandon.

New qualification executes 1,025 alpha-blended CPU draws through the unchanged
renderer in ordered 512/512/1 batches with zero allocation/free on that measured
path. It checks selective resource calls, empty selections, failed/cancelled
binding rollback, invalid/duplicate/out-of-range selections, per-draw/config
limits, overflow, allocation/budget failure, cancellation after allocation,
snapshot mismatch, Surface loss/rebind and retained snapshot leases. The mock
backend is not GLES execution and does not qualify visual blending, real assets,
Android lifecycle or server-authoritative world publication.
