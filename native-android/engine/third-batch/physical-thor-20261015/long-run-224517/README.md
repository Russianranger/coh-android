# Thor code 201 — 22:45 longer-run assessment

**Ten-minute endurance remains passed; another long run is unnecessary.** The exact released APK now records **29m58.906s active foreground**, **107,476 frames / 59.75 FPS**, mean frame 15.604 ms, p95 upper 20 ms, p99 upper 27.5 ms and maximum 47.483 ms. There are 94 samples above 33.33 ms and **zero 100 ms stalls**. Unexpected graphics/cleanup/transform/support errors remain zero across 24 contexts, 23 completed. Two canceled/stale `EGL_BAD_SURFACE` events recovered; three abandoned observer intervals are not compositor-drop measurements.

Newly verified: **one successful nonempty local chat submission** and **Male-active explicit Surface recreation**, with resource uploads continuing from 4 to 5 and rendering resuming. The two requested explicit recreations (Wretch and Male) are now covered. The appearance preview totals 2,809 frames, 22,472 draws, 5 uploads and 0 failures. Three reports reconstruct event sequences 1–212 without gaps; the last file alone is only a 128-event ring. Three pause/resume pairs are present, all Wretch-active; two immediately follow Export report, so the report cannot identify three explicit Home cycles or a Male-active Home check. The single Mock animation press occurred while Male was displayed, so it does not establish visible Wretch animation cycling.

| Sample | Active time | RSS MiB | PSS MiB | Java used MiB | Native heap MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 22:18 | 3m15s | 180.65 | 72.65 | 18.90 | 26.18 |
| 22:31 | 15m44s | 177.26 | 68.42 | 28.07 | 26.62 |
| 22:45 | 29m59s | 200.17 | 91.25 | 48.25 | 26.95 |

Whole-process memory is not flat. Fixed measured world/skin/partial-module accounting remains unchanged, but Java-used and process-memory endpoints rise. Three snapshots neither prove a leak nor establish stable residency. Source review identifies event-ring JSON cloning plus full pretty serialization every second on the main thread as a transient-allocation profiling candidate. Heap/GC/report allocation analysis is developer follow-up; the user does not need another endurance test.

Audio remains running with 7 opens/6 closes, 3 route reopens and no reported device error. Retained joined statistics show 104,708 callbacks, 7.152 ms maximum and zero recorded stream-underrun frames; current live-backend diagnostics are unavailable. Prior user-confirmed audible music/audio remains valid. Device-specific route listening and external focus interruption are separate open checks (`focus_changes=0`).

Use [the remaining-test instructions](REMAINING-TESTS.md) with the existing code201 APK. No repeated chat, Recreate or long endurance test is required. Original-source visual parity, missing assets/full zones, developer memory work and primary-agent live gameplay remain separate work; they cannot be qualified by repeating this demo.

The original report is preserved byte-for-byte as `COH-NativeSupport-20261015-224517.json.gz`; raw SHA256 `ff8e577d33279380bd7709531e6c32a6009826780444b3e3ee356fe69da3e2aa`. `assessment.json` and the independent diagnostics review preserve exact counters, source binding and limits. Runtime source/APK are unchanged. No full numbered gate closes.
