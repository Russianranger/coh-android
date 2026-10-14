# Independent original WALK law oracle

`oracle.py` verifies source SHA256 pins before extracting and compiling the
unchanged original functions in a separate host shared library. The source is
not taken from the runtime adaptation. `oracle-source-pins.json` identifies the
original Git blobs and normalized source hashes; the generated receipt records
line ranges and hashes for each extracted body.

The active walking velocity path is `entWalk` → `DoPhysics` →
`entWorldCollide`. `motion.c`'s `calcNewVelocity` has no callers in that source
and is deliberately excluded from this proof.

The oracle covers 12,736 neutral-modifier velocity cases spanning grounded,
unsupported, falling, flying, low traction, release, reversal, diagonals,
perpendicular velocity, overspeed, vertical velocity, slope thresholds, and
default/slick/icy/bouncy surfaces. Its separate 144 original `SlideWall` cases
use supplied contact transcripts to prove the three-iteration correction law,
travel-check return path, zero-distance handling, and upward-velocity shutdown.

Original arithmetic macros, `CollFlags`, and the original math functions are
extracted as well. Platform sine/cosine helpers use host libm. Struct layouts
are minimal local shims: this is an independently executable mathematical
oracle, not a claim of binary compatibility with the original client.

World/entity collision callbacks are stubbed during velocity-law tests.
SlideWall uses explicit contact responses instead of original grid traversal.
These tests do **not** qualify original broad/narrow world collision, jumps,
stumble/power modifiers, moving entities, server prediction, or a complete map.
Generated expected outputs must still be compared with the native adapter;
successful generation alone is not an adapter-equivalence proof.

Run against the full pinned repository source tree:

```sh
python native-android/tools/walk_fixture/oracle.py \
  --source-root . \
  --output /tmp/walk-source-receipt.json \
  --goldens-json /tmp/walk-source-goldens.json \
  --goldens-header /tmp/walk-source-goldens.h \
  --slide-goldens-json /tmp/walk-slide-goldens.json
```

`--world-source` and `--grid-header` support split recovered source trees.
`--program` saves the exact compiled oracle for audit. Generated outputs belong
in temporary qualification output directories rather than gameplay assets.
