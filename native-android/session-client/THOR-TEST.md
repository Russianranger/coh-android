# AYN Thor: one combined test for gates 16–18

Install `CoH-Native-Session-Client-0.1.0-arm64.apk` and open **CoH Native
Session Client**. Your launcher and earlier probes can stay installed. No
server, account or asset import is required.

1. Wait for the Wretch and Atlas bench to appear together. Confirm the actor
   is visible, animated and correctly occluded where it overlaps the bench.
2. Use short forward presses on the left stick or D-pad. Confirm the actor
   moves, runs and returns through its run-ending animation to Ready after
   release. Test left, right and backward movement with short presses.
   Offline movement accelerates rapidly and passes through geometry;
   backward/strafe animation and normal walking collision are still pending.
3. Move the right stick or drag the scene to turn the persistent camera.
   Release and confirm it stops turning. The scene no longer recenters after
   a bounded preview round. **Reset actor** restores its starting pose/view.
4. Move and turn the view, then tap **Recreate**. Confirm the actor and camera
   keep their state after the new Surface appears. Press Android Home while
   moving, return without force-stopping, and confirm movement has stopped
   while the actor/view state is retained. Move again to prove fresh input.
5. Tap **Export report** and attach `COH-NativeSession-*.json`, including a
   screenshot if the actor or scene appears incorrect. Export a failure
   before restarting; the report retains sticky native failures.

This tests one offline native actor/world session, not account login, full
Atlas, server-authoritative character movement or sustained performance.
Physical acceptance awaits your new report and observations.
