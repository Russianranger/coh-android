# Bounded native WALK (gate 20)

This kernel integrates the active pinned source path `entWalk → DoPhysics →
entWorldCollide → entWorldMoveMe`, rather than the uncalled `calcNewVelocity`
helper. It retains the original ground/air surface parameters, texture surface
flags, slope friction/traction, original velocity cap/reversal law, gravity,
maximum five physics substeps, radius queries, feet/head tests, and the original
three-pass `SlideWall` correction. Original body math and `createCTri`,
`ctriCollideRad`, cylinder-cap checks, triangle intersection and exact closest
start routines remain source controlled in `source_*.c`.

The accepted gate 17 control ramp/yaw/body kernel remains unchanged. Its controls
are held separately from WALK position; the previous NOCOLL trajectory still
exists for rollback. Neutral offline source speed and surface modifiers equal
one, with no jumping, powers, status effects, entity collisions, prediction or
networking. WALK source speed is bounded normally; NOCOLL debug acceleration is
not used for actor displacement in this scene.

The adapter precomputes original CTri for at most 8,192 immutable world-space
triangles. The actual 276-triangle authored floor/bench fixture needs about 40
KiB of cache. A bounded AABB broadphase replaces full tracker/grid traversal.
Triangle flags come from source material/trick qualification, and the baked
render/collision world vertices share exactly the same floats. Degenerate
triangles are rejected by original `createCTri`; no floor is synthesized.

The source contact routines use a thread-local portable context; two original
function-local scratch variables are thread local too. `entWorldMoveMe` has an
export-name wrapper to isolate the velocity oracle. Instrumentation and legacy
unused declarations are handled without changing arithmetic. Full original
tracker traversal, moving objects, entity capsules, scene streaming and complete
WALK equivalence are not claimed by this bounded subset.

If support is absent or the actor would leave this bounded fixture, an explicit
scene guard restores the last supported pose, clears velocity, and increments
`bounded_steps`. This is separate from authored obstacle contact: the genuine
bench block/slide tests require zero boundary interventions. Future streaming
must replace the scene guard with confirmed loaded neighboring geometry.

`CohWalkState` has no owning pointers and survives surface/context recreation.
`coh_walk_clear` clears controls and velocity on focus loss while retaining the
pose. `CohWalkWorld` owns its cache and must be destroyed before replacement.
Input validation is transactional. Original CTri disk pointers are never used.

## Qualification

Run from a full repository checkout with original pinned source present:

```sh
python3 native-android/tools/walk_fixture/check.py \
  --source-root . --fixture /path/to/walkable.bin \
  --output /path/to/walk-qualification.json
```

The independent source oracle verifies source hashes before compiling unchanged
original velocity and wall-slide functions separately. It compares 12,736
velocity witnesses and 144 supplied-contact SlideWall transcripts with the
native mapping. World and entity callbacks in that oracle are stubbed deliberately;
these comparisons establish velocity/contact-law parity, not full original-grid
parity. Synthetic adapter/safety inputs and genuine authored geometry traces run
under AddressSanitizer and UndefinedBehaviorSanitizer. Real scene tests include
held obstacle contact, diagonal sliding, reversal, release/focus-clear, reset,
and support-boundary behavior. The native selftest retains 61 selected velocity
witnesses and synthetic contact/transactional tests for ARM64 startup checks.

The source oracle and source scopes are documented separately in
`tools/walk_fixture/oracle-PROVENANCE.md`. AYN Thor physical acceptance of gates
19–21 must be recorded separately from host/emulator qualification.
