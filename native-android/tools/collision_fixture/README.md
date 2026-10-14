# Gates 19–21 preparation: collision fixture boundary

This host acquisition tool decodes the x86 little-endian `PolyCell` graph from
GEO pack 7 using integer offsets. It does not cast disk pointers, modify the
GEO, render a new world, or enable runtime collision. The source `PolyCell`
layout is two 32-bit pointers and one signed 32-bit count. The root resides at
byte zero; zero child entries represent null. Each children array has eight
32-bit offsets; triangle references are U16. Shared cells are retained once,
while repeated triangle references remain intact.

Bounds cover input bytes, triangle count, cell count, graph depth and total
references. Invalid spans, alignment, negative/excess counts, absent triangles
and cycles fail before a result is returned. Source hashes and Git blob IDs
are recorded in `source-pins.json`.

`bench-grid.json` retains the actual 500-byte grid from the already pinned
`misc_sm.geo` member; its model is `modern_bench_2wide__mbench`. Acquisition
verified exact member size, CRC32 and SHA256 using 212,460 bounded HTTP range
bytes. It did not download or hash the entire asset pack. The decoded grid
contains 3 cells and 216 triangle references covering all 188 mesh triangles.
The fixture is test input only; it is not a new Android runtime asset.

Run the new host checks from repository root:

```sh
python3 -m unittest discover -s native-android/tools/collision_fixture -v
```

Five tests cover genuine source bytes, complete triangle coverage, all 500
proper prefixes (rejected or semantically identical if only padding is lost),
leaf/child/shared-cell decoding, count/span/alignment failures, cycles and depth.
These checks establish bounded host decoding, not execution parity with the
original pointer-relocation routine, ARM64 execution or collision acceptance.

## Required next implementation

1. **Gate 19:** select an authentic Atlas ground/obstacle group and close its
   group transforms, GEO, texture and trick dependencies. Reuse existing delta
   and source world math. Convert its disk grid safely; reconstruct source
   `CTri` using `createCTri`, then apply `modelSetTexOptCtriFlags` and
   `modelSetTrickCtriFlags`. `modelCreateCtris` does these after grid inflation;
   the disk grid does not contain the finished triangle flags. Preserve model
   indices and render/collision transforms, check source degenerate triangles,
   compare an independent original-source oracle and bound memory/loading.
2. **Gate 20:** the WALK implementation is in `Common/entity/motion.c`, not
   solely `Common/player/pmotion.c`. Close `entWalk` → surface parameters,
   modifiers/texture overrides, `checkJump`, `DoPhysics`/`DoPhysicsOnce` →
   `entWorldCollide` in `Common/entity/entworldcoll.c` → source grid/capsule
   queries. Port a documented grounded subset only after gate 19 has real
   traversable ground. Compare original-source motion/contact traces for flat
   ground, slopes, obstacles, wall sliding, corners, reversals and release at
   30 Hz. Retain NOCOLL only as the explicit prior/offline fallback.
3. **Gate 21:** use the accepted locomotion source pins and raw clip acquisition.
   `RunPre` for Huge uses `huge/run` frames 18–25, CycleMove `RunCycle`,
   NextMove `Idle_Walk_Post`, MoveRate 0.7 and Interpolate 5. Resolve the complete
   inherited `Idle_Walk_Post` → `Idle_Ready` dependency and authored
   `Run_Back_Pre/Cycle`, `Run_Left_Pre/Cycle`, `Run_Right_Pre/Cycle` bindings.
   Preserve source priorities, member interruption, MoveScale/SmoothSprint,
   timing and hierarchy. Compare short taps, interrupted pre-run, diagonals,
   reversal and obstacle interruption with source selection/timing witnesses.

Integrate all three into the existing Session Client; do not create another
standalone Android probe. Retain prior byte-identical qualified APK/evidence
and an explicit rollback path. New runtime/package qualification must not
change physical gates 16–18 from pending to accepted. GPU skinning, full Atlas,
jump/gravity closure, server prediction/login and sustained Thor performance
remain later work. **No gate 19, 20 or 21 is claimed complete here.**
