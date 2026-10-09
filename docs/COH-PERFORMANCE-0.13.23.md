# 0.13.23: repair movement authorization and isolate timing overhead

The physical .22 test regressed: the user could click and rotate the camera but
could not move, and FPS was worse. The screenshot reads 4.86 FPS / 205.8 ms.
The supplied outer export confirms the exact published .22 Game and actual
Zink / Turnip Adreno 740, OpenGL 4.3 compatibility Mesa 22.3.6. Successful GPU
startup remains a completed milestone; this was not a Software fallback.

The report contains 2,192 conservatively classified gameplay frames at native
cap 30 over 333.294 seconds. Mean interval is 152.044 ms / 6.577 native cadence
Hz, p95 histogram upper bound 333 ms, maximum 578.334 ms. Main-thread CPU is
43.335 ms per frame; mean graphics submission is 134.621 ms. The .21 aggregate
was 52.189 ms / 19.161 Hz. The routes, input availability and durations differ,
so these are regression observations rather than a controlled comparison.
Native cadence is not display refresh or GPU completion.

## Movement failure and correction

Android recorded `character_session_budget_rejected` immediately after the
character connected. The guest emitted revision 1, while Android remained at
revision zero with no movement or save deadline. Walking and Jump require an
accepted save-capable budget; pointer and camera input can remain available.
This reproduces the user's symptoms without assuming that Game stopped.

| Clock in the captured run (UTC) | Time |
| --- | --- |
| Owned presentation ready | 16:05:51.426 |
| Owned launcher started | 16:06:53.901 |
| Android maximum: presentation +35 minutes | 16:40:51.426 |
| Original guest maximum: launcher +34 minutes | 16:40:53.901 |

GPU preparation took 62.475 seconds, exceeding the previous one-minute
allowance by 2.475 seconds. The guest deadline therefore exceeded Android's
unchanged hard cap and was rejected. The corrected guest budget also uses the
owned presentation clock and takes the minimum of presentation +35 minutes,
launcher +34 minutes and the existing operation reserve. It only shortens
deadlines; it does not weaken Android validation or the neutral/save reserves.

The inherited `startup_only_reopen` policy suppresses the authored-task gate,
not ordinary saving or movement. Its old startup status wording is misleading.
An accepted budget still permits normal Save, strict committed SQL/identity/
powers/costume/position validation, fresh Android views and Finish. Flipping
that policy would unnecessarily require another task qualification, so it stays
retained. The failed .22 run did not request or verify a save; cleanup completed.

## Rendering evidence and focused isolation

The measured main viewport averages 119.111 ms, UI 13.525 ms, explicit queue
flush 0.011 ms and finish 0.343 ms. Slow renderer windows contain long gaps
between commands. Swap is about 3–4 ms, measured readback is zero, selected
uploads are small, and Android capture copy freezes average 2.355 ms at roughly
one capture per second. Encoding uses about 104 ms CPU per capture off the UI
thread and can compete for CPU. These counters do not isolate pure GPU time.

The dominant viewport contains scene traversal, entity/FX work, sorting and
draw-command production. Explicit flush measurements do not include waits for
space in the worker's approximately 16 MB command ring. Renderer command wall
time includes driver waits; independent renderer windows cannot be joined to
main windows by ordinal. Existing evidence cannot choose safely between scene
CPU work, hidden queue blocking and translated instrumentation overhead.

Actual authenticated .21/.22 CMake evidence shows the same OptDebug/Win32
configuration, `/O2 /Ob2 /DNDEBUG /Zi /Oy-`, MSVC 14.51.36231 and CMake 4.4.3.
The .22 Game grows by only 6,144 bytes and retains the same import closure.
There is no accidental unoptimized build. Source review found no direct logic
regression in the worker wakeup correction, but physical evidence does not prove
that it improves FPS.

.23 retains the exact .22 Game and its completed original Windows proof. Reopen
turns off the added `COH_CLIENT_RENDER_PIPELINE` measurements after the current
typed Game gate, while retaining the earlier frame, scene and renderer streams.
This is a same-Game diagnostic isolation of timing cost, not a claimed FPS fix.
The shared Wine environment, servers and diagnostic creation path retain their
existing settings. No native Game or GPU driver/probe build is repeated.

All visual assets, resolution, shaders and effects remain retained, as do the
Android UI/controls/DEX/resources, twenty DLLs, Software fallback, persistence,
prepared cache and save acceptance. Startup and zoning remain deferred.

Input pins, representative source/backend evidence, clocks and interpretation
limits are recorded in `android-evidence/session-repair-0.13.22-thor-20261009.json`.
The initial owner `37963422463`, source `d2e686582f493b6951eff4ad44b50b269081cabc`,
passed all 107 suites / 1,556 tests / zero skips, including all seven real
PostgreSQL fixtures. Packaging stopped before creating an APK because a new
contract comparison used insertion-order bytes while qualification sorted JSON
keys. The host-only correction compares sorted typed JSON and adds a fresh
interpreter reader regression; guest and native bytes stay unchanged. New
publication must qualify its own source; the old receipt is not relabeled.
Publication validation and exact download pins will be recorded separately.

## Exact next milestone

Follow `COH-Atlas-Gameplay-0.13.23-testing.txt`: use the existing GPU Performance
setup, confirm walking and Jump after Atlas connection, then a short standing,
camera and walking route at cap 30. Save normally, wait for verification, Finish
and export the outer ZIP. The report must show an accepted budget and disabled
new pipeline timing on the same Game. FPS recovery would implicate enabled
timing overhead; persistent slow frames require bounded scene/sort/submission
and full-ring-wait instrumentation before choosing a native optimization.
Stable 30 FPS remains the target and is not established.
