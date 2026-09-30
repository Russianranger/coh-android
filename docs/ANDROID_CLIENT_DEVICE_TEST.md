# COH Game Client Test 0.6.0 — actual client startup

The physical Atlas 0.4.4 server test and 0.5.0 display test are accepted.
This step launches the pinned `CityOfHeroes.exe` through that display path.
Keep the accepted apps installed; no repeat Atlas, pattern, manual Stop/rerun,
or screen-lock test is requested.

## One foreground run

1. Install `COH-Game-Client-Test-0.6.0.apk`, the separate **COH Game Client Test** app.
2. Open it in landscape. Tap **1 · Set up runtime**, with Internet available
   and at least 5 GiB free, and wait for **Runtime ready**.
3. Tap **2 · Import client assets**. Choose the same complete
   `coh-reference-assets.zip` used for Atlas (615,541,018 bytes). Have at least
   6 GiB free after runtime setup for the import and prepared client data. Wait for
   **Client data ready**. This separate app needs its own one-time import;
   Android keeps the existing Atlas app's files private. The imported data is
   about 3 GB. Select the complete ZIP, not split parts or individual PIGGs.
4. Tap **3 · Start CoH client** once. Keep the screen visible. Wine initializes,
   then the actual CoH client loads its graphics and data. A blank view during
   early initialization is expected. The first launch also creates small links
   and installs the prepared client data caches; it does not duplicate all
   imported data. Cache preparation is included in the APK.
5. Watch for a recognizable CoH loading or login screen. No login or controller
   input is required. After startup is detected, the app observes the client
   for 30 seconds and closes it automatically.
6. Tap **Export latest report** and send the ZIP, whether the result passes or
   fails. Say what appeared on screen: CoH loading/login, an error dialog,
   black view, or a frozen view. The ZIP includes bounded screenshots and logs.

The launched runtime has a 28-minute watchdog; preparation and cleanup can add
time. Setup and import are separate. The 30 seconds refers only to observation
after startup, not the total first-launch time. If it fails or times out,
export before retrying. One run is enough for this step.

## What the result means

**Client startup observed** requires the current client process, renderer and
data completion, its main loop and mapped game window, three actual Android
PixelCopy screenshots during that window's lifetime, and verified cleanup.
Static screens can qualify; the test does not require menu animation.

Visual review establishes what the game screen actually shows. This build
starts no game server and does not establish login, world entry, controller
input, audio, hardware acceleration or playable performance.

Native Windows diagnostic prompts are recorded as text in this profile.
The game's own graphics, loading and data checks remain enabled. See the
[console profile review](android-evidence/client-console-profile-20260930.md)
for the exact diagnostic behavior changes.

Runtime installation, asset import and generated caches persist for later
launches. There is no need to repeat setup or import after this one run.
