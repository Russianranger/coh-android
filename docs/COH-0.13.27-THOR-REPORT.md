# Physical .27 Thor report — 2026-10-11 UTC

The supplied `coh-atlas-gameplay-20261011-035622.zip` contains a completed .27
session, two verified Atlas instance transfers, ordinary character save and clean
shutdown. It closes the earlier missing-successful-report gap for this run.
It does not qualify Kings Row, monorail travel, every control, background export
survival, or sustained 30 FPS.

The archive is 16,388,507 bytes, SHA-256
`90e26ee753ca0a7d0090ee71b44a71cfdc7cdf122378c380c7924358e4d13980`.
All 41 outer and 15 nested guest entries pass ZIP CRC checks. The raw archive was
read in memory and was not modified. Machine-readable receipt:
`docs/android-evidence/recovery-0.13.27-thor-20261011.json`.

## Identity and successful recovery

- App **0.13.27**, Android 13 / SDK 33, AYN Thor; runtime generation
  `94aa2c650dfb2d4a26864eb55f6e2386d98c00c269b8e6c17af515d5faeed098`;
  runtime source `31fe36f64bd23648afc4ec3ba729e7f44dd7f40b`.
- Actual Game renderer: **zink (Turnip Adreno (TM) 740)**, OpenGL 4.3 Mesa
  22.3.6. This is the Game observation, not just the requested GPU selection.
  The generic report classifier still calls it `unclassified`.
- Retained Game source `c512e912a004b66886a7667640aa1a967e95de64`, SHA-256
  `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b`.
  Requested Performance/Turnip, native 800×600, effective cap 30.
- Session `e3757bcfdb5145ad8e890648153c2154`, **03:24:50.633–03:56:13.674 UTC**
  (October 10, 22:24:50.633–22:56:13.674 America/Chicago).
- `dead_owned_display_socket_recovered` is present: .27's guarded stale-socket
  recovery was exercised successfully before Game launch.
- PostgreSQL recovered a prior unclean shutdown using WAL and became ready.
  The end-of-WAL `invalid record length ... got 0` line is followed by completed
  recovery and ready status; this archive does not show failed database recovery.
- Ordinary logout/save completed at **03:55:04.278 UTC**. Committed SQL and native
  position, character identity, powers and costume were verified on Map 1.
  No forced stop preceded save. Guest failures are empty, process exit is zero,
  Finish was requested and cleanup was verified, including graceful PostgreSQL
  shutdown. No new crash is recorded in this run.
- All four retained Android exit records predate this session. The lifecycle
  array fills its 512-record bound; 487 entries are held-input releases. Late
  lifecycle details cannot be inferred from that truncated history. The final
  report and operation log independently contain save/Finish/cleanup results.

411 input events were submitted with zero transport failures; the report still
sets `input_effect_verified:false`. This does not physically qualify all controls.
There is no subsequent saved-character reopen or background-export test here.

## Zoning separates preparation, client loading and observer delay

| Measurement | Atlas 1 → 101, cold process | Atlas 101 → 1, resident process |
| --- | ---: | ---: |
| Request → ready destination, Android clock | 239.987 s | 5.260 s |
| Delivered mapmove → native CLIENT_READY, timestamp bounds | 59.209–60.208 s | 59.264–60.263 s |
| Delivered mapmove → completed guest arrival verification | 134.886 s | 138.267 s |
| Request → three fresh Android destination views | 383.949 s | 149.006 s |

Both arrivals bind the expected endpoint, map and character, preserve the client
PID, and retain three fresh Android views. Native CLIENT_READY precedes full
observer completion by approximately **76–79 seconds**. The large observed
arrival number must not be presented as pure client scene-load duration. The
operation log repeatedly launches translated `MapServer.exe -getstatus` probes,
often spending roughly five seconds per query. Stock DbServer log buffering and
the verification path are candidates for the extra delay; the archive alone
does not establish their individual shares.

The original Map 1 console contains immediate `COH_CHARACTER_EVENT_V1` ready and
position records; the destination Map 101 console does not. Extending the exact
session/character-bound native event path to destination instances and retaining
current endpoint/liveness checks is a justified observation improvement. It
must not turn queued input or a generic server-ready marker into arrival proof.

The new destination's native startup reports **224.518 seconds**, versus
**201.309 seconds** for the initial Atlas server. Representative cold-destination
regions from console timers and timestamp gaps are:

| Region | Wall time | Interpretation |
| --- | ---: | --- |
| Sequencer region before relevant-folder caching | 56.792 s | Gap between markers; exact subroutine cost is not instrumented |
| Story arcs | 30.03 s | Native enclosing timer; includes task/map-related work |
| FX information load | 29.489 s | Start-to-complete timestamp interval |
| Map loading | 27.56 s | Native timer |
| Group-library inventory/load | 21.070 s | Timestamp interval; 3,224 files / 75,433 names |
| PhysX initialization | 18.57 s | Native timer; 2,311 objects |

Prepared definition `.bin` caches are already used. Shared memory is explicitly
disabled, so `failed: no shared heap` is an expected configuration message here,
not a fatal startup error. A repeated Atlas orphaned door-animation point is a
content warning and did not block these transfers.

Temporary nice+5 successfully affected two owned destination threads and restored
both before readiness. Peak sampled destination RSS was **1,915,160 KiB**
(approximately 1.83 GiB). The sampled system pressure was primarily CPU waiting;
memory and I/O pressure were comparatively small. These are system-wide samples,
not per-process attribution, and do not prove a gain from scheduling policy.

Both client reloads spend approximately **31.2–31.4 s in group libraries and
definitions**, **11.8–12.4 s in surviving-FX preload**, **6.3–6.4 s in graphics
tree reset**, and **3.55 s in collision/physics**. The enclosing
`groups_network_and_processing` measurement is 38.6–38.9 s and includes child
group phases; do not add it to them. Server preparation and actual client reload
both need attention for sub-30-second end-to-end travel.

## Performance and asset gaps

Across this mixed gameplay/preparation session, 6,680 native gameplay frame
intervals average **80.577 ms / 12.41 Hz**. Window means span approximately
2.53–26.05 Hz. This is one activity-mixed report, not a controlled FPS comparison;
the accepted .25 baseline remains and no FPS delta is qualified.

Sparse queue observations cover 206 sampled scene frames: setup 5.174 ms,
sort 0.078 ms and draw submission 2.731 ms weighted means. The final cumulative
queue counters record 2,727,810 commands, 110,979 wake signals, zero failed wake
signals and **zero full-ring waits**. These measurements do not support making
ring capacity the next bottleneck hypothesis. Renderer wall time and graphics
submission are not pure GPU execution time.

The raw client log contains **3,077 FILEERROR blocks**: 1,024 missing texture-trick
references, 1,024 missing custom textures, 1,024 missing costume/player textures,
three missing Atlas loading-screen matches and two missing cape submodels.
The texture categories hit their logging caps and have explicit suppression
counters; they are not a complete inventory or proof that every missing item was
visible in this Atlas scene. The cape definition `FX/JIMB/CAPES/FlagUS.cape` asks
for `GEO_Flag_04` and `GEO_Flag_Harness_04` within
`object_library/FX/Flags/Flag_01.geo`. File presence alone therefore cannot prove
asset closure: model membership, textures, loading-screen mappings, collision,
beacons and other referenced resource classes need distinct checks.

The initial server preparation also records a 277.265-second cold data mirror,
59.786-second beacon installation/verification region and 56.756-second client
visual verification. Immutable asset receipts and reusable prepared worktrees
are justified targets; bypassing verification or reducing visual fidelity is not.

No storage audit is included in this archive. It cannot demonstrate a fix for
the earlier incomplete storage inventory or establish a new reclaimable total.
