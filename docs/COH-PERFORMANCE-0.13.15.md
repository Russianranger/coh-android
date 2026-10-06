# 0.13.15 performance continuation

## Physical 0.13.14 evidence

Source baseline is continuation head `8de212e60520d1af66dfcd2f25481f57a85e1d34`,
with published APK source `25f821da9e782281953412543057054abd8dd320`.
The physical Thor report is `coh-atlas-gameplay-20261006-033901.zip`; its bounded
phase summary and SHA-256 are in `android-evidence/performance-0.13.14-thor-20261006.json`.
The user accepts observed UI completeness, native beaconization, quest objectives,
NPC pursuit, combat and task completion. The report passes ordinary save/reopen
and owned cleanup. These physical observations are separate from hosted checks.

The observed 21-minute interval is mostly **one-time server tree preparation**,
not a regression in native client or Atlas initialization. The 0.13.14 required
geometry contract correctly invalidated the three older closed server trees.
The new compatible cache key is `d3f6b18b9ea8bf59a848686a` and this completed run
returned it closed. It must be retained by guest-only performance updates.

| Phase | 0.13.13 warm physical | 0.13.14 first-update physical | Interpretation / next measurement |
| --- | ---: | ---: | --- |
| Android Reopen dispatch to guest | — | 1.49 s | Runtime installation/app-open delay is outside this measurement. |
| Client inputs/private tree | — | 1.46 s | Existing 173,011-input client tree reused. |
| Persistent profile/PostgreSQL | — | 1.00 s | Database is preserved; PostgreSQL itself 0.49 s. |
| World supplement | — | 25.02 s | 2,904 leaves reused; 207.8 MB archive read, no decompression/cache deletion. |
| Wine initialization | 7.76 s | 9.13 s | Ready prefix reused; no registration pass. |
| ODBC preparation/probe | — | 13.24 s | Preserved this pass. |
| Server preparation + DbServer readiness | 38.46 s | 538.66 s | **508.40 s** preparation; remaining 30.27 s includes native launch/readiness/SQL proof. |
| Atlas MapServer readiness | 210.36 s | 198.84 s | Within prior 3–4 minute range; beaconized graph retained. |
| Visual preparation | 29.73 s | 70.16 s | 788 new UI leaves decoded; 9,613 prior leaves verified; 859 MB archive read. |
| Client animation preparation | 13.54 s | 13.60 s | Original animation pack reused. |
| Texture-header preparation | 21.06 s | 55.82 s | New texture inventory; 43.34 s inventory, 12.42 s original header reads. Overlap only 1.11 s. |
| Actual native client startup | 188.31 s | 198.17 s | Within prior ~3-minute range; native metadata preload active. |
| Reopen to observed login | 556.89 s | 1,150.13 s | 9:17 versus 19:10; includes readiness observation/user interaction. |
| Observed login to observed world | 84.52 s | 83.81 s | Includes typing/character selection. |
| Reopen to observed world | 641.41 s | 1,233.94 s | 10:41 versus 20:34, consistent with reported ~21 min. |

Rows include nested subphases and must not be added together. Server preparation
contains required GEO verification (5.14 s, 406 originals, 16.56 MB selected
hashing, 40 affected owned caches removed once), cold mirror/seal, server donor
installation and beacon preparation (57.29 s, 5,637 inputs, 494.18 MB hashing,
2 graph/date leaves installed). It mirrored 186,535 files into 9,962 directories,
with 185,313 immutable file links and 1,208 private copies. Beacon generation
was **not** rerun. The first UI append/header rebuild is expected once; this one
report cannot demonstrate that either repeats on every unchanged launch.

## FPS and smoothness candidates

Current physical renderer is llvmpipe (LLVM 15.0.6), Mesa 22.3.6, OpenGL 4.3
compatibility at 800×600. The accepted launch explicitly caps gameplay/menu/
inactive frames at **10 FPS**; this pass preserves that cap to keep the physical
comparison and thermal behavior consistent. Eliminating contention targets
smoother delivery within the cap, and does not promise 30 FPS. Android delivered
frames do not measure native game FPS.
No credible draw-call, allocation/GC or texture-upload timing is present in this
report; those causes should not be asserted from a low display-frame count.

| Rank | Candidate | Expected benefit | Implementation / regression risk | Correctness / runtime impact |
| --- | --- | --- | --- | --- |
| 1 | Stop repeated translated registry probes after current-attempt main-loop proof; repeat fresh proof at finish | Removes recurrent Wine/FEX CPU contention; observed 21 queries cost 43.09 s | Low; session-bound readiness and final proof retained | No renderer/native/runtime change |
| 2 | Use native event/progress heartbeat during connected gameplay; full SQL/status verification on logout/save | Removes repeated MapServer.exe startup and SQL work during gameplay; 33 translated status launches cost 122.96 s | Low–moderate; test late/invalid event, logout and save failures | Keeps connection and commit-before-save proofs; guest-only |
| 3 | Reduce full console/native-hook polls after readiness | Potentially material; physical full polls consumed 127.03 s over 143 calls | Moderate; current PID/session evidence must remain live | Guest-only; bounded sampling, full startup/final checks |
| 4 | Optimize cold file-tree ancestor/path work and retain exact closed cache identity | Large first-update startup opportunity; warm cache avoids mirror entirely | Low–moderate; symlink/containment guards mandatory | Immutable bytes/cache identity unchanged; guest-only |
| 5 | Reduce X window identity polling | 143 calls cost 34.35 s | Moderate; visible-window loss/identity regressions | Deferred pending independent presentation evidence |
| 6 | Lower internal resolution/render costs with existing reversible preset | Potential fill-rate gain on software renderer | Low–moderate visual/thermal tradeoff; requires comparable physical FPS | Existing graphics controls; leave preset unchanged for this comparison |
| 7 | Tune synchronous streaming, upload, draw calls or allocations | Unknown without native measurements | Moderate–high; broad game changes need separate qualification | Deferred; accepted native Game bytes retained |
| 8 | Zink/Vulkan/device GPU or newer FEX | Potentially largest rendering gain | High; black screen/crash/assets/runtime risks | Separate native/runtime experiment; deliberately deferred |

The shipped work, actual hosted evidence and physical after measurements are
recorded below after qualification. No physical startup or FPS gain is claimed
before the new Thor test.


## Implemented changes and measurable host comparison

The exact closed server-data cache contract/key is unchanged. A compatible
existing 0.13.14 generation therefore uses warm checkout; no full-mirror fallback
is triggered by a guest-only helper update. Changed/missing inputs still follow
ordinary invalidation/recovery. Cold staging resolves common real parent paths
once per invocation, while each leaf retains a fresh file-type/containment
check and arbitrary chained/dot-component links retain strict resolution. Final
parent metadata rechecks and safe receipt names remain mandatory. Receipt seal
checks each complete recorded parent once.

The representative filesystem fixture reduces metadata calls from **4,608 to
793 (82.8%)**. The 4,002-leaf warm fixture preserves the cache key/inode/native
bins and performs **zero new links/copies**. These are hosted operation counts,
not physical elapsed-time predictions. New phase receipts separate cache
checkout, cold mirror/seal, warm restore, native dependencies, server definition
bins, animation pack, graph verification, native dispatch and schema snapshot.

The client keeps fresh initial readiness and terminal registry proof; recurrent
queries during gameplay cease. After current native Atlas connection, lightweight
native progress/events and optional task/recovery observers continue. A valid
session/PID/character-bound logout receipt starts the unchanged fresh SQL,
disconnected-status, timer, native-position and full saved-row proof. Window,
process,stop,overflow checks remain. No success result is substituted for a
fresh save witness.

**Physical after column remains pending.** The next run must demonstrate the
same compatible cache key/reused=true, no repeated full mirror, warm visual and
beacon reuse, unchanged character/UI/pathing and reduced observer work. Record
both first-update and second warm outcomes; do not subtract nested phases or
claim 166 seconds of guaranteed wall-time/FPS gain from cumulative probe durations.
