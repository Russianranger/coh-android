# COH Client Test 0.5.0 — visible display test

The physical Atlas 0.4.4 create/save/restart/resume result is accepted.
Do not repeat that server run or perform manual Stop/rerun testing for this step.
Keep the accepted Atlas app installed.

## Install and run

1. Install `COH-Client-Test-0.5.0.apk`. It is a separate **COH Client Test** app.
2. Open it in landscape. Tap **1 · Set up runtime** once, with Internet available
   and at least 5 GiB free. Wait for **Runtime ready**. No game-data ZIP is needed.
3. Tap **2 · Run display test**. Keep the app visible. Wine initializes first;
   then the colored bars and two black/white code strips animate for 60 seconds.
   The test stops and cleans up automatically.
4. Look for **Visible display test passed** and a rising **Surface frames verified**
   counter. Tap **Export latest report** and send the ZIP, even if the test fails.
   Note whether you saw the bars changing or a blank/frozen view.

One foreground run is enough for this step. No screen locking, manual Stop,
second run, server boot, or large game-data import is requested. A blank view
while Wine starts is expected. If it fails, export the report before retrying.
The display operation has a 14-minute upper bound; the animation itself is
60 seconds. The first initialization time on Thor is not yet measured.

## Scope

This proves that changing graphics from a PE32 Wine/OpenGL fixture arrive on
an actual Android SurfaceView, checked using PixelCopy. The test requires
at least six different, current-session frames spanning two seconds, a complete
native producer result, and verified owned-process cleanup. RFB bytes or a
successful OpenGL swap alone cannot produce a pass.

The fixture is not `CityOfHeroes.exe`. Game menus, world rendering, hardware
acceleration, controller input, audio and interactive gameplay remain untested.
The next step after the visible presentation pass is the separately pinned
actual CoH graphical client package and startup.
