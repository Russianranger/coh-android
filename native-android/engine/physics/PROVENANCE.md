# Source provenance and compatibility boundary

The unchanged accepted collision adapter is `native-android/walk`, pinned to
upstream source revision `0b75ade0c801735e10c5798f641948a45cc50488`.
Its source identities remain in `walk/source-pins.json`; this continuation does
not replace those receipts or confer a new license on original source.

| Original source | Reused behavior |
|---|---|
| `Common/gridcoll/ctri.c` | CTri creation and expansion, radius contact, cylinder cap, exact-start correction |
| `Common/gridcoll/tritri_isectline.c` | Original triangle/triangle intersection kernel used by CTri |
| `Common/gridcoll/gridcollobj.c` | Evidence for source collision filtering/distance conventions; original tracker traversal remains outside this adapter |
| `Common/gridcoll/gridcoll.h` | Original collision bit values; accepted material flags retained |
| `Common/entity/entworldcoll.c` | Existing accepted feet/head/wall, slide and grounded/air movement laws |
| `Common/entity/motion.c` and `Common/player/pmotion.c` | Existing accepted fixed-tick control/movement adapter, unmodified |

`coh_physics.c` is a new ownership, balanced-BVH and neighborhood adapter.
It deliberately does not claim original octree/tracker traversal parity.
Prepared inputs preserve the world-space source float vertices and original
segment/triangle order. Source contact arithmetic is called through qualified
native kernels; no generic third-party physics engine or invented floor is used.

The independent oracle build reconstructs original CTri files from the supplied
source root after verifying their complete normalized hashes. The test's
brute-force contact scan is separate from the production BVH traversal. Original
active CTri arithmetic tokens are additionally compared with the accepted native
implementation. This establishes contact-law and traversal-selection parity for
the supplied witnesses, not equivalence of every original world/grid function.

Synthetic terrain and duplicate-triangle tests are explicitly mock geometry.
The external authentic corpus remains identified by SHA256 in each newly emitted
proof. Accepted Session Client 0.3.0 and its physical evidence remain immutable.

`coh_physics_snapshot.c` is an additive coverage-admission and reference-lifetime
adapter, starting from repository revision
`3c5da1d8cd501d778e270d395109d40666fbe37a`. It does not replace any source movement
or collision law. Its four connected slope regions are explicitly synthetic
source-qualified witnesses. `check_snapshot.py` verifies the five original
source hashes above and compiles original CTri files independently before
comparing exact source-WALK/refreshed-window results. Coverage-cell declarations
are loader metadata, not original map assets and not an assertion that a full
City of Heroes map has been qualified. Refcount ownership does not confer
thread safety on a shared mutable walker; each walker retains a single tick owner.

`coh_physics_neighborhood.c` starts from integration revision
`58caf1d4ab3b39757190f194100ccbc697d57857`. It adds copied state capture,
independent off-thread prepared-cache ownership and guarded simulation-thread
publication around the existing snapshot/WALK code. No original collision or
movement arithmetic is changed. Its sixteen slope sections and half-unit step
are explicitly synthetic source-comparison witnesses, not authentic city assets.
The checker preserves original source pins, separately compiles the original
CTri files, and compares accepted WALK physical/control state. No runtime asset
acquisition, server/network hook, mutable global scene or renderer is added.
