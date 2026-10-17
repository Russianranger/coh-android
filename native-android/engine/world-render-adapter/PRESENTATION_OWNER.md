# Immutable frame publication and renderer consumer

Recovery pin: `d96354411d2f69ec325b1bfe9d0e14999626ba91`.

`coh_wr_presentation.h` now supplies the missing consumer of the existing
snapshot, frame, binding and renderer APIs. The implementation is included in
the existing standalone adapter translation unit so all owner, bundle, frame,
binding and snapshot allocations use its exact shared aggregate allocator. No
parent CMake, renderer/support source, JNI, Gradle, workflow or APK is changed.

The control thread prepares an immutable frame/binding bundle from an already
prepared snapshot, selected visibility indices and actual camera matrices. It
holds one explicit immutable resource-provider lease through pending, render,
active and retirement ownership. A monotonic publication counter supports new
camera frames over the identical immutable source snapshot without fabricating
new server packet IDs. Different snapshots retain the existing source/session,
selected DBID, transaction and generation admission rules. A production owner
refuses fixture snapshots; a fixture owner permanently refuses production scope.

The GL consumer leases pending work under a short mutex, binds every selected
exact resource, and executes the actual existing renderer begin/submit/flush
API in bounded batches. The candidate becomes active only after every batch
flush succeeds. Missing candidate resources preserve and render the old active
frame. A backend/late batch error preserves that old CPU publication and clears
all borrowed queue spans. Already drawn pixels cannot be rolled back; this API
does not provide an offscreen render target or atomic framebuffer swap.

Resources remain owned until all frame use finishes. Final releases enqueue
bundle retirement without destroying bindings, freeing memory or invoking the
provider's drop callback on the GL thread. Control-thread collection releases
the provider and CPU spans. Surface loss first abandons renderer spans, then
invalidates bindings; resume requires the exact new nonzero renderer generation
and exact new resource resolution. Home pause retains ownership. Stop closes
the session permanently, abandons spans and releases pending/active work; caller
leases must retire before owner destruction succeeds. Provider hold/drop and
all preparation run off the render thread. Publication may run concurrently
with one GL consumer. Stop/destruction require the publisher/consumer join order
documented in the header.

The provider bridge preserves ownership rather than granting new authority.
It must reserve the actual immutable resource set, old/new GPU lifetimes,
renderer queue, loader/provider scratch, stacks and driver allowances externally
once. The adapter's named 96 MiB CPU/reservation cap is not measured process RSS
or GPU memory. Repeated camera frames currently allocate small bounded bundles
off-thread; their lifecycle tests are not a frame-pacing or populated-world
performance measurement.

## Producer status and coordinator integration

The six-worker recovery confirmed independently:

| Producer | Current blocker | Required consumer input |
|---|---|---|
| Live scene A | No verified live scene-generation producer; packet/source compatibility keeps admission false | Matching observed live scene/catalog/runtime transaction |
| Resources B | Exact rigid geometry exists, but historical CLIENT dependencies do not yet grant actual composite/material permission | Complete admitted GEO/model/material/texture and Surface owners |
| Character C | Diagnostic initial update deliberately returns unsupported without reader commit; semantic full-character application remains open | Complete selected self actor/appearance/pose and full-update transaction |

No existing `CohInitial*`, `CohEntSlot`, source graph or historical material cache
may be converted into a complete renderer receipt. There is no new receipt
minting, authority flag, READY/ACK path, fixture-as-player or shipping activation.

Once those real producers close, the coordinator needs these common changes:

1. Add the existing standalone adapter library to the Combined native target and
   link the existing renderer; include `coh_wr_presentation.h`. No new translation
   unit is required. Use an actual matching `CohRendererConfig` with <=512 draws
   per batch and exclusively own that renderer on its GL thread.
2. On the existing simulation/asset worker, construct the existing complete
   `CohWrInput` only from the verified scene, admitted resources and committed
   actor transaction. Reserve their actual retained/peak ownership, prepare the
   immutable snapshot, then prepare and publish one presentation bundle. The
   resource provider must retain its actual exact Surface/GPU owner registry and
   return only already prepared matching handles. It must explicitly refuse
   unresolved resources. Source appearance/input/locomotion stay with their
   existing qualified producer; this adapter never invents pose or movement.
3. Connect real camera/input matrices to off-thread frame preparation. On the
   GL thread call resume/render, record result counters and candidate refusal,
   and call Surface-loss/pause/resume from the existing lifecycle owner. Do not
   claim source world display from publication alone: actual rendered world and
   player identities plus GLES/application evidence are still required.
4. Stop/join the producer, execute GL stop while its correct context disposition
   is known, stop/join GL, release caller bundles, collect on control and destroy
   owner/budget. Keep GPU resources and their old-context cleanup owners alive
   until all borrowed spans are abandoned and provider leases are dropped.
5. Build/execute the exact new standalone corpus on both required ABIs, then
   qualify the integrated Android13 app/Surface lifecycle and actual memory/frame
   pacing. Produce a Combined successor only after its real producer path can
   exercise genuinely new source world/player functionality.

## Qualification

The extended `check.py --sanitize` corpus passes release, ASan and UBSan with
identical **34,465 checks**. It executes the source matrix oracle and the actual
existing renderer through a deterministic backend, not GLES. New checks cover
allocation/budget rollback, resource hold refusal, candidate bind fallback,
second-batch backend failure, a newer publication replacing pending work during
candidate consumption, stale source rejection, Home/Surface/Stop, outstanding
caller lease refusal, exact final resource drops and 512 publications racing a
real consumer thread. The measured lifecycle render path performs zero
adapter heap allocations/frees against the deterministic backend. Real backend
shader compilation/eviction and driver allocations remain external/unmeasured.
Existing 2,000 source mailbox publications, 5,000 mutations,
1,025 ordered draws and 512 original matrix cases remain exercised.

The exact Android artifact driver now requires both new presentation fields and
the new corpus threshold, in addition to identical sanitizer/ABI results and
exact native/Python source hashes. Its six admission-control tests pass. There
is no local NDK/emulator in this recovered worker environment, so this tranche
does not claim Android ARM64 build, Android execution, GLES, Thor, live server
world entry, measured frame pacing or encrypted-auth acceptance.
