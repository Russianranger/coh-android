# 0.13.16 focused AYN Thor test

The scene/frame pass is already qualified and published from
`d41aab3dd1a2f169a0ec71ff47d56767a8eb65e5`. This supplemental checklist makes
the physical observations explicit; the audited published APK, checksum and
original `COH-Atlas-Gameplay-0.13.16-testing.txt` remain unchanged.

[Download APK](https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.16/COH-Atlas-Gameplay-0.13.16.apk)
· [Qualification and public APK audit](https://github.com/Russianranger/coh-android/actions/runs/37559820885)

## Setup and two startup runs

1. Install 0.13.16 as an update over the existing app, preserving app data,
   runtime, imported assets and the existing character. Keep the accepted
   Performance preset, 800×600, llvmpipe and 10 FPS cap. Complete any offered
   Game/helper update once and record its duration separately.
2. For the first run, start a stopwatch when opening the launcher. Record
   the elapsed time when pressing Reopen, when login appears, when selecting
   the character/entering Atlas, when the first useful world image appears,
   and when movement is possible. Record password/selection time separately.
   If the app was already open for the update, record that fact; do not label
   its Reopen duration as a complete cold launcher-open duration.
3. Record the app's Local Atlas startup and actual client-start durations if
   shown. Do not estimate a missing phase by adding nested stages; the full
   support package provides the measured phase evidence.
4. Describe whether scenery becomes usable progressively, or whether a blank,
   loading or frozen screen persists until the world appears. Record pauses
   between first visible scenery and playable movement.
5. After the gameplay sequence below, use ordinary Save character/log out,
   wait for Saved character verified, then Finish and owned cleanup. Export
   the complete support package before another run overwrites its evidence.
6. Close and reopen the app normally for a second warm run. Repeat the same
   timings, route, preset and gameplay sequence. Confirm character, level,
   XP, powers and costume were retained. Do not clear caches or reimport.

Report these intervals for each run: launcher-open to playable Atlas,
Reopen to login and playable Atlas, Local Atlas startup, actual client start,
and character selection to first visible/playable world. Include the update
in the true first launcher-open total, but keep it separate for comparison.
The native MapServer-connect to CLIENT_READY report excludes selection delay;
it is a separate observation from manually judged playable entry.

## Gameplay sequence

Begin promptly after world entry. Record the local start time and elapsed time
since playable entry for each activity. Spend about 30 seconds on each; allow
at least 10 seconds between activity changes so aggregate windows can be
interpreted. Use the same route in both runs, remaining in Atlas.

| Activity | Record |
| --- | --- |
| Stand still | Observed FPS/range, regular pauses, temperature |
| Rotate the camera while stationary | FPS/range, stutter as new scenery enters view |
| Move through a populated area | FPS/range, geometry/texture/NPC pop-in or pauses |
| Approach a building/interior edge or previously unseen scenery | Hitch duration, first versus repeated approach, missing visuals; stay in Atlas |
| Fight several NPCs | Stability, powers/FX/UI, NPC movement and frame pauses |
| Open ordinary UI and track an objective | UI completeness, quest marker/pathing and pauses |

Record temperature at world entry, after camera/populated movement, and at the
end; note the peak, fan mode and charging state. If no native FPS display is
available, say so; the native report supplies cadence. The Android delivered-
frame counter is a different measure and must not be labeled native game FPS.
For a visible hitch, record the time, activity, approximate duration and what
newly entered view. Note crashes, freezes, audio/control problems or visual
regressions. If a stage fails, Abort, wait for owned cleanup and export that
run's package. A failure is useful evidence; do not replace it with a new run.

## Export and diagnostics

After **each** run, use **Export latest report** and send the complete outer
`coh-atlas-gameplay-*.zip`, along with the observations above. Keep:

- Outer `operation.log`, `android-client-report.json`, and `guest-report.zip`.
- Inside `guest-report.zip`: `latest-report.json`,
  `client-evidence/client-console.log`,
  `client-evidence/character-atlas-console.txt`, and
  `character-server-logs.zip`.

New native records are in **`guest-report.zip` →
`client-evidence/client-console.log`**:

| Record/field | Interpretation |
| --- | --- |
| `COH_CLIENT_FRAME_TIMING_V1` / `pacing_wall` | Explicit waitFps pacing for the retained cap |
| `frame_interval`, `frame_wall`, `work_wall`, `engine_wall` | Native cadence and main-loop wall work; work_wall subtracts pacing but still includes other waits |
| `thread_cpu_ms` | Calling main/presentation thread CPU sampled over the window |
| `submit_wall` | Render submission and backpressure wall time |
| `presentation_interval`, `present_wall`, `swap_wall` | Presentation cadence, present function and actual SwapBuffers wall time |
| `COH_CLIENT_SCENE_PHASE_V1` | Nested group/reference/entity/collision/FX and scene-ready phase durations |
| `geometry_loader_completion`, `relevant_textures_request`, `texture_queue_completion` | Geometry completion and texture request/queue-completion budgets |
| `max_ms`, histogram, `over_125ms_count`, `over_200ms_count` | Abnormally long frames; p50/p95 are histogram bucket upper bounds |

Frame records aggregate roughly 10 seconds, with at most 120 records per
main/presentation stream. Scene output is bounded to 128 records per
translation unit. Complete the focused sequence within the first several
minutes of gameplay; the frame budget also covers earlier menu/loading work.
The final partial frame window may not be emitted. Scene intervals nest and
must not be added to enclosing intervals as independent work.

These are not GPU completion measurements. Thread CPU excludes llvmpipe,
Wine and FEX worker CPU; texture queue timing does not separately identify
individual texture decode and upload costs or every gameplay loading hitch.
The exported records plus timed physical observations will determine whether
additional attribution is needed before the next optimization.

The next agent can analyze either complete outer package with:

```bash
python3 tools/android/interactive/analyze_client_scene_performance.py COMPLETE_OUTER.zip --output report.json
```

Physical 0.13.16 startup/FPS gains and visual/gameplay preservation remain
pending these tests. Zoning remains deferred.
