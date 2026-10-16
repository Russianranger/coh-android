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
   descriptors into a single immutable allocation. Both world and selected-player
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
copied per draw; there is no shared-mesh cache or whole-Atlas capacity claim.
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
4,096 draws, old-generation leases, 2,000 publications with three reader threads,
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
