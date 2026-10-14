# AYN Thor: one combined check for gates 13–15

Install `CoH-Native-Integration-Probe-0.1.0-arm64.apk` and open
**CoH Native Integration Probe**. Existing probes and your launcher can stay
installed. This test needs no server startup, account or asset import.

1. Wait for the authentic Atlas bench scene to appear. Tap **Run checks**.
   Drag the scene left, right, up and down with short movements, releasing
   after each. Press/release **A** and circle both Thor sticks. The right stick
   controls this camera; left-stick character movement is a later milestone.
   Look should reach **15/15**, with both sticks marked complete. The camera
   view is deliberately limited to keep the bench in view.
2. Tap **Play decoded sound**. You should hear three game clips with a quieter
   middle clip. Let playback finish, then tap **Heard 3 sounds**. This time the
   compressed Ogg is decoded on your Thor before playback.
3. Tap **Resize**, wait about 6–16 seconds for the current rendered check to
   finish, then tap **Recreate** and wait again. Swipe the horizontal button
   row to expose controls outside the right edge. Use **Reset view** if needed;
   it restores the authored camera and requires a fresh rendered check.
4. Tap **Home check**. Wait for **READY — press Android Home now**, then press
   Android Home while the sound is playing. Return without force-stopping the
   app. Tap **Play decoded sound** once more and let it finish. Wait for the
   new rendered view to complete. If Home was too early or late, repeat this step.
5. When **INTEGRATION GATES PASSED**, **Sticks: complete** and **Heard: confirmed**
   appear, tap **Export report** and attach `COH-NativeIntegration-*.json`.
   Send the JSON even if a check remains pending or fails, with what you saw
   or heard. If a real failure occurs, preserve its report before relaunching.

The scene performs repeated bounded rendering rounds; allow roughly 6–16 seconds
after a view change. A passing report includes native decode, actual UDP,
four signed scene-camera directions, settled released input, two actual view
sizes, recreation and active audio/UDP Home cancellation with fresh recovery.

If installing a later build reports a signature conflict, export any old
Integration Probe report and uninstall only **CoH Native Integration Probe**.
The debug probe's key is separate from the production launcher.
