# AYN Thor: one combined test for gates 19–21

Install `CoH-Native-Session-Client-0.2.0-arm64.apk` and open **CoH Native Session
Client**. This is the same native application trajectory. The conventional
launcher/client and user imports remain separate. No server, account or asset
import is needed. The accepted gates 16–18 APK remains the rollback artifact.
Physical gates 19–21 require this new report and your observations.

1. **Ground and collision:** wait for the Wretch, authored station floor and
   bench to appear. The initial forward direction points at the nearby bench.
   Move forward into it; the actor should stay on the floor and stop against
   the bench. While still pushing forward, briefly add right or left input to
   slide along it, then release. Pushing a wall may animate slowly in place;
   that is the source minimum-rate behavior. Use short diagonal input because
   the selected floor is bounded. **Reset actor** returns to the supported spawn.
2. **Directional motion:** test forward, backward, left and right with short
   presses and releases. Forward should show RunPre then RunCycle and the
   authored stopping transition. Backward and lateral movement should use their
   own clips. Test quick taps, forward-to-back reversal and a short diagonal.
   The feet should remain on the floor. The far edge of the selected fixture
   has an explicit safety guard; it is not a new invisible wall or full map.
3. **Camera and recovery:** turn the right stick or drag, then release and
   confirm the camera stops. Move/turn, tap **Recreate**, and confirm actor/view
   state survives. Press Android Home while moving, release while away, return
   without force-stopping, and confirm input cleared while state persisted.
   Move again, use **Reset actor**, then **Export report**. Attach
   `COH-NativeSession-*.json` with visual/controller observations and a screenshot.
   Export a failure before restarting, since native failures remain sticky.

The floor currently uses the original client's grey fallback for the missing
`mono_station_floor_det` detail texture. Its authored base textures, geometry,
placement and collision are retained. This does not test full Atlas, jumping,
combat, account login, server replication or sustained frame-rate performance.
The accepted older physical report remains separate from this new qualification.
