# Next Android presentation gate

The physical 0.5.0 presentation test passed with all 120 Android PixelCopy frames.
Advance directly to step 5 below: pinned actual CoH graphical startup.
The complete physical Atlas 0.4.4 create/save/restart/resume test also passed. The
user explicitly declined manual Stop/rerun and additional lifecycle testing
because of the long boot process; those checks remain unvalidated and do not
block this step. Implement a visible Wine display in a separate client
presentation mode. Preserve the accepted server package and its gates. Do not
repeat the accepted server/database diagnostics.

## Available foundation

- `android/guest/diagnostic.py`, `Diagnostic.start_wine()`, already starts
  Xtigervnc at 800x600x24 with RFB TCP disabled and a private mode-0600 Unix
  socket. Wine/FEX and the process-owner lifecycle are available.
- `android/native/client-probe.c` has the PE32 four-color WGL fixture that
  passed on Thor with Mesa llvmpipe. It currently exits too quickly to verify
  visible presentation, reconnects or sustained frame updates.
- The new separate `android/presentation` app supplies a bounded RFB decoder,
  SurfaceView and PixelCopy verification. Its physical Android result passed; see
  [the acceptance receipt](android-evidence/accepted-presentation-thor-20260930.json).
- The Atlas APK's game package excludes `CityOfHeroes.exe`.
  `tools/android/game/package_game_runtime.py`, `choose_files()`, deliberately
  packages the server/TestClient subset. A visible surface alone will not add
  the game executable.

## Smallest useful implementation

1. Prove that native Android can connect to the app-owned X server's private
   Unix socket. Resolve its real pathname through the existing PRoot bindings;
   do not assume the guest `/state/runtime/vnc.sock` pathname is directly usable
   by Java. Respect the existing short `PROOT_TMP_DIR` socket-path mechanism.
2. Add a bounded RFB decoder and Android SurfaceView. Keep transport local to
   the private socket, bound frame dimensions/message sizes, and integrate
   cancellation and decoder shutdown with foreground-service ownership.
3. Extend the graphics fixture into a bounded animation with changing frames
   and a unique session/frame identity. Verify pixels from an actual Android
   surface capture. Receiving RFB bytes or completing `SwapBuffers` is not
   evidence that a user can see current frames.
4. Include frame freshness, socket and surface lifecycle observations and
   automatic end-of-run cleanup in the support export. The immediate physical
   test is one foreground presentation run. Do not require manual Stop/rerun,
   app switching or screen lock before advancing; these remain unvalidated
   unless separately observed.
5. Once presentation passes, add the pinned graphical executable and matching
   dependencies through a separately receipted client package profile and
   attempt visible CoH startup. Continue directly to that test rather than
   another broad database test cycle.

Useful integration points are `DiagnosticRuntime.java` for the existing probe,
`AtlasGameService.java` for foreground operation ownership, and
`AtlasGameRuntime.java` for PRoot bindings and cleanup. Any presentation classes
must be included in the exact source/payload inventory used by
`tools/android/atlasgame/build_apk.py`, or its separately identified successor.

## Graphical executable and later scope

The qualified reference runtime is run `36088012664`, recorded in
`reference-runtime-evidence/build-36088012664.json`. Its `CityOfHeroes.exe` is
9,432,576 bytes with SHA-256
`81885ffa8838ef8759c3526fa1cc0bd44f9108e92698b29054256dd0eb97a0ca`.
Keep its matching Cg/CgGL, PhysX and runtime DLL identities. Do not silently
substitute a current external client.

The initial visible probe may use software rendering and must report that
renderer accurately. It does not establish game menus/world rendering, Cg
shader compatibility, hardware acceleration, physical controls, audio, or
simultaneous playable client/server. Those follow visible actual-client startup.
Use the existing bounded `client-bins` phase in `tools/generate_runtime_data.py`
only when a concrete client startup need is established.
