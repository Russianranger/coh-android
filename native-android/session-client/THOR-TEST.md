# AYN Thor: one combined test for gates 19–21

Download
[CoH-Native-Session-Client-0.2.0-arm64.apk](https://chatgpt.com/api/library/files/libfile_1f69175230b08191b4c8ea65e369139c/download)
([GitHub artifact 11936304916](https://github.com/Russianranger/coh-android/actions/runs/38656997946/artifacts/11936304916)),
install it and open **CoH Native Session Client 0.2.0**. It installs alongside
the accepted 0.1.0 client as `org.coh.sessionclient.walk` and preserves
existing app data and reports. This is the same native application trajectory.
The conventional launcher/client and user imports remain separate. No server, account or asset
import is needed. The accepted gates 16–18 APK remains the rollback artifact.
Physical gates 19–21 were accepted on October 14, 2026 from the user's
successful combined check and [exact-APK report/receipt](../evidence/phases19-21/thor-acceptance-20261014.json).
This procedure remains the regression check for the unchanged 0.2.0 APK.

Package identity: **2,344,055 bytes**, SHA256
`2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92`.
Runtime source: `8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d`;
[build run 38656997946](https://github.com/Russianranger/coh-android/actions/runs/38656997946).
Source/host checks, the complete 1,585-file source trick audit, ARM64/x86_64
builds, lint, signatures and package integrity passed. **Physical gates 19–21
are accepted within the documented bounded offline scope.** Complete emulator
automation remains incomplete; its failures are retained independently.
The latest [emulator run](https://github.com/Russianranger/coh-android/actions/runs/38663997193)
passed startup/rendering and forward/backward movement, then failed its left
movement grounding predicate after prolonged travel in the selected scene.
Individual directional, interruption, reversal, quick-tap and release-settling
checks passed within earlier recorded partial scopes. Short manual input helps
keep this test on the authored support; report any unexpected grounding failure.

1. **Ground and collision:** wait for the Wretch, authored station floor and
   bench to appear. The initial forward direction points at the nearby bench.
   Move forward into it; the actor should stay on the floor and stop against
   the bench. While still pushing forward, add a very brief right or left tap
   to slide along it, then release as soon as the slide starts. Reset before
   trying the other direction. Pushing a wall may animate slowly in place;
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
The unchanged
[accepted 0.1.0 artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705)
and [original Thor procedure](THOR-TEST-16-18.md) remain the rollback path.

The earlier fully emulator-qualified and physically accepted rollback is
[CoH-Native-Session-Client-0.1.0-arm64.apk](https://chatgpt.com/api/library/files/libfile_bc1c1886923481919c358c8911bb9411/download)
with SHA256 `eb763d8c6e5354da06a336e8fe09a244a893755e82ef708ea1d2139dc17b8634`.
Its original [gates 16–18 procedure](THOR-TEST-16-18.md) remains unchanged.
