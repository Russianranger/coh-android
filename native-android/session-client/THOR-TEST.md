# AYN Thor: one combined test for integrated gates 22–24

Test package: **CoH-Native-Session-Client-0.3.0-arm64.apk**.
Download: [CoH-Native-Session-Client-0.3.0-arm64.apk](https://chatgpt.com/api/library/files/libfile_7909bc8bae848191911760e360ae9884/download).
Package bytes/SHA256: **1,931,361 bytes**, SHA256 `75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639`.
Build/qualification run: [build/package run 38671972824](https://github.com/Russianranger/coh-android/actions/runs/38671972824); [exact-APK qualification retry 38673357918](https://github.com/Russianranger/coh-android/actions/runs/38673357918).
Build/lint, signatures, source/host/GPU checks and initial scoped Android execution
passed. The first Android run failed the strict Home pre-clear input witness;
the corrected driver is being qualified against these same APK bytes. The
[receipt](../evidence/phases22-24/qualification.json) records the separate results.
Physical gates 22–24 remain pending the actual new-package Thor report.

Install the new package over **CoH Native Session Client 0.2.0** and open
**CoH Native Session Client 0.3.0**. Version code 3 keeps the same
`org.coh.sessionclient.walk` application ID and stable public test signer, so the
update preserves that app's data/reports. Do not uninstall or clear data.
The separate accepted 0.1.0 app and the conventional launcher/client remain
available. No server, account or imported asset pack is required for this test.

This build integrates the indexed raw-asset loader, source map/group selection
and generic native renderer into the existing offline Wretch client. The bounded
Atlas station subset retains 25 source hierarchy nodes, three admitted model
endpoints and eight original raw assets. It contains an authored floor and ten
bench instances: four two-wide and six four-wide. Visual geometry and the
expanded 2,304-triangle collision scene use the same source placements.
The accepted source WALK and twelve directional locomotion clips remain active.

1. **Dynamic source scene and view distance:** wait for the floor, benches and
   Wretch to appear. At the reset spawn, tap **View distance** to alternate Near
   24 and Far 96, then return to Near. The selection should change from six to
   eleven instances and back at that spawn; farther benches should appear and
   disappear without resetting the actor or camera. Counts change with actor
   position, so use **Reset actor** before comparing. The floor support remains
   selected in either mode. Turn the camera to inspect both bench sizes and
   their materials. Report missing textures, flicker, incorrect tint, alignment
   or holes. The exported report records selection/cache diagnostics; repeated
   toggles should reuse the already decoded meshes and textures.
2. **Source movement, expanded collision and animations:** reset, move forward
   briefly into the nearby two-wide bench, and confirm the actor stays supported
   and is blocked. Add a very brief lateral input while pushing to check sliding,
   then release and reset. Test short forward/back/left/right presses, a quick
   tap, reversal and diagonal. The authored directional pre/cycle/stop transitions
   should remain visible. Other source benches can have steep or inclined
   collision surfaces; source WALK may climb or follow a slope there. They are
   not all flat vertical walls. Keep inputs short on this bounded floor and
   report unexpected falling, passing through geometry or visual/collision drift.
3. **Camera, Surface recovery and one exported report:** move and turn, switch
   view distance, then tap **Recreate**. Confirm actor/camera/view distance persist
   and source meshes/materials return. Press Android Home while moving, release
   controls while away, then return without force-stopping; confirm input clears
   and the actor does not continue moving. Move again, reset, and tap
   **Export report**. Attach `COH-NativeSession-*.json`, a Near/Far screenshot pair
   and brief observations about controls, collision and recreation. Export any
   failure before restarting because native failures remain sticky.

The material profile uses controlled neutral ambient lighting and no fog. It
does not reconstruct Atlas environment/light grids. The floor retains the
original client's grey fallback for missing `mono_station_floor_det`; the base
textures and source placements are genuine. This test does not cover the full
Atlas map, live login/server replication, jumping, combat or sustained FPS.

Gates 19–21 remain physically accepted from the user's October 14 report and
[acceptance receipt](../evidence/phases19-21/thor-acceptance-20261014.json), recorded
in commit `dc0639d0c289386c20e71554372fd6c13ed565d6`. The earlier emulator grounding
failure remains recorded separately. The unchanged
[0.2.0 instructions](THOR-TEST-19-21.md) preserve that accepted test procedure.
Its [accepted APK](https://chatgpt.com/api/library/files/libfile_1f69175230b08191b4c8ea65e369139c/download)
has SHA256 `2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92`.
Do not uninstall 0.3.0 to downgrade an app containing reports; export them first
and retain the accepted APK as a source/package rollback reference. The separate
[0.1.0 rollback APK](https://chatgpt.com/api/library/files/libfile_bc1c1886923481919c358c8911bb9411/download)
and [gates 16–18 procedure](THOR-TEST-16-18.md) remain available without replacing
the newer app.
