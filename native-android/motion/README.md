# Gate 17: offline source-controlled motion

`coh_motion.c` adapts the original CoH binary movement controls and explicit
`MOVETYPE_NOCOLL` physics path into a persistent, allocation-free C11 state.
The renderer owns the actor transform; no motion fixture runs in place of user
input. The application calls one step per 1/30 second while foregrounded and
clears latched inputs on interruption, retaining the actor's position.

The pinned source revision is
`61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d` in
`Russianranger/coh-android`. Full normalized file hashes and original Git blob
identities are in `../tools/motion_fixture/source-pins.json`. Source files retain
their existing provenance; this adaptation does not introduce a new license
for the original game source.

The host oracle compiles unchanged bodies from:

- `Common/player/pmotion.c`: pre/post physics hold timers, input velocity and
  named directional animation states.
- `Game/src/player/player.c`: binary control changes and motion-angle adjustment.
- `Common/entity/motion.c`: `entMoveNoColl`.
- UtilitiesLib `mathutil.c/h`: source angle wrap, RYP matrix, vector transform,
  normalization and near-zero comparison.

An unchanged statement slice from the normal-strafe branch of
`playerAdjustBodyPYR` supplies the body-yaw smoothing calculation. The full body
function, forced turns, no-strafe creature facing, shell state and camera
obstruction logic do not run. Structural dependencies, sequencer state indices,
platform callbacks and control-list storage are stubs in the original oracle.
The directional output flags preserve named source meanings, and are explicitly
local encodings rather than original sequencer bit numbers.

The control contract keeps original direction IDs, opposite-key handling,
250 ms shared ramp promotion, 1000 ms saturation, short-tap ramp and diagonal
normalization. Source joystick axes enter as binary directions from the accepted
input kernel; analog speed interpolation is not added. The source 11-bit
network-angle quantization also applies before movement rotation. Direction
changes are timestamped at the start of the next fixed tick; sub-tick queued
input events are outside this offline seam.

This is **no-collision offline movement**, not normal `MOVETYPE_WALK` gameplay.
There is no ground/wall collision, gravity, jump, character-power state, live
server or prediction. The original no-collision debug path accelerates by
`(move_time + 6) / 6`, capped at 50 units per physics tick. Consequently it is
faster than ordinary walking; it is not a qualified movement-speed profile for
the eventual client. The caller supplies an initial source-world pose and an
explicit safety square (1–8192 source units from that pose). Clipping there is
reported as `bounded_steps` and is an adapter safety boundary, never collision.

Runtime state rejects nonfinite/out-of-domain yaw, unsupported directions,
broken timer invariants and invalid bounds transactionally. Focus clear stops
velocity and resets the source no-collision acceleration timer, while preserving
position and facing. State contains no user saves or server data.

`check.py` regenerates 2440 deterministic source steps: sustained directional
ramps, release/stop, diagonal combinations, opposing keys, reverse input,
angle-boundary cases and randomized changes. The unchanged source oracle is
compiled with `-fno-strict-aliasing` because its original normalization branch
type-puns floats. The actual native adaptation avoids that aliasing and is tested
with ASan/UBSan. LeakSanitizer cannot inspect this container's restricted `/proc`;
the local run used `ASAN_OPTIONS=detect_leaks=0`. No allocations occur in motion.

```sh
python3 native-android/tools/motion_fixture/check.py \
  --source-root . --output results/motion-host-proof.json --sanitize
```

The committed goldens are rebuilt from those original kernels. Host comparisons
had zero error; Android runtime comparisons allow 0.002 absolute plus 1e-6
relative float error for cross-libm transforms and accumulated positions.
Integer timers, direction-use bits and named directional state flags must match
exactly. Additional native tests cover rejection, safety clipping, focus clear
and zero movement after release. Passing host or emulator checks does not
establish physical controller handling or visible actor movement on the Thor.
