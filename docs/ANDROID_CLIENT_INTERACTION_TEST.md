# COH Client Interaction 0.7.0

## September 30 device result — no repeat menu session requested

Touch and right-stick pointer movement, A-click and text entry were confirmed
by the user; saved Android captures show `COHINPUT` with Settings open. Cleanup
passed. The original session remains failed because its final guest capture was
black after closing Settings. Loading artwork and shader compilation support a
graphics reload; return to the menu and B's separate effect were not proven.
See the [review](android-evidence/client-interaction-thor-review-20260930.json).
Keep this installation and its imported data for a future same-signature update.
The procedure below is the historical one-session test, not a request to rerun it.

For future integrated checks, avoid changing graphics controls just to prove
pointer input. Settings' red X can reapply graphics settings. If checking B,
press it while Settings is still open and observe its effect before another
action; do not combine red-X close and B as one observation.

Actual client startup passed on your Thor. This next step checks whether touch,
text and the built-in controller operate the game's menus in one session.
The accepted Atlas, display and startup tests stay complete. This app starts no
server and does not test login or world entry.

## Install once

1. Install `COH-Client-Interaction-0.7.0.apk`. It appears as **COH Client Interaction**
   beside the accepted apps. Keep those apps installed.
2. Tap **1 · Set up runtime**, with Internet available and at least 5 GiB free.
   Wait for **Runtime ready**.
3. Tap **2 · Import client assets** and choose the same complete
   `coh-reference-assets.zip` (615,541,018 bytes). Allow at least 6 GiB free after
   runtime setup. Wait for **Client data ready**.

This separate package needs its own initial setup/import because the 0.6.0 test
used a temporary signing key that was not retained. The new package has a retained,
pinned development signing identity for subsequent updates. Setup, imports, Wine
state and prepared caches persist in this app.

## One foreground interaction session

1. Tap **3 · Start interaction check** once and keep the screen visible. Wait for
   **Client ready for input** and the countdown. Loading artwork can appear before
   full readiness; preparation and loading may still take several minutes.
2. Tap **Cancel** on the game's Quality/Ultra graphics prompt, if shown.
3. Tap the game's **Account Name** field. Tap **Send test text / L3**, leave
   `COHINPUT` in the dialog and tap **Send**. Check that it appears in the game field.
4. Move the pointer onto **Settings** with the Thor's right stick and press **A**.
   Check that the settings window opens. Press **B** to try Escape. Touch and drag
   a visible settings slider if available; describe whether it follows your finger.
5. Tap **Finish and save report** when done. The session also closes automatically
   three minutes after input becomes ready. An early Finish waits until the initial
   30-second live observation is complete. Wait for cleanup to finish.
6. Tap **Export latest report** and send the ZIP. State whether touch, `COHINPUT`,
   the right-stick pointer and A/B worked. If something fails, export this same
   session; no Stop/rerun or additional server boot is requested.

Use the test word only; do not press the game's Log In button for this milestone.
The launched runtime has a 28-minute watchdog. The three-minute interaction window
begins after full startup; it is not the total launch time.

## Basic controls

| Control | Action |
| --- | --- |
| Touch | Direct pointer, tap and drag within the game image |
| Right stick | Move pointer |
| A | Left mouse button |
| B | Escape |
| Either shoulder | Right mouse button |
| D-pad | Arrow keys |
| L3 | Open the test-text dialog |
| Hardware keyboard | Text and common navigation keys |

These are initial menu controls. Editable gameplay mappings, audio, GPU
acceleration and playable performance are later work. A completed report verifies
the observed session and cleanup; transmitted input counts alone do not prove
the game responded. Screenshots and your observations establish those effects.
