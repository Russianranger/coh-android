# Authored forward locomotion subset

The `COHLOCO1` runtime bundle keeps unchanged `huge/Skel_ready`, `huge/run`
and `huge/postrun` bytes in three qualified `COHRIG01` views. It contains no
baked pose palettes. The accepted character module applies authored Wretch
morphology and the runtime samples compressed keys every rendered tick.

This module is a bounded **offline selection adapter**, not the complete CoH
sequencer. Movement sets the source `FORWARD` state to select authored
`RunCycle [1,25]`; release selects its authored `RunPost [1,23]` next move;
that move's strict end returns to `Ready [1,60]`. The selected Ready clip loops
deterministically. Backward and strafe animations are pending, and callers must
not map those states to FORWARD merely to make them animate.

The source `RunPre [18,25]` exists but is intentionally omitted here. Its early
release chooses `Idle_Walk_Post`, whose huge-type fallback uses `male/walk`,
then `Idle_Ready`. The full source Ready graph picks additional look/hips
variants and other clips. Neither graph is replaced with fabricated clips or
claimed as implemented. Source transition blending and footfall `PlayFx`
effects are also pending.

Clock and stride behavior follows the original scalar functions:

* `seqGetMovementSpeedAnimScale`: actual world displacement divided by engine
  TIMESTEP, then authored `.7` feet per engine frame, clamped to `.25..2`.
* `seqGetAnimScale`: predictable moves use capped inverse character height
  scaling `.5..1.5`; authored Wretch height is `1.3`.
* `seqStep`/`seqCycleFrame`: only frames strictly beyond the authored last
  frame wrap, using one source subtraction and reset if still beyond the end.
* `seqSetMove`: the selected transitions reset to first frame, because Ready
  is a complex cycle in source and RunPost is noncycling.
* `smoothSprintAnimation`: above rate `1.05`, HIPS bone **0** Y becomes
  `3.3 + (Y - 3.3) / (rate * rate)`. Its local translation changes before
  hierarchical propagation; the runtime updates all descendants of that bone
  using the authored root transform. The lookup's final `1` is a recursive
  search argument, not bone ID1.

`coh_locomotion_step` accepts engine-frame increments at most3 (.1seconds),
so lifecycle recovery cannot advance a long wall-clock backlog. The caller
owns pause/reset timing and persisted movement state. Parsed views borrow
caller-owned immutable bundle storage.

Host qualification compiles the unchanged hash-checked original timing/rate/
sprint functions with bounded type/platform shims, executes independent raw
encoded-key sampling for all three clips, verifies invalid input leaves outputs
unchanged, and runs a separate ASan/UBSan process over exact-size truncations
and repeated state transitions. It qualifies the declared subset, not server
movement, live client protocol, complete animation state or physical-device
acceptance.
