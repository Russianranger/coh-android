# Gate 32 continuation: immutable static worlds and source WALK neighborhoods

This opt-in library adds static-world spatial indexing and bounded neighborhood
streaming around the accepted WALK implementation. It does not edit WALK,
motion, accepted Android scenes, networking, JNI or existing build workflows.
It is an independently testable integration boundary for larger offline worlds;
it is not acceptance of the complete gate or full Atlas Park collision.

## Public API and ownership

`coh_physics_scene_create` deep copies multiple immutable world-space triangle
segments, identified by nonzero 64-bit IDs and segment generations. Scene
generation uniquely identifies the complete immutable snapshot. Never reuse a
scene generation for different geometry. Replacement snapshots can add/remove
segments without modifying an existing reader. The single owner must retain a
snapshot until concurrent scene queries have ended. No hidden global registry or
resource lifetime is involved.

The scene holds a deterministic balanced BVH and accepted source CTri data.
Caps are 1,024 segments and 262,144 triangles, plus an explicit caller byte limit.
Construction rejects malformed, nonfinite, degenerate and over-budget data
transactionally. It polls cancellation off the tick. Scene creation/build,
destruction and neighborhood preparation are control/loader-thread operations.

`coh_physics_query` implements source radius, cylinder and nearest-start contact
semantics through the unchanged CTri kernels. It uses a 32-entry local traversal
stack, with hard node and narrow-phase budgets. `COH_LIMIT` is an unresolved
query, never a miss. Contact output stays unchanged on failure; attempted query
cost is returned separately. Equal-distance contacts and HIT_ANY select original
input order, independently of BVH order. Scene queries allocate nothing. The
source CTri receives a local copy, so immutable snapshots can be read concurrently.

`coh_physics_walker_prepare` creates an accepted WALK world from up to 8,192
nearby triangles in original source order, outside the tick. A walker owns that
copy and does not retain the scene pointer. Neighborhoods use caller-selected
AABBs of 32..4,096 source-unit half extents. A 16-unit interior margin covers the
accepted kernel's velocity cap, capsule radius and six-unit head query before
each tick. `coh_physics_walker_step` calls the unchanged source-controlled WALK
kernel once per 30 Hz tick. It allocates nothing. Before entering an unknown
neighborhood it returns `COH_NOT_FOUND`; the caller prepares a replacement then
retries the same tick. No accumulator or catch-up work is performed.

Refresh retains the complete accepted WALK state, including held-input timers
and collision state. Same-generation refresh therefore preserves airborne state.
A different generation must first pass the accepted initial ground admission
test; refreshing while airborne into changed geometry remains unsupported.
Queries and steps are single owner per walker. `clear` preserves pose and clears
input/velocity using the existing focus-loss behavior. `destroy` releases the
prepared window and resets the public struct. Logical state has no GL or Surface
resources and survives Surface recreation.

The `owned_triangle_bytes` walker field reports the equivalent original triangle
span size, not the accepted WALK private prepared-cache allocation or allocator
overhead. Scene `owned_bytes` reports all library allocation payloads exactly;
temporary off-thread neighborhood storage is bounded to 360,448 bytes plus the
new accepted WALK cache. Retaining the old prepared cache until replacement
commits makes refresh transactional and temporarily holds both caches.

## Validation

```sh
python3 native-android/engine/physics/check.py \
  --source-root /path/to/full/coh-repository \
  --fixture /path/to/qualified/walkable.bin \
  --ndk /path/to/android-ndk-r28c \
  --output /path/to/new-physics-proof.json
```

The source root must contain the pinned original `upstream/ouroboros` files.
The authentic COHWALK1 floor/bench corpus is an external qualification input and
is not copied or embedded into this module. The checker verifies all five
accepted source hashes, checks original active CTri tokens, and independently
compiles the original upstream CTri and triangle-intersection files with the
accepted portable type/math shim. Only platform includes and whitespace after
one macro-continuation backslash are normalized for that independent build.

Tests compare BVH contacts against a separate brute-force implementation of the
source contact law. They cover synthetic varied elevations/slopes, nearest-start,
center, cylinder, exact-start, both-sided, HIT_ANY and stable coincident-triangle
ordering. Another 128 source-matched WALK ticks traverse synthetic graded terrain
and a half-unit authored stair, including reversal with zero boundary clamps.
Authentic authored geometry is split into separate segment IDs and
compared against the accepted unsegmented WALK world for 250 byte-identical
movement steps: obstacle contact, diagonal sliding, reverse, release and focus
clear. The existing accepted WALK selftest also runs unchanged.

Negative cases cover invalid floats and flags, duplicate segment identities,
degenerate geometry, cancellation, byte/node/triangle limits, stale scene
generations, unsupported directions, transactional failed refresh, explicit
neighborhood exhaustion and missing replacement segments. Link-time allocator
wrappers count every malloc/calloc/realloc/free call during queries and movement.
ASan/UBSan run the same corpus; leak detection is enabled by default and any
explicit local exception is recorded. The Android step compiles and links a
native API 26 ARM64 shared library with `--no-undefined` and audits exports and
the ELF machine. This is build evidence, not Android runtime qualification.

The 32,768-triangle synthetic workload is useful for checking deterministic
query-cost and memory ceilings. Its measured CPU duration includes the slow
brute-force oracle and is not an engine frame-time benchmark. No full-game FPS,
GPU performance or thermal claim follows from these tests.

The committed local receipt records 15,331 checks, 2,050 contact-oracle cases,
378 exact accepted-kernel WALK steps, zero hot-path allocator calls and zero
outstanding tracked module/kernel allocations. A 32,768-triangle scene owns
7,995,448 allocation-payload bytes; the sampled query ceiling was 47 BVH nodes
and eight narrow-phase triangles. ASan/UBSan and API 26 ARM64 compilation passed.
LeakSanitizer was explicitly disabled after this sandbox refused `/proc/.../task`
access; the proof retains that restriction rather than claiming leak-sanitizer
coverage. Emulator and physical qualification are pending.

## Integration and rollback

Link `coh_physics.c` with existing accepted WALK/motion/CTri objects exactly once.
The standalone CMake target intentionally leaves those objects to the containing
application. Root CMake, Gradle, workflows and the accepted Session Client remain
unchanged. Existing source triangles/material flags and accepted transforms are
the adapter boundary; no network message or session ABI changes are required.

To integrate incrementally, construct a snapshot from loaded decoded static
mesh segments on the loader thread, prepare a source-ordered WALK neighborhood,
then step it from the existing fixed-tick owner. Honor query budget failures and
refresh requests by pausing the tick until geometry is confirmed. Preserve
independent Scene/Surface lifetimes. Publish a consolidated offline test before
enabling it in gameplay. Reverting the additive module commit, or simply leaving
its target unlinked, restores the previous source path. Keep the accepted 0.3.0
APK and its SHA256 untouched.

The separately committed `native-android/support-client/src/support_physics.*`
adapter is a thin opaque integration hook for the consolidated offline test.
It deep copies an authentic triangle span into three deterministic contiguous
segments, prepares the accepted WALK state, and exposes step/state/clear plus a
bounded diagnostic snapshot. Explicit `refresh` is off-tick; neither step nor
snapshot allocates. It has no JNI, GL, build, protocol or release mutations.

`check_support_adapter.py --fixture ... --ndk ... --output ...` compares the
adapter to unchanged accepted WALK over 250 authentic floor/bench ticks and
tests teardown after immediately freeing the caller input, invalid inputs,
focus clear, state-preserving refresh and diagnostic snapshots. The committed
adapter receipt records 1,026 checks, three segments containing 2,304 authentic
triangles, zero hot allocator calls, zero outstanding tracked allocations,
ASan/UBSan and Android API 26 ARM64 linking. LeakSanitizer has the same recorded
local `/proc` restriction. Runtime Android/Thor acceptance is still pending.

## Remaining gate requirements

- No new jump launch/hold/release law. Accepted WALK explicitly rejects jump
  input/state; adding one without its source oracle would weaken qualification.
  Existing source gravity/fall/landing behavior is retained, not extended.
- Elevation/slope/step query witnesses are synthetic and source compared; varied
  terrain movement, stairs, long airborne paths and authentic full-map traces
  still need independent qualification.
- Static world-space triangles only. Original tracker/octree traversal, moving
  platforms, dynamic objects and entity capsules are not implemented.
- Source triangle count per WALK neighborhood remains 8,192; dense scenes fail
  safely with `COH_LIMIT`. The new BVH accelerates public scene queries and
  neighborhood assembly; the accepted narrow WALK world still uses its original
  bounded scan. No unsupported sublinear WALK claim is made.
- Source world bounds remain limited to 16,384 units per WALK neighborhood.
  AABB safety cannot prove that all neighboring assets have been loaded; segment
  availability is a loader/integration admission responsibility.
- Replacement generation ground admission is conservative and can reject a pose
  close to an obstacle although its current WALK state is supported. Keep the
  previous snapshot and retry on confirmed ground; never reset the actor.
- Android emulator execution, actual Thor collision/movement and full Atlas
  Park/Kings Row streaming remain pending. Nothing here proves gates 25–27.
