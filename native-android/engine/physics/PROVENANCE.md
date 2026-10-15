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
